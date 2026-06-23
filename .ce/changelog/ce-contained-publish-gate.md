---
slug: ce-contained-publish-gate
date: 2026-06-23
kind: added
scope: contained seat publish gate
work_class: story
---

Adds `ce publish-branch`, a host-side publish chokepoint for contained seats'
commit-only branches. The gate verifies branch attribution, refuses force and
non-fast-forward publishes, pushes through host git credentials, and records
successful publishes to the Side-Effect Ledger.
