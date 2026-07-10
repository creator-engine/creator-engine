# Reviewer brief — PR #932 repaired daemon-vs-agent rubric

## Assignment

- PR: #932, design preview held AWAITING-OPERATOR
- Exact repaired head: `e98fd8f944c5981ae582da207f9e017dcbfb506d`
- Original reviewed parent: `34531faef356c85b4a0cc197d5593df56d22d976`
- Base: `origin/main@727f01a40a94f5ddcc43c52da4d0c2d31ce4718c`
- Branch: `ce-506-daemon-vs-agent-rubric-design-s1`
- Role: `.claude/agents/reviewer.md`
- Worktree: `/home/ce-dev-2/creator-engine/.ce/wt-ce-506-daemon-vs-agent-rubric-design-s1-harvest`
- Context: self-fire and Operator-held; verdict cannot be APPROVE.

## Read-only review surface and required lenses

- `docs/design/daemon-vs-agent-rubric.md`
- `.ce/changelog/ce-506-daemon-vs-agent-rubric-design-s1.md`
- `.ce/pr-manifests/ce-506-daemon-vs-agent-rubric-design-s1.md`
- Read-only surrounding `AGENTS.md`, reviewer policy, brain-recall schema/runtime,
  and control-plane authority context needed to verify the repair.

Re-review the complete base-to-head design and explicitly resolve the two prior
blockers:

1. Governing reviewer policy must come from a trusted ratified control-plane/base
   ref bound by digest; candidate policy is reviewed input only.  AutoReview may
   emit only COMMENT/REQUEST_CHANGES evidence and must never ratify, approve, or
   become a merge predicate.
2. Structural SSOT remains authoritative; recall is derived, rebuildable,
   advisory, non-canonical, and independently fallible.  Require pointer/live
   verification, confidentiality/privacy gating, precedence, and deterministic
   SSOT/core fallback without atomic SSOT+recall coupling.

Also verify current/proposed/ratified language is honest, no authority boundary
was broadened, carrier/changelog remain exact, and the diff has only the three
declared paths.

Validation evidence: focused gates green; prior timeout test passed 5/5; final
`ce validate-pr` exited PASS with zero new failures.  The explicit long basetemp
produced 14 identical environment failures in baseline and HEAD (primarily
AF_UNIX path-length), with 10 skips; treat this as disclosed residual evidence,
not as proof of a content defect or as raw-suite failure-free evidence.

Standing preflight directive: run the FULL local validator preflight (`ce validate-pr`,
CI-parity) before every self-push or commit-for-harvest.  This read-only reviewer
must not rerun a mutating validator path.

## Deliverable and stop line

Return `COMMENT` with precise evidence if no blocker is proven, or
`REQUEST_CHANGES` with exact file/line evidence for a blocker.  Never return or
request `APPROVE`; never release the design hold.  Do not mutate, use network or
credentials, submit a review, push, approve, or merge.  Stop if head/base differs
or authority outside the reviewer role is required.

