# PR path manifest — no-ticket · Document ce session terminal framing

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-docs-cesession-framing` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=423872100d2d624fd86164f8bdd1301963e04128bd0644276a7518412f6c1ace

```text
.ce/changelog/ce-docs-cesession-framing.md
.ce/pr-manifests/ce-docs-cesession-framing.md
docs/guide/pilot-runbook.md
```
