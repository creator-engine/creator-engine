---
slug: ce-republish-020-with71
date: 2026-06-14
kind: fixed
scope: install / downloads mirror
issue: ce-ops#71
---

**Republish the 0.2.0 download mirror with the user-level os-native `--apply`.**

The published wheel at `docs/downloads/0.2.0/` predated ce-ops#71 (#226), so a
fresh `curl … | install.sh` still got the OLD gVisor-only `--apply`. This
republishes — rebuild-in-place at the SAME package version `0.2.0`
(Operator-ratified) — `creator_engine_validator-0.2.0-py3-none-any.whl` from the
merged-main source (`106792df`), so a clean install now provisions the
governance-only os-native posture by default.

- Rebuilt the published 0.2.0 app wheel from source (content-identical to the
  CI-verified in-repo wheel; new container sha `539be5fa…`).
- Re-pinned `docs/downloads/0.2.0/SHA256SUMS` (CE wheel line only; the 6
  dependency wheels + the `install.sh` entry are byte-unchanged).
- Updated and **re-signed** the install trust-root manifest `docs/llms-install.md`
  (`sha256s_sha256` + the app-wheel `sha256`); `install.sh` itself is unchanged
  (it reads the hash from `SHA256SUMS` at runtime, not hardcoded).

No source/behaviour change — packaging-surface only. Note: the `.ce/changelog/`
fragment convention (ce-ops#65) is not yet merged to main; this fragment follows
the `CHANGELOG.md` release-surface style pending the #65 schema.
