# PR path manifest — ce-ops#244 · CE worker-role agent definitions (.claude/agents)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce244-claude-agents-roles` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=57bf3fa8ddab082cec729d19da684a05c4f30839435758522958ef36a87a3eb6

```text
.ce/changelog/ce244-claude-agents-roles.md
.ce/pr-manifests/ce244-claude-agents-roles.md
.claude/agents/README.md
.claude/agents/architect_research.md
.claude/agents/implementer.md
.claude/agents/reviewer.md
.claude/agents/verification.md
```
