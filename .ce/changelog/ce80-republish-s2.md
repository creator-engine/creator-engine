---
slug: ce80-republish-s2
date: 2026-06-17
kind: changed
scope: install mirror / release republish
base: 64678da
---

Republishes the public 0.2.0 install mirror so the agent-native self-serve
install serves the post-S2 (#248) hardened validator wheel (merged≠deployed).

- Replaces `docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`
  with the S2-hardened wheel (digest
  `f94d6db443a980be06e7fbe6e977559b7cb0efb77d94ae6a70714a048b42559c`) and
  refreshes that entry in `docs/downloads/0.2.0/SHA256SUMS`.
- Re-pins `docs/llms-install.md` (`required_wheels` app-wheel sha256,
  `sha256s_sha256`, `content_sha256`) and **re-signs** its canonical bytes with
  `ce-root-v1` (SSHSIG; stock `ssh-keygen -Y verify` = `Good` for `ce-spec-v1`).
- No source / validator-package change — this is an install-surface republish
  only; the wheel content equals the S2 build merged in #248.
