# dev-3 brief: fix PR #878 binary PRD guard

Role: contained implementer worker.

Scope:
- PR: `creator-engine/creator-engine#878`
- Branch: `ce-487-shape-from-prd`
- Expected current head: `2435df3a7d018eebc9c37e8625843ccf5a23b403`

Blocking review finding to fix:
- `validators/creator_engine_validator/v3_cli.py` guards PRD input by size and UTF-8 decode only. It must also reject non-regular files and valid-UTF-8 binary/control-byte content before `seed_scope_from_prd`, including when `--from --confirm` is used.

Rules:
- You are not alone in the codebase. Do not revert or alter unrelated edits.
- Work only on PR #878 branch/worktree and only on the PRD input guard plus focused tests/carriers.
- Verify the branch head is still `2435df3a7d018eebc9c37e8625843ccf5a23b403` before editing. If not, report `HEAD_CHANGED`.
- Add tests for:
  - valid-UTF-8 binary/control-byte PRD content,
  - non-regular paths,
  - unchanged invalid UTF-8 behavior if currently covered.
- Run focused `test_v3_cli.py` coverage and source `ce validate-pr` if feasible.
- Commit locally and produce a bundle or exact commit SHA for controller harvest. Do not push directly unless the seat has an explicit self-push lane for this PR.
- Do not approve, merge, enqueue, sign, or change protected settings.

Stop line:
- `READY ce-487-shape-from-prd <sha>`
- Include changed files, validation evidence, and whether the branch was pushed or requires controller harvest.
