---
slug: ce-m2-spawn-provider-integration
date: 2026-07-12
kind: added
scope: forge
issue: M2
---

**Governed review-acting spawn provider — sequenced integration.**

- Adds the default-OFF ce review-spawn-provider forwarding seam and reports explicit policy without launching a reviewer.
- Folds all M2 provider terminal outcomes before the adapter can append them, preserving no-duplicate handling for UNCERTAIN_COMMENT.
- Adds tailored structural coverage for the oneshot systemd unit without imposing daemon restart invariants.
