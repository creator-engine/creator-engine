#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: bringup-container-openbao.sh [--plan|--apply|--destroy|--print-live-test-env]

Dry-run first single-node OpenBao container bring-up for Track B go-live.

Modes:
  --plan                 print the value-free plan; do not start containers
  --apply                start an ephemeral container and configure synthetic paths
  --destroy              remove the configured ephemeral container
  --print-live-test-env  print env exports for validator live tests

Safety:
  --apply requires OPENBAO_CONTAINER_CONFIRM=ephemeral.
  The workdir must be outside the repository because init output contains
  generated OpenBao root/unseal material for the ephemeral instance.
EOF
}

MODE="${1:---plan}"
case "$MODE" in
  --plan|--apply|--destroy|--print-live-test-env) ;;
  -h|--help) usage; exit 0 ;;
  *) usage; exit 64 ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/../../.." && pwd)"

OPENBAO_IMAGE="${OPENBAO_IMAGE:-openbao/openbao:2.5.5}"
OPENBAO_CONTAINER_NAME="${OPENBAO_CONTAINER_NAME:-ce-openbao-single-node}"
OPENBAO_CONTAINER_WORKDIR="${OPENBAO_CONTAINER_WORKDIR:-${TMPDIR:-/tmp}/ce-openbao-single-node}"
OPENBAO_CONTAINER_PORT="${OPENBAO_CONTAINER_PORT:-18200}"
OPENBAO_CONTAINER_CLUSTER_PORT="${OPENBAO_CONTAINER_CLUSTER_PORT:-18201}"
OPENBAO_CONTAINER_ADDR="${OPENBAO_CONTAINER_ADDR:-http://127.0.0.1:${OPENBAO_CONTAINER_PORT}}"
OPENBAO_DEV_IDS="${OPENBAO_DEV_IDS:-dev-1}"
OPENBAO_BAO_BIN="${OPENBAO_BAO_BIN:-bao}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

detect_engine() {
  if [[ -n "${OPENBAO_CONTAINER_ENGINE:-}" ]]; then
    printf '%s\n' "$OPENBAO_CONTAINER_ENGINE"
    return 0
  fi
  if command -v docker >/dev/null 2>&1; then
    printf 'docker\n'
    return 0
  fi
  if command -v podman >/dev/null 2>&1; then
    printf 'podman\n'
    return 0
  fi
  printf 'docker\n'
}

CONTAINER_ENGINE="$(detect_engine)"

realpath_portable() {
  "$PYTHON_BIN" - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).expanduser().resolve())
PY
}

