# PR path manifest — ce-ops#191 · clean-room rehearsal harness scaffold (N6)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce191-n6-clean-room-rehearsal` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=d3af289f71b857249d8537601603804b10f319f8d59c6b846eddec81ab40fdde

```text
.ce/changelog/ce191-n6-clean-room-rehearsal.md
.ce/pr-manifests/ce191-n6-clean-room-rehearsal.md
docs/operations/CLEAN_ROOM_REHEARSAL.md
scripts/clean-room-rehearsal.sh
```
