#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
scratch_root="${TMPDIR:-${HOME:-/tmp}/tmp}"
mkdir -p "${scratch_root}"
tmp_dir="$(mktemp -d "${scratch_root}/ce-seat-logging.XXXXXX")"
trap 'rm -rf "${tmp_dir}"' EXIT

fail() {
  printf 'seat logging smoke failed: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local label="$1" text="$2" needle="$3"

  case "${text}" in
    *"${needle}"*)
      ;;
    *)
      printf '%s did not contain %s\n' "${label}" "${needle}" >&2
      printf '%s\n' "${text}" >&2
      return 1
      ;;
  esac
}

assert_not_contains() {
  local label="$1" text="$2" needle="$3"

  case "${text}" in
    *"${needle}"*)
      printf '%s unexpectedly contained %s\n' "${label}" "${needle}" >&2
      printf '%s\n' "${text}" >&2
      return 1
      ;;
  esac
}

assert_file_contains() {
  local path="$1" needle="$2"

  [ -f "${path}" ] || fail "expected file does not exist: ${path}"
  if ! grep -Fq "${needle}" "${path}"; then
    printf 'expected %s to contain %s\n' "${path}" "${needle}" >&2
    printf '%s\n' "--- ${path} ---" >&2
    sed -n '1,120p' "${path}" >&2
    return 1
  fi
}

wait_for_path_contains() {
  local path="$1" needle="$2"
  local attempts="${3:-50}"
  local _i

  for _i in $(seq 1 "${attempts}"); do
    if [ -f "${path}" ] && grep -Fq "${needle}" "${path}"; then
      return 0
    fi
    sleep 0.1
  done
  return 1
}

wait_for_socket() {
  local path="$1"
  local attempts="${2:-50}"
  local _i

  for _i in $(seq 1 "${attempts}"); do
    if [ -S "${path}" ]; then
      return 0
    fi
    sleep 0.1
  done
  return 1
}

wait_for_process_exit() {
  local pid="$1"
  local attempts="${2:-30}"
  local _i

  for _i in $(seq 1 "${attempts}"); do
    if ! jobs -pr | grep -qx "${pid}"; then
      return 0
    fi
    sleep 0.1
  done
  return 1
}

assert_rejects_relative_log_dir() {
  local label="$1"
  local output status
  shift

  set +e
  output="$("$@" 2>&1)"
  status="$?"
  set -e
  [ "${status}" -ne 0 ] || fail "${label} accepted a relative seat log dir"
  assert_contains "${label}" "${output}" "must be an absolute path"
}

assert_rejects_relative_worktree_root() {
  local label="$1"
  local output status
  shift

  set +e
  output="$("$@" 2>&1)"
  status="$?"
  set -e
  [ "${status}" -ne 0 ] || fail "${label} accepted a relative host worktree root"
  assert_contains "${label}" "${output}" "must be an absolute path"
}

stub_dir="${tmp_dir}/stubs"
install -d -m 0700 "${stub_dir}"

cat >"${stub_dir}/herdr" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  server)
    printf 'stub herdr server starting\n' >&2
    if [ "${STUB_HERDR_FAIL:-0}" = "1" ]; then
      printf 'stub herdr server forced failure\n' >&2
      exit 42
    fi
    socket_path="${HERDR_SOCKET_PATH:-${CE_DGX_HERDR_SOCKET_PATH:-}}"
    [ -n "${socket_path}" ] || { printf 'stub herdr missing socket path\n' >&2; exit 43; }
    exec python3 - "${socket_path}" "${STUB_HERDR_SERVER_SECONDS:-0.5}" <<'PY'
import os
import signal
import socket
import sys
import time

path = sys.argv[1]
seconds = float(sys.argv[2])

def handle_term(signum, frame):
    print("stub herdr server received TERM", file=sys.stderr, flush=True)
    raise SystemExit(143)

signal.signal(signal.SIGTERM, handle_term)
os.makedirs(os.path.dirname(path), exist_ok=True)
try:
    os.unlink(path)
except FileNotFoundError:
    pass

