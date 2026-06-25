#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-controller-runsc.sh [--dry-run] [--detach] [tui] [claude args...]
  run-controller-runsc.sh [--dry-run] [--detach] exec [claude prompt args...]

Detached mode:
  --detach                      Launch with `docker run -d` under a named
                                persistent container (default name:
                                ce-dgx-controller) instead of the foreground
                                `docker run --rm`. The script polls for herdr
                                readiness, prints attach/teardown commands, and
                                returns 0 without blocking. A crashed controller
                                is left inspectable (`docker logs`, exit code)
                                because the detached container is NOT removed
                                with --rm.

Environment:
  CE_DGX_CONTROLLER_IMAGE       Docker image tag (default: creator-engine/claude-controller-runsc:c1)
  CE_DGX_IMAGE                  Deprecated alias for CE_DGX_CONTROLLER_IMAGE
  CE_DGX_RUNTIME                Docker runtime (default: runsc-gvproxy-ptrace)
  CE_DGX_DOCKER_NETWORK         Optional Docker --network value (default: unset)
  CE_DGX_NETWORK                Deprecated alias for CE_DGX_DOCKER_NETWORK
  CE_DGX_REPO                   Host repo path (default: current directory)
  CE_DGX_CONTROLLER_HOME        Dedicated host-contained controller home
                                (default: ~/.ce/controller-home)
  CE_DGX_CONTROLLER_HOME_MODE   Mount mode for controller home: rw or ro (default: rw)
  CE_DGX_CLAUDE_BIN             Optional host Claude binary mounted at /usr/local/bin/claude
  CE_DGX_HERDR_SOCKET_PATH      Container-only herdr socket path (default: /run/creator-engine/herdr/herdr.sock)
  CE_DGX_SUBSTRATE_RUN_DIR      Container tmpfs root for herdr substrate state (default: /run/creator-engine)
  CE_DGX_CONTROLLER_LOG_DIR     Container tmpfs log/state dir for the shared herdr harness
                                (default: ${CE_DGX_SUBSTRATE_RUN_DIR}/controller-log)
  CE_DGX_SUPERVISOR_SOCKET      Optional future supervisor socket source path
  CE_DGX_CONTAINER_REPO         Container repo path (default: /workspace/creator-engine)
  CE_DGX_CONTAINER_USER         Container seat user name (default: cedev4)
  CE_DGX_UID                    Container uid (default: id -u)
  CE_DGX_GID                    Container gid (default: id -g)
  CE_DGX_TTY_FLAGS              Docker TTY flags (default: -it; set to -i for non-TTY callers)
  CE_DGX_CONTROLLER_DETACH      Launch detached (docker run -d, named container) when set to 1
  CE_DGX_CONTROLLER_CONTAINER_NAME
                                 Detached container name (default: ce-dgx-controller)
  CE_DGX_DRY_RUN                Print docker argv instead of executing when set to 1
  CE_DGX_ALLOW_PLAIN_RUNSC      Allow CE_DGX_RUNTIME=runsc despite DGX root-netns failure (default: 0)
  CE_DGX_ALLOW_SYSTRAP_CONTROLLER
                                 Allow CE_DGX_RUNTIME=runsc-gvproxy despite DGX systrap caveats (default: 0)
  CE_DGX_ALLOW_DOCKER_NETWORK   Allow Docker --network despite DGX root-netns failure (default: 0)
EOF
}

fail_usage() {
  printf '%s\n' "$*" >&2
  exit 2
}

