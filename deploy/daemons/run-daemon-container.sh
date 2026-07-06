#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: run-daemon-container.sh <queue-daemon|conveyor-daemon> [daemon args...]

Runs a Creator Engine governance daemon inside the canonical runtime image.
The container engine is selected by CE_CONTAINER_ENGINE (docker or podman).

Required for queue-daemon runtime:
  GH_TOKEN, BAO_TOKEN, BAO_ADDR, CE_GATE_REPO, CE_GATE_AUTHORIZED_REVIEWERS,
  CE_OPENBAO_KV_MOUNT, CE_APPROVAL_WALL_SECRET_PATH,
  CE_APPROVAL_WALL_SECRET_FIELD, CE_APPROVAL_WALL_POLICY_SHA,
  CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA

Optional container variables:
  CE_CONTAINER_ENGINE              docker or podman executable; default docker
  CE_DAEMON_IMAGE                  canonical runtime image; default ghcr.io/creator-engine/creator-engine/ce-runtime:0.3.2
  CE_DAEMON_IMAGE_UID              canonical image uid/gid contract; default 10001
  CE_DAEMON_CONTAINER_NAME         default ce-<daemon>
  CE_DAEMON_REPO_ROOT              host checkout; default repository root
  CE_DAEMON_REPO_CONTAINER_PATH    default /workspace/creator-engine
  CE_DAEMON_STATE_ROOT             host state root; default <repo>/.ce/state
  CE_DAEMON_STATE_CONTAINER_PATH   default /ce/state
  CE_DAEMON_LEASE_ROOT             host lease root; default <state root>/daemon-leases
  CE_DAEMON_CONTAINER_LEASE_ROOT   explicit in-container lease root; default maps host lease root into /ce/state
  CE_DAEMON_ENV_FILE               optional host env file; must exist with mode 0600
  CE_DAEMON_CACERT_FILE            optional host CA cert mounted read-only for BAO_CACERT
  CE_DAEMON_TOKEN_FILE             optional host token file mounted read-only
  CE_DAEMON_TOKEN_CONTAINER_PATH   default /run/creator-engine/daemon-token
  CE_DAEMON_LOG_DIR                host log directory; default $HOME
  CE_CONVEYOR_DAEMON_*             conveyor-daemon config forwarded when present

No secret values are baked into the image or this script. Host bootstrap must
supply secrets through its approved runtime environment or token file path.
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
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

add_env_if_present() {
  local name="$1"
  if [[ -n "${!name+x}" ]]; then
    container_args+=(--env "$name")
  fi
}

file_mode() {
  local path="$1"
  stat -c '%a' -- "$path" 2>/dev/null || stat -f '%Lp' -- "$path"
}

file_uid() {
  local path="$1"
  stat -c '%u' -- "$path" 2>/dev/null || stat -f '%u' -- "$path"
}

is_unsigned_int() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

engine_requires_host_uid_match() {
  local engine="$1"
  [[ "$(basename -- "$engine")" == "docker" ]]
}

host_uid() {
  id -u
}

