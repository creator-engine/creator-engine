#!/usr/bin/env bash
# Fresh-Tenant Rehearsal harness, slice 1.
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
HARNESS_VERSION="ce-p3-rehearsal-s1"
DRY_RUN=0
LIVE=0
LIST_STAGES=0
RELEASE_SMOKE=0
SELECTED_STAGE=""
CONTAINER_ID=""
CONTAINER_OWNED=0
TEMP_DIR=""
EVIDENCE_EVENTS=""
FAILURES=""
CE_PACKAGE_VERSION=""

CE_REHEARSAL_IMAGE="${CE_REHEARSAL_IMAGE:-ubuntu:24.04}"
CE_REHEARSAL_SITE="${CE_REHEARSAL_SITE:-https://creator-engine.dev}"
CE_REHEARSAL_EVIDENCE_OUT="${CE_REHEARSAL_EVIDENCE_OUT:-/tmp/ce-rehearsal-evidence.json}"
CE_REHEARSAL_KEEP_CONTAINER="${CE_REHEARSAL_KEEP_CONTAINER:-0}"
CE_REHEARSAL_CONTAINER_NAME="${CE_REHEARSAL_CONTAINER_NAME:-ce-p3-rehearsal-$$}"
CE_REHEARSAL_ENGINE="${CE_REHEARSAL_ENGINE:-docker}"
CE_REHEARSAL_CHECKOUT_MOUNT="${CE_REHEARSAL_CHECKOUT_MOUNT:-false}"
CE_REHEARSAL_RELEASE_SMOKE_RESULT_OUT="${CE_REHEARSAL_RELEASE_SMOKE_RESULT_OUT:-/tmp/ce-release-smoke-result.json}"

STAGES=(
  provision
  install
  install_verify
  onboard
  scratch_repo
  ceo_launch
  ceo_frame
  ceo_scope
  ceo_build
  ceo_merge
  ceo_report
  teardown
)

usage() {
  cat <<EOF
Usage:
  ${SCRIPT_NAME} --dry-run [--stage NAME]
  ${SCRIPT_NAME} --live [--stage NAME]
  ${SCRIPT_NAME} --release-smoke
  ${SCRIPT_NAME} --list-stages
  ${SCRIPT_NAME} --help

Options:
  --dry-run       Print the staged plan and stub markers. Does not require
                  Docker, network, or credentials.
  --live          Affirmatively enable Docker/network execution.
  --release-smoke Run only the governed release install/install-verify smoke
                  and emit deterministic value-free result JSON.
  --stage NAME    Run one named stage. Use --list-stages for valid names.
  --list-stages   Print stage names and exit 0.
  --help, -h      Show this help.

Environment:
  CE_REHEARSAL_IMAGE             Docker image reference. Default tag: ubuntu:24.04
  CE_REHEARSAL_SITE              Installer base URL. Default: https://creator-engine.dev
  CE_REHEARSAL_EVIDENCE_OUT      Evidence JSON path. Default: /tmp/ce-rehearsal-evidence.json
  CE_REHEARSAL_KEEP_CONTAINER    Set to 1 to keep the live container for debug.
  CE_REHEARSAL_CONTAINER_NAME    Container name. Default: ce-p3-rehearsal-\$\$
  CE_REHEARSAL_ENGINE            Container engine command. Default: docker.
  CE_REHEARSAL_CHECKOUT_MOUNT    Must be exactly false for release smoke.
  CE_REHEARSAL_RELEASE_SMOKE_RESULT_OUT
                                  Explicit deterministic result path.

The harness mounts no host checkout into the container. Live execution is
fail-closed unless --live is supplied.
EOF
}

log() {
  printf 'CE_REHEARSAL status=%s stage=%s msg=%s\n' "$1" "${2:-global}" "${3:-}" >&2
}

fail() {
  local stage="$1"
  local message="$2"
  record_stage "${stage}" "fail" "" 1 "${message}"
  write_evidence || true
  log "FAIL" "${stage}" "${message}"
  exit 1
}

