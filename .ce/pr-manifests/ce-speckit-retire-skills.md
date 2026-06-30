# PR path manifest — spec-kit-retirement · Retire vendored spec-kit skills

- **Declared work class:** tiny

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-speckit-retire-skills` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=25

AUTHORIZED_PATHS_SHA256=432bcaf1916f142130e6a6af49ba024d841189f37f9b820770daa72899e722ca

```text
.agents/skills/speckit-analyze/SKILL.md
.agents/skills/speckit-checklist/SKILL.md
.agents/skills/speckit-clarify/SKILL.md
.agents/skills/speckit-constitution/SKILL.md
.agents/skills/speckit-implement/SKILL.md
.agents/skills/speckit-plan/SKILL.md
.agents/skills/speckit-specify/SKILL.md
.agents/skills/speckit-tasks/SKILL.md
.agents/skills/speckit-taskstoissues/SKILL.md
.ce/changelog/ce-speckit-retire-skills.md
.ce/pr-manifests/ce-speckit-retire-skills.md
.claude/skills/speckit-analyze/SKILL.md
.claude/skills/speckit-checklist/SKILL.md
.claude/skills/speckit-clarify/SKILL.md
.claude/skills/speckit-constitution/SKILL.md
.claude/skills/speckit-git-commit/SKILL.md
.claude/skills/speckit-git-feature/SKILL.md
.claude/skills/speckit-git-initialize/SKILL.md
.claude/skills/speckit-git-remote/SKILL.md
.claude/skills/speckit-git-validate/SKILL.md
.claude/skills/speckit-implement/SKILL.md
.claude/skills/speckit-plan/SKILL.md
.claude/skills/speckit-specify/SKILL.md
.claude/skills/speckit-tasks/SKILL.md
.claude/skills/speckit-taskstoissues/SKILL.md
```
