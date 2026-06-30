#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  deploy/vps-runsc/build-image.sh [--image IMAGE] [--dry-run]

Environment:
  CE_VPS_BUILD_IMAGE  Docker image tag (default: creator-engine/codex-runsc:x86_64)
  CE_VPS_USER         Runtime user name build arg (default: id -un)
  CE_VPS_UID          Runtime uid build arg (default: id -u)
  CE_VPS_GID          Runtime gid build arg (default: id -g)
EOF
}

quote_cmd() {
  printf '%q ' "$@"
  printf '\n'
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"
image="${CE_VPS_BUILD_IMAGE:-creator-engine/codex-runsc:x86_64}"
dry_run=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --image)
      image="${2:?missing image after --image}"
      shift 2
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

surface_build_args=()
surface_build_args_file="$(mktemp "${TMPDIR:-/tmp}/ce-vps-surface-build-args.XXXXXX")"
python3 "${repo_root}/surfaces/render.py" --arch amd64 build-args > "${surface_build_args_file}"
while read -r flag assignment; do
  surface_build_args+=("${flag}" "${assignment}")
done < "${surface_build_args_file}"
rm -f "${surface_build_args_file}"

docker_cmd=(
  docker build
  --file "${repo_root}/deploy/vps-runsc/Dockerfile"
  --tag "${image}"
  "${surface_build_args[@]}"
  --build-arg "CE_VPS_USER=${CE_VPS_USER:-$(id -un)}"
  --build-arg "CE_VPS_UID=${CE_VPS_UID:-$(id -u)}"
  --build-arg "CE_VPS_GID=${CE_VPS_GID:-$(id -g)}"
  "${repo_root}"
)

if [ "${dry_run}" = "1" ]; then
  quote_cmd "${docker_cmd[@]}"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to build the VPS runsc image; use --dry-run to inspect the command" >&2
  exit 127
fi

"${docker_cmd[@]}"
