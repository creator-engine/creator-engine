# ce-410-s10 Publish Reverify Audit

PR_PATHS_COUNT=4
PR_PATHS_SHA256=6e945d415ac4e83b755fc66090d8f593e748c5eb4731b6cfb8867a86cd97892b

```text
.ce/changelog/ce-410-s10-publish-reverify-audit.md
.ce/pr-manifests/ce-410-s10-publish-reverify-audit.md
validators/creator_engine_validator/conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon.py
```

Pre-existing checks preserved:
- Validation sandbox receipts record the daemon-owned worktree tree.
- Before publish, the landed branch tree is compared to the latest validation record tree.

Added checks:
- Publish-time landed head commit is re-derived from the repo checkout and compared to the landing result before tree identity is checked.
- Publish-time base ancestry is re-checked with `git rev-list --left-right --count`.
- Publish-time diff paths are parsed fail-closed from `git diff --name-status --find-renames` and compared to the per-PR carrier manifest.
- Checkout-local transport config is rejected for `core.hooksPath`, `credential.helper`, and `url.*.insteadOf`, including Git's lowercased `core.hookspath` and `url.*.insteadof` output.
- Allocation, validation, and publish phases emit structured audit logs without receipt nonce/signature leakage. Allocation audit keeps the existing `conveyor_allocation_audit` action and records the phase separately.
