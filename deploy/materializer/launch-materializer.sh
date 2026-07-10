#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: launch-materializer.sh [--health]

Starts the Creator Engine brain intent materializer in dry-run mode. This
launcher refuses arming and does not read private keys from disk. Future write
authority must be supplied through the governed short-TTL app issuance path.

Required environment:
  CE_GATE_REPO                         owner/name repo label for evidence context

Optional environment:
  CE_MATERIALIZER_REPO_ROOT            checkout root; default resolves relative to this script
  CE_MATERIALIZER_STATE_ROOT           default <repo>/.ce/state/brain-intent-materializer
  CE_MATERIALIZER_QUARANTINE_ROOT      default <repo>/.ce/state/brain-intent-quarantine
  CE_MATERIALIZER_INTERVAL_SECONDS     default 120
  CE_MATERIALIZER_ITERATIONS           optional bounded loop count
  CE_MATERIALIZER_MAIN_REF             default origin/main
  CE_MATERIALIZER_TAIL_REF             default main
  CE_MATERIALIZER_PYTHON               python executable; default repo venv, then python3/python
  CE_MATERIALIZER_DRY_RUN              must be 1; default 1
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    die "missing required environment variable: $name. Set it in /etc/creator-engine/ce-materializer.env."
  fi
}

repo_root() {
  if [[ -n "${CE_MATERIALIZER_REPO_ROOT:-}" ]]; then
    cd -- "$CE_MATERIALIZER_REPO_ROOT" >/dev/null
    pwd
  else
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null
    pwd
  fi
}

resolve_python() {
  local root="$1"
  if [[ -n "${CE_MATERIALIZER_PYTHON:-}" ]]; then
    [[ -x "$CE_MATERIALIZER_PYTHON" ]] || die "CE_MATERIALIZER_PYTHON is not executable: $CE_MATERIALIZER_PYTHON"
    printf '%s\n' "$CE_MATERIALIZER_PYTHON"
    return
  fi
  if [[ -x "$root/.venv/bin/python" ]]; then
    printf '%s\n' "$root/.venv/bin/python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi
  die "cannot find python for materializer dry-run loop"
}

validate_required_env() {
  require_env CE_GATE_REPO
}

validate_disarmed() {
  [[ "${CE_MATERIALIZER_DRY_RUN:-1}" == "1" ]] || die "CE_MATERIALIZER_DRY_RUN must remain 1"
  [[ "${CE_MATERIALIZER_ARMING_ENABLED:-0}" != "1" ]] || die "materializer arming is not enabled by this launcher"
  [[ -z "${CE_MATERIALIZER_PRIVATE_KEY_FILE:-}" ]] || die "private-key files are not supported for the dry-run materializer"
}

daemon_alive() {
  if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet ce-materializer.service 2>/dev/null; then
    return 0
  fi
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -af 'launch-materializer[.]sh|brain-intent-materializer|brain_intent_materializer' \
      | grep -v -- '--health' >/dev/null
  else
    die "--health requires systemctl or pgrep to verify daemon liveness"
  fi
}

python_import_check() {
  local root="$1"
  local python="$2"
  PYTHONPATH="$root/validators${PYTHONPATH:+:$PYTHONPATH}" "$python" - <<'PY'
from creator_engine_validator.brain_intent_materializer import ARMING_ENABLED, MaterializerRunLoop
if ARMING_ENABLED:
    raise SystemExit("materializer arming unexpectedly enabled")
assert MaterializerRunLoop.__name__ == "MaterializerRunLoop"
PY
}

health() {
  local root="$1"
  local python="$2"
  validate_required_env
  validate_disarmed
  [[ -d "$root/.git" || -f "$root/.git" ]] || die "repo root does not look like a git checkout: $root"
  python_import_check "$root" "$python" || die "materializer import check failed"
  daemon_alive || die "ce-materializer is not active. Check: systemctl status ce-materializer.service"
  printf 'OK: ce-materializer alive; dry-run materializer imports with arming disabled\n'
}

run_once() {
  local root="$1"
  local python="$2"
  local state_root="$3"
  local quarantine_root="$4"
  local main_ref="$5"
  local tail_ref="$6"

  PYTHONPATH="$root/validators${PYTHONPATH:+:$PYTHONPATH}" "$python" - "$root" "$state_root" "$quarantine_root" "$main_ref" "$tail_ref" <<'PY'
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from creator_engine_validator.brain_intent_materializer import (
    ARMING_ENABLED,
    HistoryScanner,
    Materializer,
    MaterializerConfig,
)

if ARMING_ENABLED:
    raise SystemExit("ERROR: materializer arming unexpectedly enabled")

root = Path(sys.argv[1])
state_root = Path(sys.argv[2])
quarantine_root = Path(sys.argv[3])
main_ref = sys.argv[4]
tail_ref = sys.argv[5]

config = MaterializerConfig(
    state_root=state_root,
    quarantine_root=quarantine_root,
    repo_root=root,
    private_key_env="CE_MATERIALIZER_APP_PRIVATE_KEY",
)
scanner = HistoryScanner(root, main_ref=main_ref)
for merge_commit_sha, intent_path in scanner.scan():
    output = Materializer.run_dry(
        merge_commit_sha=merge_commit_sha,
        intent_path=intent_path,
        branch_slug=Path(intent_path).stem,
        pr_number=0,
        config=config,
        git_ref=tail_ref,
    )
    print(json.dumps(asdict(output), sort_keys=True, separators=(",", ":")))
PY
}

main_loop() {
  local root="$1"
  local python="$2"
  local state_root="${CE_MATERIALIZER_STATE_ROOT:-$root/.ce/state/brain-intent-materializer}"
  local quarantine_root="${CE_MATERIALIZER_QUARANTINE_ROOT:-$root/.ce/state/brain-intent-quarantine}"
  local interval="${CE_MATERIALIZER_INTERVAL_SECONDS:-120}"
  local main_ref="${CE_MATERIALIZER_MAIN_REF:-origin/main}"
  local tail_ref="${CE_MATERIALIZER_TAIL_REF:-main}"
  local iterations="${CE_MATERIALIZER_ITERATIONS:-}"

  [[ "$interval" =~ ^[0-9]+$ ]] || die "CE_MATERIALIZER_INTERVAL_SECONDS must be a positive integer"
  (( interval > 0 )) || die "CE_MATERIALIZER_INTERVAL_SECONDS must be a positive integer"
  if [[ -n "$iterations" ]]; then
    [[ "$iterations" =~ ^[0-9]+$ ]] || die "CE_MATERIALIZER_ITERATIONS must be a positive integer"
    (( iterations > 0 )) || die "CE_MATERIALIZER_ITERATIONS must be a positive integer"
  fi

  cd -- "$root"
  export PYTHONPATH="$root/validators${PYTHONPATH:+:$PYTHONPATH}"
  umask 077
  install -d -m 0700 "$state_root" "$quarantine_root"

  local count=0
  while true; do
    count=$((count + 1))
    run_once "$root" "$python" "$state_root" "$quarantine_root" "$main_ref" "$tail_ref"
    if [[ -n "$iterations" && "$count" -ge "$iterations" ]]; then
      return
    fi
    sleep "$interval"
  done
}

main() {
  local mode="start"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --health)
        mode="health"
        shift
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

  local root
  root="$(repo_root)"
  local python
  python="$(resolve_python "$root")"

  if [[ "$mode" == "health" ]]; then
    health "$root" "$python"
    return
  fi

  validate_required_env
  validate_disarmed
  main_loop "$root" "$python"
}

main "$@"
