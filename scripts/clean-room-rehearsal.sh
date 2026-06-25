#!/usr/bin/env bash
# N6 clean-room rehearsal harness scaffold.
#
# Non-secret defaults:
#   CE_REHEARSAL_MYTHOS_REPO defaults to chmod735-dor/mythos.
#   CE_REHEARSAL_INSTALLATION_ID defaults to 141552951.
# Authentication tokens, Claude credentials, and GitHub credentials must be
# supplied by the caller's runtime environment. This script never embeds them.
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
DRY_RUN=0
LIVE=0
LIST_STAGES=0
SELECTED_STAGE=""
CONTAINER_ID=""
CONTAINER_OWNED=0
TEMP_DIR=""

CE_REHEARSAL_IMAGE="${CE_REHEARSAL_IMAGE:-ubuntu:24.04}"
CE_REHEARSAL_CONTAINER_NAME="${CE_REHEARSAL_CONTAINER_NAME:-ce-n6-clean-room-rehearsal-$$}"
CE_REHEARSAL_SITE="${CE_REHEARSAL_SITE:-https://creator-engine.dev}"
CE_REHEARSAL_INSTALL_URL="${CE_REHEARSAL_INSTALL_URL:-${CE_REHEARSAL_SITE%/}/install.sh}"
CE_REHEARSAL_MYTHOS_REPO="${CE_REHEARSAL_MYTHOS_REPO:-${CE_MYTHOS_REPO:-chmod735-dor/mythos}}"
CE_REHEARSAL_INSTALLATION_ID="${CE_REHEARSAL_INSTALLATION_ID:-${CE_MYTHOS_INSTALLATION_ID:-141552951}}"
CE_REHEARSAL_CONTAINER_ID="${CE_REHEARSAL_CONTAINER_ID:-}"
CE_REHEARSAL_KEEP_CONTAINER="${CE_REHEARSAL_KEEP_CONTAINER:-0}"
CE_REHEARSAL_CLAUDE_INSTALL_CMD="${CE_REHEARSAL_CLAUDE_INSTALL_CMD:-}"

STAGES=(
  provision
  claude
  install
  inventory
  onboard
  first_value
  update
  teardown
)

usage() {
  cat <<EOF
Usage:
  ${SCRIPT_NAME} --dry-run [--stage NAME]
  ${SCRIPT_NAME} --live [--stage NAME]
  ${SCRIPT_NAME} --list-stages
  ${SCRIPT_NAME} --help

Options:
  --dry-run              Print the full staged plan and exit 0. Does not require
                         Docker, network, or secrets.
  --live                 Affirmatively enable live Docker/network execution.
                         Required for any full run or per-stage run that is not
                         --dry-run.
  --stage NAME           Run one stage. Use --list-stages for valid names.
                         Most live stages require a provisioned rehearsal
                         container from this script's orchestration path.
  --list-stages          Print stage names and exit 0.
  --help, -h             Show this help.

Environment:
  CE_REHEARSAL_IMAGE             Docker image. Default: ubuntu:24.04
  CE_REHEARSAL_CONTAINER_NAME    Docker container name.
  CE_REHEARSAL_SITE              Staged docs site. Default: https://creator-engine.dev
  CE_REHEARSAL_INSTALL_URL       Installer URL. Default: \$CE_REHEARSAL_SITE/install.sh
  CE_REHEARSAL_MYTHOS_REPO       Runtime mythos repo. Default: chmod735-dor/mythos
  CE_MYTHOS_REPO                 Alias used when CE_REHEARSAL_MYTHOS_REPO is unset.
  CE_REHEARSAL_INSTALLATION_ID   Runtime installation id. Default: 141552951
  CE_MYTHOS_INSTALLATION_ID      Alias used when CE_REHEARSAL_INSTALLATION_ID is unset.
  CE_REHEARSAL_CONTAINER_ID      Existing container id/name for per-stage runs.
                                  Cleanup will not remove attached containers
                                  unless the teardown stage is run explicitly.
  CE_REHEARSAL_CLAUDE_INSTALL_CMD
                                  Optional shell command to install Claude Code.
                                  When unset, the Claude stage records an auth
                                  placeholder and continues.
  CE_REHEARSAL_KEEP_CONTAINER    Set to 1 to keep the live container for debug.

No token, credential, or auth secret is accepted as a default here. Configure
Docker, GitHub, and Claude auth outside this repository.
EOF
}

