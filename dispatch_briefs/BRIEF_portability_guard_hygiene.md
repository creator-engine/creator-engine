# BRIEF — portability-guard test hygiene (follow-ups from the #774 review, S-class)
Role: implementer. Claim: ce-portability-guard-hygiene. Branch: `ce-portability-guard-hygiene` off origin/main (fetch first — main contains the merged #774 rework: tokenizer-driven matcher in checks/portability_plane.py).

## Context (embedded)
PR #774 merged with three NON-blocking review follow-ups banked. This ticket closes them. Extend-don't-weaken throughout: the merged detections and all existing tests stay intact.

## Items
1. **Per-fixture assertion isolation** in validators/tests/unit/test_portability_plane.py: the guard test currently asserts the "runtime-only subprocess command" label appears SOMEWHERE in the combined rendering — a regression catching only one of the two new fixture forms (`sudo systemctl ...` shell-string and `["/usr/bin/systemctl", ...]` argv-list) would still pass. Restructure so each fixture form is independently asserted (offense count per line/file, or one module per form).
2. **Wrapper/abs-path fixtures for the other runtime commands**: add positive fixtures for `sudo setfacl ...`, `/usr/bin/setfacl`, `sudo journalctl ...`, `/bin/journalctl` (code path is shared with systemctl, but coverage should pin all three commands).
3. **Prose-false-positive shape** (latent, no current-tree occurrence): a plain STRING literal whose first shlex word is a runtime command — e.g. `"systemctl is required for this feature"` — trips `_contains_runtime_command` because the matcher has no call-site context. Your call as implementer, smallest-good-fix wins: EITHER (a) cheap context scoping if the tokenizer stream makes it feasible (e.g. only flag strings that appear within subprocess-call expressions) — only if genuinely small and provably no-false-negative; OR (b) keep current behavior, add a test that DOCUMENTS it (asserting the prose string trips, with a comment explaining this is accepted fail-closed behavior and the manifest/baseline is the escape hatch). Do not build a mini type-checker.

## Files
validators/tests/unit/test_portability_plane.py (+ checks/portability_plane.py ONLY if you choose 3a), changelog .ce/changelog/ce-portability-guard-hygiene.md, carrier via carrier_gen API. Work-class: S expected (use the exact line `- **Declared work class:** S`).

## Stop lines
Do NOT touch: conveyor*.py, daemon_lease.py, validation_sandbox_*, forge/**, deploy/**, docs/**, v3_cli.py/ce_cli.py, surfaces/portability-plane-manifest.yaml (no new runtime-plane declarations — if a fixture needs one, it's a test fixture inside the test module, not the real manifest).

## Preflight + signal (standing, ce-ops#303)
FULL `ce validate-pr` GREEN one pass; environmental-only failure → focused set green + BLOCKED signal with exact failure class (host preflight authoritative at harvest). Signal:
`READY-FOR-HARVEST ce-portability-guard-hygiene <full-40-hex-sha>` (or `BLOCKED ce-portability-guard-hygiene <reason>`).
