# PR path manifest — ce-ops#341 · Parameterize autoreview run mode

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-341-autoreview-runmode` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=c61ae7bb5cce408104ff928f2a67e83d511212ef226cca4503dec15549294a69

```text
.ce/changelog/ce-341-autoreview-runmode.md
.ce/pr-manifests/ce-341-autoreview-runmode.md
tools/egress-broker/ce_egress_self_review_broker.py
validators/tests/unit/test_egress_self_review_broker.py
```