sock = socket.socket(socket.AF_UNIX)
sock.bind(path)
sock.listen(1)
print("stub herdr server ready", file=sys.stderr, flush=True)
time.sleep(seconds)
print("stub herdr server stopping", file=sys.stderr, flush=True)
PY
    ;;
  workspace)
    [ "${2:-}" = "create" ] || { printf 'stub herdr unsupported workspace command\n' >&2; exit 44; }
    printf '{"result":{"type":"workspace_created","workspace":{"workspace_id":"ws-smoke"},"root_pane":{"pane_id":"pane-smoke"}}}\n'
    ;;
  pane)
    case "${2:-}" in
      run)
        printf 'stub herdr pane run\n' >&2
        /bin/sh -c "${4:-}"
        ;;
      list)
        printf '{"result":[{"pane_id":"pane-smoke"}]}\n'
        ;;
      *)
        printf 'stub herdr unsupported pane command\n' >&2
        exit 45
        ;;
    esac
    ;;
  *)
    printf 'stub herdr unsupported command: %s\n' "${1:-}" >&2
    exit 46
    ;;
esac
STUB
chmod +x "${stub_dir}/herdr"

cat >"${stub_dir}/codex" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'stub codex stderr: %s\n' "$*" >&2
STUB
chmod +x "${stub_dir}/codex"

home_dir="${tmp_dir}/home"
install -d -m 0700 "${home_dir}"

dgx_output="$(
  HOME="${home_dir}" \
  CE_DGX_SEAT_ID=seat-dgx-smoke \
  CE_DGX_LAUNCH_ID=smoke-launch \
  CE_DGX_TTY_FLAGS=-i \
  "${repo_root}/deploy/dgx-runsc/run-codex-runsc.sh" --dry-run
)"
assert_contains "dgx dry-run" "${dgx_output}" "source=${home_dir}/.ce/logs/seats/seat-dgx-smoke"
assert_contains "dgx dry-run" "${dgx_output}" "target=/var/log/ce-seat"
assert_contains "dgx dry-run" "${dgx_output}" "source=${home_dir}/.ce/logs/seats/seat-dgx-smoke/launcher/codex-config.toml"
assert_contains "dgx dry-run" "${dgx_output}" "source=${home_dir}/.ce/logs/seats/seat-dgx-smoke/worktrees/smoke-launch"
assert_contains "dgx dry-run" "${dgx_output}" "target=/var/tmp"
assert_contains "dgx dry-run" "${dgx_output}" "CE_HERDR_SERVER_LOG=/var/log/ce-seat/herdr-server.log"
assert_contains "dgx dry-run" "${dgx_output}" "CE_CODEX_STDERR_LOG=/var/log/ce-seat/codex-stderr.log"
assert_not_contains "dgx dry-run" "${dgx_output}" "/tmp/creator-engine-dgx-runsc-codex-config"
[ -f "${home_dir}/.ce/logs/seats/seat-dgx-smoke/launcher/codex-config.toml" ] || fail "dgx config was not generated under durable seat log root"
[ -d "${home_dir}/.ce/logs/seats/seat-dgx-smoke/worktrees/smoke-launch" ] || fail "dgx durable host worktree root was not created"

vps_output="$(
  HOME="${home_dir}" \
  CE_VPS_SEAT_ID=seat-vps-smoke \
  CE_VPS_CODEX_BIN=/bin/true \
  CE_VPS_LAUNCH_ID=smoke-launch \
  CE_VPS_TTY_FLAGS=-i \
  "${repo_root}/deploy/vps-runsc/run-vps-runsc.sh" --dry-run
)"
assert_contains "vps dry-run" "${vps_output}" "source=${home_dir}/.ce/logs/seats/seat-vps-smoke"
assert_contains "vps dry-run" "${vps_output}" "target=/var/log/ce-seat"
assert_contains "vps dry-run" "${vps_output}" "source=${home_dir}/.ce/logs/seats/seat-vps-smoke/launcher/codex-config.toml"
assert_contains "vps dry-run" "${vps_output}" "source=${home_dir}/.ce/logs/seats/seat-vps-smoke/worktrees/smoke-launch"
assert_contains "vps dry-run" "${vps_output}" "target=/var/tmp"
assert_contains "vps dry-run" "${vps_output}" "CE_HERDR_SERVER_LOG=/var/log/ce-seat/herdr-server.log"
assert_contains "vps dry-run" "${vps_output}" "CE_CODEX_STDERR_LOG=/var/log/ce-seat/codex-stderr.log"
assert_not_contains "vps dry-run" "${vps_output}" "/tmp/creator-engine-vps-runsc-codex-config"
[ -f "${home_dir}/.ce/logs/seats/seat-vps-smoke/launcher/codex-config.toml" ] || fail "vps config was not generated under durable seat log root"
[ -d "${home_dir}/.ce/logs/seats/seat-vps-smoke/worktrees/smoke-launch" ] || fail "vps durable host worktree root was not created"

