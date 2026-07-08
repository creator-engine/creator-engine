#!/usr/bin/env bash
set -euo pipefail

DEFAULT_QUEUE_ENV_FILE="/etc/creator-engine/ce-queue-daemon.env"
QUEUE_SERVICE="ce-queue-daemon.service"
SYSTEMD_UNIT_DIR="/etc/systemd/system"
UNIT_CHANGED=0

usage() {
  cat <<'USAGE'
Usage: redeploy-singleton.sh --daemon NAME [--dry-run] [--repo-root PATH] [--env-file PATH]

Redeploy a Creator Engine singleton daemon from the current checkout.

Required:
  --daemon NAME     Supported values: queue-daemon, option-a-materializer

Options:
  --dry-run         Print planned actions without installing, reloading, or restarting
  --repo-root PATH  Source checkout root; default resolves relative to this script
  --env-file PATH   Queue daemon env file; default /etc/creator-engine/ce-queue-daemon.env
  -h, --help        Show this help
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

resolve_repo_root() {
  local raw_root="$1"
  local script_dir
  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -z "$raw_root" ]]; then
    cd -- "$script_dir/../.." >/dev/null
  else
    cd -- "$raw_root" >/dev/null
  fi
  pwd
}

sed_replacement_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/[&#]/\\&/g'
}

validate_repo_root() {
  local repo_root="$1"
  [[ -d "$repo_root/.git" || -f "$repo_root/.git" ]] || die "repo root does not look like a git checkout: $repo_root"
  [[ -f "$repo_root/deploy/queue-daemon/$QUEUE_SERVICE" ]] || die "missing queue-daemon unit in checkout: $repo_root/deploy/queue-daemon/$QUEUE_SERVICE"
  [[ -x "$repo_root/deploy/queue-daemon/launch-queue-daemon.sh" ]] || die "missing executable health probe: $repo_root/deploy/queue-daemon/launch-queue-daemon.sh"
}

validate_queue_env_file() {
  local env_file="$1"
  if [[ ! -f "$env_file" ]]; then
    cat >&2 <<EOF
ERROR: queue-daemon env file is missing: $env_file
Create it before redeploying. See deploy/queue-daemon/RELOCATION.md for the
approved env-file keys and host setup steps.
EOF
    exit 1
  fi

  local mode
  mode="$(stat -c '%a' -- "$env_file")" || die "could not stat env file: $env_file"
  if [[ "$mode" != "600" ]]; then
    cat >&2 <<EOF
ERROR: queue-daemon env file mode must be exactly 0600: $env_file has $mode
Remediate with:
  sudo chmod 0600 $env_file
Then re-check deploy/queue-daemon/RELOCATION.md before redeploying.
EOF
    exit 1
  fi
}

render_queue_unit() {
  local repo_root="$1"
  local env_file="$2"
  local output="$3"
  local src="$repo_root/deploy/queue-daemon/$QUEUE_SERVICE"
  local rendered_repo_root
  local rendered_env_file
  rendered_repo_root="$(sed_replacement_escape "$repo_root")"
  rendered_env_file="$(sed_replacement_escape "$env_file")"
  sed \
    -e "s#/workspace/creator-engine#$rendered_repo_root#g" \
    -e "s#^EnvironmentFile=.*#EnvironmentFile=$rendered_env_file#g" \
    "$src" > "$output"
}

dry_run_queue_daemon() {
  local repo_root="$1"
  local env_file="$2"
  local dst="$SYSTEMD_UNIT_DIR/$QUEUE_SERVICE"
  local tmp
  tmp="$(mktemp "${TMPDIR:-/tmp}/ce-singleton-unit.XXXXXX")"
  trap 'rm -f -- "$tmp"' RETURN
  render_queue_unit "$repo_root" "$env_file" "$tmp"

  printf 'Dry-run redeploy plan for queue-daemon\n'
  printf 'Would verify env file exists with mode 0600: %s\n' "$env_file"
  if [[ -f "$dst" ]] && cmp -s "$tmp" "$dst"; then
    printf 'Would leave unchanged systemd unit: %s\n' "$dst"
  else
    printf 'Would install or update systemd unit: %s -> %s\n' "$repo_root/deploy/queue-daemon/$QUEUE_SERVICE" "$dst"
  fi
  printf 'Would reload systemd daemon if unit content changes\n'
  printf 'Would enable service: %s\n' "$QUEUE_SERVICE"
  printf 'Would restart service when active, or start it when inactive: %s\n' "$QUEUE_SERVICE"
  printf 'Would wait up to 30 seconds for active state: %s\n' "$QUEUE_SERVICE"
  printf 'Would run health probe: %s --health\n' "$repo_root/deploy/queue-daemon/launch-queue-daemon.sh"
  rm -f -- "$tmp"
  trap - RETURN
}

