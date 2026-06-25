#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-vps-runsc.sh [--dry-run] [--harness codex|claude|controller] [--detach] [tui] [harness args...]
  run-vps-runsc.sh [--dry-run] [--harness codex|claude|controller] [--detach] exec [harness exec args...]

Environment:
  CE_VPS_IMAGE                 Docker image tag (default: creator-engine/codex-runsc:x86_64)
  CE_VPS_RUNTIME               Docker runtime (default: runsc-gvproxy-ptrace)
  CE_VPS_DOCKER_NETWORK        Docker --network value (default: host)
  CE_VPS_HARNESS               Harness: codex, claude, or controller (default: codex)
  CE_DGX_HARNESS               Deprecated alias for CE_VPS_HARNESS
  CE_VPS_DETACH                Launch detached (docker run -d, named-persistent) when set to 1
  CE_VPS_CONTAINER_NAME        Container --name for detached launch
                                (default: ce-vps-<harness>, e.g. ce-vps-codex)
  CE_VPS_REPO                  Host repo path (default: current directory)
  CE_VPS_CODEX_HOME            Host codex home (default: $HOME/.codex)
  CE_VPS_CODEX_HOME_MODE       Mount mode for codex home: rw or ro (default: rw)
  CE_VPS_CONTAINED_CODEX_CONFIG Host path for generated contained Codex config
                                (default: /tmp/creator-engine-vps-runsc-codex-config-<uid>-<user>.toml)
  CE_VPS_CODEX_BIN             Host standalone codex binary (default: first codex on PATH)
  CE_VPS_CODEX_PACKAGE_ROOT    Optional host @openai/codex npm package root. If unset,
                                npm symlinks ending in @openai/codex/bin/codex.js are autodetected.
  CE_VPS_CLAUDE_BIN            Optional host Claude binary mounted at /usr/local/bin/claude
  CE_VPS_CONTAINER_REPO        Container repo path (default: /workspace/creator-engine)
  CE_VPS_CONTAINER_USER        Container seat user name (default: current user)
  CE_VPS_UID                   Container uid (default: id -u)
  CE_VPS_GID                   Container gid (default: id -g)
  CE_VPS_SEAT_ID               Host log seat id (default: CE_VPS_CONTAINER_NAME)
  CE_VPS_SEAT_LOG_DIR          Host log dir mounted at /var/log/ce-seat
                                (default: ~/.ce/logs/seats/<seat-id>)
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

# --detach is parsed early (like --dry-run) so it works whether placed before
# or after the optional --harness, as long as it precedes the tui/exec token.
detach="${CE_VPS_DETACH:-0}"
if [ "${1:-}" = "--detach" ]; then
  detach=1
  shift
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

# Allow --detach after --harness as well (parse order tolerance).
if [ "${1:-}" = "--detach" ]; then
  detach=1
  shift
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
CE_VPS_CODEX_PACKAGE_ROOT="${CE_VPS_CODEX_PACKAGE_ROOT:-}"
CE_VPS_CLAUDE_BIN="${CE_VPS_CLAUDE_BIN:-}"
CE_VPS_CONTAINER_REPO="${CE_VPS_CONTAINER_REPO:-/workspace/creator-engine}"
CE_VPS_CONTAINER_USER="${CE_VPS_CONTAINER_USER:-$(id -un 2>/dev/null || printf ce)}"
CE_VPS_CONTAINER_HOME="/home/${CE_VPS_CONTAINER_USER}"
CE_VPS_CONTAINER_CODEX_HOME="${CE_VPS_CONTAINER_HOME}/.codex"
CE_VPS_UID="${CE_VPS_UID:-$(id -u)}"
CE_VPS_GID="${CE_VPS_GID:-$(id -g)}"
CE_VPS_TTY_FLAGS="${CE_VPS_TTY_FLAGS:--it}"
CE_VPS_CONTAINER_NAME="${CE_VPS_CONTAINER_NAME:-ce-vps-${harness}}"
CE_VPS_SEAT_ID="${CE_VPS_SEAT_ID:-${CE_VPS_CONTAINER_NAME}}"
CE_VPS_SEAT_LOG_DIR="${CE_VPS_SEAT_LOG_DIR:-${HOME:-/home/ce}/.ce/logs/seats/${CE_VPS_SEAT_ID}}"
CE_VPS_CONTAINED_CODEX_CONFIG="${CE_VPS_CONTAINED_CODEX_CONFIG:-${XDG_RUNTIME_DIR:-/tmp}/creator-engine-vps-runsc-codex-config-${CE_VPS_UID}-${CE_VPS_CONTAINER_USER}.toml}"
CE_VPS_CONTAINER_CODEX_PACKAGE_ROOT="/usr/local/lib/node_modules/@openai/codex"
CE_VPS_CONTAINER_SEAT_LOG_DIR="/var/log/ce-seat"
CE_VPS_CONTAINER_HERDR_SERVER_LOG="${CE_VPS_CONTAINER_SEAT_LOG_DIR}/herdr-server.log"
herdr_socket_path="/run/creator-engine/herdr/herdr.sock"

