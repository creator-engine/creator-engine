---
slug: ce-431-launch-preflight-diagnostic
date: 2026-07-05
kind: fix
scope: launch
issue: 431
---

**ce launch --preflight gate-diagnostic mode.**

- 431
- Fix (CI-test): `test_launch_preflight_passes_without_claim_acquisition` stubbed the codex harness resolution via `_fake_codex` / `CE_CODEX_HARNESS` override so the harness-binary gate evaluates PASS deterministically on any host (including GitHub CI runners where codex is not installed).
- Fix (review blocking 1): `preflight_launch` now emits a `resume-runtime-policy` gate that WOULD-REFUSE when `--resume` is combined with `--backend`/`--runtime-policy`, matching the exact message that `launch()` raises at the same check — the gate was previously omitted, making the diagnostic lie (all-PASS) for an invocation the live launcher unconditionally refuses.
- Fix (review blocking 2): the `mutate=False` branch of `_evaluate_seat_surface_reuse` (preflight path) previously reimplemented the stale-surface liveness decision tree by hand. Refactored into a shared `_decide_stale_surface` pure function (no filesystem mutation); both the live archive path (`_archive_stale_launched_surface`) and the preflight diagnostic call the same decision step, eliminating the structural desync risk.
- Fix (review blocking 3): added a `critical` marker to `LaunchPreflightGate` and a `PREFLIGHT_EXIT_CRITICAL_SKIP = 3` constant. Gates that cannot be evaluated without a live launch (containment `visible-runtime-backend`; `seat-surface-reuse` when SKIPPED for `--resume`) are now marked critical. `exit_code` returns 3 (not 0) when all evaluable gates pass but at least one critical gate is SKIPPED; `format_lines()` appends a distinct summary line naming the unevaluated critical gates. Exit 0 now unambiguously means no critical skips; `--preflight` help text and cli.generated.md updated to document all three exit codes.
