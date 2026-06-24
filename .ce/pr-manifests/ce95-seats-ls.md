# PR path manifest — ce-ops#95 · ce seats ls — fleet seat liveness listing

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce95-seats-ls` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=2d3a8ba78cef49c3e7da768d0d028e544c690585f2dd9eb2fe7f6b3888eaf396

```text
.ce/changelog/ce95-seats-ls.md
.ce/pr-manifests/ce95-seats-ls.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/seats_status.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_seats_status.py
validators/tests/unit/test_version_boundary.py
```
