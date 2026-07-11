# PR path manifest — ce-ops#539 · Add a redaction-safe controller checkpoint skill

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-539-checkpoint-skill` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=1fb7f59a9d6e1b3fa70e509c9e6fabb28f7c187d9bc1e350c0abda851a039a1f

```text
.ce/changelog/ce-539-checkpoint-skill.md
.ce/pr-manifests/ce-539-checkpoint-skill.md
.claude/skills/ce-checkpoint/SKILL.md
playbooks/controller/briefs/checkpoint.md
```
