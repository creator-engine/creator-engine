# Review brief: PR #872 ce-475-broker-read-lane

Role: reviewer.

Scope:
- Repository: `creator-engine/creator-engine`
- PR: `#872`
- Expected PR head: `8e30d0c4f00be8af706e1e24c94d1fd3efa93ade`
- Author lane: not this reviewer.

Rules:
- Read `.claude/agents/reviewer.md` before review work.
- Do not edit files, push, approve, merge, enqueue, or alter PR metadata.
- Do not dump environment variables or inspect credential configuration.
- Create or reuse a local detached review worktree only if needed.
- Verify the PR head exactly matches the expected SHA before reviewing.
- Review current head only; if the head differs, stop with `HEAD_CHANGED`.
- Focus on the exit-code contract fix, config error behavior, tests, governance carriers, and regression risk.

Return:
- `APPROVE`, `REQUEST_CHANGES`, `COMMENT`, or `HEAD_CHANGED`.
- Findings with file/line references where applicable.
- Tests/checks inspected or run.
- Exact head SHA reviewed.
