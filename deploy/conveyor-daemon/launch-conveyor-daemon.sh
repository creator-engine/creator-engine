#!/usr/bin/env bash
set -euo pipefail

# Shadow-mode conveyor daemon launcher. Probe argv often needs host-only
# credentials/transports (ssh/docker/herdr); uncontained host execution is the
# evidence path until deployment mounts those probe credentials into the
# canonical daemon container. Containerized launch is the canary/live adapter.

usage() {
  cat <<'USAGE'
Usage: launch-conveyor-daemon.sh [--health] [--one-shot]

Starts the Creator Engine conveyor harvest daemon in shadow mode. The daemon
discovers READY-FOR-HARVEST seat signals and opens PRs; it does not approve,
merge, enqueue, or call reviewer-authority surfaces.

Options:
  --health    verify daemon liveness and GH_TOKEN access
  --one-shot  run one armed daemon pass, then exit

Required environment:
  CE_CONVEYOR_DAEMON_SEAT_PROBES          JSON array: [{"seat_id":"...","argv":["..."]}]
  CE_CONVEYOR_DAEMON_RUNTIME_ROOT         private runtime allocation root
  CE_CONVEYOR_DAEMON_DISCOVERY_STATE      discovery de-duplication state path
  GH_TOKEN                                GitHub token used only by gh subprocesses
  CE_DAEMON_LEASE_ROOT                    singleton lease root
  CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE  receipt signing secret file (shadow default)
    or CE_CONVEYOR_DAEMON_SIGNING_SECRET  direct receipt signing secret

Optional environment:
  CE_CONVEYOR_DAEMON_REPO_ROOT            default /workspace/creator-engine
  CE_CONVEYOR_DAEMON_INTERVAL_SECONDS     default 60
  CE_CONVEYOR_DAEMON_ITERATIONS           finite pass count
  CE_DAEMON_LEASE_TTL_SECONDS             default 300
  CE_DAEMON_LEASE_HEARTBEAT_SECONDS       supervisor default 30
  CE_DAEMON_HOLDER_ID                     optional lease holder id
  CE_CONVEYOR_DAEMON_LEDGER_PATH          JSONL mutation ledger
  CE_CONVEYOR_DAEMON_VALIDATION_LEDGER_ROOT
  CE_CONVEYOR_DAEMON_ACTIVE_WORK_LEDGER_ROOT
  CE_DAEMON_UNCONTAINED                   set to 1 for direct host launch
  CE_CONTAINER_ENGINE                     docker or podman for contained launch; default docker
  CE_DAEMON_IMAGE                         canonical runtime image for contained launch
  CE_DAEMON_STATE_ROOT                    host state root mounted into the container
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    die "missing required environment variable: $name. Set it in /etc/creator-engine/ce-conveyor-daemon.env or the approved host secret channel."
  fi
}

repo_root() {
  if [[ -n "${CE_CONVEYOR_DAEMON_REPO_ROOT:-}" ]]; then
    cd -- "$CE_CONVEYOR_DAEMON_REPO_ROOT" >/dev/null
    pwd
  else
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null
    pwd
  fi
}

validate_required_env() {
  require_env CE_CONVEYOR_DAEMON_SEAT_PROBES
  require_env CE_CONVEYOR_DAEMON_RUNTIME_ROOT
  require_env CE_CONVEYOR_DAEMON_DISCOVERY_STATE
  require_env GH_TOKEN
  require_env CE_DAEMON_LEASE_ROOT
  if [[ -z "${CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE:-}" && -z "${CE_CONVEYOR_DAEMON_SIGNING_SECRET:-}" ]]; then
    die "missing receipt signing secret: set CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE or CE_CONVEYOR_DAEMON_SIGNING_SECRET"
  fi
}

resolve_lease_python() {
  local root="$1"
  if [[ -n "${CE_DAEMON_LEASE_PYTHON:-}" ]]; then
    printf '%s\n' "$CE_DAEMON_LEASE_PYTHON"
    return 0
  fi
  if [[ -x "$root/.venv/bin/python" ]]; then
    printf '%s\n' "$root/.venv/bin/python"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  die "cannot find python for conveyor-daemon singleton lease supervisor"
}

