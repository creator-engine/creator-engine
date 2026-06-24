#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

assert_term_coercion() {
  local label="$1"
  local output="$2"

  case "${output}" in
    *"TERM=xterm-256color"*)
      ;;
    *)
      printf '%s dry-run did not contain coerced TERM=xterm-256color\n' "${label}" >&2
      printf '%s\n' "${output}" >&2
      return 1
      ;;
  esac

  case "${output}" in
    *"TERM=dumb"*)
      printf '%s dry-run leaked TERM=dumb\n' "${label}" >&2
      printf '%s\n' "${output}" >&2
      return 1
      ;;
  esac
}

dgx_output="$(TERM=dumb "${repo_root}/deploy/dgx-runsc/run-codex-runsc.sh" --dry-run)"
assert_term_coercion "dgx" "${dgx_output}"

vps_output="$(
  TERM=dumb \
  CE_VPS_CODEX_BIN=/bin/true \
  CE_VPS_CONTAINED_CODEX_CONFIG="${tmp_dir}/config.toml" \
  "${repo_root}/deploy/vps-runsc/run-vps-runsc.sh" --dry-run
)"
assert_term_coercion "vps" "${vps_output}"

printf 'TERM coercion dry-run checks passed\n'
