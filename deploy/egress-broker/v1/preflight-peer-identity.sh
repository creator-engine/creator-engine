#!/usr/bin/env bash
set -euo pipefail

readonly PREFLIGHT_VERSION=1

usage() {
  cat <<'USAGE'
Usage: preflight-peer-identity.sh --env-file PATH --target-container NAME [--container-runtime PATH]

Version 1 deployment preflight. Before installing the egress-broker unit, it
reads the target container's Creator Engine seat label and uid/gid through the
selected container runtime. It refuses activation unless the label matches the
configured seat and both ids match the configured expected peer identity in
PATH.
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

env_file=""
target_container=""
container_runtime="docker"

while (($#)); do
  case "$1" in
    --env-file)
      env_file="${2:?--env-file requires a path}"
      shift 2
      ;;
    --target-container)
      target_container="${2:?--target-container requires a name}"
      shift 2
      ;;
    --container-runtime)
      container_runtime="${2:?--container-runtime requires a path}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      fail "unknown argument: $1"
      ;;
  esac
done

[[ -n "$env_file" ]] || fail "--env-file is required"
[[ -n "$target_container" ]] || fail "--target-container is required"
[[ -f "$env_file" && ! -L "$env_file" ]] || fail "env file must be a regular file: $env_file"
command -v "$container_runtime" >/dev/null 2>&1 || fail "container runtime not found: $container_runtime"

read_required_env() {
  local key="$1"
  local line=""
  local value=""

  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      "$key"=*)
        [[ -z "$value" ]] || fail "duplicate environment key: $key"
        value="${line#*=}"
        ;;
    esac
  done < "$env_file"

  [[ -n "$value" ]] || fail "missing environment key: $key"
  printf '%s\n' "$value"
}

expected_seat="$(read_required_env CE_EGRESS_BROKER_SEAT)"
expected_uid="$(read_required_env CE_EGRESS_BROKER_EXPECTED_PEER_UID)"
expected_gid="$(read_required_env CE_EGRESS_BROKER_EXPECTED_PEER_GID)"
[[ "$expected_seat" =~ ^[a-z0-9][a-z0-9-]*$ ]] || fail "configured CE_EGRESS_BROKER_SEAT must be a lowercase seat identifier"
[[ "$expected_uid" =~ ^[0-9]+$ ]] || fail "configured CE_EGRESS_BROKER_EXPECTED_PEER_UID must be a decimal integer"
[[ "$expected_gid" =~ ^[0-9]+$ ]] || fail "configured CE_EGRESS_BROKER_EXPECTED_PEER_GID must be a decimal integer"
actual_seat="$("$container_runtime" inspect --format '{{ index .Config.Labels "io.creator-engine.seat" }}' -- "$target_container")" \
  || fail "could not read Creator Engine seat label from target container: $target_container"
actual_uid="$("$container_runtime" exec -- "$target_container" id -u)" \
  || fail "could not read uid from target container: $target_container"
actual_gid="$("$container_runtime" exec -- "$target_container" id -g)" \
  || fail "could not read gid from target container: $target_container"

[[ "$actual_seat" == "$expected_seat" ]] || fail "refusing activation: configured broker seat $expected_seat differs from target seat label $actual_seat"
[[ "$actual_uid" =~ ^[0-9]+$ ]] || fail "target container returned a non-decimal uid"
[[ "$actual_gid" =~ ^[0-9]+$ ]] || fail "target container returned a non-decimal gid"
[[ "$expected_uid" == "$actual_uid" ]] || fail "refusing installation: configured peer uid $expected_uid differs from target uid $actual_uid"
[[ "$expected_gid" == "$actual_gid" ]] || fail "refusing installation: configured peer gid $expected_gid differs from target gid $actual_gid"

printf 'PASS: egress peer identity preflight v%s matched seat %s target %s\n' "$PREFLIGHT_VERSION" "$expected_seat" "$target_container"
