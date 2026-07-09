#!/usr/bin/env bash
set -euo pipefail

SHARED_ROOT="${SHARED_ROOT:-/home/cedev2/creator-engine}"
STANDBY_ROOT="${STANDBY_ROOT:-/home/cedev2/ce-standby-main}"
DRY_RUN=0

trap 'fail "provisioning failed at line $LINENO: $BASH_COMMAND"' ERR

usage() {
  cat <<'USAGE'
Usage: provision-standby-surface.sh [--dry-run]

Provision the DGX standby controller with a dedicated main-tracking surface.

Environment:
  SHARED_ROOT   Source checkout used to create/fetch the standby worktree
                (default: /home/cedev2/creator-engine)
  STANDBY_ROOT  Dedicated standby worktree root
                (default: /home/cedev2/ce-standby-main)
USAGE
}

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRY-RUN: would run:'
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi
  "$@"
}

parse_args() {
  while (($#)); do
    case "$1" in
      --dry-run)
        DRY_RUN=1
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        fail "unknown argument: $1"
        ;;
    esac
    shift
  done
}

require_real_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

provision_worktree() {
  if [[ "$DRY_RUN" == "0" && ! -d "$SHARED_ROOT/.git" && ! -f "$SHARED_ROOT/.git" ]]; then
    fail "shared checkout is not a git worktree: $SHARED_ROOT"
  fi

  run git -C "$SHARED_ROOT" fetch origin main
  if [[ ! -e "$STANDBY_ROOT/.git" ]]; then
    run git -C "$SHARED_ROOT" worktree add "$STANDBY_ROOT" origin/main
  else
    run git -C "$STANDBY_ROOT" fetch origin
    run git -C "$STANDBY_ROOT" checkout -B main origin/main
    run git -C "$STANDBY_ROOT" reset --hard origin/main
  fi
}

verify_takeover() {
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY-RUN: would verify: ce takeover --dry-run --json from $STANDBY_ROOT"
    return 0
  fi

  (
    cd "$STANDBY_ROOT"
    ce takeover --dry-run --json | python3 -c '
import json, sys
r = json.load(sys.stdin)
assert r.get("ring0_verify", {}).get("ok") is True, f"ring0_verify.ok not true: {r}"
assert r.get("initial_state") == "AWAITING-OPERATOR", f"wrong initial_state: {r}"
print("OK: standby ce takeover --dry-run --json passed")
'
  )
}

verify_mint_helper() {
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY-RUN: would verify: python3 tools/mint-forge-token.py --help from $STANDBY_ROOT"
    return 0
  fi

  (
    cd "$STANDBY_ROOT"
    python3 tools/mint-forge-token.py --help >/dev/null
  )
}

main() {
  parse_args "$@"
  require_real_command git
  require_real_command python3
  if [[ "$DRY_RUN" == "0" ]]; then
    require_real_command ce
  fi

  provision_worktree
  verify_takeover
  verify_mint_helper

  local sha
  if [[ "$DRY_RUN" == "1" ]]; then
    sha="<dry-run>"
  else
    sha="$(git -C "$STANDBY_ROOT" rev-parse HEAD)"
  fi

  log "STANDBY SURFACE PROVISIONED"
  log "root: $STANDBY_ROOT"
  log "main sha: $sha"
  log "takeover dry-run: OK"
  log "mint-forge-token: OK"
}

main "$@"
