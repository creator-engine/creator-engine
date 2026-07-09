#!/usr/bin/env bash
# tools/preflight-caps.sh - Governed CE preflight wrapper
# Enforces: disk-backed TMPDIR, -n parallelism cap, post-run tmpdir cleanup.
# Usage: tools/preflight-caps.sh [command args...] | tools/preflight-caps.sh pytest [pytest args...]
set -euo pipefail

CE_PREFLIGHT_TMPDIR="${CE_PREFLIGHT_TMPDIR:-$HOME/tmp}"
CE_PREFLIGHT_MAX_WORKERS="${CE_PREFLIGHT_MAX_WORKERS:-4}"

mkdir -p "$CE_PREFLIGHT_TMPDIR"
export TMPDIR="$CE_PREFLIGHT_TMPDIR"

tmpdir_fstype=""
if command -v findmnt >/dev/null 2>&1; then
  tmpdir_fstype="$(findmnt -T "$TMPDIR" -no FSTYPE 2>/dev/null || true)"
fi
if [[ -z "$tmpdir_fstype" ]]; then
  tmpdir_target="$(df --output=target "$TMPDIR" 2>/dev/null | tail -n 1 || true)"
  if [[ -n "$tmpdir_target" ]] && mount | grep -q " on ${tmpdir_target} type tmpfs "; then
    tmpdir_fstype="tmpfs"
  fi
fi
if [[ "$tmpdir_fstype" == "tmpfs" ]]; then
  echo "[preflight-caps] WARNING: TMPDIR=$TMPDIR is on tmpfs; disk-backed path preferred." >&2
fi

args=("$@")
if [[ "${#args[@]}" -eq 0 ]]; then
  echo "[preflight-caps] command is required" >&2
  exit 2
fi

for i in "${!args[@]}"; do
  if [[ "${args[$i]}" == "-n" && "${args[$((i + 1))]:-}" == "auto" ]]; then
    args[$((i + 1))]="$CE_PREFLIGHT_MAX_WORKERS"
    echo "[preflight-caps] Capped -n auto to -n $CE_PREFLIGHT_MAX_WORKERS" >&2
    break
  fi
done

set +e
"${args[@]}"
rc=$?
set -e

find "$CE_PREFLIGHT_TMPDIR" -maxdepth 1 -name 'pytest-of-*' -exec rm -rf {} + 2>/dev/null || true

exit "$rc"
