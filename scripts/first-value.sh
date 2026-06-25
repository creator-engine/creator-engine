#!/usr/bin/env bash
set -euo pipefail

DEFAULT_REPO="chmod735-dor/mythos"
DEFAULT_INSTALLATION_ID="141552951"
DEFAULT_ENV_FILE="${HOME}/.ce-keys/mythos-ce-app.env"

DRY_RUN=0
ENV_FILE="${MYTHOS_CE_ENV_FILE:-$DEFAULT_ENV_FILE}"
ENV_FILE_EXPLICIT=0
CEV3_BIN="${CEV3_BIN:-cev3}"

WORKDIR="${MYTHOS_CE_WORKDIR:-.}"
STATE_ROOT="${MYTHOS_CE_STATE_ROOT:-.ce/state}"
REPO="${MYTHOS_CE_REPO:-$DEFAULT_REPO}"
INSTALLATION_ID="${MYTHOS_CE_INSTALLATION_ID:-$DEFAULT_INSTALLATION_ID}"
CLIENT_ID="${MYTHOS_CE_CLIENT_ID:-}"
PEM_PATH="${MYTHOS_CE_PEM_PATH:-}"
APP_CONFIG="${MYTHOS_CE_APP_CONFIG:-}"

SCOPE_ID="${MYTHOS_CE_SCOPE_ID:-first-value-mythos}"
GOAL="${MYTHOS_CE_GOAL:-Deliver the first governed post-scaffold value change for chmod735-dor/mythos.}"
DONE_WHEN_1="${MYTHOS_CE_DONE_WHEN_1:-A bounded post-scaffold change is authored on a branch.}"
DONE_WHEN_2="${MYTHOS_CE_DONE_WHEN_2:-A governed PR is opened, independently reviewed, and collected into runtime evidence.}"
DONE_WHEN_3="${MYTHOS_CE_DONE_WHEN_3:-The PR is merged through the governed merge leg and a completion report is rendered.}"
CHANGE_TYPE="${MYTHOS_CE_CHANGE_TYPE:-docs}"
BUDGET="${MYTHOS_CE_BUDGET:-5}"
BUDGET_UNIT="${MYTHOS_CE_BUDGET_UNIT:-\$}"
BUDGET_WINDOW="${MYTHOS_CE_BUDGET_WINDOW:-total}"
APPROVER_REF="${MYTHOS_CE_APPROVER_REF:-}"
AUTHOR_BRANCH="${MYTHOS_CE_AUTHOR_BRANCH:-ce-first-value-mythos}"
BASE_BRANCH="${MYTHOS_CE_BASE_BRANCH:-main}"
SOURCE_DIR="${MYTHOS_CE_SOURCE_DIR:-.}"
REVIEWER_ACTOR="${MYTHOS_CE_REVIEWER_ACTOR:-}"
VENUE_ROOT="${MYTHOS_CE_VENUE_ROOT:-${HOME}/.ce/venues/mythos}"
LEDGER_ROOT="${MYTHOS_CE_LEDGER_ROOT:-${HOME}/.ce/active-work}"
SEAT_ENV_FILE="${MYTHOS_CE_SEAT_ENV_FILE:-}"
TICKET="${MYTHOS_CE_TICKET:-}"
HARNESS="${MYTHOS_CE_HARNESS:-claude}"
MANIFEST_PATHS=()

