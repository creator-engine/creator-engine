# PR path manifest — ce-ops#79 · feat(brain): add advisory ingest refresh wrapper

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-brain-ingest-refresh` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=173067197f3a4717b2dabcf0f5d2302e6fa2b91bf3fc47ee0e1017c740f154cf

```text
.ce/changelog/ce-brain-ingest-refresh.md
.ce/pr-manifests/ce-brain-ingest-refresh.md
docs/operations/brain-ingest-refresh.md
scripts/brain-ingest-refresh.sh
```
