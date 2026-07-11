#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-codex-runsc.sh [--dry-run] [--detach|--foreground] [tui] [codex args...]
  run-codex-runsc.sh [--dry-run] [--detach|--foreground] exec [codex exec args...]

Detached mode:
  --detach                  Default. Launch with `docker run -d` under a named persistent
                            container (default name: ce-dgx-codex) instead of the
                            foreground `docker run --rm`. The script polls for
                            herdr readiness, prints attach/teardown commands, and
                            returns 0 without blocking. A crashed seat is left
                            inspectable (`docker logs`, exit code) because the
                            detached container is NOT removed with --rm.
  --foreground              Legacy migration mode. Launch foreground with docker
                            run --rm and block the caller's terminal.

Environment:
  CE_DGX_IMAGE              Docker image tag (default: creator-engine/codex-runsc:0.144.1-aarch64)
  CE_DGX_RUNTIME            Docker runtime (default: runsc-gvproxy-ptrace)
  CE_DGX_MEMORY_LIMIT       Docker --memory cgroup cap for this seat. Use docker units
                            (e.g. 8g, 12g, 16g). Set to empty string to disable.
                            Default: 8g  (runsc seats; prevents host OOM from unbounded sentry).
  CE_DGX_DOCKER_NETWORK     Optional Docker --network value (default: unset)
  CE_DGX_NETWORK            Deprecated alias for CE_DGX_DOCKER_NETWORK
  CE_DGX_REPO               Host repo path (default: current directory)
  CE_DGX_CODEX_HOME         Host codex home (default: /home/cedev4/.codex)
  CE_DGX_CODEX_HOME_MODE    Mount mode for codex home: rw or ro (default: rw)
  CE_DGX_CONTAINED_CODEX_CONFIG Host path for generated contained Codex config
                            (default: <seat-log-dir>/launcher/codex-config.toml)
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
  CE_LEDGER_ROOT            Host or container Active-Work Ledger root forwarded to the managed
                            Codex PreToolUse hook (default: container repo .ce/state ledger)
  CE_REVIEWER_AUTHORITY_REF Reviewer-authority envelope ref forwarded to the managed hook
  CE_DGX_SEAT_LOG_DIR       Host log dir mounted at /var/log/ce-seat
                            (default: ~/.ce/logs/seats/<seat-id>)
  CE_DGX_HOST_WORKTREE_ROOT Durable host root bind-mounted to the container worktree root
                            (default: <seat-log-dir>/worktrees/<launch-id>)
  CE_DGX_CONTAINER_WORKTREE_ROOT Container worktree root path (default: /var/tmp)
  CE_DGX_TTY_FLAGS          Docker TTY flags (default: -it; set to -i for non-TTY callers)
                            Detached default is empty; herdr owns the in-container PTY.
  CE_DGX_DETACH             Launch detached (docker run -d, named container) when set to 1
                            (default: 1)
  CE_DGX_FOREGROUND         Legacy foreground mode when set to 1
  CE_DGX_CONTAINER_NAME     Detached container name (default: ce-dgx-codex)
  CE_DGX_DOCKER_RESTART_POLICY Detached docker --restart policy
                            (default: empty; systemd template sets unless-stopped)
  CE_DGX_DRY_RUN            Print docker argv instead of executing when set to 1
  CE_DGX_ALLOW_PLAIN_RUNSC  Allow CE_DGX_RUNTIME=runsc despite DGX root-netns failure (default: 0)
  CE_DGX_ALLOW_SYSTRAP_CODEX
                            Allow CE_DGX_RUNTIME=runsc-gvproxy despite Codex guard-page panic (default: 0)
  CE_DGX_ALLOW_DOCKER_NETWORK
                            Allow Docker --network despite DGX root-netns failure (default: 0)
EOF
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

validate_no_credential_container_env() {
  local validators_root="${CE_DGX_VALIDATORS_ROOT:-${repo_root}/validators}"
  PYTHONPATH="${validators_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m creator_engine_validator.codex_launch_spec \
      --check-contained-launch-argv "$@"
}

dry_run="${CE_DGX_DRY_RUN:-0}"
if [ "${1:-}" = "--dry-run" ]; then
  dry_run=1
  shift
