# PR path manifest — feat(v3.5-D.0.3): measure dogfood-fleet compute demand

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **D.0.3 — a reproducible driver that measures the dogfood fleet's compute
demand from recorded session evidence.**

- `examples/fleet_measure.py`: the pure, reproducible measurement driver over a
  fleet of recorded session leaves.
- `validators/tests/unit/fixtures/fleet_measure_sample.jsonl`: the recorded
  sample fixture the driver and its test read.
- `validators/tests/unit/test_fleet_measure.py`: unit coverage for the driver.

**Version-boundary impact = ZERO.** This slice adds no `runner.*` module, no
schema change, no check registration, and no `runner/__init__.py` export;
`V3_RUNTIME` stays **28** and `--list-checks` stays byte-identical.

- **base:** `97dbc28e8c72717759d572ec4b022e854331048a` (current `main`).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=d66fd78cecbfd6cfd11eab5a93cb14716bcfc97f58bec7a5e0ff450a833aed6b

```text
.ce/pr-path-manifest.md
examples/fleet_measure.py
validators/tests/unit/fixtures/fleet_measure_sample.jsonl
validators/tests/unit/test_fleet_measure.py
```
