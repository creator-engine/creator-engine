# PR path manifest — ce-ops#250 · Harden herdr session rebuild coverage

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce250-herdr-session-rebuild` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=b656188251cd1b4db670e67961fb4a09e22c570e9ad7d6ee86cdbaf6adefce90

```text
.ce/changelog/ce250-herdr-session-rebuild.md
.ce/pr-manifests/ce250-herdr-session-rebuild.md
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_vps_runsc_launcher.py
```
