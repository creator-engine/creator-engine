#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
forbidden_token_env="CLAUDE_CODE_OAUTH_""TOKEN"
forbidden_token_value="synthetic-secret-""token-value"

assert_contains() {
  local label="$1" output="$2" needle="$3"
  case "${output}" in
    *"${needle}"*) ;;
    *)
      printf '%s dry-run did not contain %s\n' "${label}" "${needle}" >&2
      printf '%s\n' "${output}" >&2
      return 1
      ;;
  esac
}

assert_not_contains() {
  local label="$1" output="$2" needle="$3"
  case "${output}" in
    *"${needle}"*)
      printf '%s dry-run unexpectedly contained %s\n' "${label}" "${needle}" >&2
      printf '%s\n' "${output}" >&2
      return 1
      ;;
  esac
}

run_controller_dry_run() {
  env \
    CE_DGX_DRY_RUN=1 \
    CE_DGX_CONTROLLER_IMAGE=creator-engine/claude-controller-runsc:test \
    CE_DGX_REPO=/repo/creator-engine \
    CE_DGX_CONTROLLER_HOME=/home/cedev4/.ce-controller \
    CE_DGX_CLAUDE_BIN=/opt/claude/bin/claude \
    CE_DGX_UID=1000 \
    CE_DGX_GID=1000 \
    CE_DGX_TTY_FLAGS=-i \
    "${forbidden_token_env}=${forbidden_token_value}" \
    "${repo_root}/deploy/dgx-controller-runsc/run-controller-runsc.sh" "$@"
}

tui_output="$(TERM=dumb run_controller_dry_run tui)"
assert_contains "controller tui" "${tui_output}" "docker run"
assert_contains "controller tui" "${tui_output}" "--runtime=runsc-gvproxy-ptrace"
assert_contains "controller tui" "${tui_output}" "--security-opt=no-new-privileges"
assert_contains "controller tui" "${tui_output}" "--cap-drop=ALL"
assert_contains "controller tui" "${tui_output}" "TERM=xterm-256color"
assert_contains "controller tui" "${tui_output}" "CE_DGX_HARNESS_BIN=/usr/local/bin/ce-controller-harness"
assert_contains "controller tui" "${tui_output}" "CE_DGX_CREDENTIAL_INJECTION=SEAM-STUB"
assert_contains "controller tui" "${tui_output}" "CE_TRANSPORT_DEPUTY_SEAM_STATUS=stub-ce-ops-239-no-secret-injection"
assert_contains "controller tui" "${tui_output}" "source=/repo/creator-engine"
assert_contains "controller tui" "${tui_output}" "target=/workspace/creator-engine"
assert_contains "controller tui" "${tui_output}" "source=/home/cedev4/.ce-controller"
assert_contains "controller tui" "${tui_output}" "target=/home/cedev4"
assert_not_contains "controller tui" "${tui_output}" "--network="
assert_not_contains "controller tui" "${tui_output}" "--env HERDR_SOCKET_PATH="
assert_not_contains "controller tui" "${tui_output}" "${forbidden_token_env}"
assert_not_contains "controller tui" "${tui_output}" "${forbidden_token_value}"
assert_not_contains "controller tui" "${tui_output}" "/var/run/docker.sock"
assert_not_contains "controller tui" "${tui_output}" "/run/podman/podman.sock"
assert_not_contains "controller tui" "${tui_output}" "/run/containerd/containerd.sock"
assert_not_contains "controller tui" "${tui_output}" "/tmp/tmux-"

exec_output="$(run_controller_dry_run exec "summarize status")"
assert_contains "controller exec" "${exec_output}" "creator-engine/claude-controller-runsc:test -p summarize\\ status"
assert_not_contains "controller exec" "${exec_output}" "${forbidden_token_env}"
assert_not_contains "controller exec" "${exec_output}" "${forbidden_token_value}"

printf 'DGX controller runsc dry-run checks passed\n'
