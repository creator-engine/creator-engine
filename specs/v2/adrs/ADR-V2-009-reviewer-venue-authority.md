# ADR-V2-009: Reviewer-venue side-effect-authority seam

## Status

Accepted for G2.007.2 draft runtime.

## Context

A distinct CE-governed reviewer venue performs an independent review and must then submit its
verdict via `gh pr review` — a restricted side effect. The CC-G-C Ring-1 hook (`hook_check`)
classifies `gh pr review` as the restricted mechanic `pr_review` and, under a governed posture,
hard-denies it without `side_effect_authority`. PR #106's distinct-venue review was correctly
blocked on exactly this and had to be landed once via an Operator override (recorded governance
debt). The pre-existing seam was a hole: `build_context` read `side_effect_authority` from a raw
loose token any shell could set, and `_mechanics_would_deny` allowed on **any** truthy token — an
unbounded grant. G2.007.2 closes the hole with a bounded, auditable envelope.

## Decision

G2.007.2 adds `schemas/reviewer-authority-envelope.schema.yaml`, the `reviewer_authority_envelope`
validator, a prose contract, examples, and **modifies the Ring-2 enforcement engine
`hook_check.py`** — the first gate to do so.

The distinct-controller-review rule referenced by this ADR is canonically recorded in
ce-ops `decision-records/ADR-0003-reviewer-independence-isolation-domain.md`. This
in-repo ADR remains the Creator Engine anchor for reviewer-venue authority; readers resolving
"per ADR-0003" should follow that ce-ops decision record for the isolation-domain rule.

Key decisions:

- **Bounded, auditable envelope.** A `reviewer_authority_envelope` authorizes exactly one mechanic
  (`pr_review`) on exactly one PR (`pr_number`), with `head_sha`/`actor`/`ratified_prompt_sha`
  binding the grant for audit. No secret values (`actor` is a login name).
- **Validated resolution, not a raw token.** `build_context` resolves `side_effect_authority` from a
  schema-valid envelope (inline `ce.reviewer_authority` or a posture-bound `ce.reviewer_authority_ref`);
  the old raw loose-string path is removed. Fail-closed: any load/validation problem yields no
  authority.
- **Bounded decision.** `_mechanics_would_deny` allows a restricted mechanic only when the envelope's
  `mechanic` equals the classified action AND (for `pr_review`) the command's target PR number equals
  `pr_number`. Wrong PR / wrong mechanic / no envelope deny; `merge`/`push`/`comment`/`live_lane_launch`
  stay denied under a `pr_review` grant.
- **Honest boundary.** The hook verifies the mechanic + PR number (what the command carries);
  `head_sha`/`actor`/`ratified_prompt_sha` are auditable bindings the venue honors — the hook cannot
  re-derive head/actor without calling `gh`. Hook-side head/actor verification is deferred.
- **Backward compatibility.** With no/invalid envelope, governed restricted mechanics deny exactly as
  before; all other hook behavior (scope/secret/Stop/ungoverned-advisory, the fail-open Ring-1
  contract) is unchanged. Only the one existing loose-token test is updated.
- **No launcher / `.claude/**` change.** The envelope is written by the ratified reviewer-launch
  procedure under the governed posture inputs (tied to the ratified reviewer prompt); minting inside
  `ce launch` is deferred.

## Consequences

- A distinct reviewer venue can be granted a narrow, auditable, ratification-bound authority to
  submit exactly its `pr_review` on the named PR — replacing the one-time Operator override and
  closing the unbounded raw-token hole. The recorded #106 governance debt is resolved.
- The hook decision engine now distinguishes a bounded reviewer grant from all other restricted
  mechanics, on a backward-compatible path.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no authority by itself,
authorizes no mechanic beyond `pr_review`, relaxes no other restricted-mechanic deny, and changes no
`.claude/**`/launcher surface.
