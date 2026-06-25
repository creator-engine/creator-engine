---
slug: ce242-live-self-push-pr
date: 2026-06-25
kind: feat
scope: ce-ops
issue: ce-ops#242
---

**live contained-seat self-push broker.**

Host-side Unix-socket self-push broker that mints + injects a scoped GitHub token outside the sandbox so a contained seat pushes its own branch; fail-closed without a valid injected cred; seat never holds a raw token. Includes the host-seam daemon. (ce-ops#242)
