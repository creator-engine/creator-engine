# PR path manifest — ce-ops#N/A · pin subagent models (reviewer/implementer/architect→sonnet, verification→haiku)

- **Declared work class:** tiny

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-agent-model-pins` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=d8915601f711300927a533ba7cb87bf8d51d86ebc1b6e702ff9cb8fb7fb2ab86

```text
.ce/changelog/ce-agent-model-pins.md
.ce/pr-manifests/ce-agent-model-pins.md
.claude/agents/architect_research.md
.claude/agents/implementer.md
.claude/agents/reviewer.md
.claude/agents/verification.md
```
