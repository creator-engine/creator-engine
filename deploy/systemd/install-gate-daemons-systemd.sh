#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: install-gate-daemons-systemd.sh [--system] [--repo-root PATH] [--env-file PATH] [--egress-broker-env-file PATH] [--egress-self-review-env-file PATH] [--model-drift-env-file PATH] [--unit-dir PATH] [--no-start]

Installs Creator Engine gate daemon systemd units from this source checkout.

Defaults:
  user units:   ~/.config/systemd/user
  system units: /etc/systemd/system
  gate env file:
    ~/.config/creator-engine/gate-daemons.env (user)
    /etc/creator-engine/gate-daemons.env (--system)
  egress broker env file:
    ~/.config/creator-engine/ce-egress-broker.env (user)
    /etc/creator-engine/ce-egress-broker.env (--system)
  egress self-review env file:
    ~/.config/creator-engine/ce-egress-self-review.env (user)
    /etc/creator-engine/ce-egress-self-review.env (--system)
  model drift env file (system watcher only):
    /etc/creator-engine/ce-model-drift.env (--system)

The script copies rendered units, runs daemon-reload, enables the services, and
starts them unless --no-start is supplied. It does not create or overwrite the
secret env file; create it first with CE_GATE_REPO, CE_GATE_AUTHORIZED_REVIEWERS,
plus GH_TOKEN and/or CE_PICKUP_TOKEN as needed. Review pickup can also use the
OpenBao token supplier when CE_PICKUP_TOKEN_SECRET_TARGET_REF and the matching
SecretRef variables are present in the gate env file.

The self-push broker env file must also name CE_BROKER_HOME, an existing
controller-managed stable checkout, plus explicit numeric
CE_EGRESS_BROKER_EXPECTED_PEER_UID and CE_EGRESS_BROKER_EXPECTED_PEER_GID.
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

read_env_file_value() {
  local file="$1"
  local key="$2"
  local line=""
  local value=""
  local found=0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    if [[ "$line" == "$key="* ]]; then
      value="${line#*=}"
      found=1
    fi
  done < "$file"
  [[ "$found" -eq 1 ]] || return 1
  printf '%s\n' "$value"
}

scope="user"
repo_root=""
unit_dir=""
env_file=""
egress_broker_env_file=""
egress_self_review_env_file=""
model_drift_env_file=""
start_services=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --system)
      scope="system"
      shift
      ;;
    --repo-root)
      repo_root="${2:?--repo-root requires a path}"
      shift 2
      ;;
    --unit-dir)
      unit_dir="${2:?--unit-dir requires a path}"
      shift 2
      ;;
    --env-file)
      env_file="${2:?--env-file requires a path}"
      shift 2
      ;;
    --egress-broker-env-file)
      egress_broker_env_file="${2:?--egress-broker-env-file requires a path}"
      shift 2
      ;;
    --egress-self-review-env-file)
      egress_self_review_env_file="${2:?--egress-self-review-env-file requires a path}"
      shift 2
      ;;
    --model-drift-env-file)
      model_drift_env_file="${2:?--model-drift-env-file requires a path}"
      shift 2
      ;;
    --no-start)
      start_services=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$repo_root" ]]; then
  repo_root="$(cd -- "$script_dir/../.." && pwd)"
else
  repo_root="$(cd -- "$repo_root" && pwd)"
fi

if [[ "$scope" == "system" ]]; then
  unit_dir="${unit_dir:-/etc/systemd/system}"
  env_file="${env_file:-/etc/creator-engine/gate-daemons.env}"
  egress_broker_env_file="${egress_broker_env_file:-/etc/creator-engine/ce-egress-broker.env}"
  egress_self_review_env_file="${egress_self_review_env_file:-/etc/creator-engine/ce-egress-self-review.env}"
  model_drift_env_file="${model_drift_env_file:-/etc/creator-engine/ce-model-drift.env}"
  systemctl_cmd=(systemctl)
else
  unit_dir="${unit_dir:-$HOME/.config/systemd/user}"
  env_file="${env_file:-$HOME/.config/creator-engine/gate-daemons.env}"
  egress_broker_env_file="${egress_broker_env_file:-$HOME/.config/creator-engine/ce-egress-broker.env}"
  egress_self_review_env_file="${egress_self_review_env_file:-$HOME/.config/creator-engine/ce-egress-self-review.env}"
  model_drift_env_file="${model_drift_env_file:-}"
  systemctl_cmd=(systemctl --user)
