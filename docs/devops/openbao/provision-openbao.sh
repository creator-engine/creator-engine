#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---plan}"
if [[ "$MODE" != "--plan" && "$MODE" != "--apply" && "$MODE" != "--render-config" ]]; then
  echo "usage: $0 [--plan|--apply|--render-config]" >&2
  exit 64
fi

OPENBAO_USER="${OPENBAO_USER:-openbao}"
OPENBAO_GROUP="${OPENBAO_GROUP:-openbao}"
OPENBAO_CLUSTER_NAME="${OPENBAO_CLUSTER_NAME:-ce-openbao-prod}"
OPENBAO_NODE_ID="${OPENBAO_NODE_ID:-ce-openbao-hetzner-1}"
OPENBAO_DATA_DIR="${OPENBAO_DATA_DIR:-/var/lib/openbao}"
OPENBAO_RAFT_PATH="${OPENBAO_RAFT_PATH:-/var/lib/openbao/raft}"
OPENBAO_CONFIG_DIR="${OPENBAO_CONFIG_DIR:-/etc/openbao}"
OPENBAO_CONFIG_PATH="${OPENBAO_CONFIG_PATH:-/etc/openbao/openbao.hcl}"
OPENBAO_SERVICE_PATH="${OPENBAO_SERVICE_PATH:-/etc/systemd/system/openbao.service}"
OPENBAO_AUDIT_LOG="${OPENBAO_AUDIT_LOG:-/var/log/openbao/audit.log}"
OPENBAO_TLS_CERT_FILE="${OPENBAO_TLS_CERT_FILE:-/etc/openbao/tls/openbao.crt}"
OPENBAO_TLS_KEY_FILE="${OPENBAO_TLS_KEY_FILE:-/etc/openbao/tls/openbao.key}"
OPENBAO_TLS_CLIENT_CA_FILE="${OPENBAO_TLS_CLIENT_CA_FILE:-/etc/openbao/tls/ca.crt}"
OPENBAO_TAILNET_HOSTNAME="${OPENBAO_TAILNET_HOSTNAME:?set the tailnet DNS name, for example openbao.<tailnet>.ts.net}"
OPENBAO_TAILNET_BIND_ADDR="${OPENBAO_TAILNET_BIND_ADDR:?set the Tailscale bind address, for example 100.x.y.z}"
OPENBAO_API_PORT="${OPENBAO_API_PORT:-8200}"
OPENBAO_CLUSTER_PORT="${OPENBAO_CLUSTER_PORT:-8201}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_TEMPLATE="${SERVICE_TEMPLATE:-$ROOT_DIR/openbao.service}"

require_tailnet_bind() {
  case "$OPENBAO_TAILNET_BIND_ADDR" in
    0.0.0.0|::|"[::]"|"*"|"")
      echo "refusing public OpenBao listener address: $OPENBAO_TAILNET_BIND_ADDR" >&2
      exit 78
      ;;
    100.*|fd7a:*)
      return 0
      ;;
    *)
      if [[ "${OPENBAO_ALLOW_NON_TAILNET_FOR_TEST:-}" == "1" ]]; then
        return 0
      fi
      echo "refusing non-tailnet OpenBao bind address: $OPENBAO_TAILNET_BIND_ADDR" >&2
      echo "set OPENBAO_ALLOW_NON_TAILNET_FOR_TEST=1 only for disposable local drills" >&2
      exit 78
      ;;
  esac
}

run() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  if [[ "$MODE" == "--apply" ]]; then
    "$@"
  fi
}

require_apply_root() {
  if [[ "$MODE" == "--apply" && "$(id -u)" != "0" ]]; then
    echo "--apply requires root/sudo on the Hetzner VPS for user, directory, and systemd setup" >&2
    exit 77
  fi
}

render_config() {
  cat <<EOF
ui = false
cluster_name = "$OPENBAO_CLUSTER_NAME"

api_addr = "https://$OPENBAO_TAILNET_HOSTNAME:$OPENBAO_API_PORT"
cluster_addr = "https://$OPENBAO_TAILNET_HOSTNAME:$OPENBAO_CLUSTER_PORT"

storage "raft" {
  path    = "$OPENBAO_RAFT_PATH"
  node_id = "$OPENBAO_NODE_ID"
}

listener "tcp" {
  address         = "$OPENBAO_TAILNET_BIND_ADDR:$OPENBAO_API_PORT"
  cluster_address = "$OPENBAO_TAILNET_BIND_ADDR:$OPENBAO_CLUSTER_PORT"

  tls_disable      = false
  tls_cert_file    = "$OPENBAO_TLS_CERT_FILE"
  tls_key_file     = "$OPENBAO_TLS_KEY_FILE"
  tls_client_ca_file = "$OPENBAO_TLS_CLIENT_CA_FILE"
}

audit "file" "ce_audit" {
  description = "Creator Engine production audit sink; OpenBao must fail closed if writes fail"
  options {
    file_path = "$OPENBAO_AUDIT_LOG"
    mode      = "0600"
    format    = "json"
  }
}
EOF
}

require_tailnet_bind
if [[ "$MODE" == "--render-config" ]]; then
  render_config
  exit 0
fi
require_apply_root

if ! id -u "$OPENBAO_USER" >/dev/null 2>&1; then
  run useradd --system --home "$OPENBAO_DATA_DIR" --shell /usr/sbin/nologin "$OPENBAO_USER"
fi

run install -d -o "$OPENBAO_USER" -g "$OPENBAO_GROUP" -m 0700 "$OPENBAO_DATA_DIR" "$OPENBAO_RAFT_PATH"
run install -d -o root -g "$OPENBAO_GROUP" -m 0750 "$OPENBAO_CONFIG_DIR" "$OPENBAO_CONFIG_DIR/tls"
run install -d -o "$OPENBAO_USER" -g "$OPENBAO_GROUP" -m 0700 "$(dirname "$OPENBAO_AUDIT_LOG")"

if [[ "$MODE" == "--apply" ]]; then
  tmp_config="$(mktemp)"
  render_config > "$tmp_config"
  install -o root -g "$OPENBAO_GROUP" -m 0640 "$tmp_config" "$OPENBAO_CONFIG_PATH"
  rm -f "$tmp_config"
  install -o root -g root -m 0644 "$SERVICE_TEMPLATE" "$OPENBAO_SERVICE_PATH"
  systemctl daemon-reload
  systemctl enable openbao.service
else
  render_config
  echo "# plan only: rerun with --apply under sudo/root on the VPS to write $OPENBAO_CONFIG_PATH and $OPENBAO_SERVICE_PATH"
fi

echo "OpenBao host artifacts staged. Operator init/unseal and secret-zero injection are intentionally not performed by this script."
