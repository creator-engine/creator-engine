#!/usr/bin/env bash
set -euo pipefail

HERDR_BIN="${HERDR_BIN:-/usr/local/bin/herdr}"
HERDR_SOCKET_PATH="${HERDR_SOCKET_PATH:-/run/creator-engine/herdr/herdr.sock}"
HERDR_SOCKET_DIR="$(dirname "${HERDR_SOCKET_PATH}")"
HERDR_WORKSPACE_NAME="${HERDR_WORKSPACE_NAME:-creator-engine}"
CE_DGX_HARNESS="${CE_DGX_HARNESS:-codex}"
CE_SEAT_LOG_DIR="${CE_SEAT_LOG_DIR:-/var/log/ce-seat}"
CE_HERDR_SERVER_LOG="${CE_HERDR_SERVER_LOG:-${CE_SEAT_LOG_DIR}/herdr-server.log}"
CE_CODEX_STDERR_LOG="${CE_CODEX_STDERR_LOG:-${CE_SEAT_LOG_DIR}/codex-stderr.log}"

log_diagnostic() {
  local message="$1" log_dir

  printf '%s\n' "${message}" >&2
  if [ -n "${CE_HERDR_SERVER_LOG:-}" ]; then
    log_dir="$(dirname "${CE_HERDR_SERVER_LOG}")"
    if [ -d "${log_dir}" ] && [ -w "${log_dir}" ]; then
      printf '%s\n' "${message}" >>"${CE_HERDR_SERVER_LOG}" 2>/dev/null || true
    fi
  fi
}

fail() {
  log_diagnostic "herdr harness entrypoint refused: $*"
  exit 66
}

case "${CE_DGX_HARNESS}" in
  codex)
    harness_bin="${CE_DGX_HARNESS_BIN:-/usr/local/bin/codex}"
    ;;
  claude)
    harness_bin="${CE_DGX_HARNESS_BIN:-/usr/local/bin/claude}"
    ;;
  *)
    fail "CE_DGX_HARNESS must be codex or claude, got ${CE_DGX_HARNESS}"
    ;;
esac

