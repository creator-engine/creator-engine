# PR path manifest - ce-followups2-20260708

This per-PR carrier (`.ce/pr-manifests/ce-followups2-20260708.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-followups2-20260708` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=804e050ddba135cd3ae3fccb3971ddfe92b1c2bd80262ccc03ebd85cf36ed132

```text
.ce/changelog/ce-followups2-20260708.md
.ce/pr-manifests/ce-followups2-20260708.md
deploy/dgx-runsc/build-image.sh
deploy/singleton-redeploy/redeploy-singleton.sh
deploy/singleton-redeploy/smoke-singleton-redeploy.sh
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_surface_build_wiring.py
```
