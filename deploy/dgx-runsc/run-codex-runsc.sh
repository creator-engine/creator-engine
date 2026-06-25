#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-codex-runsc.sh [--dry-run] [--detach] [tui] [codex args...]
  run-codex-runsc.sh [--dry-run] [--detach] exec [codex exec args...]

Detached mode:
  --detach                  Launch with `docker run -d` under a named persistent
                            container (default name: ce-dgx-codex) instead of the
                            foreground `docker run --rm`. The script polls for
                            herdr readiness, prints attach/teardown commands, and
                            returns 0 without blocking. A crashed seat is left
                            inspectable (`docker logs`, exit code) because the
                            detached container is NOT removed with --rm.

Environment:
  CE_DGX_IMAGE              Docker image tag (default: creator-engine/codex-runsc:0.141.0-aarch64)
  CE_DGX_RUNTIME            Docker runtime (default: runsc-gvproxy-ptrace)
  CE_DGX_DOCKER_NETWORK     Optional Docker --network value (default: unset)
  CE_DGX_NETWORK            Deprecated alias for CE_DGX_DOCKER_NETWORK
  CE_DGX_REPO               Host repo path (default: current directory)
  CE_DGX_CODEX_HOME         Host codex home (default: /home/cedev4/.codex)
  CE_DGX_CODEX_HOME_MODE    Mount mode for codex home: rw or ro (default: rw)
  CE_DGX_CODEX_BIN          Host standalone codex binary
  CE_DGX_CONTAINED_CODEX_CONFIG Host path for generated contained Codex config
                            (default: /tmp/creator-engine-dgx-runsc-codex-config-<uid>-<user>.toml)
  CE_DGX_HERDR_SOCKET_PATH  Container-only herdr socket path (default: /run/creator-engine/herdr/herdr.sock)
  CE_DGX_SUBSTRATE_RUN_DIR  Container tmpfs root for herdr substrate state (default: /run/creator-engine)
  CE_DGX_CONTAINER_REPO     Container repo path (default: /workspace/creator-engine)
  CE_DGX_CONTAINER_USER     Container seat user name (default: cedev4)
  CE_DGX_UID                Container uid (default: id -u)
  CE_DGX_GID                Container gid (default: id -g)
  CE_DGX_SEAT_ID            Host log seat id (default: CE_DGX_CONTAINER_NAME)
  CE_DGX_EGRESS_BROKER_SOCKET Host self-push broker Unix socket to bind-mount (default: unset)
  CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET Container broker socket path
                            (default: /run/ce-egress-broker.sock)
  CE_DGX_SEAT_LOG_DIR       Host log dir mounted at /var/log/ce-seat
                            (default: ~/.ce/logs/seats/<seat-id>)
  CE_DGX_TTY_FLAGS          Docker TTY flags (default: -it; set to -i for non-TTY callers)
  CE_DGX_DETACH             Launch detached (docker run -d, named container) when set to 1
  CE_DGX_CONTAINER_NAME     Detached container name (default: ce-dgx-codex)
  CE_DGX_DRY_RUN            Print docker argv instead of executing when set to 1
  CE_DGX_ALLOW_PLAIN_RUNSC  Allow CE_DGX_RUNTIME=runsc despite DGX root-netns failure (default: 0)
  CE_DGX_ALLOW_SYSTRAP_CODEX
                            Allow CE_DGX_RUNTIME=runsc-gvproxy despite Codex guard-page panic (default: 0)
  CE_DGX_ALLOW_DOCKER_NETWORK
                            Allow Docker --network despite DGX root-netns failure (default: 0)
EOF
}

dry_run="${CE_DGX_DRY_RUN:-0}"
if [ "${1:-}" = "--dry-run" ]; then
  dry_run=1
  shift
fi
detach="${CE_DGX_DETACH:-0}"
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

