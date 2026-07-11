# PR path manifest — ce-539-checkpoint-skill

- **Declared work class:** tiny

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-539-checkpoint-skill
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope: ce-ops#539 adds one repository skill for durable, redaction-safe,
resumable controller checkpoints. It adds no runtime code, readiness state,
forge action, gate action, or publication action.

Per-file purpose (closed path-set — 3 paths):

- **`.ce/changelog/ce-539-checkpoint-skill.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce-539-checkpoint-skill.md`** *(A)* — this carrier.
- **`.claude/skills/ce-checkpoint/SKILL.md`** *(A)* — checkpoint guidance.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=4adffc1f3242f3ffdf2d4bbcf8d4f478ad85e8d5acdbf218e22f8b46460c1680

```text
.ce/changelog/ce-539-checkpoint-skill.md
.ce/pr-manifests/ce-539-checkpoint-skill.md
.claude/skills/ce-checkpoint/SKILL.md
```
