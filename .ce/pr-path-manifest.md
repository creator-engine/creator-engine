# PR path manifest — feat(v3.5-D.0.2): add the pure fleet spend and token-rate meters

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **CODE — v3.5-D.0.2, the pure fleet-level spend and token-rate meter.**
This slice extends the two existing, already-baselined runner modules:

- `spend_gate.py`: add `FleetSpendMeter`, `fleet_spend_meter`, and the shared pure
  timestamp parse/span helpers for fleet spend and spend/hour over spend-ledger
  leaves.
- `usage_tap.py`: add `FleetUsage` and `fleet_token_rate` over selected
  `UsageTurn` values, importing the shared timestamp helpers from `spend_gate.py`.
- `test_spend_gate.py` and `test_usage_tap.py`: extend the existing unit coverage
  for totals, wall-clock windows, accounting-window passthrough, global folding,
  no div-by-zero, and shared-helper discipline.

**Version-boundary impact = ZERO.** This gate adds no new `runner.*` module, no
schema change, no check registration, and no `runner/__init__.py` export. It does
not edit `_versions.py` or `test_version_boundary.py`; `V3_RUNTIME` stays **28**
and `--list-checks` stays byte-identical.

- **base:** `a76cac60b36ecf5d49ba50848af32ec2f28f3845` (current `main`; benign
  base-only refresh from the ratified prompt's older base).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=ec594748b5860b663dc0dab5436e91ebce2dd1bf55ea69f50c6bf23b44b68ee1

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/runner/spend_gate.py
validators/creator_engine_validator/runner/usage_tap.py
validators/tests/unit/test_spend_gate.py
validators/tests/unit/test_usage_tap.py
```