usage() {
  cat <<'EOF'
Usage: scripts/first-value.sh [options]

Drive the governed first-value flow for chmod735-dor/mythos.

Modes:
  --dry-run                 Print the full governed command plan and exit 0.
                            Does not require credentials and runs no live commands.

Configuration:
  --env-file PATH           Read MYTHOS_CE_* values from an env file.
                            Default: ~/.ce-keys/mythos-ce-app.env when present.
  --workdir PATH            Target repo checkout. Default: $MYTHOS_CE_WORKDIR or .
  --repo OWNER/NAME         Target GitHub repo. Default: chmod735-dor/mythos.
  --installation-id ID      GitHub App installation id. Default: 141552951.
  --client-id ID            GitHub App client id. May come from env/env-file.
  --pem-path PATH           GitHub App private key path. Contents are never printed.
  --app-config PATH         Existing cev3 App config JSON. If omitted in live mode,
                            a temporary config is built from repo/client/install/PEM.
  --cev3-bin PATH           cev3 executable. Default: cev3.

Governed run inputs:
  --scope ID                Scope id. Default: first-value-mythos.
  --goal TEXT               Scope goal.
  --done-when TEXT          Repeatable Done-when criterion. Replaces defaults on first use.
  --change-type CLASS       Scope mutation class. Default: docs.
  --budget AMOUNT           Human Budget cap. Default: 5.
  --budget-unit UNIT        $ or %. Default: $.
  --budget-window WINDOW    per_run, rolling_5h, rolling_weekly, or total. Default: total.
  --approver-ref HEX64      Value-free human ratifier digest. Required for live mode.
  --author-branch BRANCH    Authored branch to push/open. Default: ce-first-value-mythos.
  --base BRANCH             PR base branch. Default: main.
  --manifest-path PATH      Repeatable target-repo manifest path for cev3 pr.
                            Default: .ce/pr-manifests/<author-branch>.md.
  --reviewer-actor LOGIN    Distinct reviewer login. Required for live mode.
  --venue-root PATH         Reviewer venue root. Default: ~/.ce/venues/mythos.
  --ledger-root PATH        Active-work ledger root. Default: ~/.ce/active-work.
  --seat-env-file PATH      Optional reviewer venue credential env file path.
  --ticket OWNER/REPO#N     Optional work-claim ticket passed to drive/review.
  --harness NAME            Author harness. Default: claude.
  -h, --help                Show this help.

Env file keys:
  MYTHOS_CE_REPO, MYTHOS_CE_INSTALLATION_ID, MYTHOS_CE_CLIENT_ID,
  MYTHOS_CE_PEM_PATH, MYTHOS_CE_APP_CONFIG, plus any MYTHOS_CE_* option above.

Live mode fails closed before the first mutating command if required runtime
configuration is missing. Secret values and PEM contents are never printed.
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

strip_wrapping_quotes() {
  local value="$1"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

assign_from_env_file() {
  local target="$1"
  local env_key="$2"
  local value="$3"
  if [[ -z "${!env_key+x}" ]]; then
    printf -v "$target" '%s' "$value"
  fi
}

load_env_file() {
  local path="$1"
  if [[ ! -e "$path" ]]; then
    if [[ "$ENV_FILE_EXPLICIT" -eq 1 ]]; then
      fail "env file not found: $path"
    fi
    return 0
  fi
  [[ -f "$path" ]] || fail "env file is not a regular file: $path"
  [[ -r "$path" ]] || fail "env file is not readable: $path"

  local line key value
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    line="${line#export }"
    [[ "$line" == *=* ]] || continue
    key="${line%%=*}"
    value="${line#*=}"
    value="$(strip_wrapping_quotes "$value")"
    case "$key" in
      MYTHOS_CE_REPO) assign_from_env_file REPO MYTHOS_CE_REPO "$value" ;;
      MYTHOS_CE_INSTALLATION_ID) assign_from_env_file INSTALLATION_ID MYTHOS_CE_INSTALLATION_ID "$value" ;;
      MYTHOS_CE_CLIENT_ID) assign_from_env_file CLIENT_ID MYTHOS_CE_CLIENT_ID "$value" ;;
      MYTHOS_CE_PEM_PATH) assign_from_env_file PEM_PATH MYTHOS_CE_PEM_PATH "$value" ;;
      MYTHOS_CE_APP_CONFIG) assign_from_env_file APP_CONFIG MYTHOS_CE_APP_CONFIG "$value" ;;
      MYTHOS_CE_WORKDIR) assign_from_env_file WORKDIR MYTHOS_CE_WORKDIR "$value" ;;
      MYTHOS_CE_STATE_ROOT) assign_from_env_file STATE_ROOT MYTHOS_CE_STATE_ROOT "$value" ;;
      MYTHOS_CE_SCOPE_ID) assign_from_env_file SCOPE_ID MYTHOS_CE_SCOPE_ID "$value" ;;
      MYTHOS_CE_GOAL) assign_from_env_file GOAL MYTHOS_CE_GOAL "$value" ;;
      MYTHOS_CE_CHANGE_TYPE) assign_from_env_file CHANGE_TYPE MYTHOS_CE_CHANGE_TYPE "$value" ;;
      MYTHOS_CE_BUDGET) assign_from_env_file BUDGET MYTHOS_CE_BUDGET "$value" ;;
      MYTHOS_CE_BUDGET_UNIT) assign_from_env_file BUDGET_UNIT MYTHOS_CE_BUDGET_UNIT "$value" ;;
      MYTHOS_CE_BUDGET_WINDOW) assign_from_env_file BUDGET_WINDOW MYTHOS_CE_BUDGET_WINDOW "$value" ;;
      MYTHOS_CE_APPROVER_REF) assign_from_env_file APPROVER_REF MYTHOS_CE_APPROVER_REF "$value" ;;
      MYTHOS_CE_AUTHOR_BRANCH) assign_from_env_file AUTHOR_BRANCH MYTHOS_CE_AUTHOR_BRANCH "$value" ;;
      MYTHOS_CE_BASE_BRANCH) assign_from_env_file BASE_BRANCH MYTHOS_CE_BASE_BRANCH "$value" ;;
      MYTHOS_CE_SOURCE_DIR) assign_from_env_file SOURCE_DIR MYTHOS_CE_SOURCE_DIR "$value" ;;
      MYTHOS_CE_REVIEWER_ACTOR) assign_from_env_file REVIEWER_ACTOR MYTHOS_CE_REVIEWER_ACTOR "$value" ;;
      MYTHOS_CE_VENUE_ROOT) assign_from_env_file VENUE_ROOT MYTHOS_CE_VENUE_ROOT "$value" ;;
      MYTHOS_CE_LEDGER_ROOT) assign_from_env_file LEDGER_ROOT MYTHOS_CE_LEDGER_ROOT "$value" ;;
      MYTHOS_CE_SEAT_ENV_FILE) assign_from_env_file SEAT_ENV_FILE MYTHOS_CE_SEAT_ENV_FILE "$value" ;;
      MYTHOS_CE_TICKET) assign_from_env_file TICKET MYTHOS_CE_TICKET "$value" ;;
      MYTHOS_CE_HARNESS) assign_from_env_file HARNESS MYTHOS_CE_HARNESS "$value" ;;
      MYTHOS_CE_MANIFEST_PATHS)
        if [[ "${#MANIFEST_PATHS[@]}" -eq 0 ]]; then
          IFS=',' read -r -a MANIFEST_PATHS <<<"$value"
        fi
        ;;
    esac
  done < "$path"
}

