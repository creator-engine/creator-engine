---
slug: ce-466-c5-adapter-mixed-uid
date: 2026-07-06
kind: fixed
scope: deploy/daemons
issue: ce-ops#466
---

**Fix daemon container adapter reruns over production-owned state.**

- Made Docker host prep tolerate a pre-owned `10001:10001`/`0700` state root by deferring child directory creation to the container user when the invoking host uid cannot traverse the state root.
- Added a mixed-uid host-prep probe to the daemon container stateful smoke and focused unit coverage for the pre-fix permission-denied failure mode.
- Switched adapter output capture to per-attempt log files with a latest symlink, and updated the default daemon runtime image name with override coverage.