log() {
  printf 'CE_REHEARSAL status=%s stage=%s msg=%s\n' "$1" "${2:-global}" "${3:-}" >&2
}

fail() {
  local stage="$1"
  local message="$2"
  log "FAIL" "$stage" "$message"
  exit 1
}

cleanup() {
  local status=$?
  if [ -n "${TEMP_DIR:-}" ] && [ -d "${TEMP_DIR}" ]; then
    rm -rf "${TEMP_DIR}"
  fi
  if [ -n "${CONTAINER_ID:-}" ] && [ "${CONTAINER_OWNED}" = "1" ] && [ "${CE_REHEARSAL_KEEP_CONTAINER}" != "1" ]; then
    docker rm -f "${CONTAINER_ID}" >/dev/null 2>&1 || true
    log "PASS" "teardown" "container_removed=${CONTAINER_ID}"
  elif [ -n "${CONTAINER_ID:-}" ]; then
    log "PASS" "teardown" "container_kept=${CONTAINER_ID} owned=${CONTAINER_OWNED}"
  fi
  exit "${status}"
}
trap cleanup EXIT INT TERM

stage_exists() {
  local wanted="$1"
  local stage
  for stage in "${STAGES[@]}"; do
    if [ "${stage}" = "${wanted}" ]; then
      return 0
    fi
  done
  return 1
}

print_stages() {
  local stage
  for stage in "${STAGES[@]}"; do
    printf '%s\n' "${stage}"
  done
}

print_plan() {
  cat <<EOF
CE_REHEARSAL_PLAN dry_run=1 image=${CE_REHEARSAL_IMAGE}
CE_REHEARSAL_PLAN env=CE_REHEARSAL_MYTHOS_REPO value=${CE_REHEARSAL_MYTHOS_REPO}
CE_REHEARSAL_PLAN env=CE_REHEARSAL_INSTALLATION_ID value=${CE_REHEARSAL_INSTALLATION_ID}
CE_REHEARSAL_PLAN env=CE_REHEARSAL_INSTALL_URL value=${CE_REHEARSAL_INSTALL_URL}
CE_REHEARSAL_PLAN secrets=external no_secret_defaults=1
CE_REHEARSAL_PLAN stage=provision action="docker run -d --name ${CE_REHEARSAL_CONTAINER_NAME} ${CE_REHEARSAL_IMAGE} sleep infinity"
CE_REHEARSAL_PLAN stage=claude action="install Claude Code via CE_REHEARSAL_CLAUDE_INSTALL_CMD or record documented auth placeholder"
CE_REHEARSAL_PLAN stage=install action="curl --proto '=https' --tlsv1.2 -fsSL ${CE_REHEARSAL_INSTALL_URL} | bash"
CE_REHEARSAL_PLAN stage=inventory action="cev3 onboard --inventory" expect="N1 git/curl WARN rows"
CE_REHEARSAL_PLAN stage=onboard action="cev3 onboard --plan && cev3 onboard --apply"
CE_REHEARSAL_PLAN stage=first_value action="scripts/first-value.sh --dry-run author->commit->push->PR->merge for ${CE_REHEARSAL_MYTHOS_REPO}"
CE_REHEARSAL_PLAN stage=update action="cev3 update" guarded=TODO fail_closed=1
CE_REHEARSAL_PLAN stage=teardown action="docker rm -f ${CE_REHEARSAL_CONTAINER_NAME}"
EOF
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      --live)
        LIVE=1
        shift
        ;;
      --stage)
        [ "$#" -ge 2 ] || fail "global" "--stage requires a name"
        SELECTED_STAGE="$2"
        shift 2
        ;;
      --list-stages)
        LIST_STAGES=1
        shift
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        fail "global" "unknown argument: $1"
        ;;
    esac
  done
}