fi
detach="${CE_DGX_DETACH:-1}"
if [ "${CE_DGX_FOREGROUND:-0}" = "1" ]; then
  detach=0
fi
parse_launch_mode_flag() {
  case "${1:-}" in
    --detach)
      detach=1
      return 0
      ;;
    --foreground)
      detach=0
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}
if parse_launch_mode_flag "${1:-}"; then
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

CE_DGX_IMAGE="${CE_DGX_IMAGE:-creator-engine/codex-runsc:0.144.1-aarch64}"
CE_DGX_RUNTIME="${CE_DGX_RUNTIME:-runsc-gvproxy-ptrace}"
CE_DGX_MEMORY_LIMIT="${CE_DGX_MEMORY_LIMIT-8g}"
CE_DGX_DOCKER_NETWORK="${CE_DGX_DOCKER_NETWORK:-${CE_DGX_NETWORK:-}}"
CE_DGX_REPO="${CE_DGX_REPO:-$(pwd)}"
CE_DGX_CODEX_HOME="${CE_DGX_CODEX_HOME:-/home/cedev4/.codex}"
CE_DGX_CODEX_HOME_MODE="${CE_DGX_CODEX_HOME_MODE:-rw}"
CE_DGX_HERDR_SOCKET_PATH="${CE_DGX_HERDR_SOCKET_PATH:-/run/creator-engine/herdr/herdr.sock}"
CE_DGX_SUBSTRATE_RUN_DIR="${CE_DGX_SUBSTRATE_RUN_DIR:-/run/creator-engine}"
CE_DGX_CONTAINER_REPO="${CE_DGX_CONTAINER_REPO:-/workspace/creator-engine}"
CE_DGX_CONTAINER_USER="${CE_DGX_CONTAINER_USER:-cedev4}"
CE_DGX_CONTAINER_HOME="/home/${CE_DGX_CONTAINER_USER}"
CE_DGX_CONTAINER_CODEX_HOME="${CE_DGX_CONTAINER_HOME}/.codex"
CE_DGX_UID="${CE_DGX_UID:-$(id -u)}"
CE_DGX_GID="${CE_DGX_GID:-$(id -g)}"
CE_DGX_CONTAINER_NAME="${CE_DGX_CONTAINER_NAME:-ce-dgx-codex}"
CE_DGX_DOCKER_RESTART_POLICY="${CE_DGX_DOCKER_RESTART_POLICY:-}"
CE_DGX_SEAT_ID_EXPLICIT=0
if [ "${CE_DGX_SEAT_ID+x}" = "x" ]; then
  CE_DGX_SEAT_ID_EXPLICIT=1
fi
CE_DGX_SEAT_ID="${CE_DGX_SEAT_ID:-${CE_DGX_CONTAINER_NAME}}"
CE_DGX_EGRESS_BROKER_SOCKET="${CE_DGX_EGRESS_BROKER_SOCKET:-}"
CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET="${CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET:-/run/ce-egress-broker.sock}"
CE_DGX_SEAT_LOG_DIR="${CE_DGX_SEAT_LOG_DIR:-${HOME:-/home/cedev4}/.ce/logs/seats/${CE_DGX_SEAT_ID}}"
CE_DGX_LAUNCH_ID="${CE_DGX_LAUNCH_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
CE_DGX_CONTAINED_CODEX_CONFIG="${CE_DGX_CONTAINED_CODEX_CONFIG:-${CE_DGX_SEAT_LOG_DIR}/launcher/codex-config.toml}"
CE_DGX_HOST_WORKTREE_ROOT="${CE_DGX_HOST_WORKTREE_ROOT:-${CE_DGX_SEAT_LOG_DIR}/worktrees/${CE_DGX_LAUNCH_ID}}"
CE_DGX_CONTAINER_WORKTREE_ROOT="${CE_DGX_CONTAINER_WORKTREE_ROOT:-/var/tmp}"
CE_DGX_CONTAINER_SEAT_LOG_DIR="/var/log/ce-seat"
CE_DGX_CONTAINER_HERDR_SERVER_LOG="${CE_DGX_CONTAINER_SEAT_LOG_DIR}/herdr-server.log"

