# PR path manifest - ce173-null-probe-prior-app

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce173-null-probe-prior-app
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** story

Scope:
ce-ops#173 follow-up to PR #334. The slice fixes reinstall convergence so a
null live GitHub probe cannot erase the prior App installation ID before the
GitHub leg is planned.

Per-file purpose:
- **`.ce/changelog/ce173-null-probe-prior-app.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce173-null-probe-prior-app.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - filters null live probe values before prior-state probe merge.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - regression for omitted answers installation ID plus null live probe.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=ea288c4b76a04bd60f9e30665bd23a27ec11efccc22e87bf786b71828cc207ee

```text
.ce/changelog/ce173-null-probe-prior-app.md
.ce/pr-manifests/ce173-null-probe-prior-app.md
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_v3_installer.py
```
