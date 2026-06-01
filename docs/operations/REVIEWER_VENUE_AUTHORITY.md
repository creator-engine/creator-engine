# Reviewer-Venue Side-Effect-Authority Seam (G2.007.2)

A distinct CE-governed reviewer venue performs an independent review and then must submit
its verdict — a restricted side effect (`gh pr review`). The CC-G-C Ring-1 hook
(`hook_check`) classifies `gh pr review` as the restricted mechanic `pr_review` and, under
a governed posture, **hard-denies it without `side_effect_authority`**. This gate builds
that authority the sanctioned way: a **bounded, auditable reviewer-authority envelope** the
hook honors for exactly one mechanic on exactly one PR. It resolves the governance debt from
PR #106 (whose review was correctly blocked and landed once via an Operator override).

## 1. The envelope

A `reviewer_authority_envelope` (`schemas/reviewer-authority-envelope.schema.yaml`) declares:
`envelope_id`, `mechanic` (`pr_review` only), `pr_number`, `head_sha`, `actor`,
`ratified_prompt_sha`, `emitting_role`, `operating_mode`, `recorded_at`, optional `metadata`.
It carries **no secret** — `actor` is a login name; the reviewer token is referenced
out-of-band, never embedded.

The `reviewer_authority_envelope` validator (`VAL-RVA-*`) enforces the shape, the bounded
`mechanic`, the required bindings, the role/mode floors, no inline secret, and no inline
Markdown metadata.

## 2. How the hook honors it (the bounded match)

`hook_check.build_context` resolves `side_effect_authority` from a **validated** envelope
(an inline `ce.reviewer_authority` mapping or a posture-bound `ce.reviewer_authority_ref`
path) — **the old raw loose-string token is no longer honored** (it was the "any shell can
set it" hole, and it allowed any mechanic). `_mechanics_would_deny` then allows a restricted
mechanic **only** when:

- the envelope's `mechanic` equals the classified action (`pr_review`), **and**
- (for `pr_review`) the command's target PR number equals `envelope.pr_number`.

Everything else denies: no/invalid envelope, a wrong PR, `gh pr merge`/`git push`/
`gh pr comment`/`ce launch`/any other mechanic. **Fail-closed** by contract.

**Honest boundary.** The hook verifies the **mechanic + PR number** (what the command string
carries). `head_sha`, `actor`, and `ratified_prompt_sha` are **auditable bindings** the
reviewer venue honors — the hook cannot re-derive head/actor from the command alone without
calling `gh`. They make every grant traceable to a ratified reviewer prompt and a specific
head/actor.

## 3. Backward compatibility

With **no valid envelope**, governed restricted mechanics are denied exactly as before this
gate; all non-mechanic hook behavior (scope/secret/Stop/ungoverned-advisory, the fail-open
Ring-1 contract) is unchanged.

## 4. Minting (out of scope here)

The envelope is written under the governed posture inputs as part of the **ratified
reviewer-launch procedure** (tied to the ratified reviewer prompt, recorded in
`ratified_prompt_sha`). This gate does **not** modify `ce launch`/the launcher; minting the
envelope inside the launcher and hook-side `head`/`actor` verification are deferred.

## 5. Out of scope of this gate (G2.007.2)

The launcher/`ce launch` minting path; hook-side head/actor verification via `gh`;
`G2.007.1` per-harness promotions; any widening beyond the `pr_review` reviewer mechanic.