WORKDIR_REAL="$(realpath_portable "$OPENBAO_CONTAINER_WORKDIR")"
REPO_REAL="$(realpath_portable "$REPO_ROOT")"
case "$WORKDIR_REAL" in
  "$REPO_REAL"|"$REPO_REAL"/*)
    echo "refusing workdir inside repository: $WORKDIR_REAL" >&2
    exit 78
    ;;
esac

BAO_IN_CONTAINER_ADDR="http://127.0.0.1:8200"
CONTAINER_MOUNT="/openbao-local"
INIT_JSON="$WORKDIR_REAL/init/openbao-init.json"
CONFIG_PATH="$WORKDIR_REAL/openbao.hcl"
POLICY_DIR="$WORKDIR_REAL/policies"
LIVE_ENV="$WORKDIR_REAL/live-test.env"

split_dev_ids() {
  tr ', ' '\n\n' <<<"$OPENBAO_DEV_IDS" | sed '/^$/d'
}

render_config() {
  cat <<EOF
ui = false
cluster_name = "ce-openbao-container"

api_addr = "$OPENBAO_CONTAINER_ADDR"
cluster_addr = "http://127.0.0.1:$OPENBAO_CONTAINER_CLUSTER_PORT"

storage "raft" {
  path    = "$CONTAINER_MOUNT/raft"
  node_id = "ce-openbao-container-1"
}

listener "tcp" {
  address         = "0.0.0.0:8200"
  cluster_address = "0.0.0.0:8201"
  tls_disable     = true
}

audit "file" "ce_container_audit" {
  description = "Creator Engine ephemeral container audit sink"
  options = {
    file_path = "$CONTAINER_MOUNT/logs/audit.log"
    mode      = "0600"
    format    = "json"
  }
}
EOF
}

render_broker_policy() {
  cat "$ROOT_DIR/ce-broker-policy.hcl.tmpl"
}

render_import_policy() {
  cat "$ROOT_DIR/ce-operator-import-policy.hcl.tmpl"
}

render_dev_policy() {
  local dev_id="$1"
  CE_DEV_ID="$dev_id" "$ROOT_DIR/render-dev-policy.sh"
}

run_container() {
  "$CONTAINER_ENGINE" "$@"
}

bao_container() {
  run_container exec \
    -e "BAO_ADDR=$BAO_IN_CONTAINER_ADDR" \
    -e "BAO_TOKEN=$ROOT_TOKEN" \
    "$OPENBAO_CONTAINER_NAME" \
    "$OPENBAO_BAO_BIN" "$@"
}

require_apply_confirmation() {
  if [[ "${OPENBAO_CONTAINER_CONFIRM:-}" != "ephemeral" ]]; then
    echo "--apply requires OPENBAO_CONTAINER_CONFIRM=ephemeral" >&2
    exit 78
  fi
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "missing PYTHON_BIN=$PYTHON_BIN" >&2
    exit 69
  fi
  if ! command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
    echo "missing container engine: $CONTAINER_ENGINE" >&2
    exit 69
  fi
  if ! command -v curl >/dev/null 2>&1; then
    echo "missing curl for local health checks" >&2
    exit 69
  fi
}

wait_for_openbao() {
  local health_url="$OPENBAO_CONTAINER_ADDR/v1/sys/health?standbyok=true&sealedcode=200&uninitcode=200"
  for _ in $(seq 1 120); do
    if curl -fsS "$health_url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  echo "OpenBao container did not become reachable at $OPENBAO_CONTAINER_ADDR" >&2
  run_container logs "$OPENBAO_CONTAINER_NAME" >&2 || true
  exit 70
}

json_field() {
  "$PYTHON_BIN" - "$1" "$2" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    value = json.load(fh)
for part in sys.argv[2].split("."):
    if part.endswith("]"):
        key, index = part[:-1].split("[", 1)
        value = value[key][int(index)]
    else:
        value = value[part]
print(value)
PY
}

write_live_env() {
  umask 077
  cat > "$LIVE_ENV" <<EOF
export CE_OPENBAO_BIN=$OPENBAO_BAO_BIN
export BAO_ADDR=$OPENBAO_CONTAINER_ADDR
export BAO_TOKEN=<ephemeral-root-token-from-$INIT_JSON>
export CE_OPENBAO_CONTAINER_NAME=$OPENBAO_CONTAINER_NAME
export CE_OPENBAO_CONTAINER_WORKDIR=$WORKDIR_REAL
EOF
}

plan() {
  cat <<EOF
OpenBao container go-live dry-run plan

Container:
  engine: $CONTAINER_ENGINE
  image: $OPENBAO_IMAGE
  name: $OPENBAO_CONTAINER_NAME
  address: $OPENBAO_CONTAINER_ADDR
  workdir: $WORKDIR_REAL

Planned local-only steps:
  1. render single-node raft config with file audit sink
  2. start container on 127.0.0.1 only
  3. run: bao operator init -key-shares=1 -key-threshold=1 -format=json
  4. store generated init output only in the external workdir with mode 0600
  5. run: bao operator unseal <generated-unseal-share>
  6. enable ce-kv kv-v2 and approle auth
  7. write ce-broker, ce-operator-import, and one policy per CE_DEV_ID
  8. create one AppRole per CE_DEV_ID with one-use short-TTL SecretIDs
  9. write synthetic canary metadata only; do not import real secrets

SecretIdentityBackend path map:
  ce-kv/data/devs/<dev>/runtime/github-pat -> field token
  ce-kv/data/devs/<dev>/runtime/claude-code-oauth-token -> field token
  ce-kv/data/forge/github-apps/creator-engine-shared/private-key -> field pem
  ce-transit/governance/signing/ce-root-v1 -> signing operation only

Dry-run status: no container commands executed and no secret values generated.
EOF
}

apply() {
  require_apply_confirmation
  umask 077
  mkdir -p "$WORKDIR_REAL/init" "$WORKDIR_REAL/raft" "$WORKDIR_REAL/logs" "$POLICY_DIR"
  render_config > "$CONFIG_PATH"
  render_broker_policy > "$POLICY_DIR/ce-broker.hcl"
  render_import_policy > "$POLICY_DIR/ce-operator-import.hcl"
  while IFS= read -r dev_id; do
    render_dev_policy "$dev_id" > "$POLICY_DIR/ce-${dev_id}-runtime.hcl"
  done < <(split_dev_ids)

  run_container rm -f "$OPENBAO_CONTAINER_NAME" >/dev/null 2>&1 || true
  run_container run -d \
    --name "$OPENBAO_CONTAINER_NAME" \
    --publish "127.0.0.1:${OPENBAO_CONTAINER_PORT}:8200" \
    --publish "127.0.0.1:${OPENBAO_CONTAINER_CLUSTER_PORT}:8201" \
    --volume "$WORKDIR_REAL:$CONTAINER_MOUNT" \
    "$OPENBAO_IMAGE" \
    server "-config=$CONTAINER_MOUNT/openbao.hcl" >/dev/null

  wait_for_openbao
  run_container exec \
    -e "BAO_ADDR=$BAO_IN_CONTAINER_ADDR" \
    "$OPENBAO_CONTAINER_NAME" \
    "$OPENBAO_BAO_BIN" operator init -key-shares=1 -key-threshold=1 -format=json > "$INIT_JSON"
  chmod 0600 "$INIT_JSON"

  UNSEAL_KEY="$(json_field "$INIT_JSON" "unseal_keys_b64[0]")"
  ROOT_TOKEN="$(json_field "$INIT_JSON" "root_token")"
  run_container exec \
    -e "BAO_ADDR=$BAO_IN_CONTAINER_ADDR" \
    "$OPENBAO_CONTAINER_NAME" \
    "$OPENBAO_BAO_BIN" operator unseal "$UNSEAL_KEY" >/dev/null
  unset UNSEAL_KEY

  if ! bao_container secrets enable -path=ce-kv kv-v2 >/dev/null 2>&1; then
    bao_container secrets tune -description="Creator Engine runtime KV" ce-kv/ >/dev/null
  fi
  if ! bao_container auth enable approle >/dev/null 2>&1; then
    bao_container auth tune approle/ >/dev/null
  fi
  bao_container policy write ce-broker "$CONTAINER_MOUNT/policies/ce-broker.hcl" >/dev/null
  bao_container policy write ce-operator-import "$CONTAINER_MOUNT/policies/ce-operator-import.hcl" >/dev/null

  while IFS= read -r dev_id; do
    policy_name="ce-${dev_id}-runtime"
    role_name="ce-${dev_id}"
    bao_container policy write "$policy_name" "$CONTAINER_MOUNT/policies/${policy_name}.hcl" >/dev/null
    bao_container write "auth/approle/role/${role_name}" \
      "token_policies=${policy_name}" \
      token_ttl=10m \
      token_max_ttl=30m \
      secret_id_ttl=10m \
      secret_id_num_uses=1 >/dev/null
    bao_container kv put "ce-kv/devs/${dev_id}/runtime/restore-canary" ok=synthetic >/dev/null
  done < <(split_dev_ids)

  bao_container write auth/approle/role/ce-broker \
    token_policies=ce-broker \
    token_ttl=10m \
    token_max_ttl=30m \
    secret_id_ttl=10m \
    secret_id_num_uses=1 >/dev/null

  write_live_env
  chmod 0600 "$LIVE_ENV"
  echo "OpenBao ephemeral container is ready at $OPENBAO_CONTAINER_ADDR"
  echo "Init material is in $INIT_JSON; keep it outside git and destroy this instance after testing."
  echo "Live-test env template written to $LIVE_ENV"
}

destroy() {
  if ! command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
    echo "missing container engine: $CONTAINER_ENGINE" >&2
    exit 69
  fi
  run_container rm -f "$OPENBAO_CONTAINER_NAME" >/dev/null 2>&1 || true
  echo "Removed container $OPENBAO_CONTAINER_NAME. Remove $WORKDIR_REAL manually after preserving any value-free evidence you need."
}

print_live_test_env() {
  cat <<EOF
export CE_OPENBAO_BIN=$OPENBAO_BAO_BIN
export BAO_ADDR=$OPENBAO_CONTAINER_ADDR
export BAO_TOKEN=<ephemeral-root-token-from-$INIT_JSON>
export CE_OPENBAO_CONTAINER_NAME=$OPENBAO_CONTAINER_NAME
export CE_OPENBAO_CONTAINER_WORKDIR=$WORKDIR_REAL

# Run from the repository root after --apply:
#   cd validators
#   python -m pytest tests/integration/test_openbao_p3_live.py tests/integration/test_openbao_golive_restore_drill_live.py
EOF
}

case "$MODE" in
  --plan) plan ;;
  --apply) apply ;;
  --destroy) destroy ;;
  --print-live-test-env) print_live_test_env ;;
esac
