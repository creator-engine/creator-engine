# PR path manifest — ce-ops#240 · Contained controller credential seam guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce240-contained-controller-scaffold` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=de5c4ae8886c5e59287d8c1cd0416042d94d66a430c0bce57d2d278d1031254c

```text
.ce/changelog/ce240-contained-controller-scaffold.md
.ce/pr-manifests/ce240-contained-controller-scaffold.md
deploy/dgx-controller-runsc/DESIGN.md
deploy/dgx-controller-runsc/Dockerfile
deploy/dgx-controller-runsc/README.md
deploy/dgx-controller-runsc/ce-controller-gh-guard.sh
deploy/dgx-controller-runsc/test-controller-dry-run.sh
validators/tests/unit/test_dgx_controller_runsc.py
```