assert_rejects_relative_log_dir \
  "dgx dry-run relative log dir" \
  env CE_DGX_SEAT_LOG_DIR=relative CE_DGX_CONTAINED_CODEX_CONFIG="${tmp_dir}/dgx-relative.toml" \
  "${repo_root}/deploy/dgx-runsc/run-codex-runsc.sh" --dry-run

assert_rejects_relative_log_dir \
  "vps dry-run relative log dir" \
  env CE_VPS_SEAT_LOG_DIR=relative CE_VPS_CODEX_BIN=/bin/true CE_VPS_CONTAINED_CODEX_CONFIG="${tmp_dir}/vps-relative.toml" \
  "${repo_root}/deploy/vps-runsc/run-vps-runsc.sh" --dry-run

assert_rejects_relative_worktree_root \
  "dgx dry-run relative host worktree root" \
  env CE_DGX_HOST_WORKTREE_ROOT=relative CE_DGX_CONTAINED_CODEX_CONFIG="${tmp_dir}/dgx-relative-worktree.toml" \
  "${repo_root}/deploy/dgx-runsc/run-codex-runsc.sh" --dry-run

assert_rejects_relative_worktree_root \
  "vps dry-run relative host worktree root" \
  env CE_VPS_HOST_WORKTREE_ROOT=relative CE_VPS_CODEX_BIN=/bin/true CE_VPS_CONTAINED_CODEX_CONFIG="${tmp_dir}/vps-relative-worktree.toml" \
  "${repo_root}/deploy/vps-runsc/run-vps-runsc.sh" --dry-run

run_entrypoint_success() {
  local label="$1" script="$2" socket_env_name="$3"
  local log_dir="${tmp_dir}/${label}-logs"
  local run_dir="${tmp_dir}/${label}-run"
  local socket_path="${run_dir}/herdr.sock"

  install -d -m 0700 "${log_dir}" "${run_dir}"
  env \
    HERDR_BIN="${stub_dir}/herdr" \
    CE_DGX_HARNESS=codex \
    CE_DGX_HARNESS_BIN="${stub_dir}/codex" \
    CE_SEAT_LOG_DIR="${log_dir}" \
    CE_HERDR_SERVER_LOG="${log_dir}/herdr-server.log" \
    CE_CODEX_STDERR_LOG="${log_dir}/codex-stderr.log" \
    STUB_HERDR_SERVER_SECONDS=0.3 \
    "${socket_env_name}=${socket_path}" \
    "${script}" exec smoke-arg >/dev/null 2>&1

  assert_file_contains "${log_dir}/herdr-server.log" "stub herdr server starting"
  assert_file_contains "${log_dir}/herdr-server.log" "stub herdr server stopping"
  assert_file_contains "${log_dir}/codex-stderr.log" "stub codex stderr: exec smoke-arg"
}

run_entrypoint_server_failure() {
  local label="$1" script="$2" socket_env_name="$3"
  local log_dir="${tmp_dir}/${label}-failure-logs"
  local run_dir="${tmp_dir}/${label}-failure-run"
  local socket_path="${run_dir}/herdr.sock"
  local output status

  install -d -m 0700 "${log_dir}" "${run_dir}"
  set +e
  output="$(
    env \
      HERDR_BIN="${stub_dir}/herdr" \
      CE_DGX_HARNESS=codex \
      CE_DGX_HARNESS_BIN="${stub_dir}/codex" \
      CE_SEAT_LOG_DIR="${log_dir}" \
      CE_HERDR_SERVER_LOG="${log_dir}/herdr-server.log" \
      CE_CODEX_STDERR_LOG="${log_dir}/codex-stderr.log" \
      STUB_HERDR_FAIL=1 \
      "${socket_env_name}=${socket_path}" \
      "${script}" exec smoke-arg 2>&1
  )"
  status="$?"
  set -e

  [ "${status}" -eq 66 ] || {
    printf '%s failure output:\n%s\n' "${label}" "${output}" >&2
    fail "${label} server failure exited ${status}, expected 66"
  }
  assert_file_contains "${log_dir}/herdr-server.log" "stub herdr server forced failure"
  assert_file_contains "${log_dir}/herdr-server.log" "server exited before"
  [ -f "${log_dir}/codex-stderr.log" ] || fail "${label} did not preserve codex stderr log file"
}

