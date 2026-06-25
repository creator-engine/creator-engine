---
slug: ce191-n1-install-dep-soft-inventory
date: 2026-06-25
kind: added
scope: install dependency inventory
issue: ce-ops#191
---

**install dependency soft-inventory + re-source profile (N1).**

- Surface missing git/curl as WARN rows in `cev3 onboard --inventory` and emit a post-install re-source line so `cev3`/`ce` land on PATH.