install_queue_unit_if_changed() {
  local repo_root="$1"
  local env_file="$2"
  local dst="$SYSTEMD_UNIT_DIR/$QUEUE_SERVICE"
  local tmp
  tmp="$(mktemp "${TMPDIR:-/tmp}/ce-singleton-unit.XXXXXX")"
  trap 'rm -f -- "$tmp"' RETURN
  render_queue_unit "$repo_root" "$env_file" "$tmp"

  if [[ -f "$dst" ]] && cmp -s "$tmp" "$dst"; then
    printf 'unchanged: %s\n' "$dst"
    UNIT_CHANGED=0
  else
    printf 'running: sudo install -m 0644 %s %s\n' "$tmp" "$dst"
    sudo install -m 0644 "$tmp" "$dst"
    printf 'installed: %s\n' "$dst"
    UNIT_CHANGED=1
  fi

  rm -f -- "$tmp"
  trap - RETURN
}

reload_systemd_if_needed() {
  if [[ "$UNIT_CHANGED" -eq 1 ]]; then
    printf 'running: sudo systemctl daemon-reload\n'
    sudo systemctl daemon-reload
  else
    printf 'skipped: systemctl daemon-reload (unit unchanged)\n'
  fi
}

enable_and_restart_queue_service() {
  printf 'running: sudo systemctl enable %s\n' "$QUEUE_SERVICE"
  sudo systemctl enable "$QUEUE_SERVICE"
  if systemctl is-active --quiet "$QUEUE_SERVICE"; then
    printf 'running: sudo systemctl restart %s\n' "$QUEUE_SERVICE"
    sudo systemctl restart "$QUEUE_SERVICE"
  else
    printf 'running: sudo systemctl start %s\n' "$QUEUE_SERVICE"
    sudo systemctl start "$QUEUE_SERVICE"
  fi
}

wait_for_queue_service() {
  local deadline=$((SECONDS + 30))
  while (( SECONDS <= deadline )); do
    if systemctl is-active --quiet "$QUEUE_SERVICE"; then
      printf 'active: %s\n' "$QUEUE_SERVICE"
      return
    fi
    sleep 1
  done

  systemctl status "$QUEUE_SERVICE" --no-pager >&2 || true
  die "timed out waiting for active service: $QUEUE_SERVICE"
}

run_queue_health_probe() {
  local repo_root="$1"
  local env_file="$2"
  local probe="$repo_root/deploy/queue-daemon/launch-queue-daemon.sh"

  if [[ -r "$env_file" ]]; then
    printf 'running: %s --health\n' "$probe"
    (
      set -a
      # shellcheck source=/dev/null
      source "$env_file"
      set +a
      export CE_QUEUE_DAEMON_REPO_ROOT="$repo_root"
      export CE_DAEMON_REPO_ROOT="$repo_root"
      exec "$probe" --health
    )
    return
  fi

  printf 'running: sudo env CE_QUEUE_DAEMON_REPO_ROOT=%s CE_DAEMON_REPO_ROOT=%s bash -c <env-file health probe>\n' "$repo_root" "$repo_root"
  sudo env CE_QUEUE_DAEMON_REPO_ROOT="$repo_root" CE_DAEMON_REPO_ROOT="$repo_root" \
    bash -c 'set -euo pipefail; set -a; source "$1"; set +a; exec "$2" --health' \
    _ "$env_file" "$probe"
}

redeploy_queue_daemon() {
  local repo_root="$1"
  local env_file="$2"
  local dry_run="$3"

  validate_repo_root "$repo_root"
  validate_queue_env_file "$env_file"

  if [[ "$dry_run" -eq 1 ]]; then
    dry_run_queue_daemon "$repo_root" "$env_file"
    return
  fi

  install_queue_unit_if_changed "$repo_root" "$env_file"
  reload_systemd_if_needed
  enable_and_restart_queue_service
  wait_for_queue_service
  run_queue_health_probe "$repo_root" "$env_file"
  printf 'OK: queue-daemon redeploy completed\n'
}

redeploy_option_a_materializer() {
  local dry_run="$1"
  if [[ "$dry_run" -eq 1 ]]; then
    printf 'Dry-run redeploy plan for option-a-materializer\n'
    printf 'Would skip: option-a-materializer singleton is accepted as a future target but is not deployed yet.\n'
    return
  fi
  die "option-a-materializer is not yet deployed; no systemd unit exists to redeploy"
}

main() {
  local daemon=""
  local dry_run=0
  local repo_root_arg=""
  local env_file=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --daemon)
        daemon="${2:?--daemon requires a name}"
        shift 2
        ;;
      --dry-run)
        dry_run=1
        shift
        ;;
      --repo-root)
        repo_root_arg="${2:?--repo-root requires a path}"
        shift 2
        ;;
      --env-file)
        env_file="${2:?--env-file requires a path}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        usage >&2
        die "unknown argument: $1"
        ;;
    esac
  done

  [[ -n "$daemon" ]] || {
    usage >&2
    die "--daemon is required"
  }

  local repo_root
  repo_root="$(resolve_repo_root "$repo_root_arg")"

  case "$daemon" in
    queue-daemon)
      redeploy_queue_daemon "$repo_root" "${env_file:-$DEFAULT_QUEUE_ENV_FILE}" "$dry_run"
      ;;
    option-a-materializer)
      redeploy_option_a_materializer "$dry_run"
      ;;
    *)
      usage >&2
      die "unsupported daemon: $daemon"
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
