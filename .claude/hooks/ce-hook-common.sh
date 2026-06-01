#!/usr/bin/env sh
# CC-G-C Claude Code hook-pack — shared helpers.
#
# This is the Ring 1 (CLAUDE HOOK-PACK) layer: an in-band runtime gate that is
# RUNTIME (launch-pinned) and DEFEASIBLE — it can be bypassed by `--bare`,
# `settings.local.json`, `--setting-sources` excluding `project`, or
# `disableAllHooks`. It is NOT the HARD floor. The HARD floor is the Ring 0
# kernel (`ce launch` / `ce lane launch`, CC-G-D), which must later confirm the
# pack is loaded before any permission bypass. See
# docs/operations/CLAUDE_CODE_HOOK_PACK.md and
# docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md (§8 three-ring model).
#
# This file only resolves paths and invokes the Ring 2 validator
# (`creator_engine_validator hook-check`). It never launches Claude, never
# spawns a pane, never reads or echoes secret bytes, and FAILS OPEN by contract:
# a missing/broken validator or malformed input must never block here — that is
# Ring 0's job to catch later.
set -eu

# Resolve the repo that ships this hook-pack (where `validators/` lives). The
# hook scripts and the validator package are committed together, so the
# validator is always found relative to this script's location. An operator may
# override with CE_HOOK_REPO_ROOT (e.g. when invoking from an unusual cwd).
# $1 is the absolute `.claude/hooks` directory of the calling entry script.
ce_hook_repo_root() {
    if [ -n "${CE_HOOK_REPO_ROOT:-}" ]; then
        printf '%s\n' "$CE_HOOK_REPO_ROOT"
        return 0
    fi
    # .claude/hooks -> repo root is two directories up.
    (CDPATH= cd -- "$1/../.." && pwd)
}

# Resolve the posture root: the project tree whose §7 governed-posture predicate
# the gate evaluates. Claude Code exports CLAUDE_PROJECT_DIR for hooks; fall back
# to the hook-pack repo when it is unset. $1 is the resolved repo root.
ce_hook_posture_root() {
    if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
        printf '%s\n' "$CLAUDE_PROJECT_DIR"
        return 0
    fi
    printf '%s\n' "$1"
}

# Invoke the validator with the project's invocation fallback order, reading the
# hook event JSON from this process's stdin and passing decision JSON through on
# stdout. FAILS OPEN: if no validator entrypoint is available or it errors,
# print nothing and return 0 so the session is never blocked by a broken Ring 1.
# Usage: ce_hook_invoke <repo_root> <hook-check args...>
ce_hook_invoke() {
    _repo_root="$1"
    shift
    if command -v creator-engine-validator >/dev/null 2>&1; then
        creator-engine-validator "$@" 2>/dev/null || true
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        PYTHONPATH="$_repo_root/validators" python3 -m creator_engine_validator "$@" 2>/dev/null || true
        return 0
    fi
    if command -v python >/dev/null 2>&1; then
        PYTHONPATH="$_repo_root/validators" python -m creator_engine_validator "$@" 2>/dev/null || true
        return 0
    fi
    # No interpreter available -> fail open.
    return 0
}

# G2.007.3 reviewer-venue authority injection. A distinct CE reviewer venue
# (`ce lane launch --role reviewer --lane-kind review --reviewer-authority-ref ...`)
# exports the launch-pinned envelope ref as CE_REVIEWER_AUTHORITY_REF into the pane
# environment. Echo it (single value, safe to quote) so the entry hook can forward it
# to the validator as `--reviewer-authority-ref`, which injects it as
# `ce.reviewer_authority_ref` before `hook_check.build_context()`. Empty/unset prints
# nothing — fail-closed: no authority, restricted mechanics stay denied.
ce_hook_reviewer_authority_ref() {
    printf '%s\n' "${CE_REVIEWER_AUTHORITY_REF:-}"
}

# Best-effort observability: append one advisory, non-blocking NDJSON record
# under the ignored `.hermes/` evidence root. Never blocks, never fails the hook.
# Usage: ce_hook_log_observation <posture_root> <hook_event_name>
ce_hook_log_observation() {
    _obs_root="$1"
    _obs_event="$2"
    _obs_dir="$_obs_root/.hermes/cc-g-c-hook-observations"
    mkdir -p "$_obs_dir" 2>/dev/null || return 0
    _obs_ts=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf 'unknown')
    printf '{"hookEventName":"%s","observedAt":"%s","advisory":true,"blocking":false}\n' \
        "$_obs_event" "$_obs_ts" >> "$_obs_dir/observations.ndjson" 2>/dev/null || true
    return 0
}
