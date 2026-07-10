# Review brief: PR #876 ce-486-next-step-hints

Role: reviewer.

Scope:
- Repository: `creator-engine/creator-engine`
- PR: `#876`
- Expected PR head: `2a4c86f216957c412ff2128d42dbcf6e56634f81`
- Note: PR is currently draft; do not try to gate it.

Rules:
- Read `.claude/agents/reviewer.md` before review work.
- Do not edit files, push, approve, merge, enqueue, undraft, or alter PR metadata.
- Do not dump environment variables or inspect credential configuration.
- Verify the PR head exactly matches the expected SHA before reviewing.
- Review current head only; if the head differs, stop with `HEAD_CHANGED`.
- Focus on CLI next-step hint behavior, JSON readiness behavior, tests, and governance carriers.

Return:
- `APPROVE`, `REQUEST_CHANGES`, `COMMENT`, or `HEAD_CHANGED`.
- Findings with file/line references where applicable.
- Tests/checks inspected or run.
- Exact head SHA reviewed.
