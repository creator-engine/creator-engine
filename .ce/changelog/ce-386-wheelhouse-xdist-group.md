---
slug: ce-386-wheelhouse-xdist-group
date: 2026-07-02
kind: fixed
scope: validator tests
issue: ce-ops#386
---

**Serialize wheelhouse built-surface tests under xdist.**

- Added the wheel-build xdist group to the built-surface wheelhouse tests and the packaging contract wheel parity test so shared source-tree wheel builds serialize under loadgroup.
