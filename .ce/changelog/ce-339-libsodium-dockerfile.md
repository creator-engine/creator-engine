---
slug: ce-339-libsodium-dockerfile
date: 2026-07-02
kind: changed
scope: deploy/dgx-runsc Dockerfile
issue: ce-ops#339
---

**Add libsodium runtime package to DGX seat image.**

- Adds Debian bookworm runtime package `libsodium23` to the DGX seat image runtime apt package list.
- Uses the runtime library package rather than `libsodium-dev` because no headers are needed.
- CE-TEST-COUPLING-EXEMPT: Dockerfile-only infrastructure change; no testable application logic changed.
- Follow-on controller step: rebuild the DGX seat image and relaunch dev-4 after this Dockerfile change lands.
- **Declared work class:** XS
