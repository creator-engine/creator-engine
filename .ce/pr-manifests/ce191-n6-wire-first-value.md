# PR path manifest — 191 · wire N6 first_value stage to first-value.sh

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce191-n6-wire-first-value` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=98bb53ea39ea78d9886487935b7b07bfc5d15a7bd3e1184ea40073f9322b4a4c

```text
.ce/changelog/ce191-n6-wire-first-value.md
.ce/pr-manifests/ce191-n6-wire-first-value.md
scripts/clean-room-rehearsal.sh
```