quote_cmd() {
  local arg
  printf '  '
  for arg in "$@"; do
    printf '%q ' "$arg"
  done
  printf '\n'
}

print_cd_cmd() {
  local workdir="$1"
  shift
  printf '  cd %q && ' "$workdir"
  quote_cmd "$@" | sed 's/^  //'
}

append_optional() {
  local -n target="$1"
  local flag="$2"
  local value="$3"
  if [[ -n "$value" ]]; then
    target+=("$flag" "$value")
  fi
}

json_field() {
  local key="$1"
  python3 -c 'import json,sys; data=json.load(sys.stdin); value=data.get(sys.argv[1], ""); print(value if value is not None else "")' "$key"
}

run_json() {
  local __outvar="$1"
  shift
  local output
  print_cd_cmd "$WORKDIR" "$@"
  if ! output="$(cd "$WORKDIR" && "$@")"; then
    printf '%s\n' "$output" >&2
    fail "command failed"
  fi
  printf '%s\n' "$output"
  printf -v "$__outvar" '%s' "$output"
}

validate_repo() {
  [[ "$REPO" =~ ^[^[:space:]/]+/[^[:space:]/]+$ ]] || fail "repo must be owner/name, got: $REPO"
}

validate_hex64() {
  local label="$1"
  local value="$2"
  [[ "$value" =~ ^[0-9a-fA-F]{64}$ ]] || fail "$label must be a 64-hex value-free digest"
}

