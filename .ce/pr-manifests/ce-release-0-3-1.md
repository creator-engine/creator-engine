# PR path manifest — ce-ops#035 · bump 0.3.0 → 0.3.1 + publish release mirror (spec-kit retirement)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-release-0-3-1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=21

AUTHORIZED_PATHS_SHA256=7e7ad0269b92d63de4ac4e93a546b5e57c2f8f50bcc2971c0dcc0f474fc78b20

```text
.ce/changelog/ce-release-0-3-1.md
.ce/pr-manifests/ce-release-0-3-1.md
CHANGELOG.md
docs/downloads/0.3.1/SHA256SUMS
docs/downloads/0.3.1/attrs-26.1.0-py3-none-any.whl
docs/downloads/0.3.1/creator_engine_validator-0.3.1-py3-none-any.whl
docs/downloads/0.3.1/install.sh
docs/downloads/0.3.1/jsonschema-4.26.0-py3-none-any.whl
docs/downloads/0.3.1/jsonschema_specifications-2025.9.1-py3-none-any.whl
docs/downloads/0.3.1/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
docs/downloads/0.3.1/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
docs/downloads/0.3.1/referencing-0.37.0-py3-none-any.whl
docs/downloads/0.3.1/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
docs/downloads/0.3.1/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/downloads/0.3.1/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
docs/downloads/0.3.1/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/llms-install.md
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/version.py
validators/pyproject.toml
```

- **Declared work class:** epic
