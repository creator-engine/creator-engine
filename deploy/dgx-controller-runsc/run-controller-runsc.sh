#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-controller-runsc.sh [--dry-run] [tui] [claude args...]
  run-controller-runsc.sh [--dry-run] exec [claude prompt args...]

Environment:
  CE_DGX_CONTROLLER_IMAGE       Docker image tag (default: creator-engine/codex-runsc:0.141.0-aarch64)
  CE_DGX_IMAGE                  Deprecated alias for CE_DGX_CONTROLLER_IMAGE
  CE_DGX_RUNTIME                Docker runtime (default: runsc-gvproxy-ptrace)
  CE_DGX_DOCKER_NETWORK         Optional Docker --network value (default: unset)
  CE_DGX_NETWORK                Deprecated alias for CE_DGX_DOCKER_NETWORK
  CE_DGX_REPO                   Host repo path (default: current directory)
  CE_DGX_CONTROLLER_HOME        Host-contained controller home, not the host home
  CE_DGX_CONTROLLER_HOME_MODE   Mount mode for controller home: rw or ro (default: rw)
  CE_DGX_CLAUDE_BIN             Optional host Claude binary mounted at /usr/local/bin/claude
  CE_DGX_HERDR_SOCKET_PATH      Container-only herdr socket path (default: /run/creator-engine/herdr/herdr.sock)
  CE_DGX_SUBSTRATE_RUN_DIR      Container tmpfs root for herdr substrate state (default: /run/creator-engine)
  CE_DGX_SUPERVISOR_SOCKET      Optional future supervisor socket source path
  CE_DGX_CONTAINER_REPO         Container repo path (default: /workspace/creator-engine)
  CE_DGX_CONTAINER_USER         Container seat user name (default: cedev4)
  CE_DGX_UID                    Container uid (default: id -u)
  CE_DGX_GID                    Container gid (default: id -g)
  CE_DGX_TTY_FLAGS              Docker TTY flags (default: -it; set to -i for non-TTY callers)
  CE_DGX_DRY_RUN                Print docker argv instead of executing when set to 1
  CE_DGX_ALLOW_PLAIN_RUNSC      Allow CE_DGX_RUNTIME=runsc despite DGX root-netns failure (default: 0)
  CE_DGX_ALLOW_SYSTRAP_CONTROLLER
                                 Allow CE_DGX_RUNTIME=runsc-gvproxy despite DGX systrap caveats (default: 0)
  CE_DGX_ALLOW_DOCKER_NETWORK   Allow Docker --network despite DGX root-netns failure (default: 0)
  CE_DGX_ALLOW_HOST_HOME        Allow mounting HOME as controller home for diagnostics (default: 0)
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

CE_DGX_CONTROLLER_IMAGE="${CE_DGX_CONTROLLER_IMAGE:-${CE_DGX_IMAGE:-creator-engine/codex-runsc:0.141.0-aarch64}}"
CE_DGX_RUNTIME="${CE_DGX_RUNTIME:-runsc-gvproxy-ptrace}"
CE_DGX_DOCKER_NETWORK="${CE_DGX_DOCKER_NETWORK:-${CE_DGX_NETWORK:-}}"
CE_DGX_REPO="${CE_DGX_REPO:-$(pwd)}"
CE_DGX_CONTROLLER_HOME="${CE_DGX_CONTROLLER_HOME:-${HOME:-/home/cedev4}/.ce/controller-home}"
CE_DGX_CONTROLLER_HOME_MODE="${CE_DGX_CONTROLLER_HOME_MODE:-rw}"
CE_DGX_CLAUDE_BIN="${CE_DGX_CLAUDE_BIN:-}"
CE_DGX_HERDR_SOCKET_PATH="${CE_DGX_HERDR_SOCKET_PATH:-/run/creator-engine/herdr/herdr.sock}"
CE_DGX_SUBSTRATE_RUN_DIR="${CE_DGX_SUBSTRATE_RUN_DIR:-/run/creator-engine}"
CE_DGX_SUPERVISOR_SOCKET="${CE_DGX_SUPERVISOR_SOCKET:-}"
CE_DGX_CONTAINER_REPO="${CE_DGX_CONTAINER_REPO:-/workspace/creator-engine}"
CE_DGX_CONTAINER_USER="${CE_DGX_CONTAINER_USER:-cedev4}"
CE_DGX_CONTAINER_HOME="/home/${CE_DGX_CONTAINER_USER}"
CE_DGX_CONTAINER_SUPERVISOR_SOCKET="/run/ce-supervisor.sock"
CE_DGX_UID="${CE_DGX_UID:-$(id -u)}"
CE_DGX_GID="${CE_DGX_GID:-$(id -g)}"
CE_DGX_TTY_FLAGS="${CE_DGX_TTY_FLAGS:--it}"

