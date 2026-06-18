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

The eligibility model composes with the private ce-ops governance records
value-free: ce-ops ADR-0003 defines reviewer independence as isolation-domain
disjointness, and ce-ops ADR-0004 requires contained agent runtime posture. The
public in-repo anchors are
[`ADR-V2-009`](../../specs/v2/adrs/ADR-V2-009-reviewer-venue-authority.md),
[`REVIEWER_VENUE_AUTHORITY`](./REVIEWER_VENUE_AUTHORITY.md),
[`validators/creator_engine_validator/forge/plan_approval.py`](../../validators/creator_engine_validator/forge/plan_approval.py),
and the CE58 live-identity guard.

Every registry reviewer carries an `isolation_domain_attestation` with expected
forge principal/login, credential-domain ref, OS-user-domain ref,
controller/principal ref, execution sandbox ref, containment ref, host ref,
computed tier, evidence timestamp, source, and containment status. Ordinary PR
review requires at least Tier 2. Same host is allowed when identity, credential,
OS user, controller/principal, and venue domains are disjoint. Same controller
with a different login is still Tier 1 and invalid. Tier 4 is reserved for
release, root-key, signing, and comparable highest-consequence classes.

Containment fails closed for real reviewer venues when the attestation says
`uncontained`, `noop`, `advisory`, or `off`. A
`required_but_pending_enforcement` status is recorded explicitly so it cannot be
mistaken for enforced containment, but it is not treated as an uncontained
runtime by this plan-only step.

CE58 remains a live identity guard, not a credential-storage channel. Reviewer
registry `actor`/login fields are expected identities only; reviewer triage does
not introduce token, token-hash, or token-ref fields. Live reviewer execution
still has to prove that the source-host actor observed by `gh api user --jq
.login` equals the expected reviewer actor before any reviewer-side source-host
act is eligible.

ce-ops#34 ticket triage is a separate tracker-ticket/advisory queue. This
document and the `reviewer-triage-decision` schema cover PR review triage only:
PR-triggered, head-pinned, `type:review`, and non-authoritative until a distinct
reviewer venue produces evidence through the reviewer authority path.

The current `.github/CODEOWNERS` file stays in place as forge-enforcement
compatibility while dynamic routing moves into the reviewer registry and
CE-managed reviewer team. Do not delete CODEOWNERS as part of reviewer triage.
