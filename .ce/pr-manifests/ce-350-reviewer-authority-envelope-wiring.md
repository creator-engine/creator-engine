# PR path manifest — ce-ops#350 · Reviewer authority envelope wiring

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-350-reviewer-authority-envelope-wiring` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=e1f9bcb3f9191f42311cf82ee4e505a044420f3e4b09ab3d0de46f6cdb9cfb10

```text
.ce/changelog/ce-350-reviewer-authority-envelope-wiring.md
.ce/pr-manifests/ce-350-reviewer-authority-envelope-wiring.md
tools/egress-broker/ce_egress_self_review_broker.py
validators/tests/integration/test_claude_hook_pack_pretooluse.py
validators/tests/unit/test_egress_self_review_broker.py
```
