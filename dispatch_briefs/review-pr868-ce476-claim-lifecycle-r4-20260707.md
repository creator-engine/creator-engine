# Review brief: PR #868 ce-476-claim-lifecycle R4

Role: reviewer.

Scope:
- Repository: `creator-engine/creator-engine`
- PR: `#868`
- Expected PR head: `a1a5e48a0cc73614dfca618e21a4456082cf02cc`

Rules:
- Read `.claude/agents/reviewer.md` before review work.
- Do not edit files, push, approve, merge, enqueue, or alter PR metadata.
- Do not dump environment variables or inspect credential configuration.
- Fetch the PR head from remote before deciding `HEAD_CHANGED`.
- Verify the PR head exactly matches the expected SHA before reviewing.
- Review current head only; if the head differs, stop with `HEAD_CHANGED`.
- Focus on claim lifecycle behavior, `validators/creator_engine_validator/cli.py` rebase conflict resolution, `validators/tests/unit/test_version_drift.py` combined coverage, manifest fidelity, and regression risk.

Return:
- `APPROVE`, `REQUEST_CHANGES`, `COMMENT`, or `HEAD_CHANGED`.
- Findings with file/line references where applicable.
- Tests/checks inspected or run.
- Exact head SHA reviewed.