cleanup() {
  local status=$?
  if [ "${RELEASE_SMOKE}" != "1" ]; then
    write_evidence || true
  fi
  if [ -n "${CONTAINER_ID:-}" ] && [ "${CONTAINER_OWNED}" = "1" ] && [ "${CE_REHEARSAL_KEEP_CONTAINER}" != "1" ]; then
    docker rm -f "${CONTAINER_ID}" >/dev/null 2>&1 || true
  fi
  if [ -n "${TEMP_DIR:-}" ] && [ -d "${TEMP_DIR}" ]; then
    rm -rf "${TEMP_DIR}"
  fi
  exit "${status}"
}
trap cleanup EXIT INT TERM

stage_exists() {
  local wanted="$1"
  local stage
  for stage in "${STAGES[@]}"; do
    [ "${stage}" = "${wanted}" ] && return 0
  done
  return 1
}

print_stages() {
  local stage
  for stage in "${STAGES[@]}"; do
    printf '%s\n' "${stage}"
  done
}

now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

now_ms() {
  date -u +"%s%3N"
}

uuid_v4() {
  local hex
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen | tr '[:upper:]' '[:lower:]'
    return
  fi
  hex="$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"
  printf '%s-%s-4%s-8%s-%s\n' "${hex:0:8}" "${hex:8:4}" "${hex:13:3}" "${hex:17:3}" "${hex:20:12}"
}

json_escape() {
  local value="${1:-}"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  printf '%s' "${value}"
}

json_string_or_null() {
  if [ -z "${1:-}" ]; then
    printf 'null'
  else
    printf '"%s"' "$(json_escape "$1")"
  fi
}

json_int_or_null() {
  if [ -z "${1:-}" ]; then
    printf 'null'
  else
    printf '%s' "$1"
  fi
}

record_stage() {
  local stage="$1"
  local status="$2"
  local stub_reason="${3:-}"
  local exit_code="${4:-}"
  local notes="${5:-}"
  local started="${STAGE_STARTED_AT:-$(now_utc)}"
  local completed
  local duration
  completed="$(now_utc)"
  if [ -n "${STAGE_STARTED_MS:-}" ]; then
    duration=$(( "$(now_ms)" - STAGE_STARTED_MS ))
  else
    duration=0
  fi

  EVIDENCE_EVENTS="${EVIDENCE_EVENTS}${stage}"$'\t'"${status}"$'\t'"${started}"$'\t'"${completed}"$'\t'"${duration}"$'\t'"${stub_reason}"$'\t'"${exit_code}"$'\t'"${notes}"$'\n'
  if [ "${status}" = "fail" ]; then
    FAILURES="${FAILURES}${stage}"$'\t'"${notes}"$'\n'
  fi
}

stage_start() {
  STAGE_STARTED_AT="$(now_utc)"
  STAGE_STARTED_MS="$(now_ms)"
  log "RUN" "$1" "${2:-}"
}

