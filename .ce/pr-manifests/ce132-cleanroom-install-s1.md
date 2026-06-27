---
slug: ce132-cleanroom-install-s1
date: 2026-06-26
kind: fix
scope: install
issue: 132
---

# PR path manifest — 132 · fix(ce-ops#132): clean-room install S1 blockers

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce132-cleanroom-install-s1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=e69abfd30457b583beb69360eba5f9e7a8011e029baba359670fc57d026644e6

```text
.ce/changelog/ce132-cleanroom-install-s1.md
.ce/pr-manifests/ce132-cleanroom-install-s1.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/install.sh
docs/install.sh
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_v3_cli_cleanroom.py
```
