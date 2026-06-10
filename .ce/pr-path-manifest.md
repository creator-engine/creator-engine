# PR path manifest - v3.5-F.2-mini large-host-30g host class

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count + SHA256 to match the fenced block.

Ratified gate:
`/home/nefarious/projects/creator-engine-canonical/.hermes/research/v35f-vps-host-class-gate-20260610T152800Z/GATE_VPS_HOST_CLASS_composed.md`
(v2 sha256 `fb9258ae0233e4f98b72e1524a37c5dbe607e3b6b062267f3a8bb1259e33a7b3`).

Per-file purpose:
- **`validators/creator_engine_validator/resource_bound_spec.py`** *(M)* - add the pure
  `large-host-30g` host-class default at `MemTotal >= 24 GiB`.
- **`validators/tests/unit/test_resource_bound_spec.py`** *(M)* - pin the 23.99/24/30 GiB
  boundaries, exact large-host caps, regression rows, and schema-shape validation.
- **`docs/contracts/runtime-policy.md`** *(M)* - document the third §4.4 host class and boundary.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* -
  rebuilt from this branch source so the wheel oracle stays green.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - re-pinned to the rebuilt app wheel.
- **`.ce/pr-path-manifest.md`** *(M)* - this carrier.

- **base:** `6118a1c` (origin/main post-#192/#194; rebased under the base-only-refresh microauth — content unchanged from the reviewed `4efccbc`).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=53d4b455df72d4ddc29e5646bf4cc75987c8f24d468210e71b36a03b8dbb62a0

```text
.ce/pr-path-manifest.md
docs/contracts/runtime-policy.md
validators/creator_engine_validator/resource_bound_spec.py
validators/tests/unit/test_resource_bound_spec.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