write_evidence() {
  local rehearsal_id total passed failed stubbed skipped first
  local stage status started completed duration stub_reason exit_code notes
  local out_dir
  rehearsal_id="${REHEARSAL_ID:-$(uuid_v4)}"
  total=0
  passed=0
  failed=0
  stubbed=0
  skipped=0
  while IFS=$'\t' read -r stage status started completed duration stub_reason exit_code notes; do
    [ -z "${stage:-}" ] && continue
    total=$((total + 1))
    case "${status}" in
      pass) passed=$((passed + 1)) ;;
      fail) failed=$((failed + 1)) ;;
      stub) stubbed=$((stubbed + 1)) ;;
      skip) skipped=$((skipped + 1)) ;;
    esac
  done <<< "${EVIDENCE_EVENTS}"

  out_dir="$(dirname "${CE_REHEARSAL_EVIDENCE_OUT}")"
  mkdir -p "${out_dir}"
  {
    printf '{\n'
    printf '  "schema_version": "1",\n'
    printf '  "rehearsal_id": "%s",\n' "$(json_escape "${rehearsal_id}")"
    printf '  "run_timestamp_utc": "%s",\n' "$(now_utc)"
    printf '  "harness_version": "%s",\n' "${HARNESS_VERSION}"
    printf '  "container_image": "%s",\n' "$(json_escape "${CE_REHEARSAL_IMAGE}")"
    printf '  "ce_package_version": '
    json_string_or_null "${CE_PACKAGE_VERSION}"
    printf ',\n'
    printf '  "ce_site": "%s",\n' "$(json_escape "${CE_REHEARSAL_SITE}")"
    printf '  "stages": [\n'
    first=1
    while IFS=$'\t' read -r stage status started completed duration stub_reason exit_code notes; do
      [ -z "${stage:-}" ] && continue
      [ "${first}" = "1" ] || printf ',\n'
      first=0
      printf '    {"stage": "%s", "status": "%s", "started_at": "%s", "completed_at": "%s", "duration_ms": %s, "stub_reason": ' \
        "$(json_escape "${stage}")" "$(json_escape "${status}")" "$(json_escape "${started}")" "$(json_escape "${completed}")" "${duration}"
      json_string_or_null "${stub_reason}"
      printf ', "exit_code": '
      json_int_or_null "${exit_code}"
      printf ', "notes": '
      json_string_or_null "${notes}"
      printf '}'
    done <<< "${EVIDENCE_EVENTS}"
    printf '\n  ],\n'
    printf '  "summary": {"total_stages": %s, "passed": %s, "failed": %s, "stubbed": %s, "skipped": %s},\n' \
      "${total}" "${passed}" "${failed}" "${stubbed}" "${skipped}"
    printf '  "failures": [\n'
    first=1
    while IFS=$'\t' read -r stage notes; do
      [ -z "${stage:-}" ] && continue
      [ "${first}" = "1" ] || printf ',\n'
      first=0
      printf '    {"stage": "%s", "message": "%s"}' "$(json_escape "${stage}")" "$(json_escape "${notes}")"
    done <<< "${FAILURES}"
    printf '\n  ]\n'
    printf '}\n'
  } > "${CE_REHEARSAL_EVIDENCE_OUT}"
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
      --release-smoke)
        RELEASE_SMOKE=1
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

release_smoke_fail() {
  log "FAIL" "release_smoke" "$1"
  exit 1
}

