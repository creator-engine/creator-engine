#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-vps-runsc.sh [--dry-run] [--harness codex|claude|controller] [tui] [harness args...]
  run-vps-runsc.sh [--dry-run] [--harness codex|claude|controller] exec [harness exec args...]

Environment:
  CE_VPS_IMAGE                 Docker image tag (default: creator-engine/codex-runsc:x86_64)
  CE_VPS_RUNTIME               Docker runtime (default: runsc-gvproxy-ptrace)
  CE_VPS_DOCKER_NETWORK        Docker --network value (default: host)
  CE_VPS_HARNESS               Harness: codex, claude, or controller (default: codex)
  CE_DGX_HARNESS               Deprecated alias for CE_VPS_HARNESS
  CE_VPS_REPO                  Host repo path (default: current directory)
  CE_VPS_CODEX_HOME            Host codex home (default: $HOME/.codex)
  CE_VPS_CODEX_HOME_MODE       Mount mode for codex home: rw or ro (default: rw)
  CE_VPS_CODEX_BIN             Host standalone codex binary (default: first codex on PATH)
  CE_VPS_CLAUDE_BIN            Optional host Claude binary mounted at /usr/local/bin/claude
  CE_VPS_CONTAINER_REPO        Container repo path (default: /workspace/creator-engine)
  CE_VPS_CONTAINER_USER        Container seat user name (default: current user)
  CE_VPS_UID                   Container uid (default: id -u)
  CE_VPS_GID                   Container gid (default: id -g)
  CE_VPS_TTY_FLAGS             Docker TTY flags (default: -it; set to -i for non-TTY callers)
  CE_VPS_DRY_RUN               Print docker argv instead of executing when set to 1
EOF
}

dry_run="${CE_VPS_DRY_RUN:-0}"
if [ "${1:-}" = "--dry-run" ]; then
  dry_run=1
  shift
fi
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

harness="${CE_VPS_HARNESS:-${CE_DGX_HARNESS:-codex}}"
if [ "${1:-}" = "--harness" ]; then
  if [ -z "${2:-}" ]; then
    printf '%s\n' '--harness requires codex, claude, or controller' >&2
    exit 2
  fi
  harness="$2"
  shift 2
fi

mode="tui"
if [ "${1:-}" = "tui" ] || [ "${1:-}" = "exec" ]; then
  mode="$1"
  shift
fi

case "${harness}" in
  codex)
    image_harness="codex"
    ;;
  claude | controller)
    image_harness="claude"
    ;;
  *)
    printf 'CE_VPS_HARNESS must be codex, claude, or controller; got %s\n' "${harness}" >&2
    exit 2
    ;;
esac

CE_VPS_IMAGE="${CE_VPS_IMAGE:-creator-engine/codex-runsc:x86_64}"
CE_VPS_RUNTIME="${CE_VPS_RUNTIME:-runsc-gvproxy-ptrace}"
CE_VPS_DOCKER_NETWORK="${CE_VPS_DOCKER_NETWORK:-host}"
CE_VPS_REPO="${CE_VPS_REPO:-$(pwd)}"
CE_VPS_CODEX_HOME="${CE_VPS_CODEX_HOME:-${HOME:-/home/ce}/.codex}"
CE_VPS_CODEX_HOME_MODE="${CE_VPS_CODEX_HOME_MODE:-rw}"
CE_VPS_CODEX_BIN="${CE_VPS_CODEX_BIN:-$(command -v codex 2>/dev/null || true)}"
CE_VPS_CLAUDE_BIN="${CE_VPS_CLAUDE_BIN:-}"
CE_VPS_CONTAINER_REPO="${CE_VPS_CONTAINER_REPO:-/workspace/creator-engine}"
CE_VPS_CONTAINER_USER="${CE_VPS_CONTAINER_USER:-$(id -un 2>/dev/null || printf ce)}"
CE_VPS_CONTAINER_HOME="/home/${CE_VPS_CONTAINER_USER}"
CE_VPS_CONTAINER_CODEX_HOME="${CE_VPS_CONTAINER_HOME}/.codex"
CE_VPS_UID="${CE_VPS_UID:-$(id -u)}"
CE_VPS_GID="${CE_VPS_GID:-$(id -g)}"
CE_VPS_TTY_FLAGS="${CE_VPS_TTY_FLAGS:--it}"

