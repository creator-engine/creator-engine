# PR path manifest - v3.1-B.7 Cockpit fleet cost meter (the last demo surface)

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED ce-ops#14 retirement-run RUNBOOK + B.7 payload spec, Part A
(sha256 `d190f2bb...`), the dev-stays-on-v1 retirement run, 2026-06-12. Part A is
the Scope this gate implements: a pure L2 read-model fold (the Cockpit B.7 fleet
cost meter) over the `runtime_spend_ledger` leaves of every collected run, with
MEASURED vs UNPRICED (subscription) honesty tiers — a demo surface, NOT the
G-5/v3.5-G tokenomics engine. Manifest = the ratified 9-path Fork A-1 (extend in
place; ZERO counter churn). The retirement RUN that drives this Scope to merge is
Part B of the same ratified package.

Base:
`b0edeb732d84f24f6401ab9cdbd814647cc34ac5` (origin/main = #205, the v3.1-G2b
review-venue run-id + venue-cwd fix-gate; rebased onto it via the L8 documented
amendment edge — the wheel re-pin from the rebased combined source is
Operator-authorized).

Per-file purpose (the closed path-set - 9 paths, as ratified Fork A-1):
- **`.ce/pr-path-manifest.md`** *(M)* - this carrier: authorized path-set count,
  hash, fenced block, base, and ratification note.
- **`docs/v3-roadmap.md`** *(M)* - the v3.1-B.7 row (LANDING) + flip the v3.1-G2
  row LANDING->MERGED (#203 / `b4fba47`, per HALT note H-6).
- **`validators/creator_engine_validator/runner/cockpit_readmodel.py`** *(M)* -
  the L2 `fold_cost_meter` (per-scope $ via `project_spend` REUSE + fleet rollup
  via `fleet_spend_meter` REUSE; MEASURED/UNPRICED/UNAVAILABLE tiers; headroom
  FLOOR note; `chains is None` -> UNAVAILABLE) wired into `meters.cost`.
- **`validators/creator_engine_validator/runner/cockpit_demo_seed.py`** *(M)* -
  ONE explicit subscription (UNPRICED) run (actions + terminal outcome, ZERO
  priced leaves) + its pane + Scope, so both tiers show on camera.
- **`validators/creator_engine_validator/v3_cockpit.py`** *(M)* - the L3 cost rail
  render (`_meter_strip_text` + `_cost_rail_lines`; render-only; top-N truncation
  DECLARED; never a $0 lie for an unpriced run).
- **`validators/tests/unit/test_cockpit_meters.py`** *(M)* - fold correctness vs
  `project_spend`/`fleet_spend_meter`, tier classification, rollup counts, purity,
  JSON round-trip, `chains=None` UNAVAILABLE, CE_DEMO both-tiers + chains verify.
- **`validators/tests/unit/test_v3_cockpit.py`** *(M)* - the cost-rail render test
  (both tiers, no $0 lie, headroom note) + the declared-truncation test.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)*
  - rebuilt from the rebased combined branch source (cockpit modules + the #205
  v3_seat_bridge fix); CI's wheel<->source contract holds.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - re-pinned for the rebuilt wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=93b7ef7bfed66cc5fccff8646f6255d8494c9bba9930889b9ad65a07bb3d7ec0

```text
.ce/pr-path-manifest.md
docs/v3-roadmap.md
validators/creator_engine_validator/runner/cockpit_demo_seed.py
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cockpit.py
validators/tests/unit/test_cockpit_meters.py
validators/tests/unit/test_v3_cockpit.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