CE_DGX_IMAGE="${CE_DGX_IMAGE:-creator-engine/codex-runsc:0.141.0-aarch64}"
CE_DGX_RUNTIME="${CE_DGX_RUNTIME:-runsc-gvproxy-ptrace}"
CE_DGX_DOCKER_NETWORK="${CE_DGX_DOCKER_NETWORK:-${CE_DGX_NETWORK:-}}"
CE_DGX_REPO="${CE_DGX_REPO:-$(pwd)}"
CE_DGX_CODEX_HOME="${CE_DGX_CODEX_HOME:-/home/cedev4/.codex}"
CE_DGX_CODEX_HOME_MODE="${CE_DGX_CODEX_HOME_MODE:-rw}"
CE_DGX_CODEX_BIN="${CE_DGX_CODEX_BIN:-/home/cedev4/.codex/packages/standalone/current/bin/codex}"
CE_DGX_HERDR_SOCKET_PATH="${CE_DGX_HERDR_SOCKET_PATH:-/run/creator-engine/herdr/herdr.sock}"
CE_DGX_SUBSTRATE_RUN_DIR="${CE_DGX_SUBSTRATE_RUN_DIR:-/run/creator-engine}"
CE_DGX_CONTAINER_REPO="${CE_DGX_CONTAINER_REPO:-/workspace/creator-engine}"
CE_DGX_CONTAINER_USER="${CE_DGX_CONTAINER_USER:-cedev4}"
CE_DGX_CONTAINER_HOME="/home/${CE_DGX_CONTAINER_USER}"
CE_DGX_CONTAINER_CODEX_HOME="${CE_DGX_CONTAINER_HOME}/.codex"
CE_DGX_UID="${CE_DGX_UID:-$(id -u)}"
CE_DGX_GID="${CE_DGX_GID:-$(id -g)}"
CE_DGX_TTY_FLAGS="${CE_DGX_TTY_FLAGS:--it}"
CE_DGX_CONTAINER_NAME="${CE_DGX_CONTAINER_NAME:-ce-dgx-codex}"
CE_DGX_SEAT_ID_EXPLICIT=0
if [ "${CE_DGX_SEAT_ID+x}" = "x" ]; then
  CE_DGX_SEAT_ID_EXPLICIT=1
fi
CE_DGX_SEAT_ID="${CE_DGX_SEAT_ID:-${CE_DGX_CONTAINER_NAME}}"
CE_DGX_EGRESS_BROKER_SOCKET="${CE_DGX_EGRESS_BROKER_SOCKET:-}"
CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET="${CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET:-/run/ce-egress-broker.sock}"
CE_DGX_SEAT_LOG_DIR="${CE_DGX_SEAT_LOG_DIR:-${HOME:-/home/cedev4}/.ce/logs/seats/${CE_DGX_SEAT_ID}}"
CE_DGX_CONTAINED_CODEX_CONFIG="${CE_DGX_CONTAINED_CODEX_CONFIG:-${XDG_RUNTIME_DIR:-/tmp}/creator-engine-dgx-runsc-codex-config-${CE_DGX_UID}-${CE_DGX_CONTAINER_USER}.toml}"
CE_DGX_CONTAINER_SEAT_LOG_DIR="/var/log/ce-seat"
CE_DGX_CONTAINER_HERDR_SERVER_LOG="${CE_DGX_CONTAINER_SEAT_LOG_DIR}/herdr-server.log"

container_term="${TERM:-}"
if [ -z "${container_term}" ] || [ "${container_term}" = "dumb" ]; then
  container_term="xterm-256color"
fi

if [ "${CE_DGX_CODEX_HOME_MODE}" != "rw" ] && [ "${CE_DGX_CODEX_HOME_MODE}" != "ro" ]; then
  printf 'CE_DGX_CODEX_HOME_MODE must be rw or ro, got %s\n' "${CE_DGX_CODEX_HOME_MODE}" >&2
  exit 2
