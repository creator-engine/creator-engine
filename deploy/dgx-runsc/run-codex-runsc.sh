#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-codex-runsc.sh [--dry-run] [tui] [codex args...]
  run-codex-runsc.sh [--dry-run] exec [codex exec args...]

Environment:
  CE_DGX_IMAGE              Docker image tag (default: creator-engine/codex-runsc:0.141.0-aarch64)
  CE_DGX_RUNTIME            Docker runtime (default: runsc)
  CE_DGX_NETWORK            Docker network mode (default: bridge)
  CE_DGX_REPO               Host repo path (default: current directory)
  CE_DGX_CODEX_HOME         Host codex home (default: /home/cedev4/.codex)
  CE_DGX_CODEX_HOME_MODE    Mount mode for codex home: rw or ro (default: rw)
  CE_DGX_CODEX_BIN          Host standalone codex binary
  CE_DGX_CONTAINER_REPO     Container repo path (default: /workspace/creator-engine)
  CE_DGX_CONTAINER_USER     Container seat user name (default: cedev4)
  CE_DGX_UID                Container uid (default: id -u)
  CE_DGX_GID                Container gid (default: id -g)
  CE_DGX_TTY_FLAGS          Docker TTY flags (default: -it; set to -i for non-TTY callers)
  CE_DGX_DRY_RUN            Print docker argv instead of executing when set to 1
EOF
}

dry_run="${CE_DGX_DRY_RUN:-0}"
if [ "${1:-}" = "--dry-run" ]; then
  dry_run=1
  shift
fi
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

mode="tui"
if [ "${1:-}" = "tui" ] || [ "${1:-}" = "exec" ]; then
  mode="$1"
  shift
fi

CE_DGX_IMAGE="${CE_DGX_IMAGE:-creator-engine/codex-runsc:0.141.0-aarch64}"
CE_DGX_RUNTIME="${CE_DGX_RUNTIME:-runsc}"
CE_DGX_NETWORK="${CE_DGX_NETWORK:-bridge}"
CE_DGX_REPO="${CE_DGX_REPO:-$(pwd)}"
CE_DGX_CODEX_HOME="${CE_DGX_CODEX_HOME:-/home/cedev4/.codex}"
CE_DGX_CODEX_HOME_MODE="${CE_DGX_CODEX_HOME_MODE:-rw}"
CE_DGX_CODEX_BIN="${CE_DGX_CODEX_BIN:-/home/cedev4/.codex/packages/standalone/releases/0.141.0-aarch64-unknown-linux-musl/bin/codex}"
CE_DGX_CONTAINER_REPO="${CE_DGX_CONTAINER_REPO:-/workspace/creator-engine}"
CE_DGX_CONTAINER_USER="${CE_DGX_CONTAINER_USER:-cedev4}"
CE_DGX_CONTAINER_HOME="/home/${CE_DGX_CONTAINER_USER}"
CE_DGX_CONTAINER_CODEX_HOME="${CE_DGX_CONTAINER_HOME}/.codex"
CE_DGX_UID="${CE_DGX_UID:-$(id -u)}"
CE_DGX_GID="${CE_DGX_GID:-$(id -g)}"
CE_DGX_TTY_FLAGS="${CE_DGX_TTY_FLAGS:--it}"

if [ "${CE_DGX_CODEX_HOME_MODE}" != "rw" ] && [ "${CE_DGX_CODEX_HOME_MODE}" != "ro" ]; then
  printf 'CE_DGX_CODEX_HOME_MODE must be rw or ro, got %s\n' "${CE_DGX_CODEX_HOME_MODE}" >&2
  exit 2
fi

if [ "${dry_run}" != "1" ]; then
  command -v docker >/dev/null 2>&1 || { printf 'docker not found\n' >&2; exit 127; }
  [ -d "${CE_DGX_REPO}" ] || { printf 'repo path not found: %s\n' "${CE_DGX_REPO}" >&2; exit 66; }
  [ -d "${CE_DGX_CODEX_HOME}" ] || { printf 'codex home not found: %s\n' "${CE_DGX_CODEX_HOME}" >&2; exit 66; }
  [ -x "${CE_DGX_CODEX_BIN}" ] || { printf 'codex binary not executable: %s\n' "${CE_DGX_CODEX_BIN}" >&2; exit 66; }
fi

tty_flags=()
if [ -n "${CE_DGX_TTY_FLAGS}" ]; then
  read -r -a tty_flags <<<"${CE_DGX_TTY_FLAGS}"
fi

container_cmd=(/usr/local/bin/codex)
if [ "${mode}" = "exec" ]; then
  container_cmd+=(exec)
fi
container_cmd+=("$@")

repo_mount="type=bind,source=${CE_DGX_REPO},target=${CE_DGX_CONTAINER_REPO}"
codex_home_mount="type=bind,source=${CE_DGX_CODEX_HOME},target=${CE_DGX_CONTAINER_CODEX_HOME}"
if [ "${CE_DGX_CODEX_HOME_MODE}" = "ro" ]; then
  codex_home_mount="${codex_home_mount},readonly"
fi
codex_bin_mount="type=bind,source=${CE_DGX_CODEX_BIN},target=/usr/local/bin/codex,readonly"

docker_cmd=(
  docker run --rm
  "--runtime=${CE_DGX_RUNTIME}"
  "--network=${CE_DGX_NETWORK}"
  --security-opt=no-new-privileges
  --cap-drop=ALL
  --user "${CE_DGX_UID}:${CE_DGX_GID}"
  --workdir "${CE_DGX_CONTAINER_REPO}"
  --env "HOME=${CE_DGX_CONTAINER_HOME}"
  --env "CODEX_HOME=${CE_DGX_CONTAINER_CODEX_HOME}"
  --env "TERM=${TERM:-xterm-256color}"
  --mount "${repo_mount}"
  --mount "${codex_home_mount}"
  --mount "${codex_bin_mount}"
)

docker_cmd+=("${tty_flags[@]}")
docker_cmd+=("${CE_DGX_IMAGE}")
docker_cmd+=("${container_cmd[@]}")

if [ "${dry_run}" = "1" ]; then
  printf '%q ' "${docker_cmd[@]}"
  printf '\n'
  exit 0
fi

exec "${docker_cmd[@]}"
