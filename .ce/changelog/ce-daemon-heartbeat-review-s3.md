---
slug: ce-daemon-heartbeat-review-s3
date: 2026-07-11
kind: added
scope: review-pickup daemon liveness
issue: none
---

**feat(daemons): review-pickup heartbeat adoption (S3).**

- Adopt the passive daemon-heartbeat contract in review pickup with a user-state latest record.
- Emit startup, pass lifecycle, and bounded wait-seam liveness records without changing review routing behavior.