if [ "${CE_VPS_CODEX_HOME_MODE}" != "rw" ] && [ "${CE_VPS_CODEX_HOME_MODE}" != "ro" ]; then
  printf 'CE_VPS_CODEX_HOME_MODE must be rw or ro, got %s\n' "${CE_VPS_CODEX_HOME_MODE}" >&2
  exit 2
fi

if [ "${dry_run}" != "1" ]; then
  command -v docker >/dev/null 2>&1 || { printf 'docker not found\n' >&2; exit 127; }
  docker info --format '{{json .Runtimes}}' | grep -q "\"${CE_VPS_RUNTIME}\"" || {
    printf 'docker runtime not registered: %s\n' "${CE_VPS_RUNTIME}" >&2
    exit 66
  }
  [ -d "${CE_VPS_REPO}" ] || { printf 'repo path not found: %s\n' "${CE_VPS_REPO}" >&2; exit 66; }
  [ -d "${CE_VPS_CODEX_HOME}" ] || { printf 'codex home not found: %s\n' "${CE_VPS_CODEX_HOME}" >&2; exit 66; }
  [ -n "${CE_VPS_CODEX_BIN}" ] || { printf 'codex binary not found on PATH; set CE_VPS_CODEX_BIN\n' >&2; exit 66; }
  [ -x "${CE_VPS_CODEX_BIN}" ] || { printf 'codex binary not executable: %s\n' "${CE_VPS_CODEX_BIN}" >&2; exit 66; }
  if [ -n "${CE_VPS_CLAUDE_BIN}" ]; then
    [ -x "${CE_VPS_CLAUDE_BIN}" ] || { printf 'Claude binary not executable: %s\n' "${CE_VPS_CLAUDE_BIN}" >&2; exit 66; }
  fi
fi

tty_flags=()
if [ -n "${CE_VPS_TTY_FLAGS}" ]; then
  read -r -a tty_flags <<<"${CE_VPS_TTY_FLAGS}"
fi

container_cmd=()
if [ "${mode}" = "exec" ]; then
  container_cmd+=(exec)
fi
container_cmd+=("$@")

repo_mount="type=bind,source=${CE_VPS_REPO},target=${CE_VPS_CONTAINER_REPO}"
codex_home_mount="type=bind,source=${CE_VPS_CODEX_HOME},target=${CE_VPS_CONTAINER_CODEX_HOME}"
if [ "${CE_VPS_CODEX_HOME_MODE}" = "ro" ]; then
  codex_home_mount="${codex_home_mount},readonly"
fi
codex_bin_mount="type=bind,source=${CE_VPS_CODEX_BIN},target=/usr/local/bin/codex,readonly"

docker_cmd=(
  docker run --rm
  "--runtime=${CE_VPS_RUNTIME}"
  "--network=${CE_VPS_DOCKER_NETWORK}"
  --security-opt=no-new-privileges
  --cap-drop=ALL
  --user "${CE_VPS_UID}:${CE_VPS_GID}"
  --workdir "${CE_VPS_CONTAINER_REPO}"
  --env "HOME=${CE_VPS_CONTAINER_HOME}"
  --env "CODEX_HOME=${CE_VPS_CONTAINER_CODEX_HOME}"
  --env "TERM=${TERM:-xterm-256color}"
  --env "CE_DGX_HARNESS=${image_harness}"
  --env "CE_DGX_HARNESS_MODE=${mode}"
  --mount "${repo_mount}"
  --mount "${codex_home_mount}"
  --mount "${codex_bin_mount}"
)

if [ "${image_harness}" = "claude" ]; then
  docker_cmd+=(--env "CLAUDE_CODE_OAUTH_TOKEN")
  if [ -n "${CE_VPS_CLAUDE_BIN}" ]; then
    docker_cmd+=(
      --mount "type=bind,source=${CE_VPS_CLAUDE_BIN},target=/usr/local/bin/claude,readonly"
    )
  fi
fi

docker_cmd+=("${tty_flags[@]}")
docker_cmd+=("${CE_VPS_IMAGE}")
docker_cmd+=("${container_cmd[@]}")

if [ "${dry_run}" = "1" ]; then
  printf '%q ' "${docker_cmd[@]}"
  printf '\n'
  exit 0
fi

exec "${docker_cmd[@]}"