validate_app_config() {
  local path="$1"
  python3 - "$path" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1]).expanduser()
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except FileNotFoundError:
    print(f"App config not found: {path}", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError as exc:
    print(f"App config is not valid JSON: {exc}", file=sys.stderr)
    sys.exit(1)

for key in ("client_id", "installation_id", "pem_path"):
    if not str(data.get(key) or "").strip():
        print(f"App config missing {key!r}", file=sys.stderr)
        sys.exit(1)
try:
    if int(data["installation_id"]) <= 0:
        raise ValueError
except (TypeError, ValueError):
    print("App config 'installation_id' must be a positive integer", file=sys.stderr)
    sys.exit(1)
repo = str(data.get("repo") or "")
if repo and ("/" not in repo or any(ch.isspace() for ch in repo)):
    print("App config 'repo' must be owner/name", file=sys.stderr)
    sys.exit(1)
pem_path = pathlib.Path(str(data["pem_path"])).expanduser()
if not pem_path.is_file():
    print(f"PEM path from App config is not a file: {pem_path}", file=sys.stderr)
    sys.exit(1)
perms = data.get("permissions", {})
if not isinstance(perms, dict):
    print("App config 'permissions' must be an object when present", file=sys.stderr)
    sys.exit(1)
PY
}

make_temp_app_config() {
  [[ -n "$CLIENT_ID" ]] || fail "MYTHOS_CE_CLIENT_ID is required when MYTHOS_CE_APP_CONFIG is not set"
  [[ -n "$PEM_PATH" ]] || fail "MYTHOS_CE_PEM_PATH is required when MYTHOS_CE_APP_CONFIG is not set"
  [[ -f "$PEM_PATH" ]] || fail "MYTHOS_CE_PEM_PATH is not a file: $PEM_PATH"
  local tmp
  tmp="$(mktemp "${TMPDIR:-/tmp}/mythos-ce-app.XXXXXX.json")"
  chmod 600 "$tmp"
  python3 - "$tmp" "$CLIENT_ID" "$INSTALLATION_ID" "$PEM_PATH" "$REPO" <<'PY'
import json
import sys

path, client_id, installation_id, pem_path, repo = sys.argv[1:6]
data = {
    "client_id": client_id,
    "installation_id": int(installation_id),
    "pem_path": pem_path,
    "repo": repo,
    "permissions": {"contents": "write", "pull_requests": "write"},
}
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh)
    fh.write("\n")
PY
  APP_CONFIG="$tmp"
}

