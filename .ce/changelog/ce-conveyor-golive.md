---
slug: ce-conveyor-golive
date: 2026-07-01
kind: feat
scope: conveyor
issue: ce-conveyor
---

**Conveyor go-live daemon core.**

- Added a disarmed-by-default conveyor daemon that plans completed-branch harvests without mutation.
- Added armed harvest-to-land-to-push-to-PR execution through injected runners, with append-only mutation ledger records for push and PR-open attempts.
