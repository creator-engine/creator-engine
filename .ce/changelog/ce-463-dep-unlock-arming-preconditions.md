---
slug: ce-463-dep-unlock-arming-preconditions
date: 2026-07-06
kind: changed
scope: dependency unlock validator
issue: ce-ops#463
---

**Arm dependency-unlock LIVE preconditions.**

- Rechecked dependency-unlock LIVE apply targets against freshly read candidate state and blocker resolutions before removing dependency hold labels.
- Added fail-closed evidence for missing GitHub credentials and missing `gh` execution paths.
- Removed the unused `workflow_dispatch.apply` input as the smaller fix; dispatch remains a no-PR-context audit-only path and SHADOW remains the hard default.
