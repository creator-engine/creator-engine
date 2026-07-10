# PR path manifest — preflight environment propagation

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=4786b669aa5d46e60519cd76037f9ea098a2eb0c22d42654ee3e4ab44ca0dc71

```text
.ce/changelog/ce-f1s2-preflight-env-propagation.md
.ce/pr-manifests/ce-f1s2-preflight-env-propagation.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_pr_preflight_env.py
```
