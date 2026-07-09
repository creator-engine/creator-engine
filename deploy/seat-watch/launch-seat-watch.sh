#!/usr/bin/env bash
set -euo pipefail

# Observe-only seat-watch daemon launcher. Slice 1 reads configured pane
# probes and emits JSONL events; it has no dispatch authority.

usage() {
  cat <<'USAGE'
Usage: launch-seat-watch.sh [--health] [--one-shot]

Starts the Creator Engine seat-watch daemon in observe-only mode. The daemon
polls configured seat panes and emits structured JSONL events for controller
visibility; it does not dispatch work or mutate queues.

Options:
  --health    verify required configuration and exit
  --one-shot  run one poll pass, then exit

Required environment:
  CE_SEAT_WATCH_SEAT_PROBES       JSON array: [{"seat_id":"<seat-id>","argv":["<probe-command>"]}]
                                  (argv MUST be read-only pane-read commands; the daemon
                                   cannot reject write-capable commands — operator-enforced)
  CE_SEAT_WATCH_FEED_PATH         absolute path to append-only JSONL event feed
  CE_DAEMON_LEASE_ROOT            singleton lease root

Optional environment:
  CE_SEAT_WATCH_INTERVAL_SECONDS       default 30
  CE_SEAT_WATCH_IDLE_THRESHOLD_POLLS   default 5
  CE_SEAT_WATCH_DISPATCH_PATTERNS      JSON array of delivery-ack strings
  CE_SEAT_WATCH_WEBHOOK_FILE           optional append-only JSONL mirror path
  CE_SEAT_WATCH_ITERATIONS             finite poll pass count
  CE_DAEMON_LEASE_TTL_SECONDS          default 300
  CE_DAEMON_HOLDER_ID                  optional lease holder id
  CE_DAEMON_ENV_FILE                   optional environment file to source before launch
  CE_DAEMON_UNCONTAINED                defaults to 1; slice 1 supports host launch only
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    die "missing required environment variable: $name"
  fi
}

repo_root() {
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null
  pwd
}

load_env_file() {
  if [[ -z "${CE_DAEMON_ENV_FILE:-}" ]]; then
    return
  fi
  [[ -f "$CE_DAEMON_ENV_FILE" ]] || die "CE_DAEMON_ENV_FILE does not exist: $CE_DAEMON_ENV_FILE"
  set -a
  # shellcheck source=/dev/null
  source "$CE_DAEMON_ENV_FILE"
  set +a
}

validate_required_env() {
  require_env CE_SEAT_WATCH_SEAT_PROBES
  require_env CE_SEAT_WATCH_FEED_PATH
  require_env CE_DAEMON_LEASE_ROOT
}

health() {
  validate_required_env
  printf 'seat-watch daemon: healthy\n'
}

main() {
  local mode="start"
  local normalized_args=()
  local arg

  load_env_file

  for arg in "$@"; do
    case "$arg" in
      --health)
        mode="health"
        ;;
      --one-shot)
        export CE_SEAT_WATCH_ITERATIONS=1
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        normalized_args+=("$arg")
        ;;
    esac
  done
  set -- "${normalized_args[@]}"

  if [[ $# -gt 0 ]]; then
    usage >&2
    die "unknown argument: $1"
  fi

  if [[ "$mode" == "health" ]]; then
    health
    return
  fi

  validate_required_env

  if [[ "${CE_DAEMON_UNCONTAINED:-1}" != "1" ]]; then
    die "slice 1 supports uncontained host launch only"
  fi

  local root
  root="$(repo_root)"
  cd -- "$root"
  export PYTHONPATH="${PYTHONPATH:-$root/validators}"

  umask 077
  install -d -m 0700 \
    "$(dirname -- "$CE_SEAT_WATCH_FEED_PATH")" \
    "$CE_DAEMON_LEASE_ROOT"
  if [[ -n "${CE_SEAT_WATCH_WEBHOOK_FILE:-}" ]]; then
    install -d -m 0700 "$(dirname -- "$CE_SEAT_WATCH_WEBHOOK_FILE")"
  fi

  exec python -m creator_engine_validator.seat_watch_runner "$@"
}

main "$@"