build_commands() {
  if [[ "${#MANIFEST_PATHS[@]}" -eq 0 ]]; then
    MANIFEST_PATHS=(".ce/pr-manifests/${AUTHOR_BRANCH}.md")
  fi

  SCOPE_CMD=("$CEV3_BIN" scope "$SCOPE_ID"
    --goal "$GOAL"
    --budget "$BUDGET"
    --budget-unit "$BUDGET_UNIT"
    --change-type "$CHANGE_TYPE"
    --note "first-value driver for ${REPO}"
    --root "$STATE_ROOT"
    --json)
  append_optional SCOPE_CMD --done-when "$DONE_WHEN_1"
  append_optional SCOPE_CMD --done-when "$DONE_WHEN_2"
  append_optional SCOPE_CMD --done-when "$DONE_WHEN_3"
  append_optional SCOPE_CMD --budget-window "$BUDGET_WINDOW"

  RATIFY_CMD=("$CEV3_BIN" ratify "$SCOPE_ID" --approver-ref "${APPROVER_REF:-<MYTHOS_CE_APPROVER_REF>}" --root "$STATE_ROOT" --json)
  DRIVE_CMD=("$CEV3_BIN" drive "$SCOPE_ID" --spawn --harness "$HARNESS" --root "$STATE_ROOT" --json)
  append_optional DRIVE_CMD --ticket "$TICKET"

  PR_CMD=("$CEV3_BIN" pr "$SCOPE_ID" --run "<author-run-id>" --branch "$AUTHOR_BRANCH" --base "$BASE_BRANCH" --app-config "${APP_CONFIG:-<app-config>}" --source-dir "$SOURCE_DIR" --apply --root "$STATE_ROOT" --json)
  local manifest
  for manifest in "${MANIFEST_PATHS[@]}"; do
    PR_CMD+=(--manifest-path "$manifest")
  done

  REVIEW_CMD=("$CEV3_BIN" review "$SCOPE_ID" --run "<author-run-id>" --reviewer-actor "${REVIEWER_ACTOR:-<reviewer-login>}" --spawn --venue-root "$VENUE_ROOT" --ledger-root "$LEDGER_ROOT" --root "$STATE_ROOT" --json)
  append_optional REVIEW_CMD --seat-env-file "$SEAT_ENV_FILE"
  append_optional REVIEW_CMD --ticket "$TICKET"

  COLLECT_REVIEW_CMD=("$CEV3_BIN" collect "$SCOPE_ID" --run "<review-run-id>" --outcome review_submitted --pr "<pr-number>" --root "$STATE_ROOT" --json)
  COLLECT_AUTHOR_CMD=("$CEV3_BIN" collect "$SCOPE_ID" --run "<author-run-id>" --root "$STATE_ROOT" --json)
  MERGE_CMD=("$CEV3_BIN" merge "$SCOPE_ID" --run "<author-run-id>" --apply --root "$STATE_ROOT" --json)
  REPORT_CMD=("$CEV3_BIN" report "$SCOPE_ID" --run-id "<author-run-id>" --cap "$BUDGET" --root "$STATE_ROOT" --json)
}

print_plan() {
  build_commands
  cat <<EOF
First-value governed command plan

Target repo: ${REPO}
Installation id: ${INSTALLATION_ID}
Target checkout: ${WORKDIR}
State root: ${STATE_ROOT}
App config: ${APP_CONFIG:-generated at runtime from MYTHOS_CE_CLIENT_ID/MYTHOS_CE_PEM_PATH}
PEM: ${PEM_PATH:+<configured path; contents are never printed>}

1. Scope
EOF
  print_cd_cmd "$WORKDIR" "${SCOPE_CMD[@]}"
  cat <<EOF
   Evidence: ${STATE_ROOT}/scopes/${SCOPE_ID}.scope.yaml

2. Ratify
EOF
  print_cd_cmd "$WORKDIR" "${RATIFY_CMD[@]}"
  cat <<EOF
   Evidence: ratification fields in ${STATE_ROOT}/scopes/${SCOPE_ID}.scope.yaml

3. Drive
EOF
  print_cd_cmd "$WORKDIR" "${DRIVE_CMD[@]}"
  cat <<EOF
   Evidence: ${STATE_ROOT}/dispatches/<author-run-id>/dispatch.yaml and runtime policy envelope

4. PR
EOF
  print_cd_cmd "$WORKDIR" "${PR_CMD[@]}"
  cat <<EOF
   Evidence: target PR, pushed branch ${AUTHOR_BRANCH}, dispatch change block, manifest path(s): ${MANIFEST_PATHS[*]}

5. Review
EOF
  print_cd_cmd "$WORKDIR" "${REVIEW_CMD[@]}"
  cat <<EOF
   Evidence: ${STATE_ROOT}/dispatches/<review-run-id>/dispatch.yaml and reviewer authority envelope

6. Collect
EOF
  print_cd_cmd "$WORKDIR" "${COLLECT_REVIEW_CMD[@]}"
  print_cd_cmd "$WORKDIR" "${COLLECT_AUTHOR_CMD[@]}"
  cat <<EOF
   Evidence: ${STATE_ROOT}/runs/<review-run-id>.runtime-evidence.yaml and ${STATE_ROOT}/runs/<author-run-id>.runtime-evidence.yaml

7. Merge
EOF
  print_cd_cmd "$WORKDIR" "${MERGE_CMD[@]}"
  cat <<EOF
   Evidence: pr_merged entry and merge audit in ${STATE_ROOT}/runs/<author-run-id>.runtime-evidence.yaml

8. Completion report
EOF
  print_cd_cmd "$WORKDIR" "${REPORT_CMD[@]}"
  cat <<EOF
   Evidence: JSON completion report plus artifact list from cev3 report
EOF
}

