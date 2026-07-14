#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: launch-queue-daemon.sh [--health]

Starts the Creator Engine v3 merge-queue daemon in the canonical daemon
container. Set CE_DAEMON_UNCONTAINED=1 only for the documented rollback escape
hatch to use the legacy direct host launch path.

Secrets must be supplied by the host environment, the systemd EnvironmentFile,
or the documented runtime token file path; never place secret values in this
script or the unit.

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
  CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA   approval wall secret-ref policy sha/id (refs the policy that governs the secret fetch)

Optional environment:
  BAO_CACERT                                OpenBao CA certificate path
  CE_QUEUE_DAEMON_BIN                       executable wrapper; default cev3, fallback to repo venv module
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
  CE_QUEUE_DAEMON_CANARY                    set to 1 for dry-run canary with dormant wall
  CE_DAEMON_UNCONTAINED                     set to 1 for the legacy direct-launch escape hatch
  CE_DAEMON_DISK_HEADROOM_GB                minimum free GiB required on state-root filesystem; default 5; exit 75 if below
  CE_CONTAINER_ENGINE                       docker or podman for contained launch; default docker
  CE_DAEMON_IMAGE                           canonical runtime image for contained launch
  CE_DAEMON_STATE_ROOT                      host state root mounted into the container
  CE_DAEMON_LEASE_ROOT                      queue singleton lease root; default derived from daemon state root
  CE_DAEMON_LEASE_HEARTBEAT_SECONDS         default 30
  CE_DAEMON_LEASE_TTL_SECONDS               default 300
  CE_DAEMON_HOLDER_ID                       optional lease holder id; default queue-daemon:<host>:<pid>
  CE_DAEMON_TOKEN_FILE                      optional token file mounted read-only
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

is_canary_mode() {
  [[ "${CE_QUEUE_DAEMON_CANARY:-0}" == "1" ]]
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
  require_env CE_GATE_REPO
  require_env CE_GATE_AUTHORIZED_REVIEWERS
  if is_canary_mode; then
    return
  fi
  require_env BAO_TOKEN
  require_env BAO_ADDR
  require_env CE_OPENBAO_KV_MOUNT
  require_env CE_APPROVAL_WALL_SECRET_PATH
  require_env CE_APPROVAL_WALL_SECRET_FIELD
  require_env CE_APPROVAL_WALL_POLICY_SHA
  require_env CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA
}

canary_state_root_isolation_check() {
  local live_root="/var/lib/ce-queue-daemon/v3"
  require_env CE_DAEMON_STATE_ROOT
  if [[ "$CE_DAEMON_STATE_ROOT" == "$live_root" ]]; then
    die "canary state root collision: CE_DAEMON_STATE_ROOT must not equal live daemon root $live_root"
  fi
  if [[ "${CE_QUEUE_DAEMON_ROOT:-$CE_DAEMON_STATE_ROOT}" == "$live_root" ]]; then
    die "canary queue daemon root collision: CE_QUEUE_DAEMON_ROOT must not equal live daemon root $live_root"
  fi
}

resolve_queue_daemon_command() {
  local root="$1"
  local bin="${CE_QUEUE_DAEMON_BIN:-cev3}"
  if command -v "$bin" >/dev/null 2>&1; then
    QUEUE_DAEMON_CMD=("$bin")
    return 0
  fi
  if [[ -x "$root/.venv/bin/python" && -d "$root/validators/creator_engine_validator" ]]; then
    QUEUE_DAEMON_CMD=("$root/.venv/bin/python" "-m" "creator_engine_validator.v3_cli")
    return 0
  fi
  die "cannot find $bin and no repo venv module fallback at $root/.venv/bin/python. Install cev3 or set CE_QUEUE_DAEMON_BIN."
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
  die "cannot find python for queue-daemon singleton lease supervisor"
}

queue_daemon_lease_root() {
  local root="$1"
  if [[ -n "${CE_DAEMON_LEASE_ROOT:-}" ]]; then
    printf '%s\n' "$CE_DAEMON_LEASE_ROOT"
  elif [[ -n "${CE_DAEMON_STATE_ROOT:-}" ]]; then
    printf '%s\n' "$CE_DAEMON_STATE_ROOT/daemon-leases"
  elif [[ -n "${CE_QUEUE_DAEMON_ROOT:-}" ]]; then
    printf '%s\n' "$(dirname -- "$CE_QUEUE_DAEMON_ROOT")/daemon-leases"
  else
    printf '%s\n' "$root/.ce/state/daemon-leases"
  fi
}

