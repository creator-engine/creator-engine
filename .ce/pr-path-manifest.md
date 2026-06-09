# PR path manifest — feat(gate-a): wheel-source fidelity guard + fix pyproject package discovery

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **Gate A v2 — a wheel-source fidelity guard plus a pyproject
package-discovery fix so the shipped wheel can no longer go stale against the
source tree (the editable-reinstall finding, productized).**

- `validators/creator_engine_validator/packaging_runtime.py`: the wheel/source
  skew guard.
- `validators/pyproject.toml`: corrected package auto-discovery so the wheel
  includes `runner` and `forge`.
- `validators/tests/unit/test_packaging_contract.py`: coverage for the skew
  guard and the discovery contract.
- `validators/wheelhouse/SHA256SUMS`,
  `validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`: the
  rebuilt wheel + re-pinned checksum (now 407KB — forge/runner included).

**Version-boundary impact = ZERO.** No new `runner.*` module, no schema change,
no check registration, no `runner/__init__.py` export; `V3_RUNTIME` stays **28**
and `--list-checks` stays byte-identical (the wheel rebuild changes packaging,
not the enumerated check set).

- **base:** `97dbc28e8c72717759d572ec4b022e854331048a` (current `main`).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=4444b66c59200e3c8ffd46feb8701d879afcfaf21b32d87d58732282c95170eb

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/packaging_runtime.py
validators/pyproject.toml
validators/tests/unit/test_packaging_contract.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