run_entrypoint_terminated_seat() {
  local label="$1" script="$2" socket_env_name="$3"
  local log_dir="${tmp_dir}/${label}-terminated-logs"
  local run_dir="${tmp_dir}/${label}-terminated-run"
  local socket_path="${run_dir}/herdr.sock"
  local entrypoint_pid status

  install -d -m 0700 "${log_dir}" "${run_dir}"
  env \
    HERDR_BIN="${stub_dir}/herdr" \
    CE_DGX_HARNESS=codex \
    CE_DGX_HARNESS_BIN="${stub_dir}/codex" \
    CE_SEAT_LOG_DIR="${log_dir}" \
    CE_HERDR_SERVER_LOG="${log_dir}/herdr-server.log" \
    CE_CODEX_STDERR_LOG="${log_dir}/codex-stderr.log" \
    STUB_HERDR_SERVER_SECONDS=30 \
    "${socket_env_name}=${socket_path}" \
    "${script}" exec long-running-smoke >/dev/null 2>&1 &
  entrypoint_pid="$!"

  wait_for_socket "${socket_path}" || {
    kill "${entrypoint_pid}" 2>/dev/null || true
    fail "${label} long-running entrypoint did not create socket"
  }
  wait_for_path_contains "${log_dir}/herdr-server.log" "stub herdr server ready" || {
    kill "${entrypoint_pid}" 2>/dev/null || true
    fail "${label} long-running entrypoint did not write herdr readiness log"
  }
  wait_for_path_contains "${log_dir}/codex-stderr.log" "stub codex stderr: exec long-running-smoke" || {
    kill "${entrypoint_pid}" 2>/dev/null || true
    fail "${label} long-running entrypoint did not capture codex stderr"
  }

  kill -TERM "${entrypoint_pid}" 2>/dev/null || true
  if ! wait_for_process_exit "${entrypoint_pid}" 30; then
    kill -KILL "${entrypoint_pid}" 2>/dev/null || true
    wait "${entrypoint_pid}" 2>/dev/null || true
    fail "${label} long-running entrypoint did not exit after TERM"
  fi
  set +e
  wait "${entrypoint_pid}"
  status="$?"
  set -e
  case "${status}" in
    0 | 130 | 143)
      ;;
    *)
      fail "${label} long-running entrypoint exited ${status} after TERM"
      ;;
  esac

  assert_file_contains "${log_dir}/herdr-server.log" "starting herdr server: socket=${socket_path}"
  assert_file_contains "${log_dir}/herdr-server.log" "stub herdr server starting"
  assert_file_contains "${log_dir}/herdr-server.log" "stub herdr server ready"
  assert_file_contains "${log_dir}/herdr-server.log" "stub herdr server received TERM"
  assert_file_contains "${log_dir}/codex-stderr.log" "stub codex stderr: exec long-running-smoke"
  if grep -Fq "herdr server exited with status 143" "${log_dir}/herdr-server.log"; then
    fail "${label} long-running entrypoint logged misleading TERM failure diagnostic"
  fi
  if grep -Fq "refused: herdr server exited with status 143" "${log_dir}/herdr-server.log"; then
    fail "${label} long-running entrypoint logged misleading refused diagnostic"
  fi
}

run_entrypoint_success \
  "dgx" \
  "${repo_root}/deploy/dgx-runsc/herdr-harness-entrypoint.sh" \
  CE_DGX_HERDR_SOCKET_PATH
run_entrypoint_server_failure \
  "dgx" \
  "${repo_root}/deploy/dgx-runsc/herdr-harness-entrypoint.sh" \
  CE_DGX_HERDR_SOCKET_PATH
run_entrypoint_terminated_seat \
  "dgx" \
  "${repo_root}/deploy/dgx-runsc/herdr-harness-entrypoint.sh" \
  CE_DGX_HERDR_SOCKET_PATH
run_entrypoint_success \
  "vps" \
  "${repo_root}/deploy/vps-runsc/herdr-harness-entrypoint.sh" \
  HERDR_SOCKET_PATH
run_entrypoint_server_failure \
  "vps" \
  "${repo_root}/deploy/vps-runsc/herdr-harness-entrypoint.sh" \
  HERDR_SOCKET_PATH
run_entrypoint_terminated_seat \
  "vps" \
  "${repo_root}/deploy/vps-runsc/herdr-harness-entrypoint.sh" \
  HERDR_SOCKET_PATH

printf 'seat logging dry-run and stub entrypoint checks passed\n'
