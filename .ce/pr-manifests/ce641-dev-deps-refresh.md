# PR path manifest — CE641 development dependency refresh

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI verifies that the `base..HEAD` diff equals
exactly this set; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=4ba8e17040bd0b2cc1c6e9b7bf0251d8d84e2926f7288c4737c9cb859e0d9fe8

```text
.ce/changelog/ce641-dev-deps-refresh.md
.ce/pr-manifests/ce641-dev-deps-refresh.md
validators/pyproject.toml
validators/requirements-dev.txt
validators/requirements.txt
validators/creator_engine_validator/packaging_runtime.py
validators/tests/unit/test_packaging_contract.py
validators/uv.lock
validators/wheelhouse-dev/setuptools-83.0.0-py3-none-any.whl
```