container_term="${TERM:-}"
if [ -z "${container_term}" ] || [ "${container_term}" = "dumb" ]; then
  container_term="xterm-256color"
fi

if [ -z "${CE_VPS_CODEX_PACKAGE_ROOT}" ] && [ -n "${CE_VPS_CODEX_BIN}" ]; then
  codex_bin_realpath="$(realpath "${CE_VPS_CODEX_BIN}" 2>/dev/null || true)"
  case "${codex_bin_realpath}" in
    */lib/node_modules/@openai/codex/bin/codex.js)
      CE_VPS_CODEX_PACKAGE_ROOT="${codex_bin_realpath%/bin/codex.js}"
      ;;
  esac
fi

if [ "${CE_VPS_CODEX_HOME_MODE}" != "rw" ] && [ "${CE_VPS_CODEX_HOME_MODE}" != "ro" ]; then
  printf 'CE_VPS_CODEX_HOME_MODE must be rw or ro, got %s\n' "${CE_VPS_CODEX_HOME_MODE}" >&2
  exit 2
fi
case "${CE_VPS_CONTAINED_CODEX_CONFIG}" in
  /*)
    ;;
  *)
    printf 'CE_VPS_CONTAINED_CODEX_CONFIG must be an absolute path, got %s\n' "${CE_VPS_CONTAINED_CODEX_CONFIG}" >&2
    exit 2
    ;;
esac
case "${CE_VPS_SEAT_LOG_DIR}" in
  /*)
    ;;
  *)
    printf 'CE_VPS_SEAT_LOG_DIR must be an absolute path, got %s\n' "${CE_VPS_SEAT_LOG_DIR}" >&2
    exit 2
    ;;
esac
if [ -n "${CE_VPS_CODEX_PACKAGE_ROOT}" ]; then
  case "${CE_VPS_CODEX_PACKAGE_ROOT}" in
    /*)
      ;;
    *)
      printf 'CE_VPS_CODEX_PACKAGE_ROOT must be an absolute path, got %s\n' "${CE_VPS_CODEX_PACKAGE_ROOT}" >&2
      exit 2
      ;;
  esac
fi

prepare_contained_codex_config() {
  local config_dir
  config_dir="$(dirname "${CE_VPS_CONTAINED_CODEX_CONFIG}")"
  mkdir -p "${config_dir}"
  # Codex' default workspace-write mode starts an inner bwrap sandbox.
  # bwrap cannot nest inside runsc/gVisor, so gVisor is the sandbox here.
  (
    umask 077
    cat >"${CE_VPS_CONTAINED_CODEX_CONFIG}" <<'EOF'
# Generated by deploy/vps-runsc/run-vps-runsc.sh for contained VPS seats.
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
  chown "${CE_VPS_UID}:${CE_VPS_GID}" "${CE_VPS_CONTAINED_CODEX_CONFIG}" 2>/dev/null || true
  chmod 0644 "${CE_VPS_CONTAINED_CODEX_CONFIG}"
}

prepare_contained_codex_config

if [ "${dry_run}" != "1" ]; then
  mkdir -p "${CE_VPS_SEAT_LOG_DIR}"
  chown "${CE_VPS_UID}:${CE_VPS_GID}" "${CE_VPS_SEAT_LOG_DIR}" 2>/dev/null || true
  chmod 0700 "${CE_VPS_SEAT_LOG_DIR}" 2>/dev/null || true
  command -v docker >/dev/null 2>&1 || { printf 'docker not found\n' >&2; exit 127; }
  docker info --format '{{json .Runtimes}}' | grep -q "\"${CE_VPS_RUNTIME}\"" || {
    printf 'docker runtime not registered: %s\n' "${CE_VPS_RUNTIME}" >&2
    exit 66
  }
  [ -d "${CE_VPS_REPO}" ] || { printf 'repo path not found: %s\n' "${CE_VPS_REPO}" >&2; exit 66; }
  [ -d "${CE_VPS_CODEX_HOME}" ] || { printf 'codex home not found: %s\n' "${CE_VPS_CODEX_HOME}" >&2; exit 66; }
  if [ -n "${CE_VPS_CODEX_PACKAGE_ROOT}" ]; then
    [ -d "${CE_VPS_CODEX_PACKAGE_ROOT}" ] || { printf 'Codex package root not found: %s\n' "${CE_VPS_CODEX_PACKAGE_ROOT}" >&2; exit 66; }
    [ -x "${CE_VPS_CODEX_PACKAGE_ROOT}/bin/codex.js" ] || { printf 'Codex package entrypoint not executable: %s/bin/codex.js\n' "${CE_VPS_CODEX_PACKAGE_ROOT}" >&2; exit 66; }
  else
    [ -n "${CE_VPS_CODEX_BIN}" ] || { printf 'codex binary not found on PATH; set CE_VPS_CODEX_BIN or CE_VPS_CODEX_PACKAGE_ROOT\n' >&2; exit 66; }
    [ -x "${CE_VPS_CODEX_BIN}" ] || { printf 'codex binary not executable: %s\n' "${CE_VPS_CODEX_BIN}" >&2; exit 66; }
  fi
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
if [ "${image_harness}" = "codex" ]; then
  container_cmd+=(--dangerously-bypass-hook-trust)
fi
container_cmd+=("$@")

repo_mount="type=bind,source=${CE_VPS_REPO},target=${CE_VPS_CONTAINER_REPO}"
codex_home_mount="type=bind,source=${CE_VPS_CODEX_HOME},target=${CE_VPS_CONTAINER_CODEX_HOME}"
if [ "${CE_VPS_CODEX_HOME_MODE}" = "ro" ]; then
  codex_home_mount="${codex_home_mount},readonly"
fi
seat_log_mount="type=bind,source=${CE_VPS_SEAT_LOG_DIR},target=${CE_VPS_CONTAINER_SEAT_LOG_DIR}"
contained_codex_config_mount="type=bind,source=${CE_VPS_CONTAINED_CODEX_CONFIG},target=${CE_VPS_CONTAINER_CODEX_HOME}/config.toml,readonly"
codex_mount_args=()
if [ -n "${CE_VPS_CODEX_PACKAGE_ROOT}" ]; then
  codex_mount_args+=(
    --mount "type=bind,source=${CE_VPS_CODEX_PACKAGE_ROOT},target=${CE_VPS_CONTAINER_CODEX_PACKAGE_ROOT},readonly"
  )
else
  codex_mount_args+=(
    --mount "type=bind,source=${CE_VPS_CODEX_BIN},target=/usr/local/bin/codex,readonly"
  )
fi

# Foreground = ephemeral (--rm). Detached = named-persistent (no --rm, add -d
# and --name) so a crashed/stopped seat is inspectable via docker logs/exit
# code; --rm previously deleted forensic state on a live outage.
docker_run_flags=()
if [ "${detach}" = "1" ]; then
  docker_run_flags+=(-d --name "${CE_VPS_CONTAINER_NAME}")
else
  docker_run_flags+=(--rm)
  if [ "${mode}" = "tui" ]; then
    docker_run_flags+=(--name "${CE_VPS_CONTAINER_NAME}")
  fi
fi

docker_cmd=(
  docker run
  "${docker_run_flags[@]}"
  "--runtime=${CE_VPS_RUNTIME}"
  "--network=${CE_VPS_DOCKER_NETWORK}"
  --security-opt=no-new-privileges
  --cap-drop=ALL
  --user "${CE_VPS_UID}:${CE_VPS_GID}"
  --workdir "${CE_VPS_CONTAINER_REPO}"
  --env "HOME=${CE_VPS_CONTAINER_HOME}"
  --env "CODEX_HOME=${CE_VPS_CONTAINER_CODEX_HOME}"
  --env "CE_SEAT_LOG_DIR=${CE_VPS_CONTAINER_SEAT_LOG_DIR}"
  --env "CE_HERDR_SERVER_LOG=${CE_VPS_CONTAINER_HERDR_SERVER_LOG}"
  --env "CE_CODEX_STDERR_LOG=${CE_VPS_CONTAINER_SEAT_LOG_DIR}/codex-stderr.log"
  --env "XDG_CONFIG_HOME=${CE_VPS_CONTAINER_SEAT_LOG_DIR}/xdg/config"
  --env "XDG_STATE_HOME=${CE_VPS_CONTAINER_SEAT_LOG_DIR}/xdg/state"
  --env "XDG_CACHE_HOME=${CE_VPS_CONTAINER_SEAT_LOG_DIR}/xdg/cache"
  --env "TERM=${container_term}"
  --env "CE_DGX_HARNESS=${image_harness}"
  --env "CE_DGX_HARNESS_MODE=${mode}"
  --mount "${repo_mount}"
  --mount "${codex_home_mount}"
  --mount "${seat_log_mount}"
  --mount "${contained_codex_config_mount}"
  "${codex_mount_args[@]}"
)

if [ "${image_harness}" = "claude" ]; then
  # Secret-retention guard (ce-ops#408 review): a token-bearing --env lands in the
  # container's inspectable metadata (docker inspect Config.Env). In detached/named-
  # persistent mode that survives until an explicit `docker rm` — foreground --rm scrubbed
  # it on container exit. Fail closed in detached mode unless the operator opts in.
  if [ "${detach}" = "1" ] && [ "${CE_VPS_ALLOW_DETACHED_TOKEN_ENV:-0}" != "1" ]; then
    printf 'REFUSED: detached launch would persist CLAUDE_CODE_OAUTH_TOKEN in the named-persistent container inspectable metadata (docker inspect Config.Env) until "docker rm". Run foreground (omit --detach; --rm scrubs it on exit), or set CE_VPS_ALLOW_DETACHED_TOKEN_ENV=1 to accept this secret-retention tradeoff.\n' >&2
    exit 78
  fi
  if [ "${detach}" = "1" ]; then
    printf 'WARNING: CE_VPS_ALLOW_DETACHED_TOKEN_ENV=1 set — CLAUDE_CODE_OAUTH_TOKEN will persist in container metadata until docker rm.\n' >&2
  fi
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

if [ "${detach}" = "1" ]; then
  # Named-persistent detached launch: start the container, then poll herdr for
  # readiness. Do NOT exec docker here (docker run -d returns immediately).
  "${docker_cmd[@]}"
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
    docker exec "${CE_VPS_CONTAINER_NAME}" test -S "${herdr_socket_path}" >/dev/null 2>&1 || return 1
    pane_list="$(docker exec --env "HERDR_SOCKET_PATH=${herdr_socket_path}" "${CE_VPS_CONTAINER_NAME}" herdr pane list 2>/dev/null)" || return 1
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
    printf 'herdr never became ready in container %s\n' "${CE_VPS_CONTAINER_NAME}" >&2
    printf 'inspect: docker logs %s\n' "${CE_VPS_CONTAINER_NAME}" >&2
    printf 'teardown: docker stop %s && docker rm %s\n' "${CE_VPS_CONTAINER_NAME}" "${CE_VPS_CONTAINER_NAME}" >&2
    exit 69
  fi
  printf 'container %s is ready.\n' "${CE_VPS_CONTAINER_NAME}"
  printf 'attach: docker exec -it %s herdr\n' "${CE_VPS_CONTAINER_NAME}"
  printf 'retire: docker stop %s && docker rm %s\n' "${CE_VPS_CONTAINER_NAME}" "${CE_VPS_CONTAINER_NAME}"
  exit 0
fi

exec "${docker_cmd[@]}"