require_live_or_dry_run() {
  if [ "${LIVE}" = "1" ]; then
    return 0
  fi
  fail "global" "live rehearsal is fail-closed by default; rerun with --dry-run to print the safe plan or --live to affirm Docker/network execution"
}

need_container() {
  if [ -z "${CONTAINER_ID:-}" ]; then
    if [ -n "${CE_REHEARSAL_CONTAINER_ID}" ]; then
      CONTAINER_ID="${CE_REHEARSAL_CONTAINER_ID}"
      CONTAINER_OWNED=0
      log "RUN" "$1" "attached_container=${CONTAINER_ID}"
      return 0
    fi
    fail "$1" "stage requires a live container from the orchestration path or CE_REHEARSAL_CONTAINER_ID"
  fi
}

docker_exec() {
  local stage="$1"
  shift
  need_container "${stage}"
  log "RUN" "${stage}" "$*"
  docker exec \
    --env "CE_REHEARSAL_MYTHOS_REPO=${CE_REHEARSAL_MYTHOS_REPO}" \
    --env "CE_REHEARSAL_INSTALLATION_ID=${CE_REHEARSAL_INSTALLATION_ID}" \
    --env "CE_REHEARSAL_INSTALL_URL=${CE_REHEARSAL_INSTALL_URL}" \
    "${CONTAINER_ID}" "$@"
}

run_provision() {
  local stage="provision"
  command -v docker >/dev/null 2>&1 || fail "${stage}" "docker command is required for live rehearsal"
  log "RUN" "${stage}" "pull_image=${CE_REHEARSAL_IMAGE}"
  docker pull "${CE_REHEARSAL_IMAGE}" >/dev/null
  log "RUN" "${stage}" "create_container=${CE_REHEARSAL_CONTAINER_NAME}"
  CONTAINER_ID="$(docker run -d --name "${CE_REHEARSAL_CONTAINER_NAME}" "${CE_REHEARSAL_IMAGE}" sleep infinity)"
  CONTAINER_OWNED=1
  TEMP_DIR="$(mktemp -d)"
  log "PASS" "${stage}" "container_id=${CONTAINER_ID}"
}

run_claude() {
  local stage="claude"
  need_container "${stage}"
  if [ -n "${CE_REHEARSAL_CLAUDE_INSTALL_CMD}" ]; then
    docker_exec "${stage}" bash -lc "${CE_REHEARSAL_CLAUDE_INSTALL_CMD}"
    log "PASS" "${stage}" "claude_install_cmd_completed=1"
    return 0
  fi
  docker_exec "${stage}" bash -lc "mkdir -p /opt/ce-rehearsal && printf '%s\n' 'Claude Code install/auth placeholder: supply CE_REHEARSAL_CLAUDE_INSTALL_CMD and external auth at runtime.' >/opt/ce-rehearsal/claude-auth-placeholder.txt"
  log "PASS" "${stage}" "placeholder=/opt/ce-rehearsal/claude-auth-placeholder.txt"
}

run_install() {
  local stage="install"
  docker_exec "${stage}" bash -lc "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl bash openssh-client"
  docker_exec "${stage}" bash -lc "curl --proto '=https' --tlsv1.2 -fsSL \"\${CE_REHEARSAL_INSTALL_URL}\" | bash"
  log "PASS" "${stage}" "installer_completed=1"
}

run_inventory() {
  local stage="inventory"
  docker_exec "${stage}" bash -lc "cev3 onboard --inventory | tee /tmp/ce-rehearsal-inventory.log"
  docker_exec "${stage}" bash -lc "grep -Ei 'WARN.*git|git.*WARN' /tmp/ce-rehearsal-inventory.log >/dev/null"
  docker_exec "${stage}" bash -lc "grep -Ei 'WARN.*curl|curl.*WARN' /tmp/ce-rehearsal-inventory.log >/dev/null"
  log "PASS" "${stage}" "n1_git_warn_observed=1 n1_curl_warn_observed=1"
}

run_onboard() {
  local stage="onboard"
  docker_exec "${stage}" bash -lc "cev3 onboard --plan"
  docker_exec "${stage}" bash -lc "cev3 onboard --apply"
  log "PASS" "${stage}" "plan_apply_completed=1"
}

