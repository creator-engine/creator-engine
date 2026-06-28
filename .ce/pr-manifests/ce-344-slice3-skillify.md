# PR path manifest - ce-ops#344 slice 3 - skill-ify ce-dispatch + ce-harvest

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI requires this PR's `base..HEAD` diff to
equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=6a099bf11c2b24febbf45c9b2397047c4f89849cb2f2102d6c8df6e990d54c51

```text
.ce/changelog/ce-344-slice3-skillify.md
.ce/pr-manifests/ce-344-slice3-skillify.md
.claude/skills/ce-dispatch/SKILL.md
.claude/skills/ce-harvest/SKILL.md
playbooks/controller/briefs/harvest.md
validators/tests/unit/test_skill_antidrift_guard.py
```
