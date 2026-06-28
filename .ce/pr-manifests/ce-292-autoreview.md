# PR path manifest - ce-292-autoreview - ce-ops#292 reviewer self-fire wrapper

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-292-autoreview

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
- **Declared work class:** tiny
ce-ops#292 requires a narrow reviewer self-fire path before PR open and before
merge, using the existing `.claude/agents/reviewer.md` role and `/code-review`
wrapper. Reviewer evidence must post only as PR `COMMENT` or `REQUEST_CHANGES`;
the self-fire path must never emit approval.

The changes:
- Add one AGENTS.md operating line that auto-fires `/code-review` pre-PR and
  pre-merge with the existing reviewer worker role.
- Add a thin Claude `/code-review` command wrapper that maps no-blocking
  reviewer evidence to `COMMENT`, blocking evidence to `REQUEST_CHANGES`, and
  refuses any other event.
- Add focused tests for the AGENTS line, wrapper wiring, and behavioral
  approval-denial guard on the self-fire review path.
- Add this changelog and path manifest carrier.

Per-file purpose:
- **`AGENTS.md`** *(M)* - one-line auto-review operating instruction.
- **`.claude/commands/code-review.md`** *(A)* - thin `/code-review` self-fire wrapper.
- **`validators/tests/unit/test_claude_code_review_wrapper.py`** *(A)* - focused wiring and behavioral guard tests.
- **`.ce/changelog/ce-292-autoreview.md`** *(A)* - changelog fragment with `work_class: tiny`.
- **`.ce/pr-manifests/ce-292-autoreview.md`** *(A)* - this carrier.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=fa50d2da7f7687cca20822357c99f0410b477494bdc29e7867f29d39b970b94d

```text
.ce/changelog/ce-292-autoreview.md
.ce/pr-manifests/ce-292-autoreview.md
.claude/commands/code-review.md
AGENTS.md
validators/tests/unit/test_claude_code_review_wrapper.py
```