fi
case "${CE_DGX_CONTAINED_CODEX_CONFIG}" in
  /*)
    ;;
  *)
    printf 'CE_DGX_CONTAINED_CODEX_CONFIG must be an absolute path, got %s\n' "${CE_DGX_CONTAINED_CODEX_CONFIG}" >&2
    exit 2
    ;;
esac
case "${CE_DGX_SEAT_LOG_DIR}" in
  /*)
    ;;
  *)
    printf 'CE_DGX_SEAT_LOG_DIR must be an absolute path, got %s\n' "${CE_DGX_SEAT_LOG_DIR}" >&2
    exit 2
    ;;
esac
if [ -n "${CE_DGX_EGRESS_BROKER_SOCKET}" ]; then
  if [ "${CE_DGX_SEAT_ID_EXPLICIT}" != "1" ]; then
    printf 'CE_DGX_SEAT_ID must be set explicitly when CE_DGX_EGRESS_BROKER_SOCKET is set\n' >&2
    exit 2
  fi
  if [[ ! "${CE_DGX_SEAT_ID}" =~ ^dev-[0-9]+$ ]]; then
    printf 'CE_DGX_SEAT_ID must be a broker seat id like dev-4 when CE_DGX_EGRESS_BROKER_SOCKET is set, got %s\n' "${CE_DGX_SEAT_ID}" >&2
    exit 2
  fi
  case "${CE_DGX_EGRESS_BROKER_SOCKET}" in
    /*)
      ;;
    *)
      printf 'CE_DGX_EGRESS_BROKER_SOCKET must be an absolute path, got %s\n' "${CE_DGX_EGRESS_BROKER_SOCKET}" >&2
      exit 2
      ;;
  esac
  case "${CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET}" in
    /*)
      ;;
    *)
      printf 'CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET must be an absolute path, got %s\n' "${CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET}" >&2
      exit 2
      ;;
  esac
fi
prepare_contained_codex_config() {
  local config_dir
  config_dir="$(dirname "${CE_DGX_CONTAINED_CODEX_CONFIG}")"
  mkdir -p "${config_dir}"
  # Codex' default workspace-write mode starts an inner bwrap sandbox.
  # bwrap cannot nest inside runsc/gVisor, so gVisor is the sandbox here.
  (
    umask 077
    cat >"${CE_DGX_CONTAINED_CODEX_CONFIG}" <<'EOF'
# Generated by deploy/dgx-runsc/run-codex-runsc.sh for contained DGX seats.
# Nested Codex bubblewrap cannot run inside runsc/gVisor; gVisor is the sandbox.
approval_policy = "never"
sandbox_mode = "danger-full-access"
model = "gpt-5.5"
model_reasoning_effort = "high"
allow_managed_hooks_only = true

[tui]
status_line = ["model-with-reasoning", "current-dir", "git-branch", "pull-request-number", "context-remaining", "context-used", "five-hour-limit", "weekly-limit"]
status_line_use_colors = true

[features]
hooks = true

[[hooks.PreToolUse]]
matcher = "^(Bash|apply_patch|Edit|Write|MultiEdit|mcp__.*)$"

[[hooks.PreToolUse.hooks]]
type = "command"
command = 'PYTHONPATH=/workspace/creator-engine/validators python3 /workspace/creator-engine/.codex/hooks/ce-pretooluse-codex.py'
timeout = 30
statusMessage = "Checking CE Ring-1 policy"

[projects."/workspace/creator-engine"]
trust_level = "trusted"
EOF
  )
  chown "${CE_DGX_UID}:${CE_DGX_GID}" "${CE_DGX_CONTAINED_CODEX_CONFIG}" 2>/dev/null || true
  chmod 0644 "${CE_DGX_CONTAINED_CODEX_CONFIG}"
}

prepare_contained_codex_config

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

if [ "${CE_DGX_RUNTIME}" = "runsc-gvproxy" ] && [ "${CE_DGX_ALLOW_SYSTRAP_CODEX:-0}" != "1" ]; then
  cat >&2 <<'EOF'
Refusing CE_DGX_RUNTIME=runsc-gvproxy for Codex on this DGX.

The Systrap gvproxy runtime works for a basic HTTPS container here, but Codex
panics during Rust alternate signal stack guard-page setup. Use the ptrace
runtime for Codex:

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
  mkdir -p "${CE_DGX_SEAT_LOG_DIR}"
  chown "${CE_DGX_UID}:${CE_DGX_GID}" "${CE_DGX_SEAT_LOG_DIR}" 2>/dev/null || true
  chmod 0700 "${CE_DGX_SEAT_LOG_DIR}" 2>/dev/null || true
  command -v docker >/dev/null 2>&1 || { printf 'docker not found\n' >&2; exit 127; }
  docker info --format '{{json .Runtimes}}' | grep -q "\"${CE_DGX_RUNTIME}\"" || {
    printf 'docker runtime not registered: %s\n' "${CE_DGX_RUNTIME}" >&2
    exit 66
  }
  [ -d "${CE_DGX_REPO}" ] || { printf 'repo path not found: %s\n' "${CE_DGX_REPO}" >&2; exit 66; }
  [ -d "${CE_DGX_CODEX_HOME}" ] || { printf 'codex home not found: %s\n' "${CE_DGX_CODEX_HOME}" >&2; exit 66; }
  [ -x "${CE_DGX_CODEX_BIN}" ] || { printf 'codex binary not executable: %s\n' "${CE_DGX_CODEX_BIN}" >&2; exit 66; }
  if [ -n "${CE_DGX_EGRESS_BROKER_SOCKET}" ]; then
    [ -S "${CE_DGX_EGRESS_BROKER_SOCKET}" ] || {
      printf 'egress broker socket not found: %s\n' "${CE_DGX_EGRESS_BROKER_SOCKET}" >&2
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
  container_cmd+=(exec)
fi
container_cmd+=(--dangerously-bypass-hook-trust)
container_cmd+=("$@")

repo_mount="type=bind,source=${CE_DGX_REPO},target=${CE_DGX_CONTAINER_REPO}"
codex_home_mount="type=bind,source=${CE_DGX_CODEX_HOME},target=${CE_DGX_CONTAINER_CODEX_HOME}"
if [ "${CE_DGX_CODEX_HOME_MODE}" = "ro" ]; then
  codex_home_mount="${codex_home_mount},readonly"
fi
seat_log_mount="type=bind,source=${CE_DGX_SEAT_LOG_DIR},target=${CE_DGX_CONTAINER_SEAT_LOG_DIR}"
codex_bin_mount="type=bind,source=${CE_DGX_CODEX_BIN},target=/usr/local/bin/codex,readonly"
contained_codex_config_mount="type=bind,source=${CE_DGX_CONTAINED_CODEX_CONFIG},target=${CE_DGX_CONTAINER_CODEX_HOME}/config.toml,readonly"
egress_broker_mount=""
if [ -n "${CE_DGX_EGRESS_BROKER_SOCKET}" ]; then
  egress_broker_mount="type=bind,source=${CE_DGX_EGRESS_BROKER_SOCKET},target=${CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET}"
fi
# Foreground keeps --rm (ephemeral). Detached drops --rm and adds -d --name so a
# crashed/stopped seat stays inspectable (docker logs, exit code) for forensics.
lifecycle_flags=(--rm)
if [ "${detach}" = "1" ]; then
  lifecycle_flags=(-d --name "${CE_DGX_CONTAINER_NAME}")
elif [ "${mode}" = "tui" ]; then
  lifecycle_flags=(--rm --name "${CE_DGX_CONTAINER_NAME}")
fi

docker_cmd=(
  docker run "${lifecycle_flags[@]}"
  "--runtime=${CE_DGX_RUNTIME}"
  --security-opt=no-new-privileges
  --cap-drop=ALL
  --user "${CE_DGX_UID}:${CE_DGX_GID}"
  --workdir "${CE_DGX_CONTAINER_REPO}"
  --tmpfs "${CE_DGX_SUBSTRATE_RUN_DIR}:uid=${CE_DGX_UID},gid=${CE_DGX_GID},mode=0700"
  --env "HOME=${CE_DGX_CONTAINER_HOME}"
  --env "CODEX_HOME=${CE_DGX_CONTAINER_CODEX_HOME}"
  --env "CE_SEAT_LOG_DIR=${CE_DGX_CONTAINER_SEAT_LOG_DIR}"
  --env "CE_HERDR_SERVER_LOG=${CE_DGX_CONTAINER_HERDR_SERVER_LOG}"
  --env "CE_CODEX_STDERR_LOG=${CE_DGX_CONTAINER_SEAT_LOG_DIR}/codex-stderr.log"
  --env "XDG_CONFIG_HOME=${CE_DGX_CONTAINER_SEAT_LOG_DIR}/xdg/config"
  --env "XDG_STATE_HOME=${CE_DGX_CONTAINER_SEAT_LOG_DIR}/xdg/state"
  --env "XDG_CACHE_HOME=${CE_DGX_CONTAINER_SEAT_LOG_DIR}/xdg/cache"
  --env "TERM=${container_term}"
  --env "CE_DGX_HARNESS=codex"
  --env "CE_DGX_HARNESS_BIN=/usr/local/bin/codex"
  --env "CE_DGX_HARNESS_HOME=${CE_DGX_CONTAINER_HOME}"
  --env "CE_DGX_HERDR_SOCKET_PATH=${CE_DGX_HERDR_SOCKET_PATH}"
  --env "CE_DGX_TERMINAL_KIND=herdr"
  --env "CE_TERMINAL_KIND=herdr"
  --mount "${repo_mount}"
  --mount "${codex_home_mount}"
  --mount "${seat_log_mount}"
  --mount "${contained_codex_config_mount}"
  --mount "${codex_bin_mount}"
)

if [ -n "${egress_broker_mount}" ]; then
  docker_cmd+=(
    --env "CE_EGRESS_BROKER_SOCKET=${CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET}"
    --env "CE_SEAT_ID=${CE_DGX_SEAT_ID}"
    --mount "${egress_broker_mount}"
  )
fi

if [ -n "${CE_DGX_DOCKER_NETWORK}" ]; then
  docker_cmd+=("--network=${CE_DGX_DOCKER_NETWORK}")
fi

docker_cmd+=("${tty_flags[@]}")
docker_cmd+=("${CE_DGX_IMAGE}")
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

# Detached launch: start the named container in the background, then poll for
# herdr readiness. We do NOT exec (that would block); we run, poll, and return.
cid="$("${docker_cmd[@]}")" || {
  printf 'detached docker run failed for container %s\n' "${CE_DGX_CONTAINER_NAME}" >&2
  exit 1
}
printf 'started detached container %s (%s)\n' "${CE_DGX_CONTAINER_NAME}" "${cid:0:12}"

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
    raise SystemExit(0)

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
  docker exec "${CE_DGX_CONTAINER_NAME}" test -S "${CE_DGX_HERDR_SOCKET_PATH}" >/dev/null 2>&1 || return 1
  pane_list="$(docker exec --env "HERDR_SOCKET_PATH=${CE_DGX_HERDR_SOCKET_PATH}" "${CE_DGX_CONTAINER_NAME}" herdr pane list 2>/dev/null)" || return 1
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
herdr never became ready in container ${CE_DGX_CONTAINER_NAME}.

Inspect forensic state (the container is NOT auto-removed in detached mode):

  docker logs ${CE_DGX_CONTAINER_NAME}
  docker inspect ${CE_DGX_CONTAINER_NAME}

Then tear it down:

  docker stop ${CE_DGX_CONTAINER_NAME} && docker rm ${CE_DGX_CONTAINER_NAME}
EOF
  exit 1
fi

cat <<EOF
herdr is ready in detached container ${CE_DGX_CONTAINER_NAME}.

Attach (canonical drive path):

  docker exec -it ${CE_DGX_CONTAINER_NAME} herdr

Retire the seat when done:

  docker stop ${CE_DGX_CONTAINER_NAME} && docker rm ${CE_DGX_CONTAINER_NAME}
EOF
exit 0
