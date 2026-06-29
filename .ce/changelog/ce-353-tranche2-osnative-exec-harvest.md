---
slug: ce-353-tranche2-osnative-exec-harvest
date: 2026-06-29
kind: feature
scope: runner os-native backend
issue: ce-ops#353
---

**Tranche-2 OS-native sandbox execution fail-closed.**

- Keep the user-elected os-native backend fail-closed after the OQ-1 Option A primitive probe when no concrete deny-by-default host-proxy enforcement contract and restrictive seccomp policy are available.
- Refuse missing primitives and the unproven execution contract before any runner/proxy/bwrap side effect rather than falling back to unsandboxed or weaker execution.
- Add tests proving probe-pass still refuses without the enforcement contract, missing primitives refuse before side effects, and unknown handles have no fallback run path.
