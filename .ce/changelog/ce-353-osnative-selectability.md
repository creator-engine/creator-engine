---
slug: ce-353-osnative-selectability
date: 2026-06-29
kind: fixed
scope: runner os-native backend selectability
issue: ce-ops#353
---

**OS-native selectability fail-closed fix.**

- Make os-native user-electable with an OQ-1 Option A capability probe and fail-closed refusal when Linux primitives are missing.
- Keep gvisor-proxy as the default backend and leave full bwrap/Landlock/seccomp/proxy command execution as a follow-on.
