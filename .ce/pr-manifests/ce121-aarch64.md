# PR path manifest - ce121-aarch64 - Linux/aarch64 public install wheelhouse

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce121-aarch64

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Operator dispatch for ce-ops#121 on 2026-06-18: add a signed aarch64 ARM
wheelhouse and accept Linux/aarch64 in the public self-serve installer. Commit
locally only; do not push, open a PR, or fabricate the `ce-root-v1` signature.

Base:
`5302520250c1510df9f8fac1d0b7268087228b4f` (`origin/main` at branch creation).

The changes:
- `v3_installer.py` and `docs/install.sh` now accept Linux x86_64/amd64 and
  Linux aarch64/arm64 only, normalize to `linux-x86_64-cp314` or
  `linux-aarch64-cp314`, and keep every other platform fail-closed.
- `docs/llms-install.md` uses platform-qualified `required_wheels` and
  `python_acquisition` entries. The content hash is updated, but the signature
  value is intentionally `value: <RESIGN-REQUIRED-ce-root-v1>`.
- The aarch64 PyYAML, rpds-py, and uv wheels are added to both the validator
  wheelhouse and Pages mirror. Pure-Python wheels remain shared.
- The validator app wheel is rebuilt from current source and both checksum
  manifests are regenerated.
- Tests cover Python planner selection, shell aarch64 acceptance and wheel
  selection, dual-arch packaging presence, mirror SHA self-consistency, and
  x86_64 installer continuity.

Per-file purpose (the closed path-set - 23 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce121-aarch64.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce121-aarch64.md`** *(A)* - this carrier.
- **`BUILD_NOTE.md`** *(A)* - build/test/signing/publish follow-up note.
- **`docs/adr/ADR-0001-v1-baseline-and-product-form.md`** *(M)* - packaging
  contract wording updated from x86-only to Linux x86_64/aarch64.
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* - regenerated mirror manifest.
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* -
  rebuilt validator app wheel mirror copy.
- **`docs/downloads/0.2.0/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl`** *(A)* -
  aarch64 PyYAML mirror wheel.
- **`docs/downloads/0.2.0/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl`** *(A)* -
  aarch64 rpds-py mirror wheel.
- **`docs/downloads/0.2.0/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl`** *(A)* -
  aarch64 uv mirror wheel.
- **`docs/governance/V1_PRODUCT_CONTRACT.md`** *(M)* - packaging contract
  wording updated from x86-only to Linux x86_64/aarch64.
- **`docs/install.sh`** *(M)* - shell platform gate, platform-aware manifest
  parsing, and arch-specific uv tarball path.
- **`docs/llms-install.md`** *(M)* - platform-aware signed manifest, new hashes,
  and re-sign-required placeholder.
- **`validators/README.md`** *(M)* - wheelhouse wording updated for dual arch and
  installer artifacts.
- **`validators/creator_engine_validator/packaging_runtime.py`** *(M)* -
  packaging contract wording updated.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - platform
  normalization, platform-filtered wheels, and platform-filtered uv acquisition.
- **`validators/tests/integration/test_install_bootstrap.py`** *(M)* - shell
  aarch64 acceptance/selection coverage and uv path assertion.
- **`validators/tests/unit/test_packaging_contract.py`** *(M)* - dual-arch
  wheelhouse and mirror coverage.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - Python planner
  aarch64 acceptance and rejection coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - regenerated validator wheelhouse
  manifest.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* -
  rebuilt validator app wheel.
- **`validators/wheelhouse/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl`** *(A)* -
  aarch64 PyYAML validator wheelhouse copy.
- **`validators/wheelhouse/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl`** *(A)* -
  aarch64 rpds-py validator wheelhouse copy.
- **`validators/wheelhouse/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl`** *(A)* -
  aarch64 uv validator wheelhouse copy.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=23

AUTHORIZED_PATHS_SHA256=9c68bc549043158a84f61510ebd7fa1806cdeac531cf5265426521a0d4448903

```text
.ce/changelog/ce121-aarch64.md
.ce/pr-manifests/ce121-aarch64.md
BUILD_NOTE.md
docs/adr/ADR-0001-v1-baseline-and-product-form.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/downloads/0.2.0/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
docs/downloads/0.2.0/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
docs/downloads/0.2.0/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
docs/governance/V1_PRODUCT_CONTRACT.md
docs/install.sh
docs/llms-install.md
validators/README.md
validators/creator_engine_validator/packaging_runtime.py
validators/creator_engine_validator/v3_installer.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_packaging_contract.py
validators/tests/unit/test_v3_installer.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
validators/wheelhouse/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
validators/wheelhouse/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
validators/wheelhouse/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
```
