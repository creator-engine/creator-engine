---
slug: ce260-release-artifact-parity-guard
date: 2026-06-26
kind: changed
scope: release install artifact parity
---

Adds an offline validator check that binds the served installer to the
versioned release mirror:

`sha256(docs/install.sh) == SHA256SUMS[install.sh] == sha256(docs/downloads/<ver>/install.sh)`.

Refreshes the 0.2.0 mirrored installer from `docs/install.sh` and updates the
`docs/downloads/0.2.0/SHA256SUMS` `install.sh` entry.

Flagged only: re-signing `docs/llms-install.md` requires the held
`ce-root-v1` key and remains controller work. This change does not touch the
signed install spec.