run_first_value() {
  local stage="first_value"
  local script_dir first_value_sh
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  first_value_sh="${script_dir}/first-value.sh"
  [ -x "${first_value_sh}" ] || fail "${stage}" "first-value.sh not found or not executable: ${first_value_sh}"

  if [ "${DRY_RUN}" = "1" ]; then
    # Print the governed first-value command plan; no creds or live commands.
    log "RUN" "${stage}" "first-value.sh --dry-run repo=${CE_REHEARSAL_MYTHOS_REPO}"
    MYTHOS_CE_REPO="${CE_REHEARSAL_MYTHOS_REPO}" \
    MYTHOS_CE_INSTALLATION_ID="${CE_REHEARSAL_INSTALLATION_ID}" \
      "${first_value_sh}" --dry-run \
        --repo "${CE_REHEARSAL_MYTHOS_REPO}" \
        --installation-id "${CE_REHEARSAL_INSTALLATION_ID}"
    log "PASS" "${stage}" "first_value_plan_printed=1 dry_run=1"
    return 0
  fi

  # Live path: drive the real governed author->commit->push->PR->merge flow.
  #
  # PREREQUISITE for live runs: first-value.sh runs host-side (it needs the
  # cev3 binary, the target mythos checkout, the GitHub App PEM, and reviewer
  # venue credentials). The provisioned rehearsal container does NOT carry the
  # mythos repo or App creds, so this stage is intentionally NOT executed via
  # docker_exec. The caller must supply the live runtime configuration through
  # first-value.sh's own MYTHOS_CE_* env (default env file
  # ~/.ce-keys/mythos-ce-app.env: client id, PEM path, approver-ref,
  # reviewer-actor, etc.). first-value.sh fails closed before the first
  # mutating command if that configuration is missing.
  need_container "${stage}"
  log "RUN" "${stage}" "first-value.sh live repo=${CE_REHEARSAL_MYTHOS_REPO}"
  MYTHOS_CE_REPO="${CE_REHEARSAL_MYTHOS_REPO}" \
  MYTHOS_CE_INSTALLATION_ID="${CE_REHEARSAL_INSTALLATION_ID}" \
    "${first_value_sh}" \
      --repo "${CE_REHEARSAL_MYTHOS_REPO}" \
      --installation-id "${CE_REHEARSAL_INSTALLATION_ID}"
  log "PASS" "${stage}" "first_value_flow_completed=1"
}

run_update() {
  local stage="update"
  need_container "${stage}"
  fail "${stage}" "TODO guarded: cev3 update cycle is intentionally fail-closed until update contract is finalized"
}

run_teardown() {
  local stage="teardown"
  if [ -z "${CONTAINER_ID:-}" ]; then
    log "PASS" "${stage}" "no_container_to_remove=1"
    return 0
  fi
  docker rm -f "${CONTAINER_ID}" >/dev/null
  log "PASS" "${stage}" "container_removed=${CONTAINER_ID}"
  CONTAINER_ID=""
  CONTAINER_OWNED=0
}

run_stage() {
  case "$1" in
    provision) run_provision ;;
    claude) run_claude ;;
    install) run_install ;;
    inventory) run_inventory ;;
    onboard) run_onboard ;;
    first_value) run_first_value ;;
    update) run_update ;;
    teardown) run_teardown ;;
    *) fail "global" "unknown stage: $1" ;;
  esac
}

main() {
  parse_args "$@"

  if [ "${LIST_STAGES}" = "1" ]; then
    print_stages
    exit 0
  fi

  if [ -n "${SELECTED_STAGE}" ] && ! stage_exists "${SELECTED_STAGE}"; then
    fail "global" "unknown stage: ${SELECTED_STAGE}"
  fi

  if [ "${DRY_RUN}" = "1" ]; then
    print_plan
    exit 0
  fi

  require_live_or_dry_run

  if [ -n "${SELECTED_STAGE}" ]; then
    run_stage "${SELECTED_STAGE}"
    exit 0
  fi

  local stage
  for stage in "${STAGES[@]}"; do
    run_stage "${stage}"
  done
}

main "$@"