run_release_smoke() {
  local engine result_out result_tmp engine_output binding_line binding_count
  local marker package_version canonical_spec_sha256 signed_spec_sha256 finalize_manifest_sha256 artifacts_sha256 extra
  if [ "${DRY_RUN}" = "1" ] || [ "${LIVE}" = "1" ] || [ "${LIST_STAGES}" = "1" ] || [ -n "${SELECTED_STAGE}" ]; then
    release_smoke_fail "--release-smoke is a separate governed-worker mode"
  fi
  if [[ ! "${CE_REHEARSAL_IMAGE}" =~ ^[^[:space:]@]+@sha256:[0-9a-f]{64}$ ]]; then
    release_smoke_fail "release smoke image must be digest-pinned"
  fi
  if [ "${CE_REHEARSAL_CHECKOUT_MOUNT}" != "false" ]; then
    release_smoke_fail "release smoke requires host checkout mount=false"
  fi
  engine="${CE_REHEARSAL_ENGINE}"
  if ! command -v "${engine}" >/dev/null 2>&1; then
    release_smoke_fail "container engine command is unavailable: ${engine}"
  fi
  result_out="${CE_REHEARSAL_RELEASE_SMOKE_RESULT_OUT}"
  [ -n "${result_out}" ] || release_smoke_fail "release smoke result path must not be empty"
  rm -f "${result_out}"

  log "RUN" "release_smoke" "image=${CE_REHEARSAL_IMAGE}; checkout_mount=false"
  if ! engine_output="$("${engine}" run --rm \
    --env "CE_SITE=${CE_REHEARSAL_SITE}" \
    "${CE_REHEARSAL_IMAGE}" \
    bash -lc 'set -euo pipefail; apt-get update; DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl bash openssh-client git; curl --proto "=https" --tlsv1.2 -fsSL "${CE_SITE%/}/install.sh" | bash; export PATH="/root/.local/bin:${PATH}"; cev3 --version; ce --version; ce --help >/dev/null; ce onboard --help >/dev/null; smoke_dir="$(mktemp -d)"; trap "rm -rf \"${smoke_dir}\"" EXIT; curl --proto "=https" --tlsv1.2 -fsSL "${CE_SITE%/}/llms-install.md" -o "${smoke_dir}/llms-install.md"; curl --proto "=https" --tlsv1.2 -fsSL "${CE_SITE%/}/release-finalize-manifest.yml" -o "${smoke_dir}/release-finalize-manifest.yml"; package_version="$(sed -n "s/^package_version: //p" "${smoke_dir}/release-finalize-manifest.yml")"; canonical_spec_sha256="$(sed -n "s/^canonical_spec_sha256: //p" "${smoke_dir}/release-finalize-manifest.yml")"; signed_spec_sha256="$(sha256sum "${smoke_dir}/llms-install.md" | cut -d " " -f 1)"; expected_signed_spec_sha256="$(sed -n "s/^signed_spec_sha256: //p" "${smoke_dir}/release-finalize-manifest.yml")"; finalize_manifest_sha256="$(sha256sum "${smoke_dir}/release-finalize-manifest.yml" | cut -d " " -f 1)"; artifacts_sha256="$(sed -n "/^artifacts:$/,$ p" "${smoke_dir}/release-finalize-manifest.yml" | sha256sum | cut -d " " -f 1)"; [ "${signed_spec_sha256}" = "${expected_signed_spec_sha256}" ]; [[ "${package_version}" =~ ^[^[:space:]]+$ ]]; [[ "${canonical_spec_sha256}" =~ ^[0-9a-f]{64}$ ]]; [[ "${signed_spec_sha256}" =~ ^[0-9a-f]{64}$ ]]; [[ "${finalize_manifest_sha256}" =~ ^[0-9a-f]{64}$ ]]; [[ "${artifacts_sha256}" =~ ^[0-9a-f]{64}$ ]]; printf "CE_RELEASE_SMOKE_BINDING %s %s %s %s %s\n" "${package_version}" "${canonical_spec_sha256}" "${signed_spec_sha256}" "${finalize_manifest_sha256}" "${artifacts_sha256}"')"; then
    release_smoke_fail "clean-container install/install_verify failed"
  fi

  binding_count="$(printf '%s\n' "${engine_output}" | grep -c '^CE_RELEASE_SMOKE_BINDING ' || true)"
  [ "${binding_count}" = "1" ] || release_smoke_fail "clean container must emit exactly one observed release binding"
  binding_line="$(printf '%s\n' "${engine_output}" | grep '^CE_RELEASE_SMOKE_BINDING ')"
  read -r marker package_version canonical_spec_sha256 signed_spec_sha256 finalize_manifest_sha256 artifacts_sha256 extra <<< "${binding_line}"
  [ "${marker}" = "CE_RELEASE_SMOKE_BINDING" ] && [ -z "${extra:-}" ] || release_smoke_fail "observed release binding is malformed"
  [[ "${package_version}" =~ ^[^[:space:]]+$ ]] || release_smoke_fail "observed package version is malformed"
  for digest in "${canonical_spec_sha256}" "${signed_spec_sha256}" "${finalize_manifest_sha256}" "${artifacts_sha256}"; do
    [[ "${digest}" =~ ^[0-9a-f]{64}$ ]] || release_smoke_fail "observed release digest is malformed"
  done

  mkdir -p "$(dirname "${result_out}")"
  result_tmp="${result_out}.tmp.$$"
  printf '{"container_image":"%s","containment":{"host_checkout_mount":false},"release_binding":{"artifacts_sha256":"%s","canonical_spec_sha256":"%s","finalize_manifest_sha256":"%s","package_version":"%s","signed_spec_sha256":"%s"},"schema_version":"1","stages":{"install":"passed","install_verify":"passed"},"summary":{"failed":0,"stubbed":0}}' \
    "${CE_REHEARSAL_IMAGE}" "${artifacts_sha256}" "${canonical_spec_sha256}" "${finalize_manifest_sha256}" "${package_version}" "${signed_spec_sha256}" > "${result_tmp}"
  mv "${result_tmp}" "${result_out}"
  log "PASS" "release_smoke" "result=${result_out}"
}

