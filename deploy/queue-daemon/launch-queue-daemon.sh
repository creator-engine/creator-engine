#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: launch-queue-daemon.sh [--health]

Starts the Creator Engine v3 merge-queue daemon with fail-closed credential
checks. Secrets must be supplied by the host environment or the systemd
EnvironmentFile; never place secret values in this script or the unit.

Required environment:
  GH_TOKEN                                  GitHub overwatch/integrator token
  BAO_TOKEN                                 least-privilege OpenBao daemon token
  BAO_ADDR                                  OpenBao address
  CE_GATE_REPO                              owner/name repo, for example creator-engine/creator-engine
  CE_GATE_AUTHORIZED_REVIEWERS             comma-separated authorized reviewer login(s)
  CE_OPENBAO_KV_MOUNT                      OpenBao KV v2 mount, for example ce-kv
  CE_APPROVAL_WALL_SECRET_PATH             OpenBao secret path, for example forge/approval-capability/wall
  CE_APPROVAL_WALL_SECRET_FIELD            OpenBao field, for example signing_secret
  CE_APPROVAL_WALL_POLICY_SHA              approval wall policy sha/id

Optional environment:
  BAO_CACERT                                OpenBao CA certificate path
  CE_QUEUE_DAEMON_BIN                       executable wrapper; default v3_cli, fallback to repo venv module
  CE_QUEUE_DAEMON_INTERVAL_SECONDS          default 120
  CE_QUEUE_DAEMON_APPROVAL_SETTLE_SECONDS   default 0
  CE_QUEUE_DAEMON_ROOT                      v3 local-state root
  CE_APPROVAL_WALL_SECRET_TARGET_FILE       default /run/ce-queue-daemon/approval-wall-secret
  CE_APPROVAL_WALL_STATE                    default /var/lib/ce-queue-daemon/approval-wall-state.json
  CE_APPROVAL_WALL_SECRET_OWNER_REF         default controller:integrator
  CE_APPROVAL_WALL_SECRET_RUN_ID            default approval-wall-daemon
  CE_APPROVAL_WALL_SECRET_SEAT_ID           default controller
  CE_APPROVAL_WALL_SECRET_TTL_SECONDS       default 600
  CE_APPROVAL_WALL_MARKER_TTL_SECONDS       default 3600
  CE_QUEUE_DAEMON_DRY_RUN                   set to 1 only for controlled dry-run tests
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    die "missing required environment variable: $name. Set it in /etc/creator-engine/ce-queue-daemon.env or the approved host secret channel."
  fi
}

repo_root() {
  if [[ -n "${CE_QUEUE_DAEMON_REPO_ROOT:-}" ]]; then
    cd -- "$CE_QUEUE_DAEMON_REPO_ROOT" >/dev/null
    pwd
  else
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null
    pwd
  fi
}

validate_required_env() {
  require_env GH_TOKEN
  require_env BAO_TOKEN
  require_env BAO_ADDR
  require_env CE_GATE_REPO
  require_env CE_GATE_AUTHORIZED_REVIEWERS
  require_env CE_OPENBAO_KV_MOUNT
  require_env CE_APPROVAL_WALL_SECRET_PATH
  require_env CE_APPROVAL_WALL_SECRET_FIELD
  require_env CE_APPROVAL_WALL_POLICY_SHA
}

resolve_queue_daemon_command() {
  local root="$1"
  local bin="${CE_QUEUE_DAEMON_BIN:-v3_cli}"
  if command -v "$bin" >/dev/null 2>&1; then
    QUEUE_DAEMON_CMD=("$bin")
    return 0
  fi
  if [[ -x "$root/.venv/bin/python" && -d "$root/validators/creator_engine_validator" ]]; then
    QUEUE_DAEMON_CMD=("$root/.venv/bin/python" "-m" "creator_engine_validator.v3_cli")
    return 0
  fi
  die "cannot find $bin and no repo venv module fallback at $root/.venv/bin/python. Install v3_cli or set CE_QUEUE_DAEMON_BIN."
}

curl_bao() {
  local url="$1"
  local args=(--fail --silent --show-error --max-time 10)
  if [[ -n "${BAO_CACERT:-}" ]]; then
    args+=(--cacert "$BAO_CACERT")
  fi
  curl "${args[@]}" --header "X-Vault-Token: $BAO_TOKEN" "$url" >/dev/null
}

check_gh_token() {
  if command -v gh >/dev/null 2>&1; then
    GH_TOKEN="$GH_TOKEN" gh api user >/dev/null
    return
  fi
  command -v curl >/dev/null 2>&1 || die "--health requires gh or curl to validate GH_TOKEN"
  curl --fail --silent --show-error --max-time 10 \
    --header "Authorization: Bearer $GH_TOKEN" \
    --header "Accept: application/vnd.github+json" \
    https://api.github.com/user >/dev/null
}

