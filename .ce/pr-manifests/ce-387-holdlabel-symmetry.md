# PR path manifest — ce-ops#387 · Hold-label symmetry for controller inbox

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-387-holdlabel-symmetry` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=13a4c0b52fc97ccc68a2a2b6facf14202947e5984bb71ffa6e7505061c6a2a97

```text
.ce/changelog/ce-387-holdlabel-symmetry.md
.ce/pr-manifests/ce-387-holdlabel-symmetry.md
validators/creator_engine_validator/forge/controller_inbox.py
validators/creator_engine_validator/forge/hold_labels.py
validators/creator_engine_validator/forge_triage.py
validators/tests/unit/test_controller_inbox.py
```
