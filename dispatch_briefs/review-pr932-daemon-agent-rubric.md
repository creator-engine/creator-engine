# Reviewer brief — PR #932 daemon-vs-agent routing rubric

## Assignment

- Ticket/work: ce-506 daemon-vs-agent routing rubric design, slice 1
- PR: #932, `https://github.com/creator-engine/creator-engine/pull/932`
- Exact head: `34531faef356c85b4a0cc197d5593df56d22d976`
- Base: `origin/main@727f01a40a94f5ddcc43c52da4d0c2d31ce4718c`
- Branch: `ce-506-daemon-vs-agent-rubric-design-s1`
- Role: `.claude/agents/reviewer.md`
- Worktree: `/home/ce-dev-2/creator-engine/.ce/wt-ce-506-daemon-vs-agent-rubric-design-s1-harvest`
- Review context: self-fire and Operator-held design preview; verdict cannot be APPROVE.

## Read-only review surface

- `.ce/changelog/ce-506-daemon-vs-agent-rubric-design-s1.md`
- `.ce/pr-manifests/ce-506-daemon-vs-agent-rubric-design-s1.md`
- `docs/design/daemon-vs-agent-rubric.md`
- Read-only ratified policy/design context needed to assess factual and architectural fit.

Review whether the rubric is internally coherent, preserves authority boundaries,
distinguishes deterministic daemon behavior from bounded agent judgment, states a
complete hydration contract, and labels proposals versus ratified facts honestly.
Verify the actual diff against the named base and exact head.  Do not mutate files,
run network operations, or submit a review.

## Existing evidence and hold

- Controller-side canonical `ce validate-pr`: PASS on the exact head.
- GitHub `Validate governance artifacts`: SUCCESS on the exact head.
- The PR is `[DESIGN-PREVIEW — AWAITING OPERATOR]`; no review may release that hold.

Standing preflight directive: run the FULL local validator preflight (`ce validate-pr`,
CI-parity) before every self-push or commit-for-harvest.  This read-only review performs
neither; do not invoke a validator path that creates worktrees or mutates the checkout.

## Deliverable and stop line

Return only `COMMENT` with concise evidence when no blocking defect is proven, or
`REQUEST_CHANGES` with file/line evidence for any blocking defect.  Never return or
request `APPROVE`.  Stop if the head differs, the worktree is not the named exact head,
or review would require mutation, egress, credentials, or Operator ratification.

