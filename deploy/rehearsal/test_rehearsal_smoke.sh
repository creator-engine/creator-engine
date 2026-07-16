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

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT
fake_engine="${tmp_dir}/fake-engine"
cat > "${fake_engine}" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${CE_FAKE_ENGINE_ARGS}"
exit "${CE_FAKE_ENGINE_STATUS:-0}"
EOF
chmod +x "${fake_engine}"
digest_image="registry.example.invalid/ce-smoke@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
result_path="${tmp_dir}/release-smoke-result.json"
args_path="${tmp_dir}/engine-args"
CE_FAKE_ENGINE_ARGS="${args_path}" \
CE_REHEARSAL_ENGINE="${fake_engine}" \
CE_REHEARSAL_IMAGE="${digest_image}" \
CE_REHEARSAL_RELEASE_SMOKE_RESULT_OUT="${result_path}" \
  "${HARNESS}" --release-smoke

expected_result="{\"container_image\":\"${digest_image}\",\"containment\":{\"host_checkout_mount\":false},\"schema_version\":\"1\",\"stages\":{\"install\":\"passed\",\"install_verify\":\"passed\"},\"summary\":{\"failed\":0,\"stubbed\":0}}"
[ "$(cat "${result_path}")" = "${expected_result}" ] || fail "release smoke result was not deterministic canonical JSON"
grep -q -- "${digest_image}" "${args_path}" || fail "release smoke did not use digest-pinned image"
if grep -Eq -- '(^|[[:space:]])(-v|--volume|--mount)([[:space:]]|=)' "${args_path}"; then
  fail "release smoke mounted host content"
fi

set +e
CE_FAKE_ENGINE_ARGS="${args_path}" CE_REHEARSAL_ENGINE="${fake_engine}" \
CE_REHEARSAL_IMAGE="registry.example.invalid/ce-smoke:latest" \
CE_REHEARSAL_RELEASE_SMOKE_RESULT_OUT="${result_path}" \
  "${HARNESS}" --release-smoke >/dev/null 2>&1
tag_status=$?
CE_FAKE_ENGINE_ARGS="${args_path}" CE_REHEARSAL_ENGINE="${fake_engine}" \
CE_REHEARSAL_IMAGE="${digest_image}" CE_REHEARSAL_CHECKOUT_MOUNT=true \
CE_REHEARSAL_RELEASE_SMOKE_RESULT_OUT="${result_path}" \
  "${HARNESS}" --release-smoke >/dev/null 2>&1
mount_status=$?
CE_FAKE_ENGINE_ARGS="${args_path}" CE_FAKE_ENGINE_STATUS=9 CE_REHEARSAL_ENGINE="${fake_engine}" \
CE_REHEARSAL_IMAGE="${digest_image}" CE_REHEARSAL_RELEASE_SMOKE_RESULT_OUT="${result_path}" \
  "${HARNESS}" --release-smoke >/dev/null 2>&1
engine_status=$?
set -e
[ "${tag_status}" -ne 0 ] || fail "release smoke accepted a tag-only image"
[ "${mount_status}" -ne 0 ] || fail "release smoke accepted checkout mount=true"
[ "${engine_status}" -ne 0 ] || fail "release smoke accepted a failed engine run"
[ ! -e "${result_path}" ] || fail "failed release smoke left a stale result"

printf 'smoke: PASS\n'
