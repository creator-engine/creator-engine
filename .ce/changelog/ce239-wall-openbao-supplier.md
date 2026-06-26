---
slug: ce239-wall-openbao-supplier
date: 2026-07-10
kind: changed
scope: review pickup OpenBao supplier
issue: ce-ops#239
---

Record the Round 2 approval-wall-adjacent OpenBao supplier gate for
controller review-pickup token handling.

review-pickup can source the ce-dev-2 GitHub token through the generic
SecretIdentity/OpenBao supplier path instead of resolving one static token for
the daemon lifetime.

- Rebased the parked branch onto `origin/main` at
  `6ce9527e1a9da3c578266db42b79625fe86392cd`.
- Verified queue-daemon startup lease symbols remain present after rebase.
- Verified `origin/main` already carries the review-pickup CLI secret flag
  family, `_review_pickup_token_supplier_from_args()`, and per-pass
  `run_review_pickup_loop()` token supplier/runner refresh with bounded retry.
- Preserved the existing static review-pickup token resolution path when the
  pickup token secret flag family is unconfigured.
- Normalized the review-pickup default OpenBao path constant to the literal
  `forge/ce-dev-2/gh-token`.
- Left deployment files, approval-wall runtime behavior, signed artifacts, and
  queue-daemon lease code untouched.
