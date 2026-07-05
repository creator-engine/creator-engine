#!/usr/bin/env bash
set -euo pipefail

SMOKE_TMPDIR=""

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
  printf 'daemon-container-smoke-signing-secret\n' > "$path"
  chmod 0600 "$path"
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
    export CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE="$secret_file"
    export CE_CONVEYOR_DAEMON_SEAT_PROBES='[{"seat_id":"smoke","argv":["bash","-lc","sleep 2"]}]'
    export GH_TOKEN="${GH_TOKEN:-daemon-container-smoke-token}"
    "$root/deploy/daemons/run-daemon-container.sh" conveyor-daemon --one-shot
  ) >"$log_path" 2>&1 &
  local runner_pid=$!

  wait_for_file "$lease_path" "pass $pass conveyor lease"
  printf 'pass %s acquired lease: %s\n' "$pass" "$lease_path"

  "$engine" stop --time 20 "$container_name" >/dev/null 2>&1 || true
  if ! wait "$runner_pid"; then
    printf '%s\n' "---- smoke pass $pass log ----" >&2
    sed -n '1,220p' "$log_path" >&2 || true
    die "daemon container smoke pass $pass failed"
  fi

  wait_for_absent "$lease_path" "pass $pass conveyor lease"
  assert_docker_state_owned_by_image_uid "$engine" "$state_root" "$image_uid"
  assert_absent "$state_root/queue-daemon-secret/approval-wall-secret"
  assert_absent "$state_root/run/creator-engine/conveyor-daemon-secret/signing-secret"
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
  trap 'rm -rf -- "$SMOKE_TMPDIR"' EXIT
  local secret_file="$SMOKE_TMPDIR/signing-secret"
  write_secret_file "$secret_file"

  run_pass 1 "$root" "$engine" "$image_uid" "$state_root" "$secret_file" "$SMOKE_TMPDIR"
  run_pass 2 "$root" "$engine" "$image_uid" "$state_root" "$secret_file" "$SMOKE_TMPDIR"

  printf 'OK: daemon container stateful smoke passed for %s\n' "$state_root"
}

main "$@"
