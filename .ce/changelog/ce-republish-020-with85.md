---
slug: ce-republish-020-with85
date: 2026-06-15
kind: fixed
scope: install / downloads mirror
issue: ce-ops#48
---

**Republish the 0.2.0 download mirror to match main's post-#85 validator wheel.**

PR #229 (ce-ops#85, plain-join `onboard --apply`) rebuilt the in-repo 0.2.0
validator wheel (`validators/wheelhouse/`, new container sha `588eeca0…`), so the
published Pages mirror (`docs/downloads/0.2.0/`) and the signed install spec
referenced the OLD wheel (`539be5fa…`). A fresh `curl … | install.sh` would have
installed the pre-#85 onboarder (no already-CE plain-join path). This republishes
the frozen 0.2.0 release artifact in place — same package version `0.2.0`
(Operator-ratified) — so a clean install provisions main's current onboarder.

- Published wheel synced to the CI-verified in-repo wheel: the mirror
  `creator_engine_validator-0.2.0-py3-none-any.whl` is now **byte-identical** to
  `validators/wheelhouse/` (`588eeca0…`) — the strongest mirror↔source integrity.
- Re-pinned `docs/downloads/0.2.0/SHA256SUMS` (CE wheel line only; the 6
  dependency wheels and the `install.sh` entry are byte-unchanged).
- Updated and **re-signed** the install trust-root manifest `docs/llms-install.md`
  (`sha256s_sha256` `fde81151…` + the app-wheel `sha256` `588eeca0…`); the
  detached SSHSIG over the canonical bytes (`content_sha256` `88c2fbca…`) is
  re-issued with the offline `ce-root-v1` root key (namespace `ce-spec-v1`,
  Operator-laptop-held). `install.sh` is byte-unchanged (it reads the wheel hash
  from the served `SHA256SUMS` at runtime, not hardcoded).

No source/behaviour change — packaging-surface only. Internal-self-consistency of
the frozen mirror (ce-ops#69 re-scope) is preserved; the published wheel changes
here only at this ratified release + re-sign.
