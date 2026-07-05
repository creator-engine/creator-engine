# PR path manifest — ce-ops#424 · Egress broker per-seat repo scoping

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-424-broker-repo-scoping` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=db9a845ea9c07c1f3044f30f5133e6bde5d54fd44d548fdf1dabf62181986bf8

```text
.ce/changelog/ce-424-broker-repo-scoping.md
.ce/pr-manifests/ce-424-broker-repo-scoping.md
tools/egress-broker/apps.example.json
tools/egress-broker/ce_egress_self_review_broker.py
tools/egress-broker/egress_broker/config.py
tools/egress-broker/egress_broker/orchestrator.py
validators/tests/unit/test_egress_config.py
validators/tests/unit/test_egress_orchestrator.py
validators/tests/unit/test_egress_self_review_broker.py
```
