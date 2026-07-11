# PR path manifest — skills-v1.1 XS adoption

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI verifies that the `base..HEAD` diff equals
exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=f5f8797775642d23c610ba7a5272f0ccf7c2afd93889aa3115f46c611a0ec4a4

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-skills-v11-xs-adoption.md
.ce/pr-manifests/ce-skills-v11-xs-adoption.md
.claude/agents/implementer.md
.claude/agents/reviewer.md
docs/architecture/shaping-ux.md
playbooks/controller/briefs/dispatch.md
```