fi

services=(
  ce-belt-daemon.service
  ce-integrator-daemon.service
  ce-review-pickup-daemon.service
  ce-ratifier-queue.service
  # ce-egress-broker.service uses its own EnvironmentFile (ce-egress-broker.env) which must
  # include BAO_ADDR/VAULT_ADDR, BAO_CACERT/VAULT_CACERT, BROKER_APPROLE_ROLE_ID, and
  # BROKER_APPROLE_SECRET_ID for vault-backed seats; create that file before starting.
  ce-egress-broker.socket
  ce-egress-broker.service
  # ce-egress-self-review.service uses its own EnvironmentFile (ce-egress-self-review.env)
  # which must include the same BAO_ADDR/VAULT_ADDR, BAO_CACERT/VAULT_CACERT,
  # BROKER_APPROLE_ROLE_ID, and BROKER_APPROLE_SECRET_ID for vault-backed seats; create that
  # file before starting.
  ce-egress-self-review.socket
  ce-egress-self-review.service
)

if [[ "$scope" == "system" ]]; then
  services+=(ce-model-drift-watcher.service)
fi

echo "scope: $scope"
echo "repo root: $repo_root"
echo "unit dir: $unit_dir"
echo "gate env file: $env_file"
echo "egress broker env file: $egress_broker_env_file"
echo "egress self-review env file: $egress_self_review_env_file"
if [[ "$scope" == "system" ]]; then
  echo "model drift env file: $model_drift_env_file"
else
  echo "skipped: ce-model-drift-watcher.service (system-only: fixed service identity, docker group, protected /var/lib state/inbox)"
fi

if [[ ! -d "$repo_root/.git" ]]; then
  echo "ERROR: repo root does not look like a git checkout: $repo_root" >&2
  exit 1
fi

if [[ ! -x "$repo_root/.venv/bin/python" ]]; then
  echo "ERROR: expected executable virtualenv python at $repo_root/.venv/bin/python" >&2
  exit 1
fi

if [[ ! -f "$env_file" ]]; then
  cat >&2 <<EOF
ERROR: env file is missing: $env_file
Create it before starting the services. Required:
  CE_GATE_REPO=owner/name
  CE_GATE_AUTHORIZED_REVIEWERS=reviewer-login[,reviewer-login...]
  CE_BELT_IDENTITY=ce-dev-4
  GH_TOKEN=...
Optional for review pickup:
  CE_PICKUP_TOKEN=...
  BAO_ADDR=...
  BAO_TOKEN=...
  BAO_CACERT=...
  CE_OPENBAO_ALLOWED_REFS=path=forge/reviewer/gh-token;field=token;purpose=review-pickup-token;owner_ref=controller:reviewer;policy_sha=ab4769424e205eb53ee31d61da0c386ae9a418682e9bc0a6636f82de708c8982,path=forge/approval-capability/wall;field=signing_secret;purpose=approval-capability-wall;owner_ref=controller:integrator;policy_sha=<operator-supplied-64-hex>
  CE_PICKUP_TOKEN_SECRET_TARGET_REF=file:/run/user/<uid>/creator-engine/review-pickup-token
  CE_PICKUP_TOKEN_SECRET_REF_POLICY_SHA=ab4769424e205eb53ee31d61da0c386ae9a418682e9bc0a6636f82de708c8982
