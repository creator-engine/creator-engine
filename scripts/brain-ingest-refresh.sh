#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/brain-ingest-refresh.sh [options]

Refresh the local CE brain recall store from MEMORY.md and docs/.

Options:
  --repo-root PATH             Repository root. Default: git top-level or cwd.
  --state-root PATH            CE state root passed to ce brain ingest. Default: .ce/state.
  --db PATH                    Recall SQLite DB. Default: <state-root>/brain/recall.sqlite.
  --ce-bin PATH                ce executable. Default: $CE_BRAIN_INGEST_CE_BIN or ce.
  --embedder NAME              ce brain ingest embedder. Default: deterministic.
  --model-path PATH            Local model path for --embedder embeddinggemma.
  --endpoint URL               Embedding endpoint for --embedder vllm-openai.
  --endpoint-model-id ID       Endpoint model id for --embedder vllm-openai.
  --endpoint-dim N             Endpoint embedding dimension for --embedder vllm-openai.
  --scope VALUE                Scope passed to ce brain ingest.
  --scope-json JSON            Scope JSON passed to ce brain ingest.
  --allow-confidential-egress  Permit egress-requiring embedders for confidential chunks.
  --force                      Reconcile the full MEMORY.md plus docs/ corpus.
  --dry-run                    Print the ingest command and exit without running it.
  -h, --help                   Show this help.

The script is timer-safe and advisory: a concurrent run or no source drift exits 0.
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

find_python() {
  if command -v python >/dev/null 2>&1; then
    printf 'python'
  elif command -v python3 >/dev/null 2>&1; then
    printf 'python3'
  else
    return 1
  fi
}