exec_with_conveyor_daemon_lease() {
  local root="$1"
  local lease_root="${CE_DAEMON_LEASE_ROOT:-}"
  [[ -n "$lease_root" ]] || die "CE_DAEMON_LEASE_ROOT is required"
  install -d -m 0700 "$lease_root"
  export CE_DAEMON_LEASE_ROOT="$lease_root"
  export PYTHONPATH="${PYTHONPATH:-$root/validators}"
  local lease_python
  lease_python="$(resolve_lease_python "$root")"

  exec -a creator_engine_validator.conveyor_daemon_runner "$lease_python" - <<'PY'
from __future__ import annotations

import os
import socket
import sys
import threading
from pathlib import Path

from creator_engine_validator.conveyor_daemon_runner import (
    _lease_refusal_error,
    main_with_existing_lease,
)
from creator_engine_validator.daemon_lease import DaemonLeaseError, acquire


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise SystemExit(f"ERROR: {name} must be numeric")
    if value <= 0:
        raise SystemExit(f"ERROR: {name} must be positive")
    return value


lease_root = Path(os.environ["CE_DAEMON_LEASE_ROOT"])
ttl_seconds = _float_env("CE_DAEMON_LEASE_TTL_SECONDS", 300.0)
heartbeat_seconds = min(_float_env("CE_DAEMON_LEASE_HEARTBEAT_SECONDS", 30.0), ttl_seconds / 2.0)
holder_id = os.environ.get("CE_DAEMON_HOLDER_ID") or f"conveyor-daemon:{socket.gethostname()}:{os.getpid()}"
stop = threading.Event()

try:
    lease = acquire(
        "conveyor-daemon",
        holder_id,
        state_root=lease_root,
        ttl_seconds=ttl_seconds,
    )
except DaemonLeaseError as exc:
    try:
        from types import SimpleNamespace

        message = _lease_refusal_error(SimpleNamespace(lease_root=lease_root), exc)
    except Exception:
        message = f"conveyor-daemon singleton lease refused: {exc}"
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(73)


def _heartbeat() -> None:
    while not stop.wait(heartbeat_seconds):
        try:
            lease.heartbeat()
        except Exception as exc:
            print(f"ERROR: conveyor-daemon singleton lease heartbeat failed: {exc}", file=sys.stderr)
            os._exit(74)


thread = threading.Thread(target=_heartbeat, daemon=True)
thread.start()
try:
    raise SystemExit(main_with_existing_lease(lease))
finally:
    stop.set()
PY
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

daemon_alive() {
  if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet ce-conveyor-daemon.service 2>/dev/null; then
    return 0
  fi
  local engine="${CE_CONTAINER_ENGINE:-docker}"
  local container_name="${CE_DAEMON_CONTAINER_NAME:-ce-conveyor-daemon}"
  if command -v "$engine" >/dev/null 2>&1; then
    if "$engine" ps --filter "name=^${container_name}$" --format '{{.Names}}' 2>/dev/null | grep -Fx "$container_name" >/dev/null; then
      return 0
    fi
  fi
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -af '(^|[[:space:]])creator_engine_validator[.]conveyor_daemon_runner([[:space:]]|$)' >/dev/null
  else
    die "--health requires systemctl, $engine, or pgrep to verify daemon liveness"
  fi
}

health() {
  validate_required_env
  daemon_alive || die "ce-conveyor-daemon is not active. Check: systemctl status ce-conveyor-daemon.service"
  check_gh_token || die "GH_TOKEN validation failed. Refresh the conveyor daemon token in /etc/creator-engine/ce-conveyor-daemon.env."
  printf 'OK: ce-conveyor-daemon alive; GH_TOKEN is valid\n'
}

container_adapter() {
  local root
  root="$(repo_root)"
  exec "$root/deploy/daemons/run-daemon-container.sh" conveyor-daemon "$@"
}

main_uncontained() {
  local mode="start"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --health)
        mode="health"
        shift
        ;;
      --one-shot)
        export CE_CONVEYOR_DAEMON_ITERATIONS=1
        shift
        ;;
      --dry-run)
        die "--dry-run was renamed to --one-shot; the conveyor daemon has no disarmed launcher mode."
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

  umask 077
  install -d -m 0700 \
    "$CE_CONVEYOR_DAEMON_RUNTIME_ROOT" \
    "$(dirname -- "$CE_CONVEYOR_DAEMON_DISCOVERY_STATE")" \
    "$CE_DAEMON_LEASE_ROOT"

  exec_with_conveyor_daemon_lease "$root"
}

main() {
  local normalized_args=()
  local arg
  for arg in "$@"; do
    case "$arg" in
      --one-shot)
        export CE_CONVEYOR_DAEMON_ITERATIONS=1
        ;;
      --dry-run)
        die "--dry-run was renamed to --one-shot; the conveyor daemon has no disarmed launcher mode."
        ;;
      *)
        normalized_args+=("$arg")
        ;;
    esac
  done
  set -- "${normalized_args[@]}"

  case "${1:-}" in
    -h|--help)
      usage
      exit 0
      ;;
    --health)
      main_uncontained "$@"
      return
      ;;
  esac

  if [[ "${CE_DAEMON_UNCONTAINED:-0}" == "1" ]]; then
    main_uncontained "$@"
    return
  fi

  container_adapter "$@"
}

main "$@"
