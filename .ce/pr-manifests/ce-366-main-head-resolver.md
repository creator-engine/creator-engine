# PR path manifest — ce-ops#366/L1.a · Verified main HEAD artifact resolver and clean install

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-366-main-head-resolver` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=5b77030581a722453bd8e6ca7192053a951290ff3fb807d6a0a3554be778d503

```text
.ce/changelog/ce-366-main-head-resolver.md
.ce/pr-manifests/ce-366-main-head-resolver.md
.ce/reference/cli.generated.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/main_head_install.py
validators/tests/unit/test_egress_self_review_broker.py
validators/tests/unit/test_main_head_install.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