require_absolute_path() {
  local name="$1" value="$2"
  case "${value}" in
    /*) ;;
    *) fail_usage "${name} must be an absolute path, got ${value}" ;;
  esac
}

refuse_disallowed_supervisor_socket() {
  local path="$1"
  case "${path}" in
    */docker.sock|*/podman.sock|*/containerd.sock|*/herdr.sock|*/herdr/*|*/tmux|*/tmux/*|*/tmux-*|*/tmux-*/*)
      cat >&2 <<EOF
Refusing CE_DGX_SUPERVISOR_SOCKET=${path}.

C1 preserves only a non-secret future supervisor seam. It must not bind-mount
Docker, Podman, containerd, host herdr, or host tmux sockets into the contained
controller.
EOF
      exit 2
      ;;
  esac
}

dry_run="${CE_DGX_DRY_RUN:-0}"
if [ "${1:-}" = "--dry-run" ]; then
  dry_run=1
  shift
fi
detach="${CE_DGX_CONTROLLER_DETACH:-0}"
if [ "${1:-}" = "--detach" ]; then
  detach=1
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

CE_DGX_CONTROLLER_IMAGE="${CE_DGX_CONTROLLER_IMAGE:-${CE_DGX_IMAGE:-creator-engine/claude-controller-runsc:c1}}"
CE_DGX_RUNTIME="${CE_DGX_RUNTIME:-runsc-gvproxy-ptrace}"
CE_DGX_DOCKER_NETWORK="${CE_DGX_DOCKER_NETWORK:-${CE_DGX_NETWORK:-}}"
CE_DGX_REPO="${CE_DGX_REPO:-$(pwd)}"
CE_DGX_CONTROLLER_HOME="${CE_DGX_CONTROLLER_HOME:-${HOME:-/home/cedev4}/.ce/controller-home}"
CE_DGX_CONTROLLER_HOME_MODE="${CE_DGX_CONTROLLER_HOME_MODE:-rw}"
CE_DGX_CLAUDE_BIN="${CE_DGX_CLAUDE_BIN:-}"
CE_DGX_HERDR_SOCKET_PATH="${CE_DGX_HERDR_SOCKET_PATH:-/run/creator-engine/herdr/herdr.sock}"
CE_DGX_SUBSTRATE_RUN_DIR="${CE_DGX_SUBSTRATE_RUN_DIR:-/run/creator-engine}"
CE_DGX_CONTROLLER_LOG_DIR="${CE_DGX_CONTROLLER_LOG_DIR:-${CE_DGX_SUBSTRATE_RUN_DIR}/controller-log}"
CE_DGX_SUPERVISOR_SOCKET="${CE_DGX_SUPERVISOR_SOCKET:-}"
CE_DGX_CONTAINER_REPO="${CE_DGX_CONTAINER_REPO:-/workspace/creator-engine}"
CE_DGX_CONTAINER_USER="${CE_DGX_CONTAINER_USER:-cedev4}"
CE_DGX_CONTAINER_HOME="/home/${CE_DGX_CONTAINER_USER}"
CE_DGX_CONTAINER_SUPERVISOR_SOCKET="/run/ce-supervisor.sock"
CE_DGX_UID="${CE_DGX_UID:-$(id -u)}"
CE_DGX_GID="${CE_DGX_GID:-$(id -g)}"
CE_DGX_TTY_FLAGS="${CE_DGX_TTY_FLAGS:--it}"
CE_DGX_CONTROLLER_CONTAINER_NAME="${CE_DGX_CONTROLLER_CONTAINER_NAME:-ce-dgx-controller}"
CE_DGX_CREDENTIAL_INJECTION="SEAM-STUB"
CE_DGX_TRANSPORT_DEPUTY_SEAM_STATUS="stub-ce-ops-239-no-secret-injection"

container_term="${TERM:-}"
if [ -z "${container_term}" ] || [ "${container_term}" = "dumb" ]; then
  container_term="xterm-256color"
fi

if [ "${CE_DGX_CONTROLLER_HOME_MODE}" != "rw" ] && [ "${CE_DGX_CONTROLLER_HOME_MODE}" != "ro" ]; then
  fail_usage "CE_DGX_CONTROLLER_HOME_MODE must be rw or ro, got ${CE_DGX_CONTROLLER_HOME_MODE}"
fi

require_absolute_path "CE_DGX_REPO" "${CE_DGX_REPO}"
require_absolute_path "CE_DGX_CONTROLLER_HOME" "${CE_DGX_CONTROLLER_HOME}"
require_absolute_path "CE_DGX_HERDR_SOCKET_PATH" "${CE_DGX_HERDR_SOCKET_PATH}"
require_absolute_path "CE_DGX_SUBSTRATE_RUN_DIR" "${CE_DGX_SUBSTRATE_RUN_DIR}"
require_absolute_path "CE_DGX_CONTROLLER_LOG_DIR" "${CE_DGX_CONTROLLER_LOG_DIR}"
if [ -n "${CE_DGX_CLAUDE_BIN}" ]; then
  require_absolute_path "CE_DGX_CLAUDE_BIN" "${CE_DGX_CLAUDE_BIN}"
fi
if [ -n "${CE_DGX_SUPERVISOR_SOCKET}" ]; then
  require_absolute_path "CE_DGX_SUPERVISOR_SOCKET" "${CE_DGX_SUPERVISOR_SOCKET}"
  refuse_disallowed_supervisor_socket "${CE_DGX_SUPERVISOR_SOCKET}"
fi

if [ -n "${HOME:-}" ] && [ "${CE_DGX_CONTROLLER_HOME}" = "${HOME}" ]; then
  cat >&2 <<'EOF'
Refusing to mount the host HOME as CE_DGX_CONTROLLER_HOME.

The contained Controller must use a dedicated controller home so host browser,
SSH, tmux, and general home-directory state are not exposed to the runtime.
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
  mkdir -p "${CE_DGX_CONTROLLER_HOME}"
  chown "${CE_DGX_UID}:${CE_DGX_GID}" "${CE_DGX_CONTROLLER_HOME}" 2>/dev/null || true
  chmod 0700 "${CE_DGX_CONTROLLER_HOME}" 2>/dev/null || true
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

lifecycle_flags=(--rm)
if [ "${detach}" = "1" ]; then
  lifecycle_flags=(-d --name "${CE_DGX_CONTROLLER_CONTAINER_NAME}")
fi

docker_cmd=(
  docker run "${lifecycle_flags[@]}"
  "--runtime=${CE_DGX_RUNTIME}"
  --security-opt=no-new-privileges
  --cap-drop=ALL
  --user "${CE_DGX_UID}:${CE_DGX_GID}"
  --workdir "${CE_DGX_CONTAINER_REPO}"
  --tmpfs "${CE_DGX_SUBSTRATE_RUN_DIR}:uid=${CE_DGX_UID},gid=${CE_DGX_GID},mode=0700"
  --tmpfs "${CE_DGX_CONTROLLER_LOG_DIR}:uid=${CE_DGX_UID},gid=${CE_DGX_GID},mode=0700"
  --env "HOME=${CE_DGX_CONTAINER_HOME}"
  --env "PYTHONPATH=${CE_DGX_CONTAINER_REPO}/validators"
  --env "XDG_CONFIG_HOME=${CE_DGX_SUBSTRATE_RUN_DIR}/xdg/config"
  --env "XDG_STATE_HOME=${CE_DGX_SUBSTRATE_RUN_DIR}/xdg/state"
  --env "XDG_CACHE_HOME=${CE_DGX_SUBSTRATE_RUN_DIR}/xdg/cache"
  --env "CE_SEAT_LOG_DIR=${CE_DGX_CONTROLLER_LOG_DIR}"
  --env "CE_CODEX_STDERR_LOG=${CE_DGX_CONTROLLER_LOG_DIR}/controller-stderr.log"
  --env "TERM=${container_term}"
  --env "CE_DGX_HARNESS=claude"
  --env "CE_DGX_HARNESS_BIN=/usr/local/bin/ce-controller-harness"
  --env "CE_DGX_HARNESS_HOME=${CE_DGX_CONTAINER_HOME}"
  --env "CE_DGX_HERDR_SOCKET_PATH=${CE_DGX_HERDR_SOCKET_PATH}"
  --env "CE_DGX_TERMINAL_KIND=herdr"
  --env "CE_TERMINAL_KIND=herdr"
  --env "CE_DGX_CREDENTIAL_INJECTION=${CE_DGX_CREDENTIAL_INJECTION}"
  --env "CE_TRANSPORT_DEPUTY_SEAM_STATUS=${CE_DGX_TRANSPORT_DEPUTY_SEAM_STATUS}"
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

if [ "${detach}" != "1" ]; then
  exec "${docker_cmd[@]}"
fi

cid="$("${docker_cmd[@]}")" || {
  printf 'detached docker run failed for container %s\n' "${CE_DGX_CONTROLLER_CONTAINER_NAME}" >&2
  exit 1
}
printf 'started detached controller %s (%s)\n' "${CE_DGX_CONTROLLER_CONTAINER_NAME}" "${cid:0:12}"

herdr_pane_list_has_entries() {
  python3 -c '
import json
import sys

text = sys.stdin.read().strip()
if not text:
    raise SystemExit(1)
try:
    data = json.loads(text)
except json.JSONDecodeError:
    raise SystemExit(1)

def has_pane(value):
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        for key in ("result", "panes", "pane", "items"):
            if key in value and has_pane(value[key]):
                return True
        return False
    return bool(value)

raise SystemExit(0 if has_pane(data) else 1)
'
}

herdr_ready() {
  local pane_list
  docker exec "${CE_DGX_CONTROLLER_CONTAINER_NAME}" test -S "${CE_DGX_HERDR_SOCKET_PATH}" >/dev/null 2>&1 || return 1
  pane_list="$(docker exec --env "HERDR_SOCKET_PATH=${CE_DGX_HERDR_SOCKET_PATH}" "${CE_DGX_CONTROLLER_CONTAINER_NAME}" herdr pane list 2>/dev/null)" || return 1
  herdr_pane_list_has_entries <<<"${pane_list}"
}

ready=0
for _ in $(seq 1 60); do
  if herdr_ready; then
    ready=1
    break
  fi
  sleep 0.5
done

if [ "${ready}" != "1" ]; then
  cat >&2 <<EOF
herdr never became ready in controller container ${CE_DGX_CONTROLLER_CONTAINER_NAME}.

Inspect forensic state (the container is NOT auto-removed in detached mode):

  docker logs ${CE_DGX_CONTROLLER_CONTAINER_NAME}
  docker inspect ${CE_DGX_CONTROLLER_CONTAINER_NAME}

Then tear it down:

  docker stop ${CE_DGX_CONTROLLER_CONTAINER_NAME} && docker rm ${CE_DGX_CONTROLLER_CONTAINER_NAME}
EOF
  exit 1
fi

cat <<EOF
herdr is ready in detached controller container ${CE_DGX_CONTROLLER_CONTAINER_NAME}.

Attach (canonical operator path):

  docker exec -it ${CE_DGX_CONTROLLER_CONTAINER_NAME} herdr

Retire the controller when done:

  docker stop ${CE_DGX_CONTROLLER_CONTAINER_NAME} && docker rm ${CE_DGX_CONTROLLER_CONTAINER_NAME}
EOF
exit 0
