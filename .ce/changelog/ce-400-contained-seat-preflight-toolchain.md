---
slug: ce-400-contained-seat-preflight-toolchain
date: 2026-07-17
kind: fix
scope: deploy
issue: ce-ops#400
---

**Contained seat images expose the offline CI-parity preflight toolchain.**

- Add SSH, sodium, validator dev-test closure, and explicit toolchain assertions across contained image recipes.
- Stage both validator requirements files for OCI builds and assert inherited runtime tools in the seat layer.
