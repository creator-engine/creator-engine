---
slug: ce-544-seat-image-signing-strip
date: 2026-07-12
kind: changed
scope: DGX contained-seat Git signing defaults and static Dockerfile coverage
issue: ce-ops#544
---

**Disable inherited Git signing in the DGX seat image.**

Set the DGX seat image's system Git configuration to disable commit signing for
all container users and remove stale signing-key and signing-format selectors.

The image must be rebuilt before this source-only change takes effect. Roll it
out through the 0.144.1 pin canon, one seat and the canary first.
