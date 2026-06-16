---
slug: ce80-republish-post238
date: 2026-06-16
kind: fixed
scope: install / downloads mirror
issue: ce-ops#80
---

**Republish the 0.2.0 download mirror to match main's post-#239/#238 validator wheel.**

The in-repo 0.2.0 validator wheel in `validators/wheelhouse/` was rebuilt after
the post-#239/#238 changes, while the published Pages mirror
(`docs/downloads/0.2.0/`) and signed agent-native install spec still referenced
the previous post-#233 wheel. This republishes the frozen 0.2.0 release artifact
in place, keeping the package version at `0.2.0` while making fresh installs use
main's current validator wheel.

- Published wheel synced byte-identical to the in-repo wheelhouse wheel
  (`3554a293...`, 696246 bytes).
- Re-pinned `docs/downloads/0.2.0/SHA256SUMS` (CE wheel line only; dependency
  wheels and the `install.sh` entry are byte-unchanged).
- Updated and re-signed `docs/llms-install.md` (`sha256s_sha256`
  `e2c18785...`, app-wheel `sha256` `3554a293...`, `content_sha256`
  `ab3bdcd9...`) with the offline `ce-root-v1` root key under namespace
  `ce-spec-v1`.

No source/behaviour change - packaging surface only. Internal self-consistency
of the frozen mirror is preserved.