abs_path() {
  local base="$1"
  local path="$2"
  case "$path" in
    /*) printf '%s\n' "$path" ;;
    *) printf '%s/%s\n' "$base" "$path" ;;
  esac
}

quote_cmd() {
  local arg
  for arg in "$@"; do
    printf '%q ' "$arg"
  done
  printf '\n'
}

repo_root=""
state_root="${CE_BRAIN_INGEST_STATE_ROOT:-.ce/state}"
db_path="${CE_BRAIN_INGEST_DB:-}"
ce_bin="${CE_BRAIN_INGEST_CE_BIN:-ce}"
embedder="${CE_BRAIN_INGEST_EMBEDDER:-deterministic}"
model_path="${CE_BRAIN_INGEST_MODEL_PATH:-}"
endpoint="${CE_BRAIN_INGEST_ENDPOINT:-}"
endpoint_model_id="${CE_BRAIN_INGEST_ENDPOINT_MODEL_ID:-}"
endpoint_dim="${CE_BRAIN_INGEST_ENDPOINT_DIM:-}"
scope="${CE_BRAIN_INGEST_SCOPE:-}"
scope_json="${CE_BRAIN_INGEST_SCOPE_JSON:-}"
allow_confidential_egress=0
force=0
dry_run=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root) repo_root="${2:-}"; shift 2 ;;
    --state-root) state_root="${2:-}"; shift 2 ;;
    --db) db_path="${2:-}"; shift 2 ;;
    --ce-bin) ce_bin="${2:-}"; shift 2 ;;
    --embedder) embedder="${2:-}"; shift 2 ;;
    --model-path) model_path="${2:-}"; shift 2 ;;
    --endpoint) endpoint="${2:-}"; shift 2 ;;
    --endpoint-model-id) endpoint_model_id="${2:-}"; shift 2 ;;
    --endpoint-dim) endpoint_dim="${2:-}"; shift 2 ;;
    --scope) scope="${2:-}"; shift 2 ;;
    --scope-json) scope_json="${2:-}"; shift 2 ;;
    --allow-confidential-egress) allow_confidential_egress=1; shift ;;
    --force) force=1; shift ;;
    --dry-run) dry_run=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument: $1" ;;
  esac
done

if [[ -z "$repo_root" ]]; then
  if repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    :
  else
    repo_root="$(pwd)"
  fi
fi
repo_root="$(cd "$repo_root" && pwd)"

python_bin="$(find_python)" || fail "python or python3 is required"
if [[ -z "$db_path" ]]; then
  db_path="${state_root%/}/brain/recall.sqlite"
fi
db_abs="$(abs_path "$repo_root" "$db_path")"
state_root_abs="$(abs_path "$repo_root" "$state_root")"
lock_dir="${state_root_abs%/}/brain"
lock_file="${lock_dir}/ingest-refresh.lock"

mkdir -p "$lock_dir"
exec 9>"$lock_file"
if command -v flock >/dev/null 2>&1; then
  if ! flock -n 9; then
    printf 'brain ingest refresh: another refresh is running; skipping\n'
    exit 0
  fi
else
  printf 'brain ingest refresh: flock unavailable; continuing without advisory lock\n' >&2
fi

selection_output="$(
  "$python_bin" - "$repo_root" "$db_abs" "$force" <<'PY'
from __future__ import annotations

import datetime as dt
import sqlite3
import sys
from pathlib import Path

repo_root = Path(sys.argv[1]).resolve()
db_path = Path(sys.argv[2])
force = sys.argv[3] == "1"


def parse_as_of(value: str | None) -> float | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return parsed.replace(tzinfo=dt.timezone.utc).timestamp()


def current_markdown_sources() -> dict[str, Path]:
    sources: dict[str, Path] = {}
    memory = repo_root / "MEMORY.md"
    if memory.is_file():
        sources["MEMORY.md"] = memory
    docs = repo_root / "docs"
    if docs.is_dir():
        for path in sorted(docs.rglob("*.md")):
            if path.is_file():
                sources[path.relative_to(repo_root).as_posix()] = path
    return sources


def recall_state() -> tuple[str | None, set[str]]:
    if not db_path.is_file():
        return None, set()
    try:
        with sqlite3.connect(db_path) as conn:
            max_as_of = conn.execute("SELECT MAX(as_of) FROM recall_entries").fetchone()[0]
            rows = conn.execute("SELECT DISTINCT source_path FROM recall_entries").fetchall()
    except sqlite3.Error:
        return None, set()
    return max_as_of, {str(row[0]) for row in rows if row and row[0]}


current = current_markdown_sources()
max_as_of, stored = recall_state()
cutoff = parse_as_of(max_as_of)
tracked_stored = {
    path for path in stored
    if path == "MEMORY.md" or (path.startswith("docs/") and path.endswith(".md"))
}
deleted = sorted(tracked_stored.difference(current))

if not current:
    print("MODE=none")
    print(f"MAX_AS_OF={max_as_of or ''}")
    print(f"DELETED_COUNT={len(deleted)}")
    raise SystemExit(0)

if force or cutoff is None or deleted:
    print("MODE=full")
    print(f"MAX_AS_OF={max_as_of or ''}")
    print(f"DELETED_COUNT={len(deleted)}")
    if (repo_root / "MEMORY.md").is_file():
        print("SOURCE\tMEMORY.md")
    if (repo_root / "docs").is_dir():
        print("SOURCE\tdocs")
    raise SystemExit(0)

changed = [
    rel for rel, path in sorted(current.items())
    if path.stat().st_mtime > cutoff
]
print("MODE=incremental" if changed else "MODE=none")
print(f"MAX_AS_OF={max_as_of or ''}")
print(f"DELETED_COUNT={len(deleted)}")
for rel in changed:
    print(f"SOURCE\t{rel}")
PY
)"

mode="none"
max_as_of=""
deleted_count="0"
sources=()
while IFS= read -r line; do
  case "$line" in
    MODE=*) mode="${line#MODE=}" ;;
    MAX_AS_OF=*) max_as_of="${line#MAX_AS_OF=}" ;;
    DELETED_COUNT=*) deleted_count="${line#DELETED_COUNT=}" ;;
    $'SOURCE\t'*) sources+=("${line#SOURCE	}") ;;
  esac
done <<<"$selection_output"

if [[ "${#sources[@]}" -eq 0 ]]; then
  printf 'brain ingest refresh: no MEMORY.md/docs source drift detected'
  if [[ -n "$max_as_of" ]]; then
    printf ' since %s' "$max_as_of"
  fi
  printf '\n'
  exit 0
fi

as_of="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
export PYTHONPATH="${repo_root}/validators${PYTHONPATH:+:${PYTHONPATH}}"
if command -v "$ce_bin" >/dev/null 2>&1; then
  ce_cmd=("$ce_bin")
else
  ce_cmd=("$python_bin" -m creator_engine_validator.ce_cli)
fi

cmd=(
  "${ce_cmd[@]}"
  brain ingest
  --state-root "$state_root"
  --db "$db_path"
  --embedder "$embedder"
  --as-of "$as_of"
)
if [[ -n "$scope" ]]; then
  cmd+=(--scope "$scope")
fi
if [[ -n "$scope_json" ]]; then
  cmd+=(--scope-json "$scope_json")
fi
if [[ -n "$model_path" ]]; then
  cmd+=(--model-path "$model_path")
fi
if [[ -n "$endpoint" ]]; then
  cmd+=(--endpoint "$endpoint")
fi
if [[ -n "$endpoint_model_id" ]]; then
  cmd+=(--endpoint-model-id "$endpoint_model_id")
fi
if [[ -n "$endpoint_dim" ]]; then
  cmd+=(--endpoint-dim "$endpoint_dim")
fi
if [[ "$allow_confidential_egress" -eq 1 ]]; then
  cmd+=(--allow-confidential-egress)
fi
for source in "${sources[@]}"; do
  cmd+=(--source "$source")
done

printf 'brain ingest refresh: mode=%s sources=%s deleted-source-drift=%s as-of=%s\n' \
  "$mode" "${#sources[@]}" "$deleted_count" "$as_of"
if [[ "$dry_run" -eq 1 ]]; then
  printf 'dry-run: '
  quote_cmd "${cmd[@]}"
  exit 0
fi

cd "$repo_root"
exec "${cmd[@]}"
