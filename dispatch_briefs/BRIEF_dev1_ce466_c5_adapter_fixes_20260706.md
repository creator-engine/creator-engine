# DISPATCH BRIEF — dev-1 — ce-ops#466: C5 adapter mixed-uid fixes (4 items, one unit)
Dispatched: 2026-07-06 ~04:3xZ by CE-DEV-2 (controller). Role: implementer, self-push seat. Authority: day-arc 2026-07-06 lane D-E / R6 (fix-dispatch pre-authorized; cutover retry stays controller-owned).

## Unit
- Ticket: creator-engine/ce-ops#466 (READ IT IN FULL — the attempt-2 postmortem in the body is the spec; companion staging doc A2_QUEUE_DAEMON_CUTOVER_STAGING_20260704.md if present on your host).
- Branch: `ce-466-c5-adapter-mixed-uid` off FRESH origin/main (fetch first — main moved: #847-#850 merged this hour, #851/#852 may land while you work; rebase before push if needed).
- Declared work class: **story** (CI enum tiny|story|feature|epic).

## Scope — the ticket's 4 items, nothing else
1. ADAPTER MIXED-UID HOST-PREP: deploy/daemons/run-daemon-container.sh must succeed when the state root ALREADY carries production ownership (10001:10001 / 0700) and the invoker is an unprivileged user (e.g. 1003). Its host-side `install -d` prep must be ownership-aware: detect pre-owned tree → skip/adjust prep (or perform it via the documented privileged path) instead of failing `Permission denied`. Re-run idempotency is the bar: first run AND re-run over attempt-residual state both succeed.
2. MIXED-UID SMOKE: extend the stateful smoke so it actually exercises the mixed-uid host-prep path (pre-chown a scratch state root to a foreign uid where the harness allows, or simulate via a documented seam) — the #805 smoke adapted the whole contract to the caller's uid and therefore missed this. The smoke must FAIL on the pre-fix adapter and PASS on the fixed one.
3. PER-ATTEMPT LOGS: adapter writes per-attempt log files (timestamped suffix or attempt id) instead of appending to one ~/ce-wall-daemon-container.log — stale prior-attempt lines nearly misled diagnosis. Keep a stable "latest" pointer/symlink if cheap.
4. DEFAULT IMAGE TAG: fix the CE_DAEMON_IMAGE default (current default creator-engine/ce-validator:0.3.2 does not exist); default to the documented runtime image naming, and verify the env var is honored end-to-end (test or smoke assertion).

## Allowed paths (territory-checked; collision → STOP+report)
- deploy/daemons/run-daemon-container.sh (+ sibling deploy/daemons/ scripts/docs it owns)
- the stateful-smoke script wherever it lives (locate it; report the path) + its tests
- validators/tests/ if the smoke/adapter has test coverage there
- .ce/changelog/ce-466-c5-adapter-mixed-uid.md + carrier
DO NOT touch: .github/workflows/* (in-flight #462 just landed there), validators/creator_engine_validator/{onboard_apply,dependency_unlock,public_docs_confidentiality,tenant_confidentiality}.py, brain_append_* (dev-4 in-flight), release staging/downloads paths (release op in progress).

## Evidence bar + stop lines
- Standing preflight directive (ce-ops#303): FULL `ce validate-pr` GREEN one pass BEFORE self-push.
- Carrier via carrier_gen `write_carriers(base="origin/main")`; stem == branch slug; changelog required; PR body carries `- **Declared work class:** story`.
- Self-push + open PR; report PR#, head SHA, validate-pr summary, smoke evidence (pre-fix fail / post-fix pass output).
- STOP lines: NO cutover attempt, NO daemon restart, NO touching the LIVE state root or live wall daemon on any host — code+smoke only; the retry is a controller act in a quiet window. sha256-pinned file → STOP. Signature invalid → STOP; controller signs. Paths outside set → STOP+report.
