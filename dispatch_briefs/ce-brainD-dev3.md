# BRIEF — dev-3 — Company Brain slice BRAIN-D (ce-ops#79): memory-augmentation design

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Drive to READY-FOR-HARVEST. Stay in allowed paths. DESIGN-ONLY (no code) — propose, don't implement.

## Goal
Write a DESIGN doc for augmenting/replacing the flat grep-based `MEMORY.md` recall with the now-shipped AI-native semantic recall (vLLM embedder + hybrid recall surface, BRAIN-A/B/C all merged). Propose the tiered-pointer-injection model: how the controller's launch context should blend (a) the deterministic SSOT assertion ledger, (b) top-K semantic recall pointers, and (c) the always-loaded MEMORY.md index — with precedence rules, staleness/verification handling (recall is advisory, agent re-verifies vs source), confidential-scope exclusion, and a migration path. This is the design that frames a future implementation slice.

## Branch
`ce-brain-memory-augmentation` off current `origin/main`. Fresh worktree.

## Allowed paths (HARD limit)
- `docs/design/ce-brain-memory-augmentation.md` (NEW) — the design. Reference the shipped pieces by name (brain_recall_surface, the launch hydration from BRAIN-A, the eval harness from BRAIN-B) and the SSOT precedence invariant. Propose; do not change any code.
- `.ce/changelog/ce-brain-memory-augmentation.md`, `.ce/pr-manifests/ce-brain-memory-augmentation.md`
Do NOT touch any .py/schema/ce_cli/broker. Design doc only.

## Gate-coupling note
If a docs-reconciliation/index gate flags the new design doc, add the minimal required index entry AND include it; if outside these paths, STOP and report. `rm -rf validators/*.egg-info validators/build` before validate.

## Evidence (stop-line)
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-brain-memory-augmentation`
- Carriers via carrier_gen (dashed slug); manifest carries `- **Declared work class:** story` (or tiny).
- STOP and emit: `READY-FOR-HARVEST: branch ce-brain-memory-augmentation, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- ZERO internal identities/IPs/host-paths/ce-ops# in the body (carrier ce-ops# OK). No push/approve/merge. Stay in allowed paths.
