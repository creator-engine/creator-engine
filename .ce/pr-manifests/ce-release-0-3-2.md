# PR path manifest — creator-engine/ce-ops#447 · bump 0.3.1 -> 0.3.2 + CHANGELOG + release staging

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-release-0-3-2` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** epic

AUTHORIZED_PATHS_COUNT=56

AUTHORIZED_PATHS_SHA256=98fc437be5269c68fdf30959cbb0e3322283b9774be3cbffbaeb637bac3d150e

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-415-followup-tinies.md
.ce/changelog/ce-release-0-3-2.md
.ce/pr-manifests/ce-release-0-3-2.md
.ce/release-staging/0.3.2/INSTALL_SPEC_TO_SIGN
.ce/release-staging/0.3.2/SIGNING-INSTRUCTIONS.md
.ce/release-staging/0.3.2/downloads/0.3.2/SHA256SUMS
.ce/release-staging/0.3.2/downloads/0.3.2/attrs-26.1.0-py3-none-any.whl
.ce/release-staging/0.3.2/downloads/0.3.2/creator_engine_validator-0.3.2-py3-none-any.whl
.ce/release-staging/0.3.2/downloads/0.3.2/install.sh
.ce/release-staging/0.3.2/downloads/0.3.2/jsonschema-4.26.0-py3-none-any.whl
.ce/release-staging/0.3.2/downloads/0.3.2/jsonschema_specifications-2025.9.1-py3-none-any.whl
.ce/release-staging/0.3.2/downloads/0.3.2/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
.ce/release-staging/0.3.2/downloads/0.3.2/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
.ce/release-staging/0.3.2/downloads/0.3.2/referencing-0.37.0-py3-none-any.whl
.ce/release-staging/0.3.2/downloads/0.3.2/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
.ce/release-staging/0.3.2/downloads/0.3.2/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
.ce/release-staging/0.3.2/downloads/0.3.2/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
.ce/release-staging/0.3.2/downloads/0.3.2/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
.ce/release-staging/0.3.2/install.sh
.ce/release-staging/0.3.2/keys/ce-root-v1
.ce/release-staging/0.3.2/llms-install.canonical
.ce/release-staging/0.3.2/llms-install.md
.ce/release-staging/0.3.2/release-stage-manifest.yml
.ce/release-staging/0.3.2/schemas/install-answers.schema.yaml
CHANGELOG.md
deploy/daemons/Dockerfile
deploy/daemons/run-daemon-container.sh
deploy/queue-daemon/RELOCATION.md
deploy/runtime-image/Dockerfile
deploy/seat-image/Dockerfile
docs/downloads/0.3.2/SHA256SUMS
docs/downloads/0.3.2/attrs-26.1.0-py3-none-any.whl
docs/downloads/0.3.2/creator_engine_validator-0.3.2-py3-none-any.whl
docs/downloads/0.3.2/install.sh
docs/downloads/0.3.2/jsonschema-4.26.0-py3-none-any.whl
docs/downloads/0.3.2/jsonschema_specifications-2025.9.1-py3-none-any.whl
docs/downloads/0.3.2/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
docs/downloads/0.3.2/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
docs/downloads/0.3.2/referencing-0.37.0-py3-none-any.whl
docs/downloads/0.3.2/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
docs/downloads/0.3.2/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/downloads/0.3.2/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
docs/downloads/0.3.2/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/llms-install.md
docs/schemas/install-answers.schema.yaml
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/schemas/install-answers.schema.yaml
validators/creator_engine_validator/version.py
validators/pyproject.toml
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_surfaces_manifest.py
validators/tests/unit/test_v3_cli.py
```
