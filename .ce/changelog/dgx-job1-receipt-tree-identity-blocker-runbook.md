---
slug: dgx-job1-receipt-tree-identity-blocker-runbook
date: 2026-07-20
kind: docs
scope: worker-host readiness
work_class: XS
---

**Document the DGX validation receipt tree-identity refusal and safe recovery.**

- Explain why a dirty mounted tree must block receipt minting and why dirty-tree
  bypasses or blind cleanup are unsafe.
- Specify the seat-local evidence and procedure required to classify and resolve
  the refusal.
- Record the present host-loss consequence while preserving the case for a
  narrowly scoped live-runtime canary.
