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

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=ce051a5d744bf39a210c08915770d8ce2c8fb3cfacfe0110badc453c60cb94e0

```text
.ce/changelog/ce132-cleanroom-install-s1.md
.ce/pr-manifests/ce132-cleanroom-install-s1.md
docs/install.sh
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_v3_cli_cleanroom.py
```