Optional approval-wall OpenBao readiness (operator-managed placeholders only;
this does not authorize a live env edit, install, reload/restart, marker mint,
wall-state edit, or arming):
  BAO_ADDR=<openbao-url>
  BAO_TOKEN=<operator-supplied-runtime-token>
  BAO_CACERT=<optional-ca-cert-path>
  CE_APPROVAL_WALL_SECRET_BACKEND=openbao
  CE_APPROVAL_WALL_SECRET_MOUNT=ce-kv
  CE_APPROVAL_WALL_SECRET_PATH=forge/approval-capability/wall
  CE_APPROVAL_WALL_SECRET_FIELD=signing_secret
  CE_APPROVAL_WALL_SECRET_PURPOSE=approval-capability-wall
  CE_APPROVAL_WALL_SECRET_OWNER_REF=controller:integrator
  CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA=<operator-supplied-64-hex>
  CE_APPROVAL_WALL_SECRET_TARGET_REF=file:/run/user/<uid>/creator-engine/approval-wall-secret
  CE_APPROVAL_WALL_POLICY_SHA=<operator-supplied-policy-sha-or-id>
  BAO_TOKEN comes only from the approved runtime secret channel and is never committed.
  Policy values are runtime inputs; do not invent or derive them. The approval-wall
  signing-secret path is distinct from the review-pickup reviewer-token path.
  When both are enabled, the single CE_OPENBAO_ALLOWED_REFS assignment above
  carries both refs; do not add a second assignment that would overwrite the
  reviewer-token ref.
  Target refs must use file: delivery on tmpfs under /run, or an Operator-verified
  %t equivalent; never persistent storage or env:. Delivery is revoke-after-read:
  partial config, backend failure, empty material, or disallowed refs fail closed
  without environment fallback.
  CE_APPROVAL_CAPABILITY_SECRET is bootstrap fallback only via the existing
  --approval-wall-secret-env default when no backend is configured. It is not the
  production OpenBao path. This repository change neither supplies the bootstrap secret nor performs a runtime transition, so it does not arm the wall.
  If an Operator supplies the bootstrap secret through CE_APPROVAL_CAPABILITY_SECRET
  with no backend configured, the existing runtime arms the wall and persists wall state
  as armed: true. Environment custody is fork-readable/fork-forge unsafe compared
  with scoped OpenBao. A configured backend that is partial, fails, returns empty
  material, or has an invalid target refuses fallback.
Optional for work-pickup belt:
  CE_BELT_INTERVAL_SECONDS=120
  CE_BELT_LABELS=enhancement
  CE_PICKUP_TOKEN=...
Required for the ratifier proposal queue:
  CE_RATIFIER_QUEUE_CANDIDATES_PATH=/owner-only/path/candidates.json
Optional for the ratifier proposal queue:
  CE_RATIFIER_QUEUE_STATE_PATH=/owner-only/path/state.json
  CE_RATIFIER_QUEUE_INTERVAL_SECONDS=120
EOF
  exit 1
fi

if [[ ! -f "$egress_broker_env_file" ]]; then
  cat >&2 <<EOF
ERROR: egress broker env file is missing: $egress_broker_env_file
Create it before starting the services. Required:
  CE_BROKER_HOME=<controller-managed-stable-checkout>
  CE_EGRESS_BROKER_SOCKET=...
  CE_EGRESS_BROKER_SEAT=...
  CE_EGRESS_BROKER_EXPECTED_PEER_UID=...
  CE_EGRESS_BROKER_EXPECTED_PEER_GID=...
  CE_EGRESS_BROKER_REPO=...
  CE_EGRESS_BROKER_CONFIG=...
For vault-backed seats also include BAO_ADDR/VAULT_ADDR, BAO_CACERT/VAULT_CACERT,
BROKER_APPROLE_ROLE_ID, and BROKER_APPROLE_SECRET_ID.
EOF
  exit 1
fi

if [[ ! -f "$egress_self_review_env_file" ]]; then
  cat >&2 <<EOF
ERROR: egress self-review env file is missing: $egress_self_review_env_file
Create it before starting the services. Required:
  CE_EGRESS_SELF_REVIEW_SOCKET=...
  CE_EGRESS_SELF_REVIEW_CONFIG=...
  CE_EGRESS_RUN_MODE=dev
For vault-backed seats also include BAO_ADDR/VAULT_ADDR, BAO_CACERT/VAULT_CACERT,
BROKER_APPROLE_ROLE_ID, and BROKER_APPROLE_SECRET_ID.
EOF
  exit 1
fi

broker_home="$(read_env_file_value "$egress_broker_env_file" CE_BROKER_HOME || true)"
expected_peer_uid="$(read_env_file_value "$egress_broker_env_file" CE_EGRESS_BROKER_EXPECTED_PEER_UID || true)"
expected_peer_gid="$(read_env_file_value "$egress_broker_env_file" CE_EGRESS_BROKER_EXPECTED_PEER_GID || true)"

