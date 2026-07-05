# PR path manifest - ce-docs-stale-wheel-envvar - stale-wheel override docs

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-docs-stale-wheel-envvar` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=143389823520ab261586c6ea5095384c62cdfffac7a6b92759e8a586f9cf13b1

```text
.ce/changelog/ce-docs-stale-wheel-envvar.md
.ce/pr-manifests/ce-docs-stale-wheel-envvar.md
docs/guide/contributing-to-ce.md
```