path_is_under_state_root() {
  local path="$1"
  local state_root="$2"
  [[ "$path" == "$state_root"/* ]]
}

should_defer_state_child_prep_to_container() {
  local path="$1"
  local state_root="$2"
  local image_uid="$3"
  local require_host_uid_match="$4"

  [[ "$require_host_uid_match" == "1" ]] || return 1
  [[ "$path" != "$state_root" ]] || return 1
  path_is_under_state_root "$path" "$state_root" || return 1

  local current_uid
  current_uid="$(host_uid)" || return 1
  [[ "$current_uid" != "0" && "$current_uid" != "$image_uid" ]] || return 1

  local state_mode state_owner_uid
  state_mode="$(file_mode "$state_root")" || return 1
  state_owner_uid="$(file_uid "$state_root")" || return 1
  [[ "$state_mode" == "700" && "$state_owner_uid" == "$image_uid" ]]
}

prepare_state_root_dir() {
  local label="$1"
  local path="$2"
  local state_root="$3"
  local image_uid="$4"
  local require_host_uid_match="$5"

  if should_defer_state_child_prep_to_container "$path" "$state_root" "$image_uid" "$require_host_uid_match"; then
    return 0
  fi

  if [[ -e "$path" && ! -d "$path" ]]; then
    die "$label exists but is not a directory: $path"
  fi

  if [[ ! -e "$path" ]]; then
    if [[ "$require_host_uid_match" == "1" ]]; then
      install -d -m 0700 -o "$image_uid" -g "$image_uid" "$path" 2>/dev/null || \
        install -d -m 0700 "$path" || die "cannot create $label: $path"
    else
      install -d -m 0700 "$path" || die "cannot create $label: $path"
    fi
  fi

  local mode
  mode="$(file_mode "$path")" || die "cannot stat $label: $path"
  [[ "$mode" == "700" ]] || die "$label must be mode 0700: $path (mode $mode). Run: chmod 0700 $path"

  if [[ "$require_host_uid_match" == "1" ]]; then
    local owner_uid
    owner_uid="$(file_uid "$path")" || die "cannot stat $label owner: $path"
    [[ "$owner_uid" == "$image_uid" ]] || die "$label owner uid $owner_uid does not match canonical container uid $image_uid: $path. Run: chown -R $image_uid:$image_uid $state_root"
  fi
}

setup_attempt_log() {
  local daemon="$1"
  local root="$2"
  local log_dir="${CE_DAEMON_LOG_DIR:-${HOME:-$root}}"
  local timestamp
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  install -d -m 0700 "$log_dir" || die "cannot create CE_DAEMON_LOG_DIR: $log_dir"

  local log_path="$log_dir/ce-wall-daemon-container-$daemon-$timestamp-$$.log"
  local latest_path="$log_dir/ce-wall-daemon-container.log"
  : >"$log_path" || die "cannot create daemon attempt log: $log_path"
  chmod 0600 "$log_path" || die "cannot chmod daemon attempt log: $log_path"
  ln -sfn "$(basename -- "$log_path")" "$latest_path" 2>/dev/null || true

  exec > >(tee -a "$log_path") 2> >(tee -a "$log_path" >&2)
}

require_mode_0600() {
  local name="$1"
  local path="$2"
  [[ -f "$path" ]] || die "$name does not name a file: $path"
  local mode
  mode="$(file_mode "$path")" || die "cannot stat $name: $path"
  [[ "$mode" == "600" ]] || die "$name must be mode 0600: $path (mode $mode)"
}

main() {
  if [[ $# -lt 1 ]]; then
    usage >&2
    exit 2
  fi
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
  esac

  local daemon="$1"
  shift

  local engine="${CE_CONTAINER_ENGINE:-docker}"
  command -v "$engine" >/dev/null 2>&1 || die "container engine not found: $engine"

  local root
  root="$(repo_root)"
  setup_attempt_log "$daemon" "$root"
  local repo_container="${CE_DAEMON_REPO_CONTAINER_PATH:-/workspace/creator-engine}"
  local state_root="${CE_DAEMON_STATE_ROOT:-$root/.ce/state}"
  local state_container="${CE_DAEMON_STATE_CONTAINER_PATH:-/ce/state}"
  local host_lease_root="${CE_DAEMON_LEASE_ROOT:-$state_root/daemon-leases}"
  local container_lease_root
  if [[ -n "${CE_DAEMON_CONTAINER_LEASE_ROOT:-}" ]]; then
    container_lease_root="$CE_DAEMON_CONTAINER_LEASE_ROOT"
  else
    case "$host_lease_root" in
      "$state_root")
        container_lease_root="$state_container"
        ;;
      "$state_root"/*)
        container_lease_root="$state_container/${host_lease_root#"$state_root"/}"
        ;;
      *)
        die "CE_DAEMON_LEASE_ROOT must be under CE_DAEMON_STATE_ROOT for contained daemons; use CE_DAEMON_CONTAINER_LEASE_ROOT only for an explicit in-container path"
        ;;
    esac
  fi
  local image="${CE_DAEMON_IMAGE:-ghcr.io/creator-engine/creator-engine/ce-runtime:0.3.2}"
  # Canonical daemon image contract: the runtime user is uid/gid 10001 (`ce`).
  local image_uid="${CE_DAEMON_IMAGE_UID:-10001}"
  is_unsigned_int "$image_uid" || die "CE_DAEMON_IMAGE_UID must be a numeric uid/gid: $image_uid"
  local container_name="${CE_DAEMON_CONTAINER_NAME:-ce-$daemon}"
  local queue_secret_container_dir="$state_container/queue-daemon-secret"
  local queue_secret_target="$state_container/queue-daemon/approval-wall-secret"
  local queue_secret_uses_tmpfs=0
  if [[ -n "${CE_APPROVAL_WALL_SECRET_TARGET_FILE:-}" ]]; then
    queue_secret_target="$queue_secret_container_dir/approval-wall-secret"
    queue_secret_uses_tmpfs=1
  fi

  local require_host_uid_match=0
  if engine_requires_host_uid_match "$engine"; then
    require_host_uid_match=1
  fi
  prepare_state_root_dir CE_DAEMON_STATE_ROOT "$state_root" "$state_root" "$image_uid" "$require_host_uid_match"
  prepare_state_root_dir CE_DAEMON_LEASE_ROOT "$host_lease_root" "$state_root" "$image_uid" "$require_host_uid_match"

  local -a container_args=(
    run
    --rm
    --name "$container_name"
    --workdir "$repo_container"
    --user "$image_uid:$image_uid"
    --volume "$root:$repo_container:ro"
    --volume "$state_root:$state_container"
    --env "CE_DAEMON_UNCONTAINED=1"
    --env "CE_DAEMON_STATE_ROOT=$state_container"
    --env "CE_DAEMON_LEASE_ROOT=$container_lease_root"
    --env "CE_QUEUE_DAEMON_BIN=cev3"
    --env "CE_QUEUE_DAEMON_REPO_ROOT=$repo_container"
    --env "CE_QUEUE_DAEMON_ROOT=$state_container/queue-daemon/v3"
    --env "CE_APPROVAL_WALL_SECRET_TARGET_FILE=$queue_secret_target"
    --env "CE_APPROVAL_WALL_STATE=$state_container/queue-daemon/approval-wall-state.json"
  )

  if [[ "$queue_secret_uses_tmpfs" == "1" ]]; then
    container_args+=(--tmpfs "$queue_secret_container_dir:rw,size=1m,mode=0700,uid=$image_uid,gid=$image_uid")
  fi

  if [[ -n "${CE_DAEMON_ENV_FILE:-}" ]]; then
    require_mode_0600 CE_DAEMON_ENV_FILE "$CE_DAEMON_ENV_FILE"
    # Docker and Podman let explicit --env values override values loaded from
    # --env-file, so keep direct exports below as the higher-precedence source.
    container_args+=(--env-file "$CE_DAEMON_ENV_FILE")
  fi

  for env_name in \
    GH_TOKEN \
    BAO_TOKEN \
    BAO_ADDR \
    BAO_CACERT \
    CE_GATE_REPO \
    CE_GATE_AUTHORIZED_REVIEWERS \
    CE_OPENBAO_KV_MOUNT \
    CE_APPROVAL_WALL_SECRET_PATH \
    CE_APPROVAL_WALL_SECRET_FIELD \
    CE_APPROVAL_WALL_POLICY_SHA \
    CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA \
    CE_APPROVAL_WALL_SECRET_PURPOSE \
    CE_APPROVAL_WALL_SECRET_OWNER_REF \
    CE_APPROVAL_WALL_SECRET_RUN_ID \
    CE_APPROVAL_WALL_SECRET_SEAT_ID \
    CE_APPROVAL_WALL_SECRET_TTL_SECONDS \
    CE_APPROVAL_WALL_MARKER_TTL_SECONDS \
    CE_APPROVAL_WALL_SECRET_VERSION \
    CE_QUEUE_DAEMON_INTERVAL_SECONDS \
    CE_QUEUE_DAEMON_APPROVAL_SETTLE_SECONDS \
    CE_QUEUE_DAEMON_DRY_RUN
  do
    if [[ "$env_name" == "BAO_CACERT" && -n "${CE_DAEMON_CACERT_FILE:-}" ]]; then
      continue
    fi
    add_env_if_present "$env_name"
  done

  if [[ -n "${CE_DAEMON_CACERT_FILE:-}" ]]; then
    [[ -f "$CE_DAEMON_CACERT_FILE" ]] || die "CE_DAEMON_CACERT_FILE does not name a file: $CE_DAEMON_CACERT_FILE"
    local cacert_container="/ce/etc/openbao-ca.crt"
    container_args+=(--volume "$CE_DAEMON_CACERT_FILE:$cacert_container:ro")
    container_args+=(--env "BAO_CACERT=$cacert_container")
  fi

  if [[ -n "${CE_DAEMON_TOKEN_FILE:-}" ]]; then
    [[ -f "$CE_DAEMON_TOKEN_FILE" ]] || die "CE_DAEMON_TOKEN_FILE does not name a file: $CE_DAEMON_TOKEN_FILE"
    local token_container="${CE_DAEMON_TOKEN_CONTAINER_PATH:-/run/creator-engine/daemon-token}"
    container_args+=(--volume "$CE_DAEMON_TOKEN_FILE:$token_container:ro")
    container_args+=(--env "CE_DAEMON_TOKEN_FILE=$token_container")
  fi

  local -a daemon_cmd
  case "$daemon" in
    queue-daemon)
      daemon_cmd=(bash "$repo_container/deploy/queue-daemon/launch-queue-daemon.sh" "$@")
      ;;
    conveyor-daemon)
      container_args+=(--env "CE_CONVEYOR_DAEMON_REPO_ROOT=${CE_CONVEYOR_DAEMON_REPO_ROOT:-$repo_container}")
      container_args+=(--env "CE_CONVEYOR_DAEMON_RUNTIME_ROOT=${CE_CONVEYOR_DAEMON_RUNTIME_ROOT:-$state_container/conveyor-daemon/runtime}")
      container_args+=(--env "CE_CONVEYOR_DAEMON_DISCOVERY_STATE=${CE_CONVEYOR_DAEMON_DISCOVERY_STATE:-$state_container/conveyor-daemon/discovery-state.json}")
      container_args+=(--env "CE_CONVEYOR_DAEMON_LEDGER_PATH=${CE_CONVEYOR_DAEMON_LEDGER_PATH:-$state_container/conveyor-daemon/conveyor-daemon-ledger.jsonl}")
      container_args+=(--env "CE_CONVEYOR_DAEMON_VALIDATION_LEDGER_ROOT=${CE_CONVEYOR_DAEMON_VALIDATION_LEDGER_ROOT:-$state_container/conveyor-daemon/side-effect-ledger}")
      container_args+=(--env "CE_CONVEYOR_DAEMON_ACTIVE_WORK_LEDGER_ROOT=${CE_CONVEYOR_DAEMON_ACTIVE_WORK_LEDGER_ROOT:-$state_container/conveyor-daemon/active-work-ledger}")
      for env_name in \
        CE_CONVEYOR_DAEMON_SEAT_PROBES \
        CE_CONVEYOR_DAEMON_SIGNING_SECRET \
        CE_CONVEYOR_DAEMON_INTERVAL_SECONDS \
        CE_CONVEYOR_DAEMON_ITERATIONS
      do
        add_env_if_present "$env_name"
      done
      if [[ -n "${CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE:-}" ]]; then
        [[ -f "$CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE" ]] || die "CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE does not name a file: $CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE"
        local conveyor_secret_container_dir="/run/creator-engine/conveyor-daemon-secret"
        local conveyor_secret_container="$conveyor_secret_container_dir/signing-secret"
        container_args+=(--tmpfs "$conveyor_secret_container_dir:rw,size=1m,mode=0700,uid=$image_uid,gid=$image_uid")
        container_args+=(--volume "$CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE:$conveyor_secret_container:ro")
        container_args+=(--env "CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE=$conveyor_secret_container")
      fi
      daemon_cmd=(bash "$repo_container/deploy/conveyor-daemon/launch-conveyor-daemon.sh" "$@")
      ;;
    *)
      usage >&2
      die "unknown daemon: $daemon"
      ;;
  esac

  exec "$engine" "${container_args[@]}" "$image" "${daemon_cmd[@]}"
}

main "$@"