require_live_or_dry_run() {
  if [ "${LIVE}" = "1" ]; then
    return 0
  fi
  fail "global" "live rehearsal is fail-closed by default; rerun with --dry-run for a safe plan or --live to affirm Docker/network execution"
}

selected_or_all() {
  local stage
  for stage in "${STAGES[@]}"; do
    if [ -z "${SELECTED_STAGE}" ] || [ "${SELECTED_STAGE}" = "${stage}" ]; then
      printf '%s\n' "${stage}"
    fi
  done
}

print_plan() {
  local stage
  printf 'CE_REHEARSAL_PLAN dry_run=1 harness_version=%s image=%s\n' "${HARNESS_VERSION}" "${CE_REHEARSAL_IMAGE}"
  printf 'CE_REHEARSAL_PLAN env=CE_REHEARSAL_SITE value=%s\n' "${CE_REHEARSAL_SITE}"
  printf 'CE_REHEARSAL_PLAN env=CE_REHEARSAL_EVIDENCE_OUT value=%s\n' "${CE_REHEARSAL_EVIDENCE_OUT}"
  printf 'CE_REHEARSAL_PLAN isolation="docker clean container; no host checkout mount"\n'
  while IFS= read -r stage; do
    case "${stage}" in
      provision) printf 'CE_REHEARSAL_PLAN stage=provision action="docker run -d --name %s %s sleep infinity"\n' "${CE_REHEARSAL_CONTAINER_NAME}" "${CE_REHEARSAL_IMAGE}" ;;
      install) printf 'CE_REHEARSAL_PLAN stage=install action="curl --proto '\\''=https'\\'' --tlsv1.2 -fsSL %s/install.sh | bash"\n' "${CE_REHEARSAL_SITE%/}" ;;
      install_verify) printf 'CE_REHEARSAL_PLAN stage=install_verify action="cev3 --version && ce --version && ce --help && ce onboard --help"\n' ;;
      onboard) printf 'CE_REHEARSAL_PLAN stage=onboard action="cev3 onboard --inventory"\n' ;;
      scratch_repo) printf 'CE_REHEARSAL_PLAN stage=scratch_repo action="git init /tmp/scratch-repo"\n' ;;
      ceo_launch) printf 'CE_REHEARSAL_PLAN stage=ceo_launch action=stub\nCE_REHEARSAL_STUB: ceo_launch requires_live_model\n' ;;
      ceo_frame) printf 'CE_REHEARSAL_PLAN stage=ceo_frame action=stub\nCE_REHEARSAL_STUB: ceo_frame requires_live_model\n' ;;
      ceo_scope) printf 'CE_REHEARSAL_PLAN stage=ceo_scope action="stub plus ce ratify --help"\nCE_REHEARSAL_STUB: ceo_scope requires_live_model\n' ;;
      ceo_build) printf 'CE_REHEARSAL_PLAN stage=ceo_build action=stub\nCE_REHEARSAL_STUB: ceo_build requires_live_model_and_github\n' ;;
      ceo_merge) printf 'CE_REHEARSAL_PLAN stage=ceo_merge action="stub plus ce merge --help"\nCE_REHEARSAL_STUB: ceo_merge requires_live_pr\n' ;;
      ceo_report) printf 'CE_REHEARSAL_PLAN stage=ceo_report action="stub plus ce report --help"\nCE_REHEARSAL_STUB: ceo_report requires_completed_run\n' ;;
      teardown) printf 'CE_REHEARSAL_PLAN stage=teardown action="docker rm -f %s"\n' "${CE_REHEARSAL_CONTAINER_NAME}" ;;
    esac
  done < <(selected_or_all)
}

need_container() {
  [ -n "${CONTAINER_ID:-}" ] || fail "$1" "stage requires a live container from the orchestration path"
}