if [ "${CE_DGX_CONTROLLER_HOME_MODE}" != "rw" ] && [ "${CE_DGX_CONTROLLER_HOME_MODE}" != "ro" ]; then
  printf 'CE_DGX_CONTROLLER_HOME_MODE must be rw or ro, got %s\n' "${CE_DGX_CONTROLLER_HOME_MODE}" >&2
  exit 2
fi

if [ -n "${HOME:-}" ] && [ "${CE_DGX_CONTROLLER_HOME}" = "${HOME}" ] && [ "${CE_DGX_ALLOW_HOST_HOME:-0}" != "1" ]; then
  cat >&2 <<'EOF'
Refusing to mount the host HOME as CE_DGX_CONTROLLER_HOME.

The contained Controller must use a dedicated controller home so host browser,
SSH, tmux, and general home-directory state are not exposed to the runtime.
Set CE_DGX_ALLOW_HOST_HOME=1 only for an operator-directed diagnostic.
EOF
  exit 2
fi

if [ "${CE_DGX_RUNTIME}" = "runsc" ] && [ "${CE_DGX_ALLOW_PLAIN_RUNSC:-0}" != "1" ]; then
  cat >&2 <<'EOF'
Refusing CE_DGX_RUNTIME=runsc on this DGX.

Plain Docker runsc uses Docker's bridge/none network namespace path here, which
fails in the nested DGX root network namespace. Register and use the Stage-1
gvproxy-backed ptrace runtime instead:

  CE_DGX_RUNTIME=runsc-gvproxy-ptrace
EOF
  exit 2
fi

if [ "${CE_DGX_RUNTIME}" = "runsc-gvproxy" ] && [ "${CE_DGX_ALLOW_SYSTRAP_CONTROLLER:-0}" != "1" ]; then
  cat >&2 <<'EOF'
Refusing CE_DGX_RUNTIME=runsc-gvproxy for the Controller on this DGX.

The sibling Codex DGX artifact uses the ptrace gvproxy runtime after systrap
testing exposed process-startup incompatibilities. Use the same contained
runtime family for the Controller unless this is an explicit diagnostic:

  CE_DGX_RUNTIME=runsc-gvproxy-ptrace
EOF
  exit 2
fi

if [ -n "${CE_DGX_DOCKER_NETWORK}" ] && [ "${CE_DGX_ALLOW_DOCKER_NETWORK:-0}" != "1" ]; then
  cat >&2 <<EOF
Refusing Docker --network=${CE_DGX_DOCKER_NETWORK}.

Do not ask Docker for bridge/none/host networking on the nested DGX. The
runsc-gvproxy-ptrace runtime owns networking and routes egress through the DGX
gvproxy/gvisor-tap-vsock path. Set CE_DGX_ALLOW_DOCKER_NETWORK=1 only for an
operator-directed diagnostic.
EOF
  exit 2
fi

if [ "${dry_run}" != "1" ]; then
  command -v docker >/dev/null 2>&1 || { printf 'docker not found\n' >&2; exit 127; }
  docker info --format '{{json .Runtimes}}' | grep -q "\"${CE_DGX_RUNTIME}\"" || {
    printf 'docker runtime not registered: %s\n' "${CE_DGX_RUNTIME}" >&2
    exit 66
  }
  [ -d "${CE_DGX_REPO}" ] || { printf 'repo path not found: %s\n' "${CE_DGX_REPO}" >&2; exit 66; }
  [ -d "${CE_DGX_CONTROLLER_HOME}" ] || {
    printf 'controller home not found: %s\n' "${CE_DGX_CONTROLLER_HOME}" >&2
    exit 66
  }
  if [ -n "${CE_DGX_CLAUDE_BIN}" ]; then
    [ -x "${CE_DGX_CLAUDE_BIN}" ] || {
      printf 'Claude binary not executable: %s\n' "${CE_DGX_CLAUDE_BIN}" >&2
      exit 66
    }
  fi
  if [ -n "${CE_DGX_SUPERVISOR_SOCKET}" ]; then
    [ -S "${CE_DGX_SUPERVISOR_SOCKET}" ] || {
      printf 'supervisor socket not found: %s\n' "${CE_DGX_SUPERVISOR_SOCKET}" >&2
      exit 66
    }
  fi
