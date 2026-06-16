---
slug: ce80-republish-post241
date: 2026-06-17
kind: fixed
scope: install / downloads mirror
issue: ce-ops#80
---

**Republish the 0.2.0 download mirror to match main's post-#241 validator wheel.**

PR #241 (ce-ops#90) loosened the brownfield "already-CE" detector and rebuilt the
in-repo 0.2.0 validator wheel in `validators/wheelhouse/`, while the published Pages
mirror (`docs/downloads/0.2.0/`) and the signed agent-native install spec still
referenced the post-#240 wheel (old detector). This republishes the frozen 0.2.0
release artifact in place — keeping the package version at `0.2.0` — so fresh installs
provision main's current (post-#241) validator wheel and brownfield onboarding of
legacy-`validate.yml` repos succeeds.

- Published wheel synced byte-identical to the in-repo wheelhouse wheel (`ac8117d3...`).
- Re-pinned `docs/downloads/0.2.0/SHA256SUMS` (CE wheel line only; dependency wheels and
  install.sh unchanged) → file `sha256` `a2f6a701...`.
- Updated and re-signed `docs/llms-install.md` (`sha256s_sha256` → `a2f6a701...`, app-wheel
  `sha256` → `ac8117d3...`, `content_sha256` → `5820a9f8...`) under the offline `ce-root-v1`
  root key / `ce-spec-v1` namespace; local verify returns `Good`.
