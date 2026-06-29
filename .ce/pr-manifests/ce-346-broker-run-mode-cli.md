# PR path manifest — ce-ops#346 · Broker run-mode CLI

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-346-broker-run-mode-cli` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=83a98d6540f2ac4e926850cdf5422faf5ae575451c28d06ad5cb8636b5c2de2f

```text
.ce/changelog/ce-346-broker-run-mode-cli.md
.ce/pr-manifests/ce-346-broker-run-mode-cli.md
deploy/systemd/ce-egress-self-review.service
tools/egress-broker/ce_egress_self_review_broker.py
validators/tests/unit/test_egress_self_review_broker.py
```