fi

tty_flags=()
if [ -n "${CE_DGX_TTY_FLAGS}" ]; then
  read -r -a tty_flags <<<"${CE_DGX_TTY_FLAGS}"
fi

container_cmd=()
if [ "${mode}" = "exec" ]; then
  container_cmd+=(-p)
fi
container_cmd+=("$@")

repo_mount="type=bind,source=${CE_DGX_REPO},target=${CE_DGX_CONTAINER_REPO}"
controller_home_mount="type=bind,source=${CE_DGX_CONTROLLER_HOME},target=${CE_DGX_CONTAINER_HOME}"
if [ "${CE_DGX_CONTROLLER_HOME_MODE}" = "ro" ]; then
  controller_home_mount="${controller_home_mount},readonly"
fi

docker_cmd=(
  docker run --rm
  "--runtime=${CE_DGX_RUNTIME}"
  --security-opt=no-new-privileges
  --cap-drop=ALL
  --user "${CE_DGX_UID}:${CE_DGX_GID}"
  --workdir "${CE_DGX_CONTAINER_REPO}"
  --tmpfs "${CE_DGX_SUBSTRATE_RUN_DIR}:uid=${CE_DGX_UID},gid=${CE_DGX_GID},mode=0700"
  --env "HOME=${CE_DGX_CONTAINER_HOME}"
  --env "XDG_CONFIG_HOME=${CE_DGX_SUBSTRATE_RUN_DIR}/xdg/config"
  --env "XDG_STATE_HOME=${CE_DGX_SUBSTRATE_RUN_DIR}/xdg/state"
  --env "XDG_CACHE_HOME=${CE_DGX_SUBSTRATE_RUN_DIR}/xdg/cache"
  --env "TERM=${TERM:-xterm-256color}"
  --env "CLAUDE_CODE_OAUTH_TOKEN"
  --env "CE_DGX_HARNESS=claude"
  --env "CE_DGX_HARNESS_BIN=/usr/local/bin/claude"
  --env "CE_DGX_HARNESS_HOME=${CE_DGX_CONTAINER_HOME}"
  --env "CE_DGX_HERDR_SOCKET_PATH=${CE_DGX_HERDR_SOCKET_PATH}"
  --env "CE_DGX_TERMINAL_KIND=herdr"
  --env "CE_TERMINAL_KIND=herdr"
  --mount "${repo_mount}"
  --mount "${controller_home_mount}"
)

if [ -n "${CE_DGX_CLAUDE_BIN}" ]; then
  docker_cmd+=(
    --mount "type=bind,source=${CE_DGX_CLAUDE_BIN},target=/usr/local/bin/claude,readonly"
  )
fi

if [ -n "${CE_DGX_SUPERVISOR_SOCKET}" ]; then
  docker_cmd+=(
    --env "CE_SUPERVISOR_SOCKET=${CE_DGX_CONTAINER_SUPERVISOR_SOCKET}"
    --mount "type=bind,source=${CE_DGX_SUPERVISOR_SOCKET},target=${CE_DGX_CONTAINER_SUPERVISOR_SOCKET}"
  )
fi

if [ -n "${CE_DGX_DOCKER_NETWORK}" ]; then
  docker_cmd+=("--network=${CE_DGX_DOCKER_NETWORK}")
fi

docker_cmd+=("${tty_flags[@]}")
docker_cmd+=("${CE_DGX_CONTROLLER_IMAGE}")
if [ "${#container_cmd[@]}" -gt 0 ]; then
  docker_cmd+=("${container_cmd[@]}")
fi

if [ "${dry_run}" = "1" ]; then
  printf '%q ' "${docker_cmd[@]}"
  printf '\n'
  exit 0
fi

exec "${docker_cmd[@]}"
