# PR path manifest — ce-ops#240 · Contained controller runsc C1 scaffold

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce240-contained-controller-c1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=483a266b8bc9347cc3d839b07ae24db9088316bc400e46cc468f4682610113b0

```text
.ce/changelog/ce240-contained-controller-c1.md
.ce/pr-manifests/ce240-contained-controller-c1.md
deploy/dgx-controller-runsc/DESIGN.md
deploy/dgx-controller-runsc/Dockerfile
deploy/dgx-controller-runsc/README.md
deploy/dgx-controller-runsc/run-controller-runsc.sh
deploy/dgx-controller-runsc/test-controller-dry-run.sh
validators/tests/unit/test_dgx_controller_runsc.py
```
