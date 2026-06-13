# PR path manifest — ce57-datebomb-fix · ce-ops#57 Work-Claim Date-Bomb Test Fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce57-datebomb-fix
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED gate spec `ce-57-datebomb-fix-RATIFIED-20260613.md`
(file sha256 `ebf7b059e4725b7e1a4980c2a5c602435546830045a987f419f7a03154fec2bc`) on ce-ops#57.
Pinned @ `44b4c712`. The spec's closed implementation manifest is 4 paths
(hash `670fed7c44258648a0072598efeddb531faaf84a563d6c293ef4e61ab0b79305`); this carrier adds
itself as the 5th path per the ce-ops#21 per-PR-carrier convention (the gate spec's manifest
governs the implementation diff; the carrier is the PR-fidelity envelope around it).

Base:
`44b4c71236e9b1e5b7db1c13853d7eb04d99705f` (`main` = #218, the ce-ops#38 work-claim locks
merge). This P1 test-fix merges FIRST to un-red `main` (the #218 work-claim tests went red on
the 2026-06-13 date rollover) before the E-wave PR. The path-set + hash are satisfiable at this base.

The change (test-only):
The v3 dispatch path (`v3_cli._acquire_dispatch_claim`) and the `ce claim` CLI call
`work_claims.acquire/status/release` WITHOUT an explicit `now`, so they evaluate claim staleness
against wall-clock time. The work-claim tests pinned fixtures to `claimed_at=2026-06-12T14:00:00Z`
under a 4h (`stale_after_seconds=14400`) fence, so on 2026-06-13 the active-foreign fixture crossed
its fence and production CORRECTLY returned `claim_stale_foreign_claim` instead of
`claim_active_foreign_claim` — turning `validate.yml` red on date rollover. The fix is a test-only
frozen work-claim clock plus time-relative fixtures; the production staleness logic is untouched
(V1=23 / V3=36 / registry=53 counters UNCHANGED; no schema, workflow, or dependency edit).

Per-file purpose (the closed path-set — 5 paths):
- **`.ce/pr-manifests/ce57-datebomb-fix.md`** *(A)* — this carrier (self-inclusive).
- **`validators/tests/conftest.py`** *(M)* — `freeze_work_claim_clock` fixture: monkeypatches
  `work_claims.datetime` with a `datetime` subclass whose `now()` returns a supplied aware-UTC
  instant, leaving `fromisoformat`/`max`/construction intact for `compute_state`.
- **`validators/tests/unit/test_v3_claim_dispatch.py`** *(M)* — autouse freeze to `NOW`, `_ts(delta)`
  fixtures (`_foreign_acquire` = active `NOW-1h` under the 4h fence), and a date-bomb guard asserting
  the foreign fixture is active-not-stale relative to `NOW`.
- **`validators/tests/unit/test_work_claims.py`** *(M)* — autouse freeze + `_ts(delta)` fixtures so
  the active (`NOW-1h`) / stale (`NOW-6h`) state-machine distinction is derived from `NOW`, not a
  hardcoded wall-clock date.
- **`validators/tests/unit/test_ce_claim_cli.py`** *(M)* — autouse freeze + `_ts(delta)` fixtures so
  the `ce claim` command-surface tests no longer depend on the host date.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=3734780607badb9c4ec65a618e4bb814381b8f6876553d73763cba0a3fac637f

```text
.ce/pr-manifests/ce57-datebomb-fix.md
validators/tests/conftest.py
validators/tests/unit/test_ce_claim_cli.py
validators/tests/unit/test_v3_claim_dispatch.py
validators/tests/unit/test_work_claims.py
```
