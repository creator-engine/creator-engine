---
slug: ce80-republish-233
date: 2026-06-16
kind: fixed
scope: install / downloads mirror
issue: ce-ops#80
---

**Republish the 0.2.0 download mirror to match main's post-#233 validator wheel (brownfield live-forge ApplyDriver).**

Tonight's merges through #233 (`feat(creator-engine#88): production live-forge
ApplyDriver (Phase 1)`) rebuilt the in-repo 0.2.0 validator wheel
(`validators/wheelhouse/`, new sha `de40b62f…`) — adding `onboard_apply_live.py`,
the brownfield plain-join `onboard --apply` legs — but the published Pages mirror
(`docs/downloads/0.2.0/`) and the signed install spec were last republished at
#231 and still pinned the pre-#233 wheel (`588eeca0…`, no `onboard_apply_live`).
A fresh `curl … | install.sh` therefore installed a build whose team-mode
brownfield `onboard --apply` dead-ends at `e2_brownfield_seam_unavailable`. This
republishes the frozen 0.2.0 release artifact in place — same package version
`0.2.0` — so a clean install provisions main's current onboarder, brownfield
apply capability included.

- Published wheel synced **byte-identical** to the CI-verified in-repo wheel
  (`de40b62f…`); `onboard_apply_live` is now present in the served wheel.
- Re-pinned `docs/downloads/0.2.0/SHA256SUMS` (CE wheel line only; the 6
  dependency wheels and the `install.sh` entry are byte-unchanged).
- Updated and **re-signed** `docs/llms-install.md` (`sha256s_sha256`
  `e346f52f…`, app-wheel `sha256` `de40b62f…`, `content_sha256` `416179a7…`);
  the detached SSHSIG over the canonical bytes is re-issued with the offline
  `ce-root-v1` root key (namespace `ce-spec-v1`, Operator-laptop-held).
  `install.sh` is byte-unchanged (it reads the wheel hash from the served
  `SHA256SUMS` at runtime).

No source/behaviour change — packaging-surface only. Internal self-consistency of
the frozen mirror (ce-ops#69 re-scope) is preserved. This closes the merged≠deployed
staleness ce-ops#80 tracks — the manual republish is the stopgap; the codified
build→deploy→serve workflow + `verify-release-surface-fresh` gate is the durable fix.
