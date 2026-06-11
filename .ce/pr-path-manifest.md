# PR path manifest - v3.5-B2 Cockpit live-feeds gate

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
`~/ce-launch/v35b-livefeeds-wave/v35b-cockpit-livefeeds-gate-RATIFIED-20260611.md`
(sha256 `b7fc78ff027e93bdbbd45e1282d24b82b25d993cf94c01582e117152f59e5c0b`;
Operator-ratified 2026-06-11, §7 fork resolutions binding).

Implementer mandate:
`~/ce-launch/v35b-livefeeds-wave/B2_IMPL_MANDATE.md`.

Base:
`86ca1d31f034b6b841fa266e6cbf0f47f8a9c01f` (origin/main post-G1).

Per-file purpose (the closed §2 manifest — 14 paths, as ratified):
- **`schemas/escalation-record.schema.yaml`** *(A)* - Feed 1 value-free
  AWAITING-OPERATOR local record schema with required recommendation.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - `V3_SCHEMAS`
  += `schemas/escalation-record.schema.yaml` only; runtime counters stay flat.
- **`validators/creator_engine_validator/runner/cockpit_readmodel.py`** *(M)* -
  `SNAPSHOT_VERSION` 2, escalation/dispatch loaders, pure feed folds,
  availability keys, watch paths, and dispatch-derived board signals.
- **`validators/creator_engine_validator/runner/cockpit_demo_seed.py`** *(M)* -
  CE_DEMO parity for two escalation records and two schema-true dispatch records.
- **`validators/creator_engine_validator/v3_cockpit.py`** *(M)* - render-only
  left/right rail additions for dispatches and AWAITING-OPERATOR items.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - `ce escalation
  open|resolve|sync`; sync is a fail-closed `gh issue list` edge with no fold call.
- **`validators/tests/unit/test_cockpit_readmodel.py`** *(M)* - feed fold,
  loader, purity, failed-dispatch, board-signal, and demo parity tests.
- **`validators/tests/unit/test_v3_cockpit.py`** *(M)* - rail-render tests plus
  `CE_DEMO=1 ce cockpit --json` feed assertions.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - escalation CLI tests with
  faked runner and zero-write refusal proofs.
- **`docs/architecture/cockpit.md`** *(M)* - live-feed architecture, local
  escalation layout, sync posture, and snapshot-shape bump.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* -
  landing: app wheel rebuilt once from final branch source.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - landing: re-pinned for the
  rebuilt app wheel.
- **`docs/v3-roadmap.md`** *(M)* - landing: G1 merged at `86ca1d3`; B2 row added.
- **`.ce/pr-path-manifest.md`** *(M)* - this carrier.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=c2c29e112597df9f482fed641ce934b266326af60fe643f1cdaf6e5b581b6cd5

```text
.ce/pr-path-manifest.md
docs/architecture/cockpit.md
docs/v3-roadmap.md
schemas/escalation-record.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/runner/cockpit_demo_seed.py
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_cockpit.py
validators/tests/unit/test_cockpit_readmodel.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_cockpit.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
