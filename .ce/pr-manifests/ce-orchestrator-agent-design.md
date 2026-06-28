# PR path manifest — ce-ops#TBD · CE Orchestrator Agent design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-orchestrator-agent-design` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=40a41b60424f88861ef1864f29abe8efe8f7b8409e5582366d10b94231ef5a70

```text
.ce/changelog/ce-orchestrator-agent-design.md
.ce/pr-manifests/ce-orchestrator-agent-design.md
docs/design/ce-orchestrator-agent-epic.md
docs/design/ce-orchestrator-agent.md
```
