---
brief_id: verify-ce-506-daemon-vs-agent-rubric-design-s1
ticket: ce-506
branch: ce-506-daemon-vs-agent-rubric-design-s1
head_sha: 34531faef356c85b4a0cc197d5593df56d22d976
role: verification
worktree: /home/ce-dev-2/creator-engine/.ce/wt-ce-506-daemon-vs-agent-rubric-design-s1-harvest
declared_work_class: story
base: origin/main@727f01a40a94f5ddcc43c52da4d0c2d31ce4718c
---

# Read-only full preflight verification: ce-506

Follow `.claude/agents/verification.md` exactly. This is a read-only host
verification of the pinned harvest branch. Do not edit, format, stage, commit,
push, open a PR, contact the network, or use credentials.

Allocated read-only worktree:
`/home/ce-dev-2/creator-engine/.ce/wt-ce-506-daemon-vs-agent-rubric-design-s1-harvest`

Expected territory:

- `.ce/changelog/ce-506-daemon-vs-agent-rubric-design-s1.md`
- `.ce/pr-manifests/ce-506-daemon-vs-agent-rubric-design-s1.md`
- `docs/design/daemon-vs-agent-rubric.md`

Run from the allocated worktree and return exact evidence for:

1. `git rev-parse HEAD` equals the pinned SHA above.
2. `git status --short` is empty before validation.
3. `git diff --check origin/main..HEAD` passes.
4. Full CI-parity preflight:
   `/home/ce-dev-2/creator-engine/.venv/bin/ce validate-pr --repo-root . --base origin/main --declared-work-class story --head-ref ce-506-daemon-vs-agent-rubric-design-s1`
5. `git status --short` remains empty after validation.

The design-preview hold is not a validation failure: this worker verifies only.
Stop on any head mismatch or RED result. Return PASS/FAIL, exact commands,
relevant failure excerpts, and residual risks. Do not mutate the worktree.
