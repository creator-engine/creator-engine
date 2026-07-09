#!/usr/bin/env bash
set -euo pipefail

SMOKE_TMPDIR=""
SMOKE_SECRET_VALUE="daemon-container-smoke-signing-secret"

# Tracks the in-flight pass's container/runner so the EXIT trap can stop them
# on ANY exit path (including an early die() such as a wait_for_file
# timeout), without ever touching a container this script did not start.
CURRENT_ENGINE=""
CURRENT_CONTAINER_NAME=""
CURRENT_RUNNER_PID=""

usage() {
  cat <<'USAGE'
Usage: smoke-daemon-container.sh <scratch-state-root>

Runs a host-operator smoke for the canonical daemon container adapter. The
script starts the conveyor daemon container twice against the same scratch state
root, observes the singleton lease on each pass, stops the container, and
asserts the lease is released between passes.

Environment:
  CE_CONTAINER_ENGINE      docker or podman executable; default docker
  CE_DAEMON_IMAGE          runtime image; default inherited from run-daemon-container.sh
  CE_DAEMON_IMAGE_UID      runtime image uid/gid; default 10001
  GH_TOKEN                 optional; a smoke-only placeholder is used when unset

The default Docker path enforces the image uid ownership contract. If Docker is
not installed or not reachable, this script exits 77 with a SKIP message.

Before starting the real engine passes, the smoke runs a host-prep-only mixed-uid
probe with fake docker/stat shims against scratch state. This documented
simulation covers the rerun case where an unprivileged host user sees a
10001-owned 0700 state root but cannot traverse it.
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

skip() {
  printf 'SKIP: %s\n' "$*" >&2
  exit 77
}

repo_root() {
  if [[ -n "${CE_DAEMON_REPO_ROOT:-}" ]]; then
    cd -- "$CE_DAEMON_REPO_ROOT" >/dev/null
    pwd
  else
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null
    pwd
  fi
}

engine_name() {
  basename -- "$1"
}

is_unsigned_int() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

wait_for_file() {
  local path="$1"
  local label="$2"
  local deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    [[ -f "$path" ]] && return 0
    sleep 0.1
  done
  die "timed out waiting for $label: $path"
}

wait_for_absent() {
  local path="$1"
  local label="$2"
  local deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    [[ ! -e "$path" ]] && return 0
    sleep 0.1
  done
  die "timed out waiting for $label to be removed: $path"
}

assert_absent() {
  local path="$1"
  [[ ! -e "$path" ]] || die "tmpfs-backed secret path leaked onto host state: $path"
}

assert_secret_content_absent_from_state() {
  # Recursively scan the ENTIRE host state root for the smoke's placeholder
  # secret content, rather than checking only specific known tmpfs mount
  # points. A content scan catches leakage via any persistence path (a future
  # config change, a bind mount, a symlink) instead of just the mount points
  # this script happens to know about today.
  local state_root="$1"
  local hit
  # grep exits 1 on the expected/good "no match" outcome; under pipefail that
  # would otherwise abort the script via set -e before the check below runs.
  hit="$(grep -rlI -- "$SMOKE_SECRET_VALUE" "$state_root" 2>/dev/null | head -n1)" || true
  [[ -z "$hit" ]] || die "smoke secret content leaked onto host state: $hit"
}

assert_docker_state_owned_by_image_uid() {
  local engine="$1"
  local state_root="$2"
  local image_uid="$3"
  if [[ "$(engine_name "$engine")" != "docker" ]]; then
    return 0
  fi
  local wrong_owner
  wrong_owner="$(find "$state_root" ! -uid "$image_uid" -print -quit)"
  [[ -z "$wrong_owner" ]] || die "state path is not owned by image uid $image_uid: $wrong_owner"
}

write_secret_file() {
  local path="$1"
  umask 077
  printf '%s\n' "$SMOKE_SECRET_VALUE" > "$path"
  chmod 0600 "$path"
  chown "${CE_DAEMON_IMAGE_UID:-10001}:${CE_DAEMON_IMAGE_UID:-10001}" "$path" 2>/dev/null || true
}

write_mixed_uid_probe_engine() {
  local path="$1"
  local calls_file="$2"
  local state_root="$3"
  cat >"$path" <<EOF
#!/usr/bin/env bash
set -euo pipefail
printf 'CALL' >> "$calls_file"
for arg in "\$@"; do printf '\\t%s' "\$arg" >> "$calls_file"; done
printf '\\n' >> "$calls_file"
if [[ "\${1:-}" == "run" ]]; then
  chmod 0700 "$state_root"
  install -d -m 0700 "$state_root/daemon-leases"
fi
exit 0
EOF
  chmod 0755 "$path"
}

write_mixed_uid_probe_stat() {
  local path="$1"
  local state_root="$2"
  local image_uid="$3"
  local real_stat
  real_stat="$(command -v stat)"
  cat >"$path" <<EOF
#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "-c" && "\${3:-}" == "--" && "\${4:-}" == "$state_root" ]]; then
  case "\${2:-}" in
    %a)
      printf '700\\n'
      exit 0
      ;;
    %u)
      printf '$image_uid\\n'
      exit 0
      ;;
  esac
