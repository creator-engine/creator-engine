#!/usr/bin/env sh
# CC-G-C Stop hook — ADVISORY / OBSERVABILITY ONLY (Source decision D2).
#
# In CC-G-C v1.0 this hook MUST NOT block. Hard Stop blocking — verifying the
# canonical closeout terminal sections and a referenced completion-report
# pointer — is deferred to the Ring 0 kernel (CC-G-D), which injects the
# deterministic closeout / completion_report_ref pointers this hook is
# forbidden from inferring. This hook therefore does NOT parse the transcript
# and never emits {"decision":"block"}. It records a best-effort, non-blocking
# advisory observation under the ignored `.hermes/` evidence root and exits 0.
# See docs/operations/CLAUDE_CODE_HOOK_PACK.md.
set -eu

CE_HOOK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=./ce-hook-common.sh
. "$CE_HOOK_DIR/ce-hook-common.sh"

CE_REPO_ROOT=$(ce_hook_repo_root "$CE_HOOK_DIR")
CE_POSTURE_ROOT=$(ce_hook_posture_root "$CE_REPO_ROOT")

# Consume the Stop event from stdin. It is intentionally NOT parsed for closeout
# or transcript text in CC-G-C (D2); we only drain it so the writer does not
# block on a full pipe.
cat >/dev/null 2>&1 || true

# Best-effort, non-blocking observability under the ignored `.hermes/` root.
ce_hook_log_observation "$CE_POSTURE_ROOT" "Stop"

# Advisory-only: emit no decision (no-decision == allow), never block.
exit 0