parse_args() {
  local reset_done_when=0
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --dry-run) DRY_RUN=1; shift ;;
      --env-file) ENV_FILE="${2:?missing --env-file value}"; ENV_FILE_EXPLICIT=1; shift 2 ;;
      --workdir) WORKDIR="${2:?missing --workdir value}"; shift 2 ;;
      --repo) REPO="${2:?missing --repo value}"; shift 2 ;;
      --installation-id) INSTALLATION_ID="${2:?missing --installation-id value}"; shift 2 ;;
      --client-id) CLIENT_ID="${2:?missing --client-id value}"; shift 2 ;;
      --pem-path) PEM_PATH="${2:?missing --pem-path value}"; shift 2 ;;
      --app-config) APP_CONFIG="${2:?missing --app-config value}"; shift 2 ;;
      --cev3-bin) CEV3_BIN="${2:?missing --cev3-bin value}"; shift 2 ;;
      --scope) SCOPE_ID="${2:?missing --scope value}"; shift 2 ;;
      --goal) GOAL="${2:?missing --goal value}"; shift 2 ;;
      --done-when)
        if [[ "$reset_done_when" -eq 0 ]]; then
          DONE_WHEN_1="${2:?missing --done-when value}"
          DONE_WHEN_2=""
          DONE_WHEN_3=""
          reset_done_when=1
        elif [[ -z "$DONE_WHEN_2" ]]; then
          DONE_WHEN_2="${2:?missing --done-when value}"
        elif [[ -z "$DONE_WHEN_3" ]]; then
          DONE_WHEN_3="${2:?missing --done-when value}"
        else
          fail "this script accepts up to three --done-when values"
        fi
        shift 2
        ;;
      --change-type) CHANGE_TYPE="${2:?missing --change-type value}"; shift 2 ;;
      --budget) BUDGET="${2:?missing --budget value}"; shift 2 ;;
      --budget-unit) BUDGET_UNIT="${2:?missing --budget-unit value}"; shift 2 ;;
      --budget-window) BUDGET_WINDOW="${2:?missing --budget-window value}"; shift 2 ;;
      --approver-ref) APPROVER_REF="${2:?missing --approver-ref value}"; shift 2 ;;
      --author-branch) AUTHOR_BRANCH="${2:?missing --author-branch value}"; shift 2 ;;
      --base) BASE_BRANCH="${2:?missing --base value}"; shift 2 ;;
      --manifest-path) MANIFEST_PATHS+=("${2:?missing --manifest-path value}"); shift 2 ;;
      --reviewer-actor) REVIEWER_ACTOR="${2:?missing --reviewer-actor value}"; shift 2 ;;
      --venue-root) VENUE_ROOT="${2:?missing --venue-root value}"; shift 2 ;;
      --ledger-root) LEDGER_ROOT="${2:?missing --ledger-root value}"; shift 2 ;;
      --seat-env-file) SEAT_ENV_FILE="${2:?missing --seat-env-file value}"; shift 2 ;;
      --ticket) TICKET="${2:?missing --ticket value}"; shift 2 ;;
      --harness) HARNESS="${2:?missing --harness value}"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) fail "unknown argument: $1" ;;
    esac
  done
}

