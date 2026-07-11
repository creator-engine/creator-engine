# PR path manifest — skills-v1.1 XS adoption

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI verifies that the `base..HEAD` diff equals
exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=5f112cd11ffbbb000377b466fa84831a67ba2089340a5abc12708748b70dc202

```text
.ce/changelog/ce-skills-v11-xs-adoption.md
.ce/pr-manifests/ce-skills-v11-xs-adoption.md
.claude/agents/implementer.md
.claude/agents/reviewer.md
docs/architecture/shaping-ux.md
playbooks/controller/briefs/dispatch.md
```