docker_exec() {
  local stage="$1"
  shift
  need_container "${stage}"
  docker exec \
    --env "CE_SITE=${CE_REHEARSAL_SITE}" \
    --env "CE_REHEARSAL_SITE=${CE_REHEARSAL_SITE}" \
    --env "PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    "${CONTAINER_ID}" "$@"
}

run_provision() {
  stage_start "provision" "image=${CE_REHEARSAL_IMAGE}"
  command -v docker >/dev/null 2>&1 || fail "provision" "docker command is required for live rehearsal"
  docker pull "${CE_REHEARSAL_IMAGE}" >/dev/null
  CONTAINER_ID="$(docker run -d --name "${CE_REHEARSAL_CONTAINER_NAME}" "${CE_REHEARSAL_IMAGE}" sleep infinity)"
  CONTAINER_OWNED=1
  record_stage "provision" "pass" "" 0 "container=${CONTAINER_ID}"
}

run_install() {
  stage_start "install" "site=${CE_REHEARSAL_SITE}"
  docker_exec "install" bash -lc "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl bash openssh-client git"
  docker_exec "install" bash -lc "curl --proto '=https' --tlsv1.2 -fsSL \"\${1%/}/install.sh\" | bash" bash "${CE_REHEARSAL_SITE}"
  record_stage "install" "pass" "" 0 "installer_completed=1"
}

run_install_verify() {
  local cev3_version ce_version cev3_exit ce_exit ce_help_exit ce_onboard_help_exit
  stage_start "install_verify" "capture versions"
  if cev3_version="$(docker_exec "install_verify" bash -lc "cev3 --version" 2>&1)"; then
    cev3_exit=0
  else
    cev3_exit=$?
  fi
  if ce_version="$(docker_exec "install_verify" bash -lc "ce --version" 2>&1)"; then
    ce_exit=0
  else
    ce_exit=$?
  fi
  if docker_exec "install_verify" bash -lc "ce --help >/tmp/ce-help.txt" >/dev/null 2>&1; then
    ce_help_exit=0
  else
    ce_help_exit=$?
  fi
  if docker_exec "install_verify" bash -lc "ce onboard --help >/tmp/ce-onboard-help.txt" >/dev/null 2>&1; then
    ce_onboard_help_exit=0
  else
    ce_onboard_help_exit=$?
  fi
  if [ "${cev3_exit}" -ne 0 ] || [ "${ce_exit}" -ne 0 ] || [ "${ce_help_exit}" -ne 0 ] || [ "${ce_onboard_help_exit}" -ne 0 ]; then
    fail "install_verify" "cev3_exit=${cev3_exit}; ce_exit=${ce_exit}; ce_help=${ce_help_exit}; ce_onboard_help=${ce_onboard_help_exit}"
  fi
  CE_PACKAGE_VERSION="${cev3_version:-${ce_version}}"
  record_stage "install_verify" "pass" "" 0 "cev3=${cev3_version}; ce=${ce_version}; cev3_exit=${cev3_exit}; ce_exit=${ce_exit}; ce_help=${ce_help_exit}; ce_onboard_help=${ce_onboard_help_exit}"
}

run_onboard() {
  local venv_path
  stage_start "onboard" "inventory only"
  docker_exec "onboard" bash -lc "cev3 onboard --inventory | tee /tmp/ce-rehearsal-inventory.log >/dev/null"
  venv_path="$(docker_exec "onboard" bash -lc "sed -n 's/^venv_path=//p' /root/.local/share/creator-engine/bootstrap/state 2>/dev/null | head -1" 2>/dev/null || true)"
  record_stage "onboard" "pass" "" 0 "inventory_captured=1; venv_path=${venv_path:-unknown}"
}

run_scratch_repo() {
  stage_start "scratch_repo" "git init"
  docker_exec "scratch_repo" bash -lc "rm -rf /tmp/scratch-repo && mkdir -p /tmp/scratch-repo && cd /tmp/scratch-repo && git init"
  record_stage "scratch_repo" "pass" "" 0 "path=/tmp/scratch-repo"
}

