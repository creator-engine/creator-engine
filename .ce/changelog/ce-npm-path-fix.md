---
slug: ce-npm-path-fix
date: 2026-07-05
kind: fixed
scope: validator
issue: live-canary
---

**Fix npm profile PATH discovery.**

- Replaced dynamic npm global-bin discovery with a stable prefix-derived path.
- Added a directory-exists guard to the shared PATH prepend helper so missing or garbage paths are ignored.
- Added regression coverage for rewriting the managed block and ignoring stdout error text from npm stubs.
- Noted that `docs/install.sh` and `docs/downloads` mirrors embed a duplicated pre-fix copy of this block; those signed release surfaces are out of scope here and the fix rides the 0.3.2 re-sign.
