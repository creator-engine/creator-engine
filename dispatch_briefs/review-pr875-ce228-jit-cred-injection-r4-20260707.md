# Review brief: PR #875 ce-228-jit-cred-injection R4

Role: reviewer.

Scope:
- Repository: `creator-engine/creator-engine`
- PR: `#875`
- Expected PR head: `9da759081011af5342e81c4c78e5c88664680d88`

Rules:
- Read `.claude/agents/reviewer.md` before review work.
- Do not edit files, push, approve, merge, enqueue, or alter PR metadata.
- Do not dump environment variables or inspect credential configuration.
- Fetch the PR head from remote before deciding `HEAD_CHANGED`.
- Verify the PR head exactly matches the expected SHA before reviewing.
- Review current head only; if the head differs, stop with `HEAD_CHANGED`.
- Specifically verify the prior blockers:
  1. JIT credential expiry is capped to the broker's 300s TTL even when upstream returns a longer `expires_at`.
  2. Nested secret-key-name scanning preserves secret-key context recursively and catches nested keys such as `contained.docker.create.env.GITHUB_TOKEN` even when the value is not token-shaped.
- Also review tests, governance carriers, and regression risk.

Return:
- `APPROVE`, `REQUEST_CHANGES`, `COMMENT`, or `HEAD_CHANGED`.
- Findings with file/line references where applicable.
- Tests/checks inspected or run.
- Exact head SHA reviewed.