container_repo_path() {
  local raw="$1"
  case "${raw}" in
    "${CE_DGX_REPO}")
      printf '%s' "${CE_DGX_CONTAINER_REPO}"
      ;;
    "${CE_DGX_REPO}/"*)
      printf '%s/%s' "${CE_DGX_CONTAINER_REPO}" "${raw#"${CE_DGX_REPO}/"}"
      ;;
    *)
      printf '%s' "${raw}"
      ;;
  esac
}

shell_quote_env_value() {
  local value="$1"
  case "${value}" in
    *"'"*|*$'\n'*)
      printf 'governance hook env value contains unsupported quoting characters\n' >&2
      exit 2
      ;;
  esac
  printf '%q' "${value}"
}

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
case "${CE_DGX_HOST_WORKTREE_ROOT}" in
  /*)
    ;;
  *)
    printf 'CE_DGX_HOST_WORKTREE_ROOT must be an absolute path, got %s\n' "${CE_DGX_HOST_WORKTREE_ROOT}" >&2
    exit 2
    ;;
esac
case "${CE_DGX_CONTAINER_WORKTREE_ROOT}" in
  /*)
    ;;
  *)
    printf 'CE_DGX_CONTAINER_WORKTREE_ROOT must be an absolute path, got %s\n' "${CE_DGX_CONTAINER_WORKTREE_ROOT}" >&2
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

backup_stale_herdr_session() {
  local seat_log_dir="$1"
  local session_dir="${seat_log_dir}/xdg/config/herdr"
  local session_file="${session_dir}/session.json"
  local seat_real session_dir_real digest backup_file

  if [ ! -e "${session_file}" ] && [ ! -L "${session_file}" ]; then
    return 0
  fi
  if [ -L "${session_file}" ]; then
    printf 'refusing to clear symlinked herdr session file: %s\n' "${session_file}" >&2
    exit 66
  fi
  if [ ! -f "${session_file}" ]; then
    printf 'refusing to clear non-regular herdr session file: %s\n' "${session_file}" >&2
    exit 66
  fi

  seat_real="$(realpath -e "${seat_log_dir}")" || {
    printf 'could not resolve seat log dir: %s\n' "${seat_log_dir}" >&2
    exit 66
  }
  session_dir_real="$(realpath -e "${session_dir}")" || {
    printf 'could not resolve herdr session dir: %s\n' "${session_dir}" >&2
    exit 66
  }
  case "${session_dir_real}/" in
    "${seat_real}/"*)
      ;;
    *)
      printf 'refusing to clear herdr session outside seat log dir: %s resolves to %s (seat log dir %s)\n' "${session_dir}" "${session_dir_real}" "${seat_real}" >&2
      exit 66
      ;;
  esac

  digest="$(sha256sum "${session_file}" | awk '{print $1}')" || {
    printf 'could not hash stale herdr session: %s\n' "${session_file}" >&2
    exit 66
  }
  backup_file="${session_dir}/session.json.prelaunch-backup.${digest}"
  if [ -e "${backup_file}" ] || [ -L "${backup_file}" ]; then
    if [ -f "${backup_file}" ] && [ ! -L "${backup_file}" ]; then
      rm -f -- "${backup_file}"
    else
      printf 'refusing to overwrite unsafe herdr session backup path: %s\n' "${backup_file}" >&2
      exit 66
    fi
  fi
  mv -- "${session_file}" "${backup_file}"
  printf 'backed up stale herdr session: %s -> %s\n' "${session_file}" "${backup_file}" >&2
}

prepare_contained_codex_config() {
  local config_dir hook_command ledger_root reviewer_ref
  config_dir="$(dirname "${CE_DGX_CONTAINED_CODEX_CONFIG}")"
  mkdir -p "${config_dir}"
  ledger_root="${CE_LEDGER_ROOT:-${CE_DGX_REPO}/.ce/state/active-work-ledger}"
  ledger_root="$(container_repo_path "${ledger_root}")"
  hook_command="CE_LEDGER_ROOT=$(shell_quote_env_value "${ledger_root}")"
  if [ -n "${CE_REVIEWER_AUTHORITY_REF:-}" ]; then
    reviewer_ref="$(container_repo_path "${CE_REVIEWER_AUTHORITY_REF}")"
    hook_command="${hook_command} CE_REVIEWER_AUTHORITY_REF=$(shell_quote_env_value "${reviewer_ref}")"
  fi
  hook_command="${hook_command} PYTHONPATH=/workspace/creator-engine/validators python3 /workspace/creator-engine/.codex/hooks/ce-pretooluse-codex.py"
  # Codex' default workspace-write mode starts an inner bwrap sandbox.
  # bwrap cannot nest inside runsc/gVisor, so gVisor is the sandbox here.
  (
    umask 077
    cat >"${CE_DGX_CONTAINED_CODEX_CONFIG}" <<EOF
# Generated by deploy/dgx-runsc/run-codex-runsc.sh for contained DGX seats.
# Nested Codex bubblewrap cannot run inside runsc/gVisor; gVisor is the sandbox.
approval_policy = "never"
sandbox_mode = "danger-full-access"
model = "gpt-5.6-terra"
model_reasoning_effort = "high"
allow_managed_hooks_only = true
check_for_update_on_startup = false

[tui]
status_line = ["model-with-reasoning", "current-dir", "git-branch", "pull-request-number", "context-remaining", "context-used", "five-hour-limit", "weekly-limit"]
status_line_use_colors = true

[features]
hooks = true

[[hooks.PreToolUse]]
matcher = "^(Bash|Read|apply_patch|Edit|Write|MultiEdit|mcp__.*)$"

[[hooks.PreToolUse.hooks]]
type = "command"
command = '${hook_command}'
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

mkdir -p "${CE_DGX_HOST_WORKTREE_ROOT}"
chown "${CE_DGX_UID}:${CE_DGX_GID}" "${CE_DGX_HOST_WORKTREE_ROOT}" 2>/dev/null || true
chmod 0700 "${CE_DGX_HOST_WORKTREE_ROOT}" 2>/dev/null || true

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
  if [ -n "${CE_DGX_EGRESS_BROKER_SOCKET}" ]; then
    [ -S "${CE_DGX_EGRESS_BROKER_SOCKET}" ] || {
      printf 'egress broker socket not found: %s\n' "${CE_DGX_EGRESS_BROKER_SOCKET}" >&2
      exit 66
    }
  fi
  backup_stale_herdr_session "${CE_DGX_SEAT_LOG_DIR}"
fi

if [ "${CE_DGX_TTY_FLAGS+x}" != "x" ]; then
  if [ "${detach}" = "1" ]; then
    CE_DGX_TTY_FLAGS=""
  else
    CE_DGX_TTY_FLAGS="-it"
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
contained_codex_config_mount="type=bind,source=${CE_DGX_CONTAINED_CODEX_CONFIG},target=${CE_DGX_CONTAINER_CODEX_HOME}/config.toml,readonly"
worktree_root_mount="type=bind,source=${CE_DGX_HOST_WORKTREE_ROOT},target=${CE_DGX_CONTAINER_WORKTREE_ROOT}"
egress_broker_mount=""
if [ -n "${CE_DGX_EGRESS_BROKER_SOCKET}" ]; then
  egress_broker_mount="type=bind,source=${CE_DGX_EGRESS_BROKER_SOCKET},target=${CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET}"
fi
# Foreground keeps --rm (ephemeral). Detached drops --rm and adds -d --name so a
# crashed/stopped seat stays inspectable (docker logs, exit code) for forensics.
lifecycle_flags=(--rm)
if [ "${detach}" = "1" ]; then
  lifecycle_flags=(-d --name "${CE_DGX_CONTAINER_NAME}")
  if [ -n "${CE_DGX_DOCKER_RESTART_POLICY}" ]; then
    lifecycle_flags+=("--restart=${CE_DGX_DOCKER_RESTART_POLICY}")
  fi
elif [ "${mode}" = "tui" ]; then
  lifecycle_flags=(--rm --name "${CE_DGX_CONTAINER_NAME}")
fi

docker_cmd=(
  docker run "${lifecycle_flags[@]}"
  "--runtime=${CE_DGX_RUNTIME}"
)
if [[ -n "$CE_DGX_MEMORY_LIMIT" ]]; then
  docker_cmd+=(--memory "$CE_DGX_MEMORY_LIMIT")
fi
docker_cmd+=(
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
  --mount "${worktree_root_mount}"
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

validate_no_credential_container_env "${docker_cmd[@]}"

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
