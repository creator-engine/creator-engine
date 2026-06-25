#!/usr/bin/env bash
set -euo pipefail

HERDR_BIN="${HERDR_BIN:-/usr/local/bin/herdr}"
DEFAULT_SOCKET="/run/creator-engine/herdr/herdr.sock"
WORKSPACE_CWD="${CE_DGX_CONTAINER_REPO:-/workspace/creator-engine}"
WORKSPACE_LABEL="${CE_DGX_HERDR_LABEL:-creator-engine-dgx-runsc}"
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
  log_diagnostic "ce-herdr-harness-entrypoint: $*"
  exit 66
}

quote_cmd() {
  local out="" part
  for part in "$@"; do
    printf -v part '%q' "${part}"
    if [ -n "${out}" ]; then
      out+=" "
    fi
    out+="${part}"
  done
  printf '%s' "${out}"
}

json_get_root_pane_id() {
  python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result")
if not isinstance(result, dict):
    raise SystemExit("herdr workspace create did not return a result object")
if result.get("type") != "workspace_created":
    raise SystemExit("herdr workspace create did not return workspace_created")
root_pane = result.get("root_pane")
if not isinstance(root_pane, dict):
    raise SystemExit("herdr workspace create did not return root_pane")
pane_id = root_pane.get("pane_id")
if not isinstance(pane_id, str) or not pane_id:
    raise SystemExit("herdr workspace create did not return root pane_id")
print(pane_id)
'
}

herdr_cli() {
  HERDR_SOCKET_PATH="${CE_DGX_HERDR_SOCKET_PATH:-${DEFAULT_SOCKET}}" "${HERDR_BIN}" "$@"
}

[ -x "${HERDR_BIN}" ] || fail "herdr binary is not executable: ${HERDR_BIN}"

case "${CE_DGX_HARNESS:-codex}" in
  codex)
    HARNESS_BIN="${CE_DGX_HARNESS_BIN:-/usr/local/bin/codex}"
    ;;
  claude)
    HARNESS_BIN="${CE_DGX_HARNESS_BIN:-/usr/local/bin/claude}"
    ;;
  *)
    fail "unsupported CE_DGX_HARNESS: ${CE_DGX_HARNESS}"
    ;;
esac

[ -x "${HARNESS_BIN}" ] || fail "harness binary is not executable: ${HARNESS_BIN}"

SOCKET_PATH="${CE_DGX_HERDR_SOCKET_PATH:-${DEFAULT_SOCKET}}"
SOCKET_DIR="$(dirname "${SOCKET_PATH}")"
install -d -m 0700 "${SOCKET_DIR}"
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
if [ "${CE_DGX_HARNESS:-codex}" = "codex" ]; then
  : >>"${CE_CODEX_STDERR_LOG}" || fail "codex stderr log is not writable: ${CE_CODEX_STDERR_LOG}"
fi

printf 'starting herdr server: socket=%s\n' "${SOCKET_PATH}" >>"${CE_HERDR_SERVER_LOG}"
HERDR_SOCKET_PATH="${SOCKET_PATH}" "${HERDR_BIN}" server >>"${CE_HERDR_SERVER_LOG}" 2>&1 &
HERDR_SERVER_PID="$!"

cleanup() {
  if [ -n "${HERDR_SERVER_PID:-}" ] && kill -0 "${HERDR_SERVER_PID}" >/dev/null 2>&1; then
    kill "${HERDR_SERVER_PID}" >/dev/null 2>&1 || true
    wait "${HERDR_SERVER_PID}" >/dev/null 2>&1 || true
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

for _ in $(seq 1 100); do
  if [ -S "${SOCKET_PATH}" ]; then
    break
  fi
  if ! kill -0 "${HERDR_SERVER_PID}" >/dev/null 2>&1; then
    server_status=0
    wait "${HERDR_SERVER_PID}" || server_status="$?"
    fail "herdr server exited before creating ${SOCKET_PATH}"
  fi
  sleep 0.05
done

[ -S "${SOCKET_PATH}" ] || fail "herdr server did not create socket: ${SOCKET_PATH}"

WORKSPACE_JSON="$(herdr_cli workspace create --cwd "${WORKSPACE_CWD}" --label "${WORKSPACE_LABEL}")"
ROOT_PANE_ID="$(printf '%s\n' "${WORKSPACE_JSON}" | json_get_root_pane_id)"

HARNESS_HOME="${CE_DGX_HARNESS_HOME:-${HOME:-/home/cedev4}}"
harness_cmd=(
  /usr/bin/env
  -i
  "HOME=${HARNESS_HOME}"
  "PATH=${PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"
  "TERM=${TERM:-xterm-256color}"
  "CE_DGX_HARNESS=${CE_DGX_HARNESS:-codex}"
  "CE_DGX_TERMINAL_KIND=herdr"
  "CE_TERMINAL_KIND=herdr"
  "XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-${CE_SEAT_LOG_DIR}/xdg/config}"
  "XDG_STATE_HOME=${XDG_STATE_HOME:-${CE_SEAT_LOG_DIR}/xdg/state}"
  "XDG_CACHE_HOME=${XDG_CACHE_HOME:-${CE_SEAT_LOG_DIR}/xdg/cache}"
)

if [ -n "${CODEX_HOME:-}" ]; then
  harness_cmd+=("CODEX_HOME=${CODEX_HOME}")
fi
if [ "${CE_DGX_HARNESS:-codex}" = "codex" ]; then
  harness_cmd+=("CE_CODEX_STDERR_LOG=${CE_CODEX_STDERR_LOG}")
fi
if [ -n "${CE_EGRESS_BROKER_SOCKET:-}" ]; then
  harness_cmd+=("CE_EGRESS_BROKER_SOCKET=${CE_EGRESS_BROKER_SOCKET}")
fi
if [ -n "${CE_SEAT_ID:-}" ]; then
  harness_cmd+=("CE_SEAT_ID=${CE_SEAT_ID}")
fi

if [ "${CE_DGX_HARNESS:-codex}" = "codex" ]; then
  harness_cmd+=(/bin/sh -c 'exec "$@" 2>>"${CE_CODEX_STDERR_LOG}"' sh "${HARNESS_BIN}")
else
  harness_cmd+=("${HARNESS_BIN}")
fi
harness_cmd+=("$@")

herdr_cli pane run "${ROOT_PANE_ID}" "$(quote_cmd "${harness_cmd[@]}")"

server_status=0
wait "${HERDR_SERVER_PID}" || server_status="$?"
if [ "${server_status}" -eq 130 ] || [ "${server_status}" -eq 143 ]; then
  cleanup
  trap - EXIT INT TERM
  exit "${server_status}"
fi
trap - EXIT INT TERM
if [ "${server_status}" -ne 0 ]; then
  fail "herdr server exited with status ${server_status}"
fi