fi
exec "$real_stat" "\$@"
EOF
  chmod 0755 "$path"
}

run_mixed_uid_host_prep_probe() {
  local root="$1"
  local image_uid="$2"
  local tmpdir="$3"
  local probe_dir="$tmpdir/mixed-uid-host-prep-probe"
  local state_root="$probe_dir/state"
  local calls_file="$probe_dir/engine-calls"
  local fake_docker="$probe_dir/docker"
  local fake_stat="$probe_dir/stat"

  install -d -m 0700 "$probe_dir"
  install -d -m 0700 "$state_root"
  chmod 0000 "$state_root"
  write_mixed_uid_probe_engine "$fake_docker" "$calls_file" "$state_root"
  write_mixed_uid_probe_stat "$fake_stat" "$state_root" "$image_uid"

  (
    export PATH="$probe_dir:$PATH"
    export CE_CONTAINER_ENGINE="$fake_docker"
    export CE_DAEMON_CONTAINER_NAME="ce-daemon-mixed-uid-probe-$$"
    export CE_DAEMON_REPO_ROOT="$root"
    export CE_DAEMON_STATE_ROOT="$state_root"
    export CE_DAEMON_LEASE_ROOT="$state_root/daemon-leases"
    export CE_DAEMON_IMAGE_UID="$image_uid"
    export CE_DAEMON_LOG_DIR="$probe_dir/logs"
    export CE_CONVEYOR_DAEMON_SIGNING_SECRET="mixed-uid-probe-secret"
    export GH_TOKEN="${GH_TOKEN:-daemon-container-smoke-token}"
    "$root/deploy/daemons/run-daemon-container.sh" conveyor-daemon --one-shot
  ) >"$probe_dir/adapter.stdout" 2>"$probe_dir/adapter.stderr" || {
    chmod 0700 "$state_root" 2>/dev/null || true
    printf '%s\n' "---- mixed-uid host-prep probe stdout ----" >&2
    sed -n '1,160p' "$probe_dir/adapter.stdout" >&2 || true
    printf '%s\n' "---- mixed-uid host-prep probe stderr ----" >&2
    sed -n '1,160p' "$probe_dir/adapter.stderr" >&2 || true
    die "mixed-uid host-prep probe failed"
  }
  chmod 0700 "$state_root"
  [[ -s "$calls_file" ]] || die "mixed-uid host-prep probe did not reach fake docker"
  printf 'mixed-uid host-prep probe reached container engine\n'
}

# Best-effort stop of the currently tracked pass's container/runner. Invoked
# from the EXIT trap so a die() anywhere after the container starts (e.g. a
# wait_for_file timeout) cannot leak a running container or an orphaned
# backgrounded runner process. Only ever targets the container name this
# script derived and started itself.
stop_current_container() {
  if [[ -n "$CURRENT_ENGINE" && -n "$CURRENT_CONTAINER_NAME" ]]; then
    "$CURRENT_ENGINE" stop --time 5 "$CURRENT_CONTAINER_NAME" >/dev/null 2>&1 || true
  fi
  if [[ -n "$CURRENT_RUNNER_PID" ]]; then
    # Bound the wait: a healthy engine stop lets the backgrounded runner exit
    # promptly, but never block cleanup indefinitely on a runner that outlives
    # the engine stop (e.g. an unreachable engine at trap time).
    local deadline=$((SECONDS + 10))
    while (( SECONDS < deadline )) && kill -0 "$CURRENT_RUNNER_PID" 2>/dev/null; do
      sleep 0.2
    done
    pkill -KILL -P "$CURRENT_RUNNER_PID" 2>/dev/null || true
    kill -KILL "$CURRENT_RUNNER_PID" 2>/dev/null || true
    wait "$CURRENT_RUNNER_PID" 2>/dev/null || true
  fi
  CURRENT_ENGINE=""
  CURRENT_CONTAINER_NAME=""
  CURRENT_RUNNER_PID=""
}