# Resolve the nearest existing ancestor of $path (itself if it exists).
_nearest_existing_path() {
  local path="$1"
  while [[ -n "$path" && "$path" != "/" ]]; do
    if [[ -e "$path" ]]; then
      printf '%s\n' "$path"
      return 0
    fi
    path="$(dirname -- "$path")"
  done
  printf '/\n'
}

check_disk_headroom() {
  # Refuse to start if the filesystem hosting the daemon state root has less
  # than CE_DAEMON_DISK_HEADROOM_GB (default 5) GiB of free space.
  # Fail-closed BEFORE the singleton lease is acquired.
  # Exit code 75 with a message naming "disk_headroom" distinguishes this
  # failure from lease conflicts (73/74) and other startup errors.
  local root="$1"

  # Resolve the state root path to check (walk up to nearest existing ancestor).
  local state_root="${CE_DAEMON_STATE_ROOT:-}"
  if [[ -z "$state_root" ]]; then
    if [[ -n "${CE_QUEUE_DAEMON_ROOT:-}" ]]; then
      state_root="$(dirname -- "$CE_QUEUE_DAEMON_ROOT")"
    else
      state_root="$root"
    fi
  fi
  local check_path
  check_path="$(_nearest_existing_path "$state_root")"

  if ! command -v df >/dev/null 2>&1; then
    printf 'WARNING: df not found; disk headroom check skipped\n' >&2
    return 0
  fi

  local avail_kb
  avail_kb="$(df -Pk -- "$check_path" 2>/dev/null | awk 'NR==2{print $4}')"
  if [[ -z "$avail_kb" ]]; then
    printf 'WARNING: disk headroom check could not read available space for %s; skipping\n' "$check_path" >&2
    return 0
  fi

  local threshold_gb="${CE_DAEMON_DISK_HEADROOM_GB:-5}"
  local threshold_kb
  threshold_kb="$(( threshold_gb * 1024 * 1024 ))"

  if [[ "$avail_kb" -lt "$threshold_kb" ]]; then
    printf 'ERROR: disk_headroom: only %s kB free on filesystem containing %s, need %s GiB (%s kB). Free disk space and retry.\n' \
      "$avail_kb" "$check_path" "$threshold_gb" "$threshold_kb" >&2
    exit 75
  fi
}

