#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Build the Creator Engine validator OCI image.

Usage:
  deploy/oci/build-image.sh [--image IMAGE] [--platform PLATFORM[,PLATFORM...]] [--load|--push] [--dry-run]

Defaults:
  IMAGE:    creator-engine/ce-validator:0.3.4
  PLATFORM: linux/arm64
  OUTPUT:   --load for a single platform, --push when explicitly requested

Examples:
  deploy/oci/build-image.sh
  deploy/oci/build-image.sh --platform linux/arm64,linux/amd64 --push
  deploy/oci/build-image.sh --dry-run

Run the built image:
  docker run --rm creator-engine/ce-validator:0.3.4 ce --help
  docker run --rm -v "$PWD:/workspace/creator-engine" -w /workspace/creator-engine \
    creator-engine/ce-validator:0.3.4 creator-engine-validator check-examples
USAGE
}

quote_cmd() {
  printf '%q ' "$@"
  printf '\n'
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
image="${CE_OCI_IMAGE:-creator-engine/ce-validator:0.3.4}"
platform="${CE_OCI_PLATFORM:-linux/arm64}"
output_mode="${CE_OCI_OUTPUT_MODE:-load}"
dry_run=0
source_date_epoch="${SOURCE_DATE_EPOCH:-946684800}"
keep_context="${CE_OCI_KEEP_CONTEXT:-0}"

if [ -n "${CE_OCI_CONTEXT_DIR:-}" ]; then
  context_dir="${CE_OCI_CONTEXT_DIR}"
  context_dir_auto=0
else
  context_dir="$(mktemp -d "${TMPDIR:-/tmp}/ce-oci-context.XXXXXX")"
  context_dir_auto=1
fi

cleanup() {
  if [ "${keep_context}" != "1" ] && [ "${context_dir_auto}" = "1" ]; then
    rm -rf "${context_dir}"
  fi
}
trap cleanup EXIT

require_buildx() {
  if ! command -v docker >/dev/null 2>&1 || ! docker buildx version >/dev/null 2>&1; then
    printf '%s\n' \
      'docker buildx is required to build the Creator Engine validator OCI image.' \
      'Install or enable the Docker Buildx plugin, then rerun deploy/oci/build-image.sh.' \
      'Use --dry-run to inspect the build command without Docker or buildx.' >&2
    exit 127
  fi
}

render_surface_build_args() {
  local surface_arch
  case "${platform}" in
    linux/arm64)
      surface_arch="arm64"
      ;;
    linux/amd64)
      surface_arch="amd64"
      ;;
    linux/arm64,linux/amd64|linux/amd64,linux/arm64)
      # Buildx needs the manifest-list pin for a true multi-platform build;
      # a child digest is valid for only one target architecture. Render the
      # manifest-list record as the existing Dockerfile argument and omit the
      # child-only keys.
      python3 "${repo_root}/surfaces/render.py" build-args | sed \
        -e '/OCI_CPYTHON_BASE_IMAGE_AMD64_COMMIT_OR_DIGEST=/d' \
        -e '/OCI_CPYTHON_BASE_IMAGE_ARM64_COMMIT_OR_DIGEST=/d' \
        -e 's/OCI_CPYTHON_BASE_IMAGE_MANIFEST_LIST_COMMIT_OR_DIGEST=/OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST=/'
      return
      ;;
    *)
      printf 'unsupported OCI platform: %s (expected linux/arm64 or linux/amd64)\n' "${platform}" >&2
      exit 2
      ;;
  esac
  # Preserve the full rendered provenance set in the dry-run/build command,
  # then append the architecture-selected generic arguments consumed by the
  # OCI Dockerfile. The latter comes last, so its child digest is authoritative
  # for this single-platform build.
  python3 "${repo_root}/surfaces/render.py" build-args
  python3 "${repo_root}/surfaces/render.py" --arch "${surface_arch}" build-args
}