cleanup() {
  stop_current_container
  if [[ -n "$SMOKE_TMPDIR" && -d "$SMOKE_TMPDIR" ]]; then
    for _log in "$SMOKE_TMPDIR"/smoke-pass-*.log; do
      [[ -f "$_log" ]] || continue
      local _label
      _label="$(basename "$_log" .log)"
      printf '%s\n' "---- $_label log (cleanup dump) ----" >&2
      sed -n '1,220p' "$_log" >&2 || true
    done
  fi
  [[ -z "$SMOKE_TMPDIR" ]] || rm -rf -- "$SMOKE_TMPDIR"
}

run_pass() {
  local pass="$1"
  local root="$2"
  local engine="$3"
  local image_uid="$4"
  local state_root="$5"
  local secret_file="$6"
  local tmpdir="$7"
  local container_name="ce-daemon-smoke-$$-$pass"
  local lease_path="$state_root/daemon-leases/conveyor-daemon.lease"
  local log_path="$tmpdir/smoke-pass-$pass.log"

  rm -f -- "$lease_path"

  (
    export CE_CONTAINER_ENGINE="$engine"
    export CE_DAEMON_CONTAINER_NAME="$container_name"
    export CE_DAEMON_REPO_ROOT="$root"
    export CE_DAEMON_STATE_ROOT="$state_root"
    export CE_DAEMON_LEASE_ROOT="$state_root/daemon-leases"
    export CE_DAEMON_IMAGE_UID="$image_uid"
    export CE_DAEMON_LOG_DIR="$tmpdir/adapter-logs"
    export CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE="$secret_file"
    export CE_CONVEYOR_DAEMON_SEAT_PROBES='[{"seat_id":"smoke","argv":["bash","-lc","sleep 2"]}]'
    export GH_TOKEN="${GH_TOKEN:-daemon-container-smoke-token}"
    "$root/deploy/daemons/run-daemon-container.sh" conveyor-daemon --one-shot
  ) >"$log_path" 2>&1 &
  local runner_pid=$!
  CURRENT_ENGINE="$engine"
  CURRENT_CONTAINER_NAME="$container_name"
  CURRENT_RUNNER_PID="$runner_pid"

  wait_for_file "$lease_path" "pass $pass conveyor lease"
  printf 'pass %s acquired lease: %s\n' "$pass" "$lease_path"

  "$engine" stop --time 20 "$container_name" >/dev/null 2>&1 || true
  if ! wait "$runner_pid"; then
    printf '%s\n' "---- smoke pass $pass log ----" >&2
    sed -n '1,220p' "$log_path" >&2 || true
    die "daemon container smoke pass $pass failed"
  fi
  CURRENT_ENGINE=""
  CURRENT_CONTAINER_NAME=""
  CURRENT_RUNNER_PID=""

  wait_for_absent "$lease_path" "pass $pass conveyor lease"
  assert_docker_state_owned_by_image_uid "$engine" "$state_root" "$image_uid"
  assert_secret_content_absent_from_state "$state_root"
  assert_absent "$state_root/conveyor-daemon-secret/signing-secret"
  printf 'pass %s released lease and left host secret paths absent\n' "$pass"
}

main() {
  case "${1:-}" in
    -h|--help)
      usage
      exit 0
      ;;
  esac
  [[ $# -eq 1 ]] || {
    usage >&2
    exit 2
  }

  # Armed before anything that could start a container so that ANY exit path
  # (including an early die()) stops the smoke's own container/runner and
  # cleans up scratch state; see stop_current_container/cleanup.
  trap cleanup EXIT

  local state_root="$1"
  [[ -e "$state_root" && ! -d "$state_root" ]] && die "state root exists but is not a directory: $state_root"

  local root
  root="$(repo_root)"
  local engine="${CE_CONTAINER_ENGINE:-docker}"
  command -v "$engine" >/dev/null 2>&1 || skip "container engine not found: $engine"
  "$engine" info >/dev/null 2>&1 || skip "container engine is not reachable: $engine"

  local image_uid="${CE_DAEMON_IMAGE_UID:-10001}"
  is_unsigned_int "$image_uid" || die "CE_DAEMON_IMAGE_UID must be numeric: $image_uid"

  SMOKE_TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/ce-daemon-smoke.XXXXXX")"
  local secret_file="$SMOKE_TMPDIR/signing-secret"
  write_secret_file "$secret_file"

  run_mixed_uid_host_prep_probe "$root" "$image_uid" "$SMOKE_TMPDIR"
  run_pass 1 "$root" "$engine" "$image_uid" "$state_root" "$secret_file" "$SMOKE_TMPDIR"
  run_pass 2 "$root" "$engine" "$image_uid" "$state_root" "$secret_file" "$SMOKE_TMPDIR"

  printf 'OK: daemon container stateful smoke passed for %s\n' "$state_root"
}

main "$@"
