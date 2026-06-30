---
slug: ce-l4-launch-hydration-fallback
date: 2026-06-30
kind: fixed
scope: validator launch runtime
issue: ce-L4
---

**Launch hydration deterministic fallback.**

- Retry Controller launch recall hydration with the deterministic default store when vllm-openai is unavailable or dimension-mismatched.
- Cover deterministic fallback and rebuild-stable keyword/graph recall invariants.