stub_stage() {
  local stage="$1"
  local reason="$2"
  local notes="${3:-}"
  stage_start "${stage}" "stub"
  printf 'CE_REHEARSAL_STUB: %s %s\n' "${stage}" "${reason}"
  record_stage "${stage}" "stub" "${reason}" "" "${notes}"
}

run_ceo_launch() {
  stub_stage "ceo_launch" "requires_live_model" "documented command: ce launch --backend host"
}

run_ceo_frame() {
  stub_stage "ceo_frame" "requires_live_model" "simulated_input=Add a README to the scratch repo."
}

run_ceo_scope() {
  local exit_code
  stage_start "ceo_scope" "stub plus ratify help"
  printf 'CE_REHEARSAL_STUB: ceo_scope requires_live_model\n'
  # STUB: ce ratify -- no live Scope.
  if docker_exec "ceo_scope" bash -lc "ce ratify --help >/tmp/ce-ratify-help.txt" >/dev/null 2>&1; then
    exit_code=0
  else
    exit_code=$?
  fi
  record_stage "ceo_scope" "stub" "requires_live_model" "${exit_code}" "synthetic_scope_id=rehearsal-scope; approver_ref=0000000000000000000000000000000000000000000000000000000000000000"
}

run_ceo_build() {
  stub_stage "ceo_build" "requires_live_model_and_github" "agent build, PR open, independent review"
}

run_ceo_merge() {
  local exit_code
  stage_start "ceo_merge" "stub plus merge help"
  printf 'CE_REHEARSAL_STUB: ceo_merge requires_live_pr\n'
  if docker_exec "ceo_merge" bash -lc "ce merge --help >/tmp/ce-merge-help.txt" >/dev/null 2>&1; then
    exit_code=0
  else
    exit_code=$?
  fi
  record_stage "ceo_merge" "stub" "requires_live_pr" "${exit_code}" "documented command: ce merge <scope-id> --run <run-id> --apply"
}

run_ceo_report() {
  local exit_code
  stage_start "ceo_report" "stub plus report help"
  printf 'CE_REHEARSAL_STUB: ceo_report requires_completed_run\n'
  if docker_exec "ceo_report" bash -lc "ce report --help >/tmp/ce-report-help.txt" >/dev/null 2>&1; then
    exit_code=0
  else
    exit_code=$?
  fi
  record_stage "ceo_report" "stub" "requires_completed_run" "${exit_code}" "documented command: ce report <scope-id> --run-id <run-id>"
}

run_teardown() {
  local rm_exit
  stage_start "teardown" "cleanup"
  if [ -n "${CONTAINER_ID:-}" ] && [ "${CONTAINER_OWNED}" = "1" ]; then
    if docker rm -f "${CONTAINER_ID}" >/dev/null 2>&1; then
      rm_exit=0
    else
      rm_exit=$?
    fi
    if [ "${rm_exit}" -ne 0 ]; then
      record_stage "teardown" "fail" "" "${rm_exit}" "docker_rm=${rm_exit}"
      CONTAINER_ID=""
      return 1
    fi
    CONTAINER_ID=""
  else
    rm_exit=0
  fi
  record_stage "teardown" "pass" "" "${rm_exit}" "container_removed=1; docker_rm=${rm_exit}"
}

run_stage() {
  case "$1" in
    provision) run_provision ;;
    install) run_install ;;
    install_verify) run_install_verify ;;
    onboard) run_onboard ;;
    scratch_repo) run_scratch_repo ;;
    ceo_launch) run_ceo_launch ;;
    ceo_frame) run_ceo_frame ;;
    ceo_scope) run_ceo_scope ;;
    ceo_build) run_ceo_build ;;
    ceo_merge) run_ceo_merge ;;
    ceo_report) run_ceo_report ;;
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

  if [ "${RELEASE_SMOKE}" = "1" ]; then
    run_release_smoke
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
  TEMP_DIR="$(mktemp -d)"
  REHEARSAL_ID="$(uuid_v4)"

  while IFS= read -r stage; do
    run_stage "${stage}"
  done < <(selected_or_all)
  write_evidence
  log "PASS" "evidence" "path=${CE_REHEARSAL_EVIDENCE_OUT}"
}

main "$@"
