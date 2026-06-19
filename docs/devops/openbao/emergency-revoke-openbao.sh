#!/usr/bin/env bash
set -euo pipefail

BAO_BIN="${BAO_BIN:-bao}"
MODE="${1:-}"
ACTION="${2:-}"

usage() {
  cat >&2 <<'EOF'
usage: emergency-revoke-openbao.sh --plan|--execute lease|lease-prefix|approle|seal

Required common environment:
  CE_DEV_ID                  per-dev identity, for example dev-1

Action-specific environment:
  lease:        OPENBAO_LEASE_ID
  lease-prefix: OPENBAO_LEASE_PREFIX
  approle:      OPENBAO_APPROLE_ROLE (default ce-${CE_DEV_ID}), OPENBAO_SECRET_ID_ACCESSOR, optional OPENBAO_TOKEN_ACCESSOR
  seal:         OPENBAO_EMERGENCY_REASON
EOF
}

if [[ "$MODE" != "--plan" && "$MODE" != "--execute" ]]; then
  usage
  exit 64
fi
if [[ -z "$ACTION" ]]; then
  usage
  exit 64
fi

CE_DEV_ID="${CE_DEV_ID:?set CE_DEV_ID to bind the revocation to a per-dev identity}"

run() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  if [[ "$MODE" == "--execute" ]]; then
    "$@"
  fi
}

echo "emergency action=$ACTION dev_identity=$CE_DEV_ID mode=$MODE"

case "$ACTION" in
  lease)
    : "${OPENBAO_LEASE_ID:?set OPENBAO_LEASE_ID}"
    run "$BAO_BIN" lease revoke "$OPENBAO_LEASE_ID"
    ;;
  lease-prefix)
    : "${OPENBAO_LEASE_PREFIX:?set OPENBAO_LEASE_PREFIX}"
    run "$BAO_BIN" lease revoke -prefix "$OPENBAO_LEASE_PREFIX"
    ;;
  approle)
    OPENBAO_APPROLE_ROLE="${OPENBAO_APPROLE_ROLE:-ce-${CE_DEV_ID}}"
    : "${OPENBAO_SECRET_ID_ACCESSOR:?set OPENBAO_SECRET_ID_ACCESSOR}"
    run "$BAO_BIN" write "auth/approle/role/$OPENBAO_APPROLE_ROLE/secret-id-accessor/destroy" "secret_id_accessor=$OPENBAO_SECRET_ID_ACCESSOR"
    if [[ -n "${OPENBAO_TOKEN_ACCESSOR:-}" ]]; then
      run "$BAO_BIN" token revoke -accessor "$OPENBAO_TOKEN_ACCESSOR"
    fi
    ;;
  seal)
    : "${OPENBAO_EMERGENCY_REASON:?set OPENBAO_EMERGENCY_REASON for the incident log}"
    run "$BAO_BIN" operator seal
    ;;
  *)
    usage
    exit 64
    ;;
esac