[[ -n "$broker_home" ]] || fail "CE_BROKER_HOME is required in $egress_broker_env_file"
[[ -n "$expected_peer_uid" ]] || fail "CE_EGRESS_BROKER_EXPECTED_PEER_UID is required in $egress_broker_env_file"
[[ -n "$expected_peer_gid" ]] || fail "CE_EGRESS_BROKER_EXPECTED_PEER_GID is required in $egress_broker_env_file"
[[ "$broker_home" == /* ]] || fail "CE_BROKER_HOME must be an absolute path"
case "$broker_home" in
  /workspace/creator-engine|/workspace/creator-engine/*|/home/ce-dev-*|/home/ce-dev-*/*|/home/cedev*|/home/cedev*/*)
    fail "CE_BROKER_HOME looks like a mutable seat checkout: $broker_home"
    ;;
esac
[[ "$expected_peer_uid" =~ ^[0-9]+(,[0-9]+)*$ ]] ||
  fail "CE_EGRESS_BROKER_EXPECTED_PEER_UID must contain only numeric ids"
[[ "$expected_peer_gid" =~ ^[0-9]+(,[0-9]+)*$ ]] ||
  fail "CE_EGRESS_BROKER_EXPECTED_PEER_GID must contain only numeric ids"
[[ -d "$broker_home" ]] || fail "stable broker checkout is missing: $broker_home"
[[ -d "$broker_home/.git" || -f "$broker_home/.git" ]] ||
  fail "CE_BROKER_HOME is not a git checkout: $broker_home"
[[ -f "$broker_home/tools/egress-broker/ce_egress_self_push_broker.py" ]] ||
  fail "stable self-push broker entrypoint is missing under CE_BROKER_HOME: $broker_home"

# EnvironmentFile contents may include credential material. Keep the existing
# file and values intact while enforcing an owner-only mode.
if [[ "$scope" == "system" ]]; then
  [[ "$EUID" -eq 0 ]] || fail "--system requires root to preserve unit and config ownership"
  chown root:root "$egress_broker_env_file"
fi
chmod 0600 "$egress_broker_env_file"

legacy_egress_unit="$unit_dir/ce-egress-broker-dev3.service"
if [[ -L "$legacy_egress_unit" ]]; then
  fail "refusing symlinked legacy egress broker unit: $legacy_egress_unit"
fi
if [[ -f "$legacy_egress_unit" ]]; then
  if ! grep -q -- 'ce_egress_self_push_broker.py' "$legacy_egress_unit" ||
     ! grep -q -- '--socket' "$legacy_egress_unit"; then
    fail "refusing unknown legacy egress broker unit shape: $legacy_egress_unit"
  fi
  echo "running: ${systemctl_cmd[*]} disable --now ce-egress-broker-dev3.service"
  "${systemctl_cmd[@]}" disable --now ce-egress-broker-dev3.service
  rm -f -- "$legacy_egress_unit"
  echo "migrated: ce-egress-broker-dev3.service -> ce-egress-broker.socket + ce-egress-broker.service"
fi

# This observer is intentionally isolated from the credential-bearing gate
# environment. Its managed file contains only fixed, non-secret paths and it
# is system-only because it requires a fixed service account, Docker group,
# and protected /var/lib state and controller-inbox directories.
ensure_model_drift_directory() {
  local path="$1"
  case "$path" in
    /var/lib/creator-engine/model-drift|/var/lib/creator-engine/controller-inbox)
      ;;
    *)
      echo "ERROR: refusing unsafe model drift runtime path: $path" >&2
      exit 1
      ;;
  esac
  local component=""
  for component in /var /var/lib /var/lib/creator-engine "$path"; do
    if [[ -L "$component" ]]; then
      echo "ERROR: refusing symlinked model drift runtime path: $component" >&2
      exit 1
    fi
  done
  install -d -o creator-engine -g creator-engine -m 0700 "$path"
}

if [[ "$scope" == "system" && ( -L "$model_drift_env_file" || -L "$(dirname -- "$model_drift_env_file")" ) ]]; then
  echo "ERROR: refusing symlinked model drift env path: $model_drift_env_file" >&2
  exit 1
fi

if [[ "$scope" == "system" && ! -f "$model_drift_env_file" ]]; then
  install -d -o creator-engine -g creator-engine -m 0700 "$(dirname -- "$model_drift_env_file")"
  umask 077
  cat > "$model_drift_env_file" <<EOF
CE_MODEL_DRIFT_CANON=$repo_root/surfaces/model-canon.yaml
CE_MODEL_DRIFT_STATE_PATH=/var/lib/creator-engine/model-drift/state.json
CE_MODEL_DRIFT_LEASE_ROOT=/var/lib/creator-engine/model-drift/leases
CE_MODEL_DRIFT_INBOX_PATH=/var/lib/creator-engine/controller-inbox/model-drift.ndjson
CE_MODEL_DRIFT_CADENCE_SECONDS=60
EOF
  chmod 0600 "$model_drift_env_file"
fi

if [[ "$scope" == "system" ]]; then
  ensure_model_drift_directory /var/lib/creator-engine/model-drift
  ensure_model_drift_directory /var/lib/creator-engine/controller-inbox
  if [[ -L /var/lib/creator-engine/controller-inbox/model-drift.ndjson ]]; then
    echo "ERROR: refusing symlinked model drift inbox file" >&2
    exit 1
  fi
  if [[ ! -e /var/lib/creator-engine/controller-inbox/model-drift.ndjson ]]; then
    install -o creator-engine -g creator-engine -m 0600 /dev/null /var/lib/creator-engine/controller-inbox/model-drift.ndjson
  else
    chown creator-engine:creator-engine /var/lib/creator-engine/controller-inbox/model-drift.ndjson
    chmod 0600 /var/lib/creator-engine/controller-inbox/model-drift.ndjson
  fi
fi

mkdir -p "$unit_dir"

render_unit() {
  local src="$1"
  local dst="$2"
  local env_path="${3:-}"
  local unit_name
  local tmp
  local rendered_repo_root
  local rendered_env_file
  local rendered_broker_home
  unit_name="$(basename -- "$src")"
  rendered_repo_root="$(printf '%s' "$repo_root" | sed 's/[&#]/\\&/g')"
  rendered_env_file="$(printf '%s' "$env_path" | sed 's/[&#]/\\&/g')"
  rendered_broker_home="$(printf '%s' "$broker_home" | sed 's/[&#]/\\&/g')"
  tmp="$(mktemp "$unit_dir/.ce-systemd-unit.XXXXXX")"
  if [[ "$unit_name" == "ce-egress-self-review.service" && -n "$rendered_env_file" ]]; then
    sed \
      -e "s#^EnvironmentFile=.*#EnvironmentFile=$rendered_env_file#g" \
      "$src" > "$tmp"
  elif [[ "$unit_name" == "ce-egress-self-review.service" ]]; then
    cat "$src" > "$tmp"
  elif [[ "$unit_name" == "ce-egress-broker.service" && -n "$rendered_env_file" ]]; then
    sed \
      -e "s#/opt/ce-broker/creator-engine#$rendered_broker_home#g" \
      -e "s#^EnvironmentFile=.*#EnvironmentFile=$rendered_env_file#g" \
      "$src" > "$tmp"
  elif [[ -n "$rendered_env_file" ]]; then
    sed \
      -e "s#^WorkingDirectory=.*#WorkingDirectory=$rendered_repo_root#g" \
      -e "s#^EnvironmentFile=.*#EnvironmentFile=$rendered_env_file#g" \
      "$src" > "$tmp"
  else
    sed \
      -e "s#^WorkingDirectory=.*#WorkingDirectory=$rendered_repo_root#g" \
      "$src" > "$tmp"
  fi
  if [[ -f "$dst" ]] && cmp -s "$tmp" "$dst"; then
    echo "unchanged: $dst"
    rm -f "$tmp"
  else
    install -m 0644 "$tmp" "$dst"
    echo "installed: $dst"
    rm -f "$tmp"
  fi
}

env_file_for_service() {
  case "$1" in
    ce-egress-broker.service)
      printf '%s\n' "$egress_broker_env_file"
      ;;
    ce-egress-self-review.service)
      printf '%s\n' "$egress_self_review_env_file"
      ;;
    ce-model-drift-watcher.service)
      printf '%s\n' "$model_drift_env_file"
      ;;
    *.service)
      printf '%s\n' "$env_file"
      ;;
    *)
      printf '\n'
      ;;
  esac
}

for service in "${services[@]}"; do
  render_unit "$script_dir/$service" "$unit_dir/$service" "$(env_file_for_service "$service")"
done

echo "running: ${systemctl_cmd[*]} daemon-reload"
"${systemctl_cmd[@]}" daemon-reload

for service in "${services[@]}"; do
  echo "running: ${systemctl_cmd[*]} enable $service"
  "${systemctl_cmd[@]}" enable "$service"
done

if [[ "$start_services" -eq 1 ]]; then
  for service in "${services[@]}"; do
    echo "running: ${systemctl_cmd[*]} start $service"
    "${systemctl_cmd[@]}" start "$service"
  done
else
  echo "skipped service start (--no-start)"
fi
