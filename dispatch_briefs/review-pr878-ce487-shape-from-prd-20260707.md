# Review brief: PR #878 ce-487-shape-from-prd

Role: reviewer.

Scope:
- Repository: `creator-engine/creator-engine`
- PR: `#878`
- Expected PR head: `2435df3a7d018eebc9c37e8625843ccf5a23b403`

Rules:
- Read `.claude/agents/reviewer.md` before review work.
- Do not edit files, push, approve, merge, enqueue, or alter PR metadata.
- Do not dump environment variables or inspect credential configuration.
- Verify the PR head exactly matches the expected SHA before reviewing.
- Review current head only; if the head differs, stop with `HEAD_CHANGED`.
- Focus on the PRD size/read guards, non-UTF-8/binary handling, `--from --confirm` scope behavior, tests, and governance carriers.

Return:
- `APPROVE`, `REQUEST_CHANGES`, `COMMENT`, or `HEAD_CHANGED`.
- Findings with file/line references where applicable.
- Tests/checks inspected or run.
- Exact head SHA reviewed.
