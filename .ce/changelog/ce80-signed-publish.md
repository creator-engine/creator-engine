---
slug: ce80-signed-publish
date: 2026-06-22
kind: added
scope: release publish pipeline
issue: ce-ops#80
---

**Add a deterministic signed-release staging pipeline.**

Introduces an Operator-gated release staging command that prepares the Pages
install mirror from a chosen merged main commit: it writes the build identity,
builds the first-party validator wheel through the existing wheel-bake seam,
verifies wheel/source parity, regenerates `SHA256SUMS`, stages the installer
mirror, and stops at a `ce-root-v1` signing placeholder with explicit
`ssh-keygen -Y sign` instructions.

This does not publish live Pages bytes, create tags, create GitHub releases, or
use the root signing key. The staged output is the artifact surface consumed by a
later Operator signing/publish gate and by `ce update` work in ce-ops#190.
