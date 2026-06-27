#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  deploy/dgx-controller-runsc/build-image.sh [--image IMAGE] [--dry-run]

Environment:
  CE_DGX_CONTROLLER_BUILD_IMAGE  Docker image tag (default: creator-engine/claude-controller-runsc:c1)
  CE_DGX_USER                    Runtime user name build arg (default: id -un)
  CE_DGX_UID                     Runtime uid build arg (default: id -u)
  CE_DGX_GID                     Runtime gid build arg (default: id -g)
EOF
}

quote_cmd() {
  printf '%q ' "$@"
  printf '\n'
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"
image="${CE_DGX_CONTROLLER_BUILD_IMAGE:-creator-engine/claude-controller-runsc:c1}"
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
surface_build_args_file="$(mktemp "${TMPDIR:-/tmp}/ce-dgx-controller-surface-build-args.XXXXXX")"
python3 "${repo_root}/surfaces/render.py" build-args > "${surface_build_args_file}"
while read -r flag assignment; do
  surface_build_args+=("${flag}" "${assignment}")
done < "${surface_build_args_file}"
rm -f "${surface_build_args_file}"

docker_cmd=(
  docker build
  --file "${repo_root}/deploy/dgx-controller-runsc/Dockerfile"
  --tag "${image}"
  "${surface_build_args[@]}"
  --build-arg "CE_DGX_USER=${CE_DGX_USER:-$(id -un)}"
  --build-arg "CE_DGX_UID=${CE_DGX_UID:-$(id -u)}"
  --build-arg "CE_DGX_GID=${CE_DGX_GID:-$(id -g)}"
  "${repo_root}"
)

if [ "${dry_run}" = "1" ]; then
  quote_cmd "${docker_cmd[@]}"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to build the DGX controller runsc image; use --dry-run to inspect the command" >&2
  exit 127
fi

"${docker_cmd[@]}"
