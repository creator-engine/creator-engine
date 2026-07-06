# PR path manifest — creator-engine/ce-ops#469 · bump 0.3.2 -> 0.3.3 + CHANGELOG + release staging

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-release-0-3-3` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** epic

AUTHORIZED_PATHS_COUNT=47

AUTHORIZED_PATHS_SHA256=2e95fba8114006fc8359e1c92790f7469b9b1f1eff24c7e78812361d2dd924dd

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-release-0-3-3.md
.ce/pr-manifests/ce-release-0-3-3.md
.ce/release-staging/0.3.3/INSTALL_SPEC_TO_SIGN
.ce/release-staging/0.3.3/SIGNING-INSTRUCTIONS.md
.ce/release-staging/0.3.3/downloads/0.3.3/SHA256SUMS
.ce/release-staging/0.3.3/downloads/0.3.3/attrs-26.1.0-py3-none-any.whl
.ce/release-staging/0.3.3/downloads/0.3.3/creator_engine_validator-0.3.3-py3-none-any.whl
.ce/release-staging/0.3.3/downloads/0.3.3/install.sh
.ce/release-staging/0.3.3/downloads/0.3.3/jsonschema-4.26.0-py3-none-any.whl
.ce/release-staging/0.3.3/downloads/0.3.3/jsonschema_specifications-2025.9.1-py3-none-any.whl
.ce/release-staging/0.3.3/downloads/0.3.3/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
.ce/release-staging/0.3.3/downloads/0.3.3/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
.ce/release-staging/0.3.3/downloads/0.3.3/referencing-0.37.0-py3-none-any.whl
.ce/release-staging/0.3.3/downloads/0.3.3/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
.ce/release-staging/0.3.3/downloads/0.3.3/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
.ce/release-staging/0.3.3/downloads/0.3.3/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
.ce/release-staging/0.3.3/downloads/0.3.3/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
.ce/release-staging/0.3.3/install.sh
.ce/release-staging/0.3.3/keys/ce-root-v1
.ce/release-staging/0.3.3/llms-install.canonical
.ce/release-staging/0.3.3/llms-install.md
.ce/release-staging/0.3.3/release-stage-manifest.yml
.ce/release-staging/0.3.3/schemas/install-answers.schema.yaml
.gitignore
CHANGELOG.md
docs/downloads/0.3.3/SHA256SUMS
docs/downloads/0.3.3/attrs-26.1.0-py3-none-any.whl
docs/downloads/0.3.3/creator_engine_validator-0.3.3-py3-none-any.whl
docs/downloads/0.3.3/install.sh
docs/downloads/0.3.3/jsonschema-4.26.0-py3-none-any.whl
docs/downloads/0.3.3/jsonschema_specifications-2025.9.1-py3-none-any.whl
docs/downloads/0.3.3/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
docs/downloads/0.3.3/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
docs/downloads/0.3.3/referencing-0.37.0-py3-none-any.whl
docs/downloads/0.3.3/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
docs/downloads/0.3.3/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/downloads/0.3.3/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
docs/downloads/0.3.3/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/llms-install.md
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/version.py
validators/pyproject.toml
validators/tests/integration/test_release_finalize_integration.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_wheel_bake.py
```
