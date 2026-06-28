# PR path manifest — ce-ops#315 · publish signed 0.3.0 release (ce-root-v1)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref release-0-3-0-publish` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=20

AUTHORIZED_PATHS_SHA256=58d30abd0ec9e2a3d0c70005be1b546d484ee848646ae5bce9ea2da781e511f8

```text
.ce/changelog/release-0-3-0-publish.md
.ce/pr-manifests/release-0-3-0-publish.md
docs/downloads/0.3.0/SHA256SUMS
docs/downloads/0.3.0/attrs-26.1.0-py3-none-any.whl
docs/downloads/0.3.0/creator_engine_validator-0.3.0-py3-none-any.whl
docs/downloads/0.3.0/install.sh
docs/downloads/0.3.0/jsonschema-4.26.0-py3-none-any.whl
docs/downloads/0.3.0/jsonschema_specifications-2025.9.1-py3-none-any.whl
docs/downloads/0.3.0/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
docs/downloads/0.3.0/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
docs/downloads/0.3.0/referencing-0.37.0-py3-none-any.whl
docs/downloads/0.3.0/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
docs/downloads/0.3.0/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/downloads/0.3.0/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
docs/downloads/0.3.0/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/llms-install.md
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_v3_installer.py
```
