# Review brief: PR #868 ce-476-claim-lifecycle

Role: reviewer.

Scope:
- Repository: `creator-engine/creator-engine`
- PR: `#868`
- Expected PR head: `0ceabebbd5cf8e9ede7fea3df0c52e36cfbd5e14`
- Author lane: not this reviewer.

Rules:
- Read `.claude/agents/reviewer.md` before review work.
- Do not edit files, push, approve, merge, enqueue, or alter PR metadata.
- Do not dump environment variables or inspect credential configuration.
- Create or reuse a local detached review worktree only if needed.
- Verify the PR head exactly matches the expected SHA before reviewing.
- Review current head only; if the head differs, stop with `HEAD_CHANGED`.
- Focus on correctness, governance behavior, tests, and regression risk.

Return:
- `APPROVE`, `REQUEST_CHANGES`, `COMMENT`, or `HEAD_CHANGED`.
- Findings with file/line references where applicable.
- Tests/checks inspected or run.
- Exact head SHA reviewed.