exec_with_queue_daemon_lease() {
  local root="$1"
  shift
  local lease_root
  lease_root="$(queue_daemon_lease_root "$root")"
  install -d -m 0700 "$lease_root"
  export CE_DAEMON_LEASE_ROOT="$lease_root"
  local lease_python
  lease_python="$(resolve_lease_python "$root")"

  exec "$lease_python" - "$@" <<'PY'
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from creator_engine_validator import daemon_lease
from creator_engine_validator.daemon_lease import DaemonLeaseError, DaemonLeaseStale, acquire


_QUEUE_STARTUP_RECOVERY_REASON = "automatic queue-daemon same-host dead-pid recovery"
_LEASE_FIELDS = {"holder_id", "pid", "host", "acquired_at", "heartbeat_at"}


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


def _same_host_dead_pid_lease(payload: object) -> bool:
    """Return true only for the bounded automatic queue-startup recovery case."""

    if not isinstance(payload, dict) or set(payload) != _LEASE_FIELDS:
        return False
    pid = payload.get("pid")
    if (
        payload.get("host") != socket.gethostname()
        or isinstance(pid, bool)
        or not isinstance(pid, int)
        or pid <= 0
    ):
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except (PermissionError, OSError):
        return False
    return False


def _recover_same_host_dead_pid_lease(
    lease_path: Path,
    *,
    holder_id: str,
) -> daemon_lease.DaemonLease:
    """Audit-and-replace only the exact stale record validated under the lease lock."""

    with daemon_lease._operation_lock(lease_path, daemon_name="queue-daemon", wait=False):
        try:
            raw_payload = json.loads(lease_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DaemonLeaseStale("queue-daemon lease is not eligible for automatic recovery") from exc
        if not _same_host_dead_pid_lease(raw_payload):
            raise DaemonLeaseStale("queue-daemon lease is not eligible for automatic recovery")

        existing = daemon_lease._read_payload(lease_path)
        if existing.as_dict() != raw_payload:
            raise DaemonLeaseStale("queue-daemon lease changed during automatic recovery")

        timestamp = daemon_lease._acquisition_timestamp(None)
        replacement = daemon_lease.DaemonLeasePayload(
            holder_id=holder_id,
            pid=os.getpid(),
            host=socket.gethostname(),
            acquired_at=timestamp,
            heartbeat_at=timestamp,
        )
        daemon_lease._takeover_stale_lease(
            lease_path=lease_path,
            daemon_name="queue-daemon",
            old_payload=existing,
            new_payload=replacement,
            reason=_QUEUE_STARTUP_RECOVERY_REASON,
            now=timestamp,
        )
        return daemon_lease.DaemonLease("queue-daemon", holder_id, lease_path, replacement)


cmd = sys.argv[1:]
if not cmd:
    raise SystemExit("ERROR: queue-daemon singleton lease supervisor received no command")

lease_root = Path(os.environ["CE_DAEMON_LEASE_ROOT"])
ttl_seconds = _float_env("CE_DAEMON_LEASE_TTL_SECONDS", 300.0)
heartbeat_seconds = min(_float_env("CE_DAEMON_LEASE_HEARTBEAT_SECONDS", 30.0), ttl_seconds / 2.0)
holder_id = os.environ.get("CE_DAEMON_HOLDER_ID") or f"queue-daemon:{socket.gethostname()}:{os.getpid()}"
lease_path = lease_root / "queue-daemon.lease"

try:
    lease = acquire(
        "queue-daemon",
        holder_id,
        state_root=lease_root,
        ttl_seconds=ttl_seconds,
    )
except DaemonLeaseStale:
    try:
        lease = _recover_same_host_dead_pid_lease(
            lease_path,
            holder_id=holder_id,
        )
    except DaemonLeaseError as exc:
        print(f"ERROR: queue-daemon singleton lease refused: {exc}", file=sys.stderr)
        raise SystemExit(73)
except DaemonLeaseError as exc:
    print(f"ERROR: queue-daemon singleton lease refused: {exc}", file=sys.stderr)
    raise SystemExit(73)

process = subprocess.Popen(cmd)


def _forward(signum: int, _frame: object) -> None:
    if process.poll() is None:
        process.send_signal(signum)


signal.signal(signal.SIGTERM, _forward)
signal.signal(signal.SIGINT, _forward)

try:
    while True:
        try:
            returncode = process.wait(timeout=heartbeat_seconds)
            raise SystemExit(returncode)
        except subprocess.TimeoutExpired:
            try:
                lease.heartbeat()
            except Exception as exc:
                print(f"ERROR: queue-daemon singleton lease heartbeat failed: {exc}", file=sys.stderr)
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise SystemExit(74)
finally:
    lease.release()
PY
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
  local engine="${CE_CONTAINER_ENGINE:-docker}"
  local container_name="${CE_DAEMON_CONTAINER_NAME:-ce-queue-daemon}"
  if command -v "$engine" >/dev/null 2>&1; then
    if "$engine" ps --filter "name=^${container_name}$" --format '{{.Names}}' 2>/dev/null | grep -Fx "$container_name" >/dev/null; then
      return 0
    fi
  fi
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -af '((v3_cli|cev3|creator_engine_validator[.]v3_cli).*[[:space:]]queue-daemon|queue-daemon.*--loop)' >/dev/null
  else
    die "--health requires systemctl, $engine, or pgrep to verify daemon liveness"
  fi
}

health() {
  validate_required_env
  daemon_alive || die "ce-queue-daemon is not active. Check: systemctl status ce-queue-daemon.service"
  check_gh_token || die "GH_TOKEN validation failed. Refresh the overwatch/integrator token in /etc/creator-engine/ce-queue-daemon.env."
  if is_canary_mode; then
    printf 'OK: ce-queue-daemon alive; GH_TOKEN is valid; BAO_TOKEN skipped for canary mode\n'
    return
  fi
  check_bao_token || die "BAO_TOKEN validation failed against $BAO_ADDR. Refresh the least-privilege OpenBao daemon token."
  printf 'OK: ce-queue-daemon alive; GH_TOKEN and BAO_TOKEN are valid\n'
}

container_adapter() {
  local root
  root="$(repo_root)"
  exec "$root/deploy/daemons/run-daemon-container.sh" queue-daemon "$@"
}

main_uncontained() {
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

  local root
  root="$(repo_root)"
  cd -- "$root"

  validate_required_env
  check_disk_headroom "$root"
  local canary_mode=0
  if is_canary_mode; then
    canary_mode=1
    canary_state_root_isolation_check
  fi

  export PYTHONPATH="${PYTHONPATH:-$root/validators}"
  if [[ "$canary_mode" != "1" ]]; then
    export CE_APPROVAL_WALL_SECRET_TARGET_FILE="${CE_APPROVAL_WALL_SECRET_TARGET_FILE:-/run/ce-queue-daemon/approval-wall-secret}"
    export CE_APPROVAL_WALL_STATE="${CE_APPROVAL_WALL_STATE:-/var/lib/ce-queue-daemon/approval-wall-state.json}"

    umask 077
    install -d -m 0700 "$(dirname -- "$CE_APPROVAL_WALL_SECRET_TARGET_FILE")" "$(dirname -- "$CE_APPROVAL_WALL_STATE")"
  fi

  local -a QUEUE_DAEMON_CMD
  resolve_queue_daemon_command "$root"

  local daemon_root="${CE_QUEUE_DAEMON_ROOT:-/var/lib/ce-queue-daemon/v3}"
  if [[ "$canary_mode" == "1" ]]; then
    daemon_root="${CE_QUEUE_DAEMON_ROOT:-$CE_DAEMON_STATE_ROOT}"
  fi

  local -a args=(
    queue-daemon
    --repo "$CE_GATE_REPO"
    --loop
    --interval "${CE_QUEUE_DAEMON_INTERVAL_SECONDS:-120}"
    --approval-settle-seconds "${CE_QUEUE_DAEMON_APPROVAL_SETTLE_SECONDS:-0}"
    --token-env GH_TOKEN
    --authorized-reviewer "$CE_GATE_AUTHORIZED_REVIEWERS"
  )

  if [[ "$canary_mode" == "1" ]]; then
    printf 'CANARY MODE — dry_run=true, wall=dormant, no merge authority\n' >&2
    args+=(--dry-run)
  else
    args+=(
    --approval-wall-secret-backend openbao
    --approval-wall-secret-mount "$CE_OPENBAO_KV_MOUNT"
    --approval-wall-secret-path "$CE_APPROVAL_WALL_SECRET_PATH"
    --approval-wall-secret-field "$CE_APPROVAL_WALL_SECRET_FIELD"
    --approval-wall-secret-purpose "${CE_APPROVAL_WALL_SECRET_PURPOSE:-approval-capability-wall}"
    --approval-wall-secret-owner-ref "${CE_APPROVAL_WALL_SECRET_OWNER_REF:-controller:integrator}"
    --approval-wall-secret-ref-policy-sha "$CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA"
    --approval-wall-secret-target-ref "file:$CE_APPROVAL_WALL_SECRET_TARGET_FILE"
    --approval-wall-secret-repo "$CE_GATE_REPO"
    --approval-wall-secret-run-id "${CE_APPROVAL_WALL_SECRET_RUN_ID:-approval-wall-daemon}"
    --approval-wall-secret-seat-id "${CE_APPROVAL_WALL_SECRET_SEAT_ID:-controller}"
    --approval-wall-secret-ttl-seconds "${CE_APPROVAL_WALL_SECRET_TTL_SECONDS:-600}"
    --approval-wall-marker-ttl-seconds "${CE_APPROVAL_WALL_MARKER_TTL_SECONDS:-3600}"
    --approval-wall-state "$CE_APPROVAL_WALL_STATE"
    --approval-wall-policy-sha "$CE_APPROVAL_WALL_POLICY_SHA"
    )
  fi

  args+=(--root "$daemon_root" --json)

  if [[ "$canary_mode" != "1" && -n "${CE_APPROVAL_WALL_SECRET_VERSION:-}" ]]; then
    args+=(--approval-wall-secret-version "$CE_APPROVAL_WALL_SECRET_VERSION")
  fi
  if [[ "$canary_mode" != "1" && "${CE_QUEUE_DAEMON_DRY_RUN:-0}" == "1" ]]; then
    args+=(--dry-run)
  fi

  exec_with_queue_daemon_lease "$root" "${QUEUE_DAEMON_CMD[@]}" "${args[@]}"
}

main() {
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

  if is_canary_mode; then
    main_uncontained "$@"
    return
  fi

  container_adapter "$@"
}

main "$@"
