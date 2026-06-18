# Reviewer Triage

Reviewer triage is the plan-only assignment step for the `reviewer` role
introduced in ce-ops#118. It computes who should review a PR from ownership,
mutation class, risk tier, author identity, forge-enforcement facts, reviewer
eligibility, and declared durable availability. The output is a
`reviewer-triage-decision` record.

Reviewer assignment is not ratification. In N=1 mode, agentic reviewer evidence
is useful but non-counting; the Operator remains the reviewer/ratifier boundary
for privileged authority. A triage decision does not approve, ratify, merge,
waive policy, submit a review request, mint a reviewer-authority envelope, or
spawn a reviewer venue.

`ce reviewer-triage plan --pr <n> --json` is intentionally plan-only. It reads
explicit PR facts and tracked local policy inputs, generates candidates from
CODEOWNERS, `.ce/coordination.yml` area-owner data, and the ratified reviewer
registry, filters fail-closed eligibility, applies deterministic ranking, and
emits the decision record. Candidate generation is ownership-only; git-history
scoring is not used.

The current `.github/CODEOWNERS` file stays in place as forge-enforcement
compatibility while dynamic routing moves into the reviewer registry and
CE-managed reviewer team. Do not delete CODEOWNERS as part of reviewer triage.
