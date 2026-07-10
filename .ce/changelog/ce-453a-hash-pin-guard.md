---
slug: ce-453a-hash-pin-guard
date: 2026-07-10
kind: validator
scope: validate-pr
issue: ce-ops#453
---

**signed artifact hash-pin validate-pr guard.**

- Add a validate-pr guard for signed artifact hash-pinned source changes.
- Cover pinned-file, paired pin update, unrelated, and pin-only diff cases.
- Fail CLOSED (`VAL-SIGNED-ARTIFACT-PINS-INVALID`) on frontmatter corruption,
  a missing/malformed `artifact_manifest` section, or zero discoverable pins,
  instead of silently degrading protection to an empty pin set.
- Protect the `install.sh` / `docs/install.sh` byte chain via the existing
  `sha256s_sha256` pin's SHA256SUMS alias, so editing the installer without a
  matching pin/SHA256SUMS change is caught.
- Give whole-document pins (e.g. `content_sha256`) a distinct "whole-document
  re-sign required" notice instead of the generic missing-pinned-file wording.
- Cover missing/unreadable signed doc, frontmatter-corruption, git-diff
  subprocess failure, synthetic-fixture-doc-changes-in-diff, and the
  install.sh-chain RED case.
