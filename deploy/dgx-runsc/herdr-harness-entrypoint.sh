#!/usr/bin/env bash
set -euo pipefail

HERDR_BIN="/usr/local/bin/herdr"
DEFAULT_SOCKET="/run/creator-engine/herdr/herdr.sock"
WORKSPACE_CWD="${CE_DGX_CONTAINER_REPO:-/workspace/creator-engine}"
WORKSPACE_LABEL="${CE_DGX_HERDR_LABEL:-creator-engine-dgx-runsc}"

fail() {
  printf 'ce-herdr-harness-entrypoint: %s\n' "$*" >&2
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

herdr_cli server &
HERDR_SERVER_PID="$!"

cleanup() {
  if kill -0 "${HERDR_SERVER_PID}" >/dev/null 2>&1; then
    kill "${HERDR_SERVER_PID}" >/dev/null 2>&1 || true
    wait "${HERDR_SERVER_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 100); do
  if [ -S "${SOCKET_PATH}" ]; then
    break
  fi
  if ! kill -0 "${HERDR_SERVER_PID}" >/dev/null 2>&1; then
    wait "${HERDR_SERVER_PID}" || true
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
  -u HERDR_SOCKET_PATH
  -u HERDR_SOCKET
  "HOME=${HARNESS_HOME}"
  "CE_DGX_HARNESS=${CE_DGX_HARNESS:-codex}"
  "CE_DGX_TERMINAL_KIND=herdr"
  "CE_TERMINAL_KIND=herdr"
)

if [ -n "${CODEX_HOME:-}" ]; then
  harness_cmd+=("CODEX_HOME=${CODEX_HOME}")
fi

harness_cmd+=("${HARNESS_BIN}")
harness_cmd+=("$@")

herdr_cli pane run "${ROOT_PANE_ID}" "$(quote_cmd "${harness_cmd[@]}")"

trap - EXIT INT TERM
wait "${HERDR_SERVER_PID}"
