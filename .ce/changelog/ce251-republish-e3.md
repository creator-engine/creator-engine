---
slug: ce251-republish-e3
date: 2026-06-18
kind: changed
scope: install mirror / release republish
base: 50ce51a
---

Republishes the public 0.2.0 install mirror so the agent-native self-serve
install serves the post-E3 (#251) validator wheel (merged≠deployed).

The mirror app wheel (`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`)
is replaced with the E3 build (digest `884aeb45…`, was `d81c646c…`),
`SHA256SUMS` is refreshed, and `docs/llms-install.md` is re-pinned
(`required_wheels` app-wheel sha256, `sha256s_sha256`, `content_sha256`) and
re-signed over its canonical bytes with the `ce-root-v1` trust root (SSHSIG,
namespace `ce-spec-v1`). Stock `ssh-keygen -Y verify` reports `Good`. No
source/validator-package change.
