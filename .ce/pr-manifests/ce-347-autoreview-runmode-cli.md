# PR path manifest - ce-ops#347 - AutoReview run-mode CLI wiring

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-347-autoreview-runmode-cli` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** S

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=71ac93fc62cbf937b80f46216008e617825240ea142696ce45c2cea45e1c92d3

```text
.ce/changelog/ce-347-autoreview-runmode-cli.md
.ce/pr-manifests/ce-347-autoreview-runmode-cli.md
validators/tests/unit/test_egress_self_review_broker.py
```