[ "$#" -gt 0 ] || fail "missing harness mode args"
[ -x "${HERDR_BIN}" ] || fail "herdr binary is not executable: ${HERDR_BIN}"
[ -x "${harness_bin}" ] || fail "harness binary is not executable: ${harness_bin}"
[ -d "${HERDR_SOCKET_DIR}" ] || fail "herdr socket directory is missing: ${HERDR_SOCKET_DIR}"
[ "$(stat -c '%a' "${HERDR_SOCKET_DIR}")" = "700" ] || {
  fail "herdr socket directory must be mode 0700: ${HERDR_SOCKET_DIR}"
}
[ -d "${CE_SEAT_LOG_DIR}" ] || fail "seat log directory is missing: ${CE_SEAT_LOG_DIR}"
[ -w "${CE_SEAT_LOG_DIR}" ] || fail "seat log directory is not writable: ${CE_SEAT_LOG_DIR}"
case "${CE_HERDR_SERVER_LOG}" in
  /*)
    ;;
  *)
    fail "CE_HERDR_SERVER_LOG must be an absolute path: ${CE_HERDR_SERVER_LOG}"
    ;;
esac
case "${CE_CODEX_STDERR_LOG}" in
  /*)
    ;;
  *)
    fail "CE_CODEX_STDERR_LOG must be an absolute path: ${CE_CODEX_STDERR_LOG}"
    ;;
esac
: >>"${CE_HERDR_SERVER_LOG}" || fail "herdr server log is not writable: ${CE_HERDR_SERVER_LOG}"
install -d -m 0700 \
  "${XDG_CONFIG_HOME:-${CE_SEAT_LOG_DIR}/xdg/config}" \
  "${XDG_STATE_HOME:-${CE_SEAT_LOG_DIR}/xdg/state}" \
  "${XDG_CACHE_HOME:-${CE_SEAT_LOG_DIR}/xdg/cache}"
if [ "${CE_DGX_HARNESS}" = "codex" ]; then
  : >>"${CE_CODEX_STDERR_LOG}" || fail "codex stderr log is not writable: ${CE_CODEX_STDERR_LOG}"
fi

cleanup() {
  if [ -n "${herdr_pid:-}" ] && kill -0 "${herdr_pid}" 2>/dev/null; then
    kill "${herdr_pid}" 2>/dev/null || true
    wait "${herdr_pid}" 2>/dev/null || true
  fi
}
handle_term() {
  cleanup
  exit 143
}
handle_int() {
  cleanup
  exit 130
}
trap cleanup EXIT
trap handle_int INT
trap handle_term TERM

rm -f "${HERDR_SOCKET_PATH}"
printf 'starting herdr server: socket=%s\n' "${HERDR_SOCKET_PATH}" >>"${CE_HERDR_SERVER_LOG}"
HERDR_SOCKET_PATH="${HERDR_SOCKET_PATH}" "${HERDR_BIN}" server >>"${CE_HERDR_SERVER_LOG}" 2>&1 &
herdr_pid="$!"

for _ in $(seq 1 100); do
  if [ -S "${HERDR_SOCKET_PATH}" ]; then
    break
  fi
  if ! kill -0 "${herdr_pid}" 2>/dev/null; then
    server_status=0
    wait "${herdr_pid}" || server_status="$?"
    fail "herdr server exited before creating socket"
  fi
  sleep 0.05
done

[ -S "${HERDR_SOCKET_PATH}" ] || fail "herdr server did not create socket"

herdr_cli() {
  HERDR_SOCKET_PATH="${HERDR_SOCKET_PATH}" "${HERDR_BIN}" "$@"
}

harness_env=(
  "HOME=${HOME:-/home/ce}"
  "PATH=${PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"
  "TERM=${TERM:-xterm-256color}"
  "CE_DGX_HARNESS=${CE_DGX_HARNESS}"
  "XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-${CE_SEAT_LOG_DIR}/xdg/config}"
  "XDG_STATE_HOME=${XDG_STATE_HOME:-${CE_SEAT_LOG_DIR}/xdg/state}"
  "XDG_CACHE_HOME=${XDG_CACHE_HOME:-${CE_SEAT_LOG_DIR}/xdg/cache}"
)
if [ -n "${CODEX_HOME:-}" ]; then
  harness_env+=("CODEX_HOME=${CODEX_HOME}")
fi
if [ "${CE_DGX_HARNESS}" = "codex" ]; then
  harness_env+=("CE_CODEX_STDERR_LOG=${CE_CODEX_STDERR_LOG}")
fi

workspace_json="$(herdr_cli workspace create --cwd "${PWD}" --label "${HERDR_WORKSPACE_NAME}")" || {
  fail "could not create herdr workspace"
}
read -r workspace_id root_pane_id < <(
  python3 -c '
import json, sys

data = json.load(sys.stdin)
result = data.get("result") if isinstance(data, dict) else {}
if not isinstance(result, dict):
    result = {}
workspace = result.get("workspace") if isinstance(result.get("workspace"), dict) else {}
root_pane = result.get("root_pane") if isinstance(result.get("root_pane"), dict) else {}
print(workspace.get("workspace_id", ""), root_pane.get("pane_id", ""))
' <<<"${workspace_json}"
)

[ -n "${workspace_id}" ] || fail "herdr workspace response did not include workspace id"
[ -n "${root_pane_id}" ] || fail "herdr workspace response did not include root pane id"

if [ "${CE_DGX_HARNESS}" = "codex" ]; then
  governed_harness=(/usr/bin/env -i "${harness_env[@]}" /bin/sh -c 'exec "$@" 2>>"${CE_CODEX_STDERR_LOG}"' sh "${harness_bin}" "$@")
else
  governed_harness=(/usr/bin/env -i "${harness_env[@]}" "${harness_bin}" "$@")
fi
quoted_harness="$(printf '%q ' "${governed_harness[@]}")"
herdr_cli pane run "${root_pane_id}" "${quoted_harness}" || {
  fail "could not start governed harness through herdr"
}

server_status=0
wait "${herdr_pid}" || server_status="$?"
if [ "${server_status}" -eq 130 ] || [ "${server_status}" -eq 143 ]; then
  cleanup
  trap - EXIT INT TERM
  exit "${server_status}"
fi
trap - EXIT INT TERM
if [ "${server_status}" -ne 0 ]; then
  fail "herdr server exited with status ${server_status}"
fi
