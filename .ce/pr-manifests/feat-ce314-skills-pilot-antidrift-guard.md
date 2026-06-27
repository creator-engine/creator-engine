# PR path manifest — ce-ops#318 · Playbooks→Skills slice 1 — ce-dispatch + ce-merge-gate pilot + anti-drift guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref feat-ce314-skills-pilot-antidrift-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** feature

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=8e652ce1e1aaab2bbf5b0010103e0e4dd940fdf394dbd2270999caaa21105a75

```text
.ce/changelog/feat-ce314-skills-pilot-antidrift-guard.md
.ce/pr-manifests/feat-ce314-skills-pilot-antidrift-guard.md
.claude/skills/ce-dispatch/SKILL.md
.claude/skills/ce-merge-gate/SKILL.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/skill_antidrift_guard.py
validators/tests/unit/test_skill_antidrift_guard.py
```
