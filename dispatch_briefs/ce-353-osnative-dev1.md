# BRIEF — dev-1 — os-native selectability fix: governed escape-hatch (ce-ops#353, OQ-1 Option A ratified)

Non-contained, SELF-PUSH as ce-dev-1. Fresh branch `ce-353-osnative-selectability` off CURRENT origin/main (git fetch origin main first). Drive to a green PR.

## Context — OQ-1 Option A is RATIFIED (2026-06-29)
The mechanism for the os-native (Tier-1) backend is decided: Linux bwrap+Landlock+seccomp + deny-by-default egress proxy; gvisor-proxy stays the DEFAULT; os-native is **user-elected + fail-closed**; macOS Seatbelt is a separate later lane. This unblocks the bug below.

## The bug (ce-ops#353)
The os-native backend currently raises `BackendUnavailable` UNCONDITIONALLY → a user cannot ELECT the unprivileged os-native isolation path. This is the "missing escape hatch": while contained/gvisor is the default, CE is supposed to ALSO let the user elect os-native if they choose. There is no `--no-sandbox` bypass and there shouldn't be — the governed answer is a real, fail-closed os-native backend, not an unsafe bypass.

## Investigate first (read-only)
Read the backend code + selector. Find exactly where os-native raises `BackendUnavailable` unconditionally, how backends are selected (the backend-selector / RunnerBackend abstraction), and how gvisor-proxy is wired as default. Read the merged OQ-1 decision doc (search the repo for the os-native mechanism decision) so your fix matches Option A.

## The fix (scope conservatively — selectability + fail-closed)
Make os-native USER-ELECTABLE with FAIL-CLOSED semantics per Option A:
- When the user elects os-native AND the required Linux primitives (bwrap + Landlock + seccomp) ARE available → proceed via os-native (or, if the full mechanism wiring is a larger follow-on, gate to it cleanly).
- When os-native is elected but the mechanism is NOT available (missing bwrap/Landlock/seccomp, or non-Linux) → **fail CLOSED**: refuse with a clear governed error. NEVER silently fall back to unsandboxed execution.
- Do NOT change the DEFAULT (gvisor-proxy stays default). os-native remains opt-in/elected.
- If the full bwrap+Landlock+seccomp execution mechanism is NOT yet implemented in the backend and is too large for this slice, scope THIS PR to the SELECTABILITY + fail-closed plumbing (electable + capability-probe + fail-closed refusal), and clearly note the full-mechanism execution as a follow-on in the PR body. Do not silently stub an unsafe path.

## SAFETY INVARIANT
- No unsandboxed execution path may become reachable. Fail-closed everywhere the mechanism is absent.
- Default backend unchanged (gvisor-proxy). This only RESTORES the user's ability to elect os-native, governed.

## Tests
Cover: electing os-native with the mechanism available → selected (or cleanly gated); electing it without the mechanism / on non-Linux → fail-closed refusal (NOT unsandboxed, NOT silent gvisor fallback unless that's the explicit designed behavior — if so, test it); default path unchanged (gvisor-proxy).

## PR
- Title: `fix(isolation): make os-native backend user-electable + fail-closed (ce-ops#353, OQ-1 Option A)`.
- Body: one-line summary; `- **Declared work class:** story` (or feature if the diff floor demands — state exactly); Governance: references ce-ops#353 + the ratified OQ-1 Option A; states the fail-closed invariant (no unsandboxed path) and whether the full bwrap+Landlock mechanism execution is included or scoped as a follow-on.
- Path-manifest + changelog carriers matching base..HEAD. Run FULL `ce validate-pr` GREEN locally before pushing. Push as ce-dev-1, then STOP (controller reviews + gates). Report PR number + SHA + whether full-mechanism is in or follow-on.