check_bao_token() {
  command -v curl >/dev/null 2>&1 || die "--health requires curl to validate BAO_TOKEN"
  curl_bao "$BAO_ADDR/v1/auth/token/lookup-self"
}

daemon_alive() {
  if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet ce-queue-daemon.service 2>/dev/null; then
    return 0
  fi
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -af '((v3_cli|cev3|creator_engine_validator[.]v3_cli).*[[:space:]]queue-daemon|queue-daemon.*--loop)' >/dev/null
  else
    die "--health requires systemctl or pgrep to verify daemon liveness"
  fi
}

health() {
  validate_required_env
  daemon_alive || die "ce-queue-daemon is not active. Check: systemctl status ce-queue-daemon.service"
  check_gh_token || die "GH_TOKEN validation failed. Refresh the overwatch/integrator token in /etc/creator-engine/ce-queue-daemon.env."
  check_bao_token || die "BAO_TOKEN validation failed against $BAO_ADDR. Refresh the least-privilege OpenBao daemon token."
  printf 'OK: ce-queue-daemon alive; GH_TOKEN and BAO_TOKEN are valid\n'
}

main() {
  local mode="start"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --health)
        mode="health"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        usage >&2
        die "unknown argument: $1"
        ;;
    esac
  done

  if [[ "$mode" == "health" ]]; then
    health
    return
  fi

  validate_required_env

  local root
  root="$(repo_root)"
  cd -- "$root"

  export PYTHONPATH="${PYTHONPATH:-$root/validators}"
  export CE_APPROVAL_WALL_SECRET_TARGET_FILE="${CE_APPROVAL_WALL_SECRET_TARGET_FILE:-/run/ce-queue-daemon/approval-wall-secret}"
  export CE_APPROVAL_WALL_STATE="${CE_APPROVAL_WALL_STATE:-/var/lib/ce-queue-daemon/approval-wall-state.json}"

  umask 077
  install -d -m 0700 "$(dirname -- "$CE_APPROVAL_WALL_SECRET_TARGET_FILE")" "$(dirname -- "$CE_APPROVAL_WALL_STATE")"

  local -a QUEUE_DAEMON_CMD
  resolve_queue_daemon_command "$root"

  local -a args=(
    queue-daemon
    --repo "$CE_GATE_REPO"
    --loop
    --interval "${CE_QUEUE_DAEMON_INTERVAL_SECONDS:-120}"
    --approval-settle-seconds "${CE_QUEUE_DAEMON_APPROVAL_SETTLE_SECONDS:-0}"
    --token-env GH_TOKEN
    --authorized-reviewer "$CE_GATE_AUTHORIZED_REVIEWERS"
    --approval-wall-secret-backend openbao
    --approval-wall-secret-mount "$CE_OPENBAO_KV_MOUNT"
    --approval-wall-secret-path "$CE_APPROVAL_WALL_SECRET_PATH"
    --approval-wall-secret-field "$CE_APPROVAL_WALL_SECRET_FIELD"
    --approval-wall-secret-purpose "${CE_APPROVAL_WALL_SECRET_PURPOSE:-approval-capability-wall}"
    --approval-wall-secret-owner-ref "${CE_APPROVAL_WALL_SECRET_OWNER_REF:-controller:integrator}"
    --approval-wall-secret-target-ref "file:$CE_APPROVAL_WALL_SECRET_TARGET_FILE"
    --approval-wall-secret-repo "$CE_GATE_REPO"
    --approval-wall-secret-run-id "${CE_APPROVAL_WALL_SECRET_RUN_ID:-approval-wall-daemon}"
    --approval-wall-secret-seat-id "${CE_APPROVAL_WALL_SECRET_SEAT_ID:-controller}"
    --approval-wall-secret-ttl-seconds "${CE_APPROVAL_WALL_SECRET_TTL_SECONDS:-600}"
    --approval-wall-marker-ttl-seconds "${CE_APPROVAL_WALL_MARKER_TTL_SECONDS:-3600}"
    --approval-wall-state "$CE_APPROVAL_WALL_STATE"
    --approval-wall-policy-sha "$CE_APPROVAL_WALL_POLICY_SHA"
    --root "${CE_QUEUE_DAEMON_ROOT:-/var/lib/ce-queue-daemon/v3}"
    --json
  )

  if [[ -n "${CE_APPROVAL_WALL_SECRET_VERSION:-}" ]]; then
    args+=(--approval-wall-secret-version "$CE_APPROVAL_WALL_SECRET_VERSION")
  fi
  if [[ "${CE_QUEUE_DAEMON_DRY_RUN:-0}" == "1" ]]; then
    args+=(--dry-run)
  fi

  exec "${QUEUE_DAEMON_CMD[@]}" "${args[@]}"
}

main "$@"
