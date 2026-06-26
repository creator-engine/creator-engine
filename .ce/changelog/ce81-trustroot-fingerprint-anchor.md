---
slug: ce81-trustroot-fingerprint-anchor
date: 2026-06-26
kind: fixed
scope: install trust anchor — out-of-band fingerprint publication
issue: ce-ops#81
---

Publishes the `ce-root-v1` signing key fingerprint
(`SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ`) to independent channels
in the GitHub repository, resolving the self-referential trust-anchor finding
(ce-ops#81).

Changes:

- Added `docs/security/trust-anchors.md`: the canonical in-repo out-of-band trust
  anchor document. Lists both signing keys (`ce-root-v1` and `ce-dev1-root-v1`)
  with their ed25519 fingerprints, custody, and ratification date. Documents the
  two published independent anchor channels (this file + DNS TXT
  `_ce-root-v1.creator-engine.dev`), shell verification recipes for each, the
  trust model distinguishing integrity from authenticity, and the key lifecycle.

- Updated `README.md` Install Story: added a "Trust anchor" paragraph that
  surface-publishes the `ce-root-v1` fingerprint inline and links to the new
  `trust-anchors.md`. Users and agents reading the repo README now have the
  fingerprint without having to discover the DNS TXT record first.

- Updated `docs/llms.txt`: extended the `ce-root-v1` bullet to include the
  fingerprint inline and added a `trust-anchors.md` bullet so agents parsing
  `llms.txt` as their install context receive the anchor immediately.

None of these changes touch the signed artifact `docs/llms-install.md` or any
detached signature; no re-signing is required.
