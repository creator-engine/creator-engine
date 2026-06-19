# PR path manifest - ce121-134-aarch64-wheelhouse - aarch64 dev wheelhouse

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce121-134-aarch64-wheelhouse

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified scope:
Controller relay on 2026-06-19: prepare ce-ops#121 publish/sign/install-verify
follow-through for DGX/Grace by folding ce-ops#134 aarch64 dev wheels. Commit
must be held until PR #271 merge confirmation because downstream publishing may
share wheelhouse checksum context; do not push.

Base:
`1d01e097fc44004324fbc5665667eca6cca160ab` (`origin/main` after PR #271 merge).

The changes:
- Runtime wheelhouse scope is unchanged: `validators/wheelhouse/` already has
  Linux/aarch64 cp314 wheels for the only compiled runtime dependencies,
  `PyYAML` and `rpds-py`, plus the aarch64 `uv` installer artifact from
  ce-ops#121. This branch does not touch `validators/wheelhouse/SHA256SUMS`,
  served install docs, public downloads, or the runtime app wheel.
- `validators/wheelhouse-dev/` gains Linux/aarch64 cp314 manylinux wheels for
  the seven native dev/test packages missing from the offline DGX/Grace install:
  `aiohttp`, `frozenlist`, `MarkupSafe`, `multidict`, `propcache`,
  `watchfiles`, and `yarl`.
- `test_packaging_contract.py` now asserts the dev wheelhouse has no stale
  non-cp314 ABI wheels and contains both Linux x86_64 and Linux aarch64 cp314
  manylinux wheels for those seven native dev/test packages.

Per-file purpose (the closed path-set - 10 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce121-134-aarch64-wheelhouse.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce121-134-aarch64-wheelhouse.md`** *(A)* - this carrier.
- **`validators/tests/unit/test_packaging_contract.py`** *(M)* - dev wheelhouse
  cp314 dual-arch packaging-contract tests.
- **`validators/wheelhouse-dev/aiohttp-3.14.1-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl`** *(A)* -
  aarch64 aiohttp dev/test wheel.
- **`validators/wheelhouse-dev/frozenlist-1.8.0-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl`** *(A)* -
  aarch64 frozenlist dev/test wheel.
- **`validators/wheelhouse-dev/markupsafe-3.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl`** *(A)* -
  aarch64 MarkupSafe dev/test wheel.
- **`validators/wheelhouse-dev/multidict-6.7.1-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl`** *(A)* -
  aarch64 multidict dev/test wheel.
- **`validators/wheelhouse-dev/propcache-0.5.2-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl`** *(A)* -
  aarch64 propcache dev/test wheel.
- **`validators/wheelhouse-dev/watchfiles-1.2.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl`** *(A)* -
  aarch64 watchfiles dev/test wheel.
- **`validators/wheelhouse-dev/yarl-1.24.2-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl`** *(A)* -
  aarch64 yarl dev/test wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=622a711d2010ca26a088b6b7d58069d28dd92aacfd5a80a98df54192b29ff027

```text
.ce/changelog/ce121-134-aarch64-wheelhouse.md
.ce/pr-manifests/ce121-134-aarch64-wheelhouse.md
validators/tests/unit/test_packaging_contract.py
validators/wheelhouse-dev/aiohttp-3.14.1-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
validators/wheelhouse-dev/frozenlist-1.8.0-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
validators/wheelhouse-dev/markupsafe-3.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
validators/wheelhouse-dev/multidict-6.7.1-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
validators/wheelhouse-dev/propcache-0.5.2-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
validators/wheelhouse-dev/watchfiles-1.2.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
validators/wheelhouse-dev/yarl-1.24.2-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
```
