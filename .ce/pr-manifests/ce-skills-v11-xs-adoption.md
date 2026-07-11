# PR path manifest — skills-v1.1 XS adoption

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI verifies that the `base..HEAD` diff equals
exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=5bfa5aec8340e482140cd842d4ef22cff43e64482a91abf8bdaf4c86cacee0c9

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-skills-v11-xs-adoption.md
.ce/pr-manifests/ce-skills-v11-xs-adoption.md
.claude/agents/implementer.md
.claude/agents/reviewer.md
docs/architecture/shaping-ux.md
playbooks/controller/briefs/dispatch.md
validators/tests/unit/test_ce_brain_drift.py
```
