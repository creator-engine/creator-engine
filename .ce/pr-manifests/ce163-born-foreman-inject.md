# PR path manifest - ce163-born-foreman-inject

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce163-born-foreman-inject
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified scope:
ce-ops#163 REQ-1 only - born-a-foreman launcher injection. This PR injects the
foreman charter and merged worker-spawn capability into the shared launch
bootstrap material and adds regression coverage for representative harness
paths. It does not implement REQ-3 hard-deny behavior.

Work class:
Story. This changes one shared launch bootstrap projection and its focused
regression coverage, plus required PR governance carriers.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=b14f6dd2315db7e5f6194bbfde9e24b49f07f3ed46b7ed9fd62dabaa9887cfe6

```text
.ce/changelog/ce163-born-foreman-inject.md
.ce/pr-manifests/ce163-born-foreman-inject.md
validators/creator_engine_validator/brain_bootstrap.py
validators/tests/unit/test_brain_bootstrap.py
validators/tests/unit/test_launch_runtime.py
```
