#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  deploy/dgx-runsc/build-image.sh [--image IMAGE] [--arch ARCH] [--dry-run]

Environment:
  CE_DGX_BUILD_IMAGE  Docker image tag (default: creator-engine/codex-runsc:0.144.1-aarch64)
  CE_DGX_USER         Runtime user name build arg (default: id -un)
  CE_DGX_UID          Runtime uid build arg (default: id -u)
  CE_DGX_GID          Runtime gid build arg (default: id -g)
EOF
}

quote_cmd() {
  printf '%q ' "$@"
  printf '\n'
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"
image="${CE_DGX_BUILD_IMAGE:-creator-engine/codex-runsc:0.144.1-aarch64}"
host_arch="$(dpkg --print-architecture 2>/dev/null || uname -m)"
case "${host_arch}" in
  aarch64)
    render_arch="arm64"
    ;;
  x86_64)
    render_arch="amd64"
    ;;
  *)
    render_arch="${host_arch}"
    ;;
esac
dry_run=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --image)
      image="${2:?missing image after --image}"
      shift 2
      ;;
    --arch)
      render_arch="${2:?missing arch after --arch}"
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
surface_build_args_file="$(mktemp "${TMPDIR:-/tmp}/ce-dgx-surface-build-args.XXXXXX")"
python3 "${repo_root}/surfaces/render.py" --arch "${render_arch}" build-args > "${surface_build_args_file}"
while read -r flag assignment; do
  surface_build_args+=("${flag}" "${assignment}")
done < "${surface_build_args_file}"
rm -f "${surface_build_args_file}"

docker_cmd=(
  docker build
  --file "${repo_root}/deploy/dgx-runsc/Dockerfile"
  --tag "${image}"
  "${surface_build_args[@]}"
  --build-arg "CE_DGX_USER=${CE_DGX_USER:-$(id -un)}"
  --build-arg "CE_DGX_UID=${CE_DGX_UID:-$(id -u)}"
  --build-arg "CE_DGX_GID=${CE_DGX_GID:-$(id -g)}"
  --build-arg "CODEX_VERSION=${CE_DGX_CODEX_VERSION:-0.144.1}"
  --build-arg "CODEX_SHA256=${CE_DGX_CODEX_SHA256:-9513fa3f5f4ad444ac1e40d972aef0e2664834ec54da987d54aba0dc2f13ea07}"
  "${repo_root}"
)

if [ "${dry_run}" = "1" ]; then
  quote_cmd "${docker_cmd[@]}"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to build the DGX runsc image; use --dry-run to inspect the command" >&2
  exit 127
fi

"${docker_cmd[@]}"
