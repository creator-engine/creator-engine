# PR path manifest —  · release: 0.3.5 (train 1)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-release-0-3-5` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** epic

AUTHORIZED_PATHS_COUNT=58

AUTHORIZED_PATHS_SHA256=325c83bc217562db70482c94136a5903130d69e76cf1e2a4769cc2f78370f2b3

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-release-0-3-5.md
.ce/pr-manifests/ce-release-0-3-5.md
.ce/release-staging/0.3.5/INSTALL_SPEC_TO_SIGN
.ce/release-staging/0.3.5/INSTALL_SPEC_TO_SIGN.sig
.ce/release-staging/0.3.5/RELEASE_NOTES.md
.ce/release-staging/0.3.5/SIGNING-INSTRUCTIONS.md
.ce/release-staging/0.3.5/downloads/0.3.5/SHA256SUMS
.ce/release-staging/0.3.5/downloads/0.3.5/attrs-26.1.0-py3-none-any.whl
.ce/release-staging/0.3.5/downloads/0.3.5/creator_engine_validator-0.3.5-py3-none-any.whl
.ce/release-staging/0.3.5/downloads/0.3.5/install.sh
.ce/release-staging/0.3.5/downloads/0.3.5/jsonschema-4.26.0-py3-none-any.whl
.ce/release-staging/0.3.5/downloads/0.3.5/jsonschema_specifications-2025.9.1-py3-none-any.whl
.ce/release-staging/0.3.5/downloads/0.3.5/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
.ce/release-staging/0.3.5/downloads/0.3.5/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
.ce/release-staging/0.3.5/downloads/0.3.5/referencing-0.37.0-py3-none-any.whl
.ce/release-staging/0.3.5/downloads/0.3.5/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
.ce/release-staging/0.3.5/downloads/0.3.5/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
.ce/release-staging/0.3.5/downloads/0.3.5/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
.ce/release-staging/0.3.5/downloads/0.3.5/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
.ce/release-staging/0.3.5/install.sh
.ce/release-staging/0.3.5/keys/ce-root-v1
.ce/release-staging/0.3.5/llms-install.canonical
.ce/release-staging/0.3.5/llms-install.md
.ce/release-staging/0.3.5/release-stage-manifest.yml
.ce/release-staging/0.3.5/schemas/install-answers.schema.yaml
CHANGELOG.md
README.md
deploy/daemons/Dockerfile
deploy/daemons/README.md
deploy/daemons/run-daemon-container.sh
deploy/oci/README.md
deploy/oci/build-image.sh
deploy/runtime-image/Dockerfile
deploy/seat-image/Dockerfile
docs/downloads/0.3.5/SHA256SUMS
docs/downloads/0.3.5/attrs-26.1.0-py3-none-any.whl
docs/downloads/0.3.5/creator_engine_validator-0.3.5-py3-none-any.whl
docs/downloads/0.3.5/install.sh
docs/downloads/0.3.5/jsonschema-4.26.0-py3-none-any.whl
docs/downloads/0.3.5/jsonschema_specifications-2025.9.1-py3-none-any.whl
docs/downloads/0.3.5/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
docs/downloads/0.3.5/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
docs/downloads/0.3.5/referencing-0.37.0-py3-none-any.whl
docs/downloads/0.3.5/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
docs/downloads/0.3.5/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/downloads/0.3.5/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
docs/downloads/0.3.5/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/llms-install.md
docs/llms.txt
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/version.py
validators/pyproject.toml
validators/tests/integration/test_release_finalize_integration.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_daemon_lease.py
validators/tests/unit/test_signed_artifact_pins.py
```
