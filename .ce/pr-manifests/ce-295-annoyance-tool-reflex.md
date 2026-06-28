# PR path manifest — ce-ops#295 · Codify the annoyance→tool reflex and replace the empty AGENTS.md stub with an agent-authored session-bootstrap policy block

- **Declared work class:** tiny

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-295-annoyance-tool-reflex` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=6b24d36bcd380898bb6ef283f5ab423ff25a49b9552c740f05b2f5eed0f1c4bc

```text
.ce/changelog/ce-295-annoyance-tool-reflex.md
.ce/pr-manifests/ce-295-annoyance-tool-reflex.md
AGENTS.md
playbooks/controller/briefs/annoyance-to-tool.md
playbooks/controller/workflow.ce.yml
```
