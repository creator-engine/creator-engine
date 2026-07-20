#!/usr/bin/env bash
set -euo pipefail

readonly PREFLIGHT_VERSION=1

usage() {
  cat <<'USAGE'
Usage: preflight-peer-identity.sh --env-file PATH --target-container NAME [--container-runtime PATH]

Version 1 deployment preflight. Before installing the egress-broker unit, it
reads the target container's uid/gid through the selected container runtime and
refuses installation when either value differs from the configured expected
peer identity in PATH.
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

read_expected_id() {
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

  [[ "$value" =~ ^[0-9]+$ ]] || fail "configured $key must be a decimal integer"
  printf '%s\n' "$value"
}

expected_uid="$(read_expected_id CE_EGRESS_BROKER_EXPECTED_PEER_UID)"
expected_gid="$(read_expected_id CE_EGRESS_BROKER_EXPECTED_PEER_GID)"
actual_uid="$("$container_runtime" exec -- "$target_container" id -u)" \
  || fail "could not read uid from target container: $target_container"
actual_gid="$("$container_runtime" exec -- "$target_container" id -g)" \
  || fail "could not read gid from target container: $target_container"

[[ "$actual_uid" =~ ^[0-9]+$ ]] || fail "target container returned a non-decimal uid"
[[ "$actual_gid" =~ ^[0-9]+$ ]] || fail "target container returned a non-decimal gid"
[[ "$expected_uid" == "$actual_uid" ]] || fail "refusing installation: configured peer uid $expected_uid differs from target uid $actual_uid"
[[ "$expected_gid" == "$actual_gid" ]] || fail "refusing installation: configured peer gid $expected_gid differs from target gid $actual_gid"

printf 'PASS: egress peer identity preflight v%s matched target %s\n' "$PREFLIGHT_VERSION" "$target_container"
