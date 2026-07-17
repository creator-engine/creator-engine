#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run-vps-runsc.sh [--dry-run] [--harness codex|claude|controller] [--detach|--foreground] [tui] [harness args...]
  run-vps-runsc.sh [--dry-run] [--harness codex|claude|controller] [--detach|--foreground] exec [harness exec args...]

Launch mode:
  --detach                    Default. Launch with docker run -d under a named
                              persistent container, poll herdr readiness, and return.
  --foreground                Legacy migration mode. Launch foreground with docker
                              run --rm and block the caller's terminal.

Environment:
  CE_VPS_IMAGE                 Explicit governed Docker image override. By default,
                                source + digest are resolved from surfaces/manifest.yaml.
  CE_VPS_RUNTIME               Docker runtime (default: runsc-gvproxy-ptrace)
  CE_VPS_MEMORY_LIMIT          Docker --memory cgroup cap for this seat. Default: 8g.
                                Set to empty string to disable.
  CE_VPS_DOCKER_NETWORK        Docker --network value (default: host)
  CE_VPS_HARNESS               Harness: codex, claude, or controller (default: codex)
  CE_DGX_HARNESS               Deprecated alias for CE_VPS_HARNESS
  CE_VPS_DETACH                Launch detached when set to 1 (default: 1)
  CE_VPS_FOREGROUND            Legacy foreground mode when set to 1
  CE_VPS_CONTAINER_NAME        Container --name for detached launch
                                (default: ce-vps-<harness>, e.g. ce-vps-codex)
  CE_VPS_DOCKER_RESTART_POLICY Detached docker --restart policy
                                (default: empty; systemd template sets unless-stopped)
  CE_VPS_REPO                  Host repo path (default: current directory)
  CE_VPS_CODEX_HOME            Host codex home (default: $HOME/.codex)
  CE_VPS_CODEX_HOME_MODE       Mount mode for codex home: rw or ro (default: rw)
  CE_VPS_CONTAINED_CODEX_CONFIG Host path for generated contained Codex config
                                (default: <seat-log-dir>/launcher/codex-config.toml)
  CE_VPS_CODEX_BIN             Host standalone codex binary (default: first codex on PATH)
  CE_VPS_CODEX_PACKAGE_ROOT    Optional host @openai/codex npm package root. If unset,
                                npm symlinks ending in @openai/codex/bin/codex.js are autodetected.
  CE_VPS_CLAUDE_BIN            Optional host Claude binary mounted at /usr/local/bin/claude
  CE_LEDGER_ROOT               Host or container Active-Work Ledger root forwarded to the managed
                                Codex PreToolUse hook (default: container repo .ce/state ledger)
  CE_REVIEWER_AUTHORITY_REF    Reviewer-authority envelope ref forwarded to the managed hook
  CE_VPS_CONTAINER_REPO        Container repo path (default: /workspace/creator-engine)
  CE_VPS_CONTAINER_USER        Container seat user name (default: current user)
  CE_VPS_UID                   Container uid (default: id -u)
  CE_VPS_GID                   Container gid (default: id -g)
  CE_VPS_SEAT_ID               Host log seat id (default: CE_VPS_CONTAINER_NAME)
  CE_VPS_EGRESS_BROKER_SOCKET  Host self-push broker Unix socket whose parent directory is bind-mounted
                                (default: unset)
  CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET Container broker socket path. When unset and
                                CE_VPS_EGRESS_BROKER_SOCKET is set, defaults to
                                /run/ce-egress/<host-socket-basename>.
  CE_VPS_EGRESS_SELF_REVIEW_SOCKET Host self-review broker Unix socket whose parent directory is
                                bind-mounted (default: unset)
                                Requires CE_VPS_SEAT_ID to be set explicitly (same rule as self-push).
  CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET Container self-review socket path
                                When unset and CE_VPS_EGRESS_SELF_REVIEW_SOCKET is set, defaults to
                                /run/ce-egress/<host-socket-basename>.
  CE_VPS_SEAT_LOG_DIR          Host log dir mounted at /var/log/ce-seat
                                (default: ~/.ce/logs/seats/<seat-id>)
  CE_VPS_HOST_WORKTREE_ROOT    Durable host root bind-mounted to the container worktree root
                                (default: <seat-log-dir>/worktrees/<launch-id>)
  CE_VPS_CONTAINER_WORKTREE_ROOT Container worktree root path (default: /var/tmp)
  CE_VPS_TTY_FLAGS             Docker TTY flags (default: -it; set to -i for non-TTY callers)
                                Detached default is empty; herdr owns the in-container PTY.
  CE_VPS_DRY_RUN               Print docker argv instead of executing when set to 1
