---
slug: ce247-mint-on-approval-pr
date: 2026-06-25
kind: feat
scope: ce-ops
issue: ce-ops#247
---

**mint-on-approval: auto-mint approval-capability marker on trusted approval.**

Auto-mint a valid approval-capability marker (OpenBao-sourced wall secret) when a trusted approver approves, so arming the wall does not fail-closed on legit approvals. Fail-closed if backend unreachable; trusted-approver-only (never contained seats); idempotent per (PR,head,approver); round-trip tests. Unblocks the wall flip. (ce-ops#247)
