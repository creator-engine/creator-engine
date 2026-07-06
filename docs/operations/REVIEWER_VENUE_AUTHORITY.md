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
`ratified_prompt_sha`, `emitting_role`, `operating_mode`, `recorded_at`, optional `metadata`,
and, for launcher-minted envelopes, `capability: independent_review_venue`, `target_pr_author`,
`expires_at`, `single_use: true`, and launch consumption fields.
It carries **no secret** — `actor` is a login name; the reviewer token is referenced
out-of-band, never embedded.

The `reviewer_authority_envelope` validator (`VAL-RVA-*`) enforces the shape, the bounded
`mechanic`, the optional `independent_review_venue` capability value, the required bindings,
the role/mode floors, no actor-as-target-author self-review binding, no inline secret, and no
inline Markdown metadata.

## 2. How the hook honors it (the bounded match)

`hook_check.build_context` resolves `side_effect_authority` from a **validated** envelope
(an inline `ce.reviewer_authority` mapping or a posture-bound `ce.reviewer_authority_ref`
path) — **the old raw loose-string token is no longer honored** (it was the "any shell can
set it" hole, and it allowed any mechanic). `_mechanics_would_deny` then allows a restricted
mechanic **only** when:

- the envelope's `mechanic` equals the classified action (`pr_review`), **and**
- when present, the envelope's `capability` is `independent_review_venue`, **and**
- (for `pr_review`) the command's target PR number equals `envelope.pr_number`.

Everything else denies: no/invalid envelope, a wrong PR, `gh pr merge`/`git push`/
`gh pr comment`/`ce launch`/any other mechanic. Approval-capable broker paths reject
`capability: independent_review_venue`; this envelope is review-venue authority, not approval
authority. **Fail-closed** by contract.

**Honest boundary.** The hook verifies the **mechanic + PR number** (what the command string
carries). `head_sha`, `actor`, and `ratified_prompt_sha` are **auditable bindings** the
reviewer venue honors — the hook cannot re-derive head/actor from the command alone without
calling `gh`. They make every grant traceable to a ratified reviewer prompt and a specific
head/actor.

## 3. Backward compatibility

With **no valid envelope**, governed restricted mechanics are denied exactly as before this
gate; all non-mechanic hook behavior (scope/secret/Stop/ungoverned-advisory, the fail-open
Ring-1 contract) is unchanged.

## 4. Carrying the envelope into the live hook (G2.007.3)

G2.007.2 proved the hook honors `ce.reviewer_authority_ref` **synthetically**; it left the
launch→live-hook carrier and the distinct-reviewer-venue identity deferred. G2.007.3 closes
that gap without weakening any gate:

- **Distinct reviewer venue identity.** `ce lane launch --role reviewer --lane-kind review`
  is the only venue allowed to carry an injected authority ref. `lane_runtime.launch`
  validates the binding with `is_distinct_reviewer_venue` (role `reviewer` + lane kind
  `review`) and records the venue identity (`role`, `lane_kind`, `reviewer_venue: true`,
  `reviewer_authority_ref`) in the ignored governance sidecar next to the Pane Registry
  record. The canonical-root authoring Controller seat is **not** a reviewer venue.
- **Authority injection carrier.** `lane_runtime.launch` validates the ref as a schema-valid
  envelope **before any side effect** and refuses spent or expired refs (fail-closed
  `G3-REVIEWER-AUTHORITY-INVALID`; a ref on a non-reviewer venue is
  `G3-REVIEWER-VENUE-IDENTITY`). Launcher-minted envelopes are short-lived and single-use:
  they are stamped consumed on the first successful venue launch before the pane is spawned.
  The launch then exports the ref to the pane environment as `CE_REVIEWER_AUTHORITY_REF` via
  tmux `-e` (never printed). The committed
  `.claude/hooks/ce-pretooluse.sh` reads it and forwards `--reviewer-authority-ref <ref>` to
  the validator, which injects it as `ce.reviewer_authority_ref` **before**
  `hook_check.build_context()` — so the same bounded mechanic+PR semantics from §2 now hold on
  the live path. An event that already carries its own `ce` authority wins (the flag is a
  fallback carrier, never an override).
- **Fail-closed end to end.** No env var ⇒ no flag ⇒ no authority ⇒ restricted mechanics stay
  denied. An invalid/missing envelope resolves to no authority. Posture handling is unchanged:
  a governed venue hard-denies an unauthorized mechanic and hard-allows only the matching
  `pr_review`.

G11 adds in-launcher minting for distinct reviewer venues. Minting requires the PR/head,
reviewer actor, target PR author, and ratified prompt SHA; it refuses actor-as-author
self-review before any side effect. The minted envelope is written under ignored lane ledger
state with `capability: independent_review_venue`, short expiry, and single-use semantics.

## 5. Out of scope of this gate (G2.007.3)

Hook-side `head_sha`/`actor` verification via `gh`; the Controller-seat `ce launch` path (a
reviewer venue is a `ce lane launch` lane, not the Controller seat); `G2.007.1` per-harness
promotions; any widening beyond the `pr_review` reviewer mechanic.