EOF
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

resolve_manifest_vps_image() {
  local manifest_path="$1"
  python3 - "${manifest_path}" <<'PY'
import re
import sys

import yaml

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
except (OSError, yaml.YAMLError) as exc:
    raise SystemExit(f"VPS runsc image manifest refusal: cannot read canonical manifest: {exc}")

surfaces = document.get("surfaces") if isinstance(document, dict) else None
if not isinstance(surfaces, list):
    raise SystemExit("VPS runsc image manifest refusal: surfaces must be a list")
matches = [item for item in surfaces if isinstance(item, dict) and item.get("name") == "VPS runsc image"]
if len(matches) != 1:
    raise SystemExit("VPS runsc image manifest refusal: expected exactly one VPS runsc image entry")
surface = matches[0]
source = surface.get("source")
digest = surface.get("commit_or_digest")
version = surface.get("version")
update_policy = surface.get("update_policy")
if version != "x86_64":
    raise SystemExit("VPS runsc image manifest refusal: version must be x86_64")
if source != "docker.io/creator-engine/codex-runsc:x86_64":
    raise SystemExit("VPS runsc image manifest refusal: source is missing, mutable, or inconsistent")
if not isinstance(digest, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
    raise SystemExit("VPS runsc image manifest refusal: commit_or_digest must be an immutable sha256 pin")
if not isinstance(update_policy, str) or "digest pin required" not in update_policy:
    raise SystemExit("VPS runsc image manifest refusal: update policy does not require a digest pin")
print(f"{source}@{digest}")
PY
}

validate_no_credential_container_env() {
  local validators_root="${CE_VPS_VALIDATORS_ROOT:-${repo_root}/validators}"
  PYTHONPATH="${validators_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m creator_engine_validator.codex_launch_spec \
      --check-contained-launch-argv "$@"
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

detach="${CE_VPS_DETACH:-1}"
if [ "${CE_VPS_FOREGROUND:-0}" = "1" ]; then
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

harness="${CE_VPS_HARNESS:-${CE_DGX_HARNESS:-codex}}"
if [ "${1:-}" = "--harness" ]; then
  if [ -z "${2:-}" ]; then
    printf '%s\n' '--harness requires codex, claude, or controller' >&2
    exit 2
  fi
  harness="$2"
  shift 2
fi

# Allow launch-mode flags after --harness as well (parse order tolerance).
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

manifest_path="${repo_root}/surfaces/manifest.yaml"
if [ "${CE_VPS_DRY_RUN:-0}" = "1" ] && [ -n "${CE_VPS_TEST_SURFACES_MANIFEST:-}" ]; then
  manifest_path="${CE_VPS_TEST_SURFACES_MANIFEST}"
fi
if [ -z "${CE_VPS_IMAGE:-}" ]; then
  CE_VPS_IMAGE="$(resolve_manifest_vps_image "${manifest_path}")"
fi
CE_VPS_RUNTIME="${CE_VPS_RUNTIME:-runsc-gvproxy-ptrace}"
CE_VPS_MEMORY_LIMIT="${CE_VPS_MEMORY_LIMIT-8g}"
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
CE_VPS_CONTAINER_NAME="${CE_VPS_CONTAINER_NAME:-ce-vps-${harness}}"
CE_VPS_DOCKER_RESTART_POLICY="${CE_VPS_DOCKER_RESTART_POLICY:-}"
CE_VPS_SEAT_ID_EXPLICIT=0
if [ "${CE_VPS_SEAT_ID+x}" = "x" ]; then
  CE_VPS_SEAT_ID_EXPLICIT=1
fi
CE_VPS_SEAT_ID="${CE_VPS_SEAT_ID:-${CE_VPS_CONTAINER_NAME}}"
CE_VPS_EGRESS_BROKER_SOCKET="${CE_VPS_EGRESS_BROKER_SOCKET:-}"
CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET="${CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET:-}"
CE_VPS_EGRESS_SELF_REVIEW_SOCKET="${CE_VPS_EGRESS_SELF_REVIEW_SOCKET:-}"
CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET="${CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET:-}"
CE_VPS_SEAT_LOG_DIR="${CE_VPS_SEAT_LOG_DIR:-${HOME:-/home/ce}/.ce/logs/seats/${CE_VPS_SEAT_ID}}"
CE_VPS_LAUNCH_ID="${CE_VPS_LAUNCH_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
CE_VPS_CONTAINED_CODEX_CONFIG="${CE_VPS_CONTAINED_CODEX_CONFIG:-${CE_VPS_SEAT_LOG_DIR}/launcher/codex-config.toml}"
CE_VPS_HOST_WORKTREE_ROOT="${CE_VPS_HOST_WORKTREE_ROOT:-${CE_VPS_SEAT_LOG_DIR}/worktrees/${CE_VPS_LAUNCH_ID}}"
CE_VPS_CONTAINER_WORKTREE_ROOT="${CE_VPS_CONTAINER_WORKTREE_ROOT:-/var/tmp}"
CE_VPS_CONTAINER_CODEX_PACKAGE_ROOT="/usr/local/lib/node_modules/@openai/codex"
CE_VPS_CONTAINER_SEAT_LOG_DIR="/var/log/ce-seat"
CE_VPS_CONTAINER_HERDR_SERVER_LOG="${CE_VPS_CONTAINER_SEAT_LOG_DIR}/herdr-server.log"
herdr_socket_path="/run/creator-engine/herdr/herdr.sock"

container_repo_path() {
  local raw="$1"
  case "${raw}" in
    "${CE_VPS_REPO}")
      printf '%s' "${CE_VPS_CONTAINER_REPO}"
      ;;
    "${CE_VPS_REPO}/"*)
      printf '%s/%s' "${CE_VPS_CONTAINER_REPO}" "${raw#"${CE_VPS_REPO}/"}"
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
if [ -n "${CE_VPS_EGRESS_BROKER_SOCKET}" ]; then
  if [ "${CE_VPS_SEAT_ID_EXPLICIT}" != "1" ]; then
    printf 'CE_VPS_SEAT_ID must be set explicitly when CE_VPS_EGRESS_BROKER_SOCKET is set\n' >&2
    exit 2
  fi
  if [[ ! "${CE_VPS_SEAT_ID}" =~ ^dev-[0-9]+$ ]]; then
    printf 'CE_VPS_SEAT_ID must be a broker seat id like dev-3 when CE_VPS_EGRESS_BROKER_SOCKET is set, got %s\n' "${CE_VPS_SEAT_ID}" >&2
    exit 2
  fi
  case "${CE_VPS_EGRESS_BROKER_SOCKET}" in
    /*)
      ;;
    *)
      printf 'CE_VPS_EGRESS_BROKER_SOCKET must be an absolute path, got %s\n' "${CE_VPS_EGRESS_BROKER_SOCKET}" >&2
      exit 2
      ;;
  esac
  if [ -z "${CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET}" ]; then
    CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET="/run/ce-egress/$(basename -- "${CE_VPS_EGRESS_BROKER_SOCKET}")"
  fi
  case "${CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET}" in
    /*)
      ;;
    *)
      printf 'CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET must be an absolute path, got %s\n' "${CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET}" >&2
      exit 2
      ;;
  esac
  if [ "$(basename -- "${CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET}")" != "$(basename -- "${CE_VPS_EGRESS_BROKER_SOCKET}")" ]; then
    printf 'CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET basename must match CE_VPS_EGRESS_BROKER_SOCKET basename for stable directory mounts: %s vs %s\n' "${CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET}" "${CE_VPS_EGRESS_BROKER_SOCKET}" >&2
    exit 2
  fi
fi
if [ -n "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}" ]; then
  if [ "${CE_VPS_SEAT_ID_EXPLICIT}" != "1" ]; then
    printf 'CE_VPS_SEAT_ID must be set explicitly when CE_VPS_EGRESS_SELF_REVIEW_SOCKET is set\n' >&2
    exit 2
  fi
  if [[ ! "${CE_VPS_SEAT_ID}" =~ ^dev-[0-9]+$ ]]; then
    printf 'CE_VPS_SEAT_ID must be a broker seat id like dev-3 when CE_VPS_EGRESS_SELF_REVIEW_SOCKET is set, got %s\n' "${CE_VPS_SEAT_ID}" >&2
    exit 2
  fi
  case "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}" in
    /*)
      ;;
    *)
      printf 'CE_VPS_EGRESS_SELF_REVIEW_SOCKET must be an absolute path, got %s\n' "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}" >&2
      exit 2
      ;;
  esac
  if [ -z "${CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET}" ]; then
    CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET="/run/ce-egress/$(basename -- "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}")"
  fi
  case "${CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET}" in
    /*)
      ;;
    *)
      printf 'CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET must be an absolute path, got %s\n' "${CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET}" >&2
      exit 2
      ;;
  esac
  if [ "$(basename -- "${CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET}")" != "$(basename -- "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}")" ]; then
    printf 'CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET basename must match CE_VPS_EGRESS_SELF_REVIEW_SOCKET basename for stable directory mounts: %s vs %s\n' "${CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET}" "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}" >&2
    exit 2
  fi
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
case "${CE_VPS_HOST_WORKTREE_ROOT}" in
  /*)
    ;;
  *)
    printf 'CE_VPS_HOST_WORKTREE_ROOT must be an absolute path, got %s\n' "${CE_VPS_HOST_WORKTREE_ROOT}" >&2
    exit 2
    ;;
esac
case "${CE_VPS_CONTAINER_WORKTREE_ROOT}" in
  /*)
    ;;
  *)
    printf 'CE_VPS_CONTAINER_WORKTREE_ROOT must be an absolute path, got %s\n' "${CE_VPS_CONTAINER_WORKTREE_ROOT}" >&2
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
  config_dir="$(dirname "${CE_VPS_CONTAINED_CODEX_CONFIG}")"
  mkdir -p "${config_dir}"
  ledger_root="${CE_LEDGER_ROOT:-${CE_VPS_REPO}/.ce/state/active-work-ledger}"
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
    cat >"${CE_VPS_CONTAINED_CODEX_CONFIG}" <<EOF
# Generated by deploy/vps-runsc/run-vps-runsc.sh for contained VPS seats.
# Nested Codex bubblewrap cannot run inside runsc/gVisor; gVisor is the sandbox.
approval_policy = "never"
sandbox_mode = "danger-full-access"
model = "gpt-5.6-terra"
model_reasoning_effort = "high"
allow_managed_hooks_only = true

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
  chown "${CE_VPS_UID}:${CE_VPS_GID}" "${CE_VPS_CONTAINED_CODEX_CONFIG}" 2>/dev/null || true
  chmod 0644 "${CE_VPS_CONTAINED_CODEX_CONFIG}"
}

prepare_contained_codex_config
mkdir -p "${CE_VPS_HOST_WORKTREE_ROOT}"
chown "${CE_VPS_UID}:${CE_VPS_GID}" "${CE_VPS_HOST_WORKTREE_ROOT}" 2>/dev/null || true
chmod 0700 "${CE_VPS_HOST_WORKTREE_ROOT}" 2>/dev/null || true

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
  if [ -n "${CE_VPS_EGRESS_BROKER_SOCKET}" ]; then
    [ -S "${CE_VPS_EGRESS_BROKER_SOCKET}" ] || {
      printf 'egress broker socket not found: %s\n' "${CE_VPS_EGRESS_BROKER_SOCKET}" >&2
      exit 66
    }
  fi
  if [ -n "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}" ]; then
    [ -S "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}" ] || {
      printf 'egress self-review socket not found: %s\n' "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}" >&2
      exit 66
    }
  fi
  backup_stale_herdr_session "${CE_VPS_SEAT_LOG_DIR}"
fi

if [ "${CE_VPS_TTY_FLAGS+x}" != "x" ]; then
  if [ "${detach}" = "1" ]; then
    CE_VPS_TTY_FLAGS=""
  else
    CE_VPS_TTY_FLAGS="-it"
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
worktree_root_mount="type=bind,source=${CE_VPS_HOST_WORKTREE_ROOT},target=${CE_VPS_CONTAINER_WORKTREE_ROOT}"
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
egress_broker_mount=""
if [ -n "${CE_VPS_EGRESS_BROKER_SOCKET}" ]; then
  egress_broker_mount="type=bind,source=$(dirname -- "${CE_VPS_EGRESS_BROKER_SOCKET}"),target=$(dirname -- "${CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET}"),readonly"
fi
egress_self_review_mount=""
if [ -n "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}" ]; then
  egress_self_review_mount="type=bind,source=$(dirname -- "${CE_VPS_EGRESS_SELF_REVIEW_SOCKET}"),target=$(dirname -- "${CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET}"),readonly"
fi

# Foreground = ephemeral (--rm). Detached = named-persistent (no --rm, add -d
# and --name) so a crashed/stopped seat is inspectable via docker logs/exit
# code; --rm previously deleted forensic state on a live outage.
docker_run_flags=()
if [ "${detach}" = "1" ]; then
  docker_run_flags+=(-d --name "${CE_VPS_CONTAINER_NAME}")
  if [ -n "${CE_VPS_DOCKER_RESTART_POLICY}" ]; then
    docker_run_flags+=("--restart=${CE_VPS_DOCKER_RESTART_POLICY}")
  fi
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
)
if [[ -n "$CE_VPS_MEMORY_LIMIT" ]]; then
  docker_cmd+=(--memory "$CE_VPS_MEMORY_LIMIT")
fi
docker_cmd+=(
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
  --mount "${worktree_root_mount}"
  "${codex_mount_args[@]}"
)

if [ "${image_harness}" = "claude" ]; then
  if [ -n "${CE_VPS_CLAUDE_BIN}" ]; then
    docker_cmd+=(
      --mount "type=bind,source=${CE_VPS_CLAUDE_BIN},target=/usr/local/bin/claude,readonly"
    )
  fi
fi

if [ -n "${egress_broker_mount}" ]; then
  docker_cmd+=(
    --env "CE_EGRESS_BROKER_SOCKET=${CE_VPS_CONTAINER_EGRESS_BROKER_SOCKET}"
    --env "CE_SEAT_ID=${CE_VPS_SEAT_ID}"
    --mount "${egress_broker_mount}"
  )
fi

if [ -n "${egress_self_review_mount}" ]; then
  docker_cmd+=(
    --env "CE_EGRESS_SELF_REVIEW_SOCKET=${CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET}"
    --env "CE_SEAT_ID=${CE_VPS_SEAT_ID}"
  )
  # The broker and self-review sockets commonly live side-by-side in the same
  # host directory (e.g. /run/ce-egress/dev-3.sock and dev-3-review.sock), so
  # the parent-directory mount specs computed above are frequently identical.
  # `docker run` rejects two `--mount` flags with the same destination
  # ("Duplicate mount point"), so only append this mount when it differs from
  # the one already emitted for the broker socket; both sockets remain
  # reachable inside the container because they share the single mounted dir.
  if [ "${egress_self_review_mount}" != "${egress_broker_mount}" ]; then
    docker_cmd+=(--mount "${egress_self_review_mount}")
  fi
fi

docker_cmd+=("${tty_flags[@]}")
docker_cmd+=("${CE_VPS_IMAGE}")
docker_cmd+=("${container_cmd[@]}")

validate_no_credential_container_env "${docker_cmd[@]}"

if [ "${dry_run}" = "1" ]; then
  printf '%q ' "${docker_cmd[@]}"
  printf '\n'
  exit 0
fi

if [ "${detach}" = "1" ]; then
  # Named-persistent detached launch: start the container, then poll herdr for
  # readiness. Do NOT exec docker here (docker run -d returns immediately).
  docker rm -f "${CE_VPS_CONTAINER_NAME}" 2>/dev/null || true
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
    pane_list="$(docker exec "${CE_VPS_CONTAINER_NAME}" herdr pane list 2>/dev/null)" || return 1
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