preflight_live() {
  command -v "$CEV3_BIN" >/dev/null 2>&1 || fail "cev3 executable not found: $CEV3_BIN"
  command -v python3 >/dev/null 2>&1 || fail "python3 is required for JSON parsing"
  [[ -d "$WORKDIR" ]] || fail "target checkout does not exist: $WORKDIR"
  validate_repo
  [[ "$INSTALLATION_ID" =~ ^[0-9]+$ ]] || fail "installation id must be numeric"
  validate_hex64 "MYTHOS_CE_APPROVER_REF" "$APPROVER_REF"
  [[ -n "$REVIEWER_ACTOR" ]] || fail "MYTHOS_CE_REVIEWER_ACTOR is required for live review dispatch"
  [[ -n "$AUTHOR_BRANCH" ]] || fail "author branch is required"
  [[ -n "$STATE_ROOT" ]] || fail "state root is required"
  [[ -n "$VENUE_ROOT" ]] || fail "venue root is required"
  [[ -n "$LEDGER_ROOT" ]] || fail "ledger root is required"
  if [[ -n "$SEAT_ENV_FILE" && ! -f "$SEAT_ENV_FILE" ]]; then
    fail "seat env file is not a file: $SEAT_ENV_FILE"
  fi
  if [[ -n "$APP_CONFIG" ]]; then
    validate_app_config "$APP_CONFIG"
  else
    make_temp_app_config
  fi
}

execute_live() {
  build_commands
  printf 'Running governed first-value flow for %s from %s\n' "$REPO" "$WORKDIR"
  printf 'Secret values and PEM contents will not be printed.\n\n'

  local scope_json drive_json pr_json review_json collect_json merge_json report_json
  local author_run_id review_run_id pr_number

  run_json scope_json "${SCOPE_CMD[@]}"
  run_json scope_json "${RATIFY_CMD[@]}"
  run_json drive_json "${DRIVE_CMD[@]}"
  author_run_id="$(printf '%s' "$drive_json" | json_field run_id)"
  [[ -n "$author_run_id" ]] || fail "drive did not return an author run_id"

  local pr_cmd_live=()
  local arg
  for arg in "${PR_CMD[@]}"; do
    [[ "$arg" == "<author-run-id>" ]] && pr_cmd_live+=("$author_run_id") || pr_cmd_live+=("$arg")
  done
  run_json pr_json "${pr_cmd_live[@]}"
  pr_number="$(printf '%s' "$pr_json" | json_field pr_number)"
  [[ -n "$pr_number" ]] || fail "pr --apply did not return a pr_number"

  local review_cmd_live=()
  for arg in "${REVIEW_CMD[@]}"; do
    [[ "$arg" == "<author-run-id>" ]] && review_cmd_live+=("$author_run_id") || review_cmd_live+=("$arg")
  done
  run_json review_json "${review_cmd_live[@]}"
  review_run_id="$(printf '%s' "$review_json" | json_field review_run_id)"
  [[ -n "$review_run_id" ]] || fail "review --spawn did not return a review_run_id"

  run_json collect_json "$CEV3_BIN" collect "$SCOPE_ID" --run "$review_run_id" --outcome review_submitted --pr "$pr_number" --root "$STATE_ROOT" --json
  run_json collect_json "$CEV3_BIN" collect "$SCOPE_ID" --run "$author_run_id" --root "$STATE_ROOT" --json
  run_json merge_json "$CEV3_BIN" merge "$SCOPE_ID" --run "$author_run_id" --apply --root "$STATE_ROOT" --json
  run_json report_json "$CEV3_BIN" report "$SCOPE_ID" --run-id "$author_run_id" --cap "$BUDGET" --root "$STATE_ROOT" --json

  printf '\nFirst-value flow complete.\n'
  printf 'Author run: %s\n' "$author_run_id"
  printf 'Review run: %s\n' "$review_run_id"
  printf 'PR: %s#%s\n' "$REPO" "$pr_number"
}

main() {
  local original_args=("$@")
  local arg
  while [[ "$#" -gt 0 ]]; do
    arg="$1"
    case "$arg" in
      --env-file)
        ENV_FILE="${2:?missing --env-file value}"
        ENV_FILE_EXPLICIT=1
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        shift
        ;;
    esac
  done
  load_env_file "$ENV_FILE"
  parse_args "${original_args[@]}"
  validate_repo

  if [[ "$DRY_RUN" -eq 1 ]]; then
    print_plan
    exit 0
  fi

  preflight_live
  execute_live
}

main "$@"