print_stage_context_commands() {
  quote_cmd rm -rf "${context_dir}/validators"
  quote_cmd mkdir -p "${context_dir}/validators"
  quote_cmd cp "${repo_root}/validators/pyproject.toml" "${context_dir}/validators/pyproject.toml"
  quote_cmd cp -R "${repo_root}/validators/creator_engine_validator" "${context_dir}/validators/creator_engine_validator"
  quote_cmd cp -R "${repo_root}/validators/wheelhouse" "${context_dir}/validators/wheelhouse"
  quote_cmd cp -R "${repo_root}/validators/wheelhouse-dev" "${context_dir}/validators/wheelhouse-dev"
  quote_cmd find "${context_dir}" -type d '(' -name __pycache__ -o -name .pytest_cache -o -name build -o -name '*.egg-info' ')' -prune -exec rm -rf '{}' '+'
  quote_cmd find "${context_dir}" -type f '(' -name '*.pyc' -o -name '*.pyo' ')' -delete
}

stage_context() {
  rm -rf "${context_dir}/validators"
  mkdir -p "${context_dir}/validators"
  cp "${repo_root}/validators/pyproject.toml" "${context_dir}/validators/pyproject.toml"
  cp -R "${repo_root}/validators/creator_engine_validator" "${context_dir}/validators/creator_engine_validator"
  cp -R "${repo_root}/validators/wheelhouse" "${context_dir}/validators/wheelhouse"
  cp -R "${repo_root}/validators/wheelhouse-dev" "${context_dir}/validators/wheelhouse-dev"
  find "${context_dir}" -type d \( -name __pycache__ -o -name .pytest_cache -o -name build -o -name '*.egg-info' \) -prune -exec rm -rf {} +
  find "${context_dir}" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --image)
      image="${2:?missing image after --image}"
      shift 2
      ;;
    --platform)
      platform="${2:?missing platform after --platform}"
      shift 2
      ;;
    --load)
      output_mode="load"
      shift
      ;;
    --push)
      output_mode="push"
      shift
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

if [[ "${platform}" == *","* && "${output_mode}" == "load" ]]; then
  printf 'multi-platform builds require --push; --load supports one platform only\n' >&2
  exit 2
fi

if [ "${dry_run}" != "1" ]; then
  require_buildx
fi

surface_build_args=()
surface_build_args_file="$(mktemp "${TMPDIR:-/tmp}/ce-surface-build-args.XXXXXX")"
render_surface_build_args > "${surface_build_args_file}"
while read -r flag assignment; do
  surface_build_args+=("${flag}" "${assignment}")
done < "${surface_build_args_file}"
rm -f "${surface_build_args_file}"

source_commit="$(git -C "${repo_root}" rev-parse --verify HEAD)"

docker_cmd=(
  docker buildx build
  --file "${repo_root}/deploy/oci/Dockerfile"
  --platform "${platform}"
  "${surface_build_args[@]}"
  --build-arg "SOURCE_DATE_EPOCH=${source_date_epoch}"
  --build-arg "CE_IMAGE_REVISION=${source_commit}"
  --tag "${image}"
)

case "${output_mode}" in
  load) docker_cmd+=(--load) ;;
  push) docker_cmd+=(--push) ;;
  *)
    printf 'unsupported CE_OCI_OUTPUT_MODE: %s\n' "${output_mode}" >&2
    exit 2
    ;;
esac

docker_cmd+=("${context_dir}")

if [ "${dry_run}" = "1" ]; then
  print_stage_context_commands
  quote_cmd "${docker_cmd[@]}"
  quote_cmd docker run --rm "${image}" ce --help
  exit 0
fi

stage_context
"${docker_cmd[@]}"

cat <<EOF

Run the image:
  docker run --rm ${image} ce --help
  docker run --rm -v "\$PWD:/workspace/creator-engine" -w /workspace/creator-engine ${image} creator-engine-validator check-examples
EOF
