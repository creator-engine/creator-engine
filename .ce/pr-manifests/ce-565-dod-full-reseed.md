# PR path manifest — ce-ops#565 · Define deployable-capability closure evidence

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-565-dod-full-reseed` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=5c4dc3a778c335c85712d7ab31dc44a2070d07fa875f5ffc402feabf625c321d

```text
.ce/changelog/ce-565-dod-full-reseed.md
.ce/pr-manifests/ce-565-dod-full-reseed.md
.claude/agents/README.md
.claude/agents/architect_research.md
.claude/agents/canary_qa.md
.claude/agents/implementer.md
.claude/agents/reviewer.md
.claude/agents/verification.md
playbooks/controller/briefs/dispatch.md
```
