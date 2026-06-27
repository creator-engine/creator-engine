# PR path manifest - ce-292-autoreview-enforcement - ce-ops#292 raw API approval guard

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
- **Declared work class:** tiny
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-292-autoreview-enforcement

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#292 requires the reviewer-authority hook to deny self-fire approval
attempts submitted through raw GitHub review API calls.

The changes:
- Classify raw `gh api` review writes carrying `event=APPROVE` as restricted
  `pr_review` mechanics.
- Keep raw API approval attempts denied even with a normal `pr_review`
  reviewer-authority envelope.
- Clarify reviewer worker policy so self-fire review cannot return or post
  `APPROVE`.
- Add focused runtime unit coverage for `-f event=APPROVE` and
  `--raw-field event=APPROVE` forms.

Per-file purpose:
- **`.ce/changelog/ce-292-autoreview-enforcement.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-292-autoreview-enforcement.md`** *(A)* - this carrier.
- **`.claude/agents/reviewer.md`** *(M)* - self-fire approval prohibition.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* - raw API review approval classification and fail-closed authority behavior.
- **`validators/tests/unit/test_hook_check_reviewer_authority.py`** *(M)* - behavioral runtime coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=cc633e5ab17d422ab5bee1caa72f4782385e9417f906202f5cf82584c8858bb6

```text
.ce/changelog/ce-292-autoreview-enforcement.md
.ce/pr-manifests/ce-292-autoreview-enforcement.md
.claude/agents/reviewer.md
validators/creator_engine_validator/hook_check.py
validators/tests/unit/test_hook_check_reviewer_authority.py
```
