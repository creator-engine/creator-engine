#!/usr/bin/env bash
set -euo pipefail

SMOKE_TMPDIR=""

usage() {
  cat <<'USAGE'
Usage: smoke-singleton-redeploy.sh

Runs host-local smoke assertions for redeploy-singleton.sh without touching the
live systemd service. The smoke covers help text, queue-daemon dry-run planning,
and fail-closed behavior for an explicit missing env file.
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

repo_root() {
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null
  pwd
}

cleanup() {
  [[ -z "$SMOKE_TMPDIR" ]] || rm -rf -- "$SMOKE_TMPDIR"
}

assert_grep() {
  local pattern="$1"
  local file="$2"
  grep -F -- "$pattern" "$file" >/dev/null || die "expected output line not found: $pattern"
}

main() {
  case "${1:-}" in
    -h|--help)
      usage
      exit 0
      ;;
  esac
  [[ $# -eq 0 ]] || {
    usage >&2
    exit 2
  }

  local root
  root="$(repo_root)"
  local script="$root/deploy/singleton-redeploy/redeploy-singleton.sh"
  [[ -x "$script" ]] || die "redeploy script is not executable: $script"

  local tmpdir
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/ce-singleton-smoke.XXXXXX")"
  SMOKE_TMPDIR="$tmpdir"
  trap cleanup EXIT

  local env_file="$tmpdir/ce-queue-daemon.env"
  umask 077
  printf 'GH_TOKEN=placeholder\n' > "$env_file"
  chmod 0600 "$env_file"

  "$script" --help > "$tmpdir/help.out"
  assert_grep "Usage: redeploy-singleton.sh" "$tmpdir/help.out"
  assert_grep "--daemon NAME" "$tmpdir/help.out"

  "$script" --daemon queue-daemon --dry-run --repo-root "$root" --env-file "$env_file" > "$tmpdir/dry-run.out"
  assert_grep "Would install" "$tmpdir/dry-run.out"
  assert_grep "Would reload" "$tmpdir/dry-run.out"
  assert_grep "Would enable" "$tmpdir/dry-run.out"
  assert_grep "Would restart" "$tmpdir/dry-run.out"
  assert_grep "Would wait up to 30 seconds" "$tmpdir/dry-run.out"
  assert_grep "Would run health probe" "$tmpdir/dry-run.out"

  if "$script" --daemon queue-daemon --dry-run --repo-root "$root" --env-file "$tmpdir/missing.env" > "$tmpdir/missing.out" 2>&1; then
    die "missing explicit env file unexpectedly passed"
  fi
  assert_grep "env file is missing" "$tmpdir/missing.out"

  "$script" --daemon option-a-materializer --dry-run --repo-root "$root" > "$tmpdir/option-a.out"
  assert_grep "not deployed yet" "$tmpdir/option-a.out"

  printf 'OK: singleton redeploy smoke passed\n'
}

main "$@"
