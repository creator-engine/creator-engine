#!/usr/bin/env sh
# CC-G-C PreToolUse hook — Ring 1 (RUNTIME, launch-pinned, DEFEASIBLE).
#
# Reads the Claude PreToolUse event on stdin and asks the Ring 2 validator
# (`creator_engine_validator hook-check --format claude`) for a decision,
# passing the Claude-hook-shaped JSON through verbatim on stdout. Under the
# governed §7 posture the validator denies out-of-manifest tracked writes,
# credential-like reads, and restricted mechanics; under an ungoverned posture
# it advises (allow) only. `--evidence-root .hermes` keeps ignored instance
# evidence writes from being denied. Always exits 0 — a deny is communicated as
# hook JSON, not via exit status. See docs/operations/CLAUDE_CODE_HOOK_PACK.md.
set -eu

CE_HOOK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=./ce-hook-common.sh
. "$CE_HOOK_DIR/ce-hook-common.sh"

CE_REPO_ROOT=$(ce_hook_repo_root "$CE_HOOK_DIR")
CE_POSTURE_ROOT=$(ce_hook_posture_root "$CE_REPO_ROOT")

# Base invocation. Build the argv in positional params so the two launch-pinned,
# OPTIONAL flags below compose without arrays (POSIX sh).
set -- hook-check --stdin --format claude \
    --posture-root "$CE_POSTURE_ROOT" --evidence-root .hermes

# Gate B: forward the launch-pinned absolute ledger root (if any) so the validator
# scopes §7 posture to the seat's REAL ledger. Unset => omit the flag; the validator
# then scopes to <posture_root>/.hermes/active-work-ledger (never the whole tree).
CE_LEDGER_ROOT_VAL=$(ce_hook_ledger_root)
if [ -n "$CE_LEDGER_ROOT_VAL" ]; then
    set -- "$@" --ledger-root "$CE_LEDGER_ROOT_VAL"
fi

# G2.007.3: forward the launch-pinned reviewer-venue authority ref (if any) so the
# validator injects it as ce.reviewer_authority_ref before build_context(). Unset =>
# omit the flag entirely (fail-closed: no authority, restricted mechanics denied).
CE_RVA_REF=$(ce_hook_reviewer_authority_ref)
if [ -n "$CE_RVA_REF" ]; then
    set -- "$@" --reviewer-authority-ref "$CE_RVA_REF"
fi

ce_hook_invoke "$CE_REPO_ROOT" "$@"

exit 0
