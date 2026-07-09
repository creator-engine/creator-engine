#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS="${SCRIPT_DIR}/run-rehearsal.sh"

fail() {
  printf 'smoke: FAIL: %s\n' "$1" >&2
  exit 1
}

[ -x "${HARNESS}" ] || fail "harness is not executable: ${HARNESS}"

help_output="$("${HARNESS}" --help)"
printf '%s\n' "${help_output}" | grep -q 'Usage:' || fail "--help did not print usage"

stage_output="$("${HARNESS}" --list-stages)"
expected_stages='provision
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
teardown'
[ "${stage_output}" = "${expected_stages}" ] || fail "--list-stages output mismatch"

dry_output="$("${HARNESS}" --dry-run)"
printf '%s\n' "${dry_output}" | grep -q 'CE_REHEARSAL_PLAN dry_run=1' || fail "dry-run did not print plan header"
printf '%s\n' "${dry_output}" | grep -q 'ce onboard --help' || fail "dry-run did not include shipped onboard help probe"
if printf '%s\n' "${dry_output}" | grep -q 'ce inbox --help'; then
  fail "dry-run included unshipped inbox help probe"
fi

for stage in ceo_launch ceo_frame ceo_scope ceo_build ceo_merge ceo_report; do
  printf '%s\n' "${dry_output}" | grep -q "CE_REHEARSAL_STUB: ${stage} " || fail "missing stub marker for ${stage}"
done

set +e
no_arg_output="$("${HARNESS}" 2>&1)"
no_arg_status=$?
set -e
[ "${no_arg_status}" -ne 0 ] || fail "no-arg invocation unexpectedly succeeded"
printf '%s\n' "${no_arg_output}" | grep -q 'fail-closed' || fail "no-arg invocation did not mention fail-closed"

printf 'smoke: PASS\n'
