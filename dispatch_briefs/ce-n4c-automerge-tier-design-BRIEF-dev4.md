# Seed Brief: N4c — Auto-merge policy-tier EXPANSION proposal (DESIGN-ONLY)

- Role: architect (read + analyze + write ONE report file). Night-arc mandate lane N4c.
- This is DESIGN-ONLY. Nothing you produce takes effect; the proposal is staged for Operator
  ratification. You change NO code, NO workflows, NO config, NO gates.

## Context (embedded — do not attempt to read external tickets)
- CE currently auto-merges exactly ONE PR class: docs-class PRs inside the ratified ceo/docs
  envelope (went LIVE 2026-06-30, Operator "Option A" decision). Kill-switch = a CLI rollback
  (see `ce` CLI automerge kill-switch surface) + revert of the arming commit.
- The merge gate stack today: PR needs path-manifest carrier matching base..HEAD, declared work
  class (tiny|story|feature|epic) vs diff floor, changelog fragment, full validate-pr GREEN in CI,
  independent review (author ≠ approver), ce-dev-2 approval on CURRENT head, then the approval-wall
  queue daemon auto-enqueues/merges approved+green PRs (~120s).
- Adjacent caution (from a fresh independent security review of the conveyor arming path, verdict
  DO-NOT-ARM): any expansion that lets landed content influence privileged execution must respect —
  (1) daemon-owned path allocation, (2) credentialless validation sandbox (no os.environ merge),
  (3) transport-credential separation from validation, (4) daemon-private roots. Treat these as
  standing design constraints for every tier you propose.

## Read (in-repo, this is your evidence base)
- validators/creator_engine_validator/forge/automerge_policy.py
- validators/creator_engine_validator/forge/auto_merge.py
- .github/workflows/automerge-decide.yml and .github/workflows/automerge-actuate.yml
- The work-class / carrier gate code they reference (follow imports as needed)
- Any ADR in docs/adr/ touching merge/automation safety (notably ADR-0004 for the safety idiom)

Use a fresh read-only worktree: `git -C /workspace/creator-engine fetch origin` then
`git -C /workspace/creator-engine worktree add /var/tmp/n4c-design-read origin/main`. If fetch
fails (no egress), read your current checkout instead and RECORD the exact SHA you read.

## Produce: /var/tmp/AUTOMERGE_TIER_EXPANSION_PROPOSAL_dev4_20260702.md
A ratification-grade proposal containing:
1. Current-state map: exactly what the docs-class tier permits today, enforced where (file:line).
2. Candidate next tiers, each with: PR-class definition (machine-checkable predicate), required
   evidence bundle (checks, review class, work-class ceiling, path envelope), residual risk, blast
   radius if wrong, rollback story. Order tiers by risk ascending. Candidates to evaluate at
   minimum: (a) brain-ledger supersede chores (append-only assertions.yaml + count-bump pattern),
   (b) changelog/carrier-only mechanical regens, (c) test-only diffs, (d) tiny work-class code
   diffs with full green + independent review. You may add/reject candidates with reasons.
3. Per-tier kill-switch and observability requirements (what audit line proves each auto-merge
   was policy-conformant; how the Operator turns one tier off without touching others).
4. Explicit ratification asks: one numbered decision per tier (recommend a default per
   user-choice-architecture: encode your recommendation as the default option).
5. Non-goals: what must stay human-gated regardless (releases, gate/wall config, envelope edits).

## Evidence + stop line
- Done-report format (single line, then stop):
  `READY-FOR-HARVEST report=/var/tmp/AUTOMERGE_TIER_EXPANSION_PROPOSAL_dev4_20260702.md sha256=<sha256sum of the file> read-sha=<main SHA you read>`
- NO commits, NO branch, NO push, NO PR, NO edits outside /var/tmp. Do not modify
  /workspace/creator-engine working tree (worktree add is fine). Stop after the done-report.
