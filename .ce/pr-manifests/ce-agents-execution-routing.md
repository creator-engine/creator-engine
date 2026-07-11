# PR path manifest — ce-ops#531 · Add execution-routing / no-inlining section to AGENTS.md

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-agents-execution-routing` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=abe9b1552621522219552c4c115c92437e51020c0f4f10082f8f08c777531e7b

```text
.ce/changelog/ce-agents-execution-routing.md
.ce/pr-manifests/ce-agents-execution-routing.md
AGENTS.md
```
