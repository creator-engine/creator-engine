# PR path manifest — ce-ops#315 · bump 0.2.0 to 0.3.0 + refresh wheelhouse for the clean-install cut

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref release-0-3-0-staging` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=cb62a92810303ebb9f39927ff70cfbf485090f453cd7fb6b60783865ea7626d2

```text
.ce/changelog/release-0-3-0-staging.md
.ce/pr-manifests/release-0-3-0-staging.md
CHANGELOG.md
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/version.py
validators/pyproject.toml
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```
