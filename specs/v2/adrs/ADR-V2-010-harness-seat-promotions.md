# ADR-V2-010: Codex / Hermes / OpenClaw harness seat-contract promotions

## Status

Accepted for G2.007.1 draft promotions. Builds on ADR-V2-008 (harness seat-contract substrate).

## Context

G2.007.0 (ADR-V2-008) landed a harness-agnostic `seat_contract` schema + `harness_seat_contract`
validator whose `harness` enum already admits `claude_code`/`codex`/`hermes`/`openclaw`, with the
`claude_code` reference instance and the per-harness `permission_mode_flag` bindings for
`hermes`/`openclaw` explicitly deferred to G2.007.1. The substrate binds the full-permission flag
for *known in-seat harnesses* (`HARNESS_FULL_PERMISSION_FLAGS`) and enforces it via
`VAL-SEAT-PERMISSION-FLAG`. G2.007.1 resolves the deferred bindings and ships a seat-contract
instance for each remaining harness, closing the 007 harness line.

Two harness specifics make the bindings non-mechanical:

- **Hermes does not have a skip-approval flag.** The repo's authoritative Hermes governance
  (`hermes_launch_spec.py`, Hermes Agent v0.14.0) **refuses** `--yolo` as the approval-bypass
  clause `HM-D-2` and governs Hermes by pinning `--profile creator-engine`. Hermes realizes the
  harness-agnostic `full_permission_mode` (the efficient, governed, no-per-action-approval
  posture) **through that pinned governed profile**, not a `--dangerously-skip-permissions`/
  `--yolo`-style flag.
- **OpenClaw is a SEAM harness, never in-seat.** `CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md`,
  `CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md`, and `V1_PRODUCT_CONTRACT.md` all record OpenClaw as a
  `SEAM` (in-seat harnesses are exactly `{hermes, claude-code, codex}`). A seam attaches *through*
  the Controller-seat seam rather than occupying the seat, so it does not hold the full-permission
  **in-seat** Controller posture.

## Decision

G2.007.1 promotes the three harnesses onto the existing shape with the minimum surface:

- **Codex ⟹ `--yolo`** (already bound in G2.007.0): add a valid Codex seat-contract example
  (`full_permission_mode: true`, `permission_mode_flag: --yolo`). No validator change for Codex.
- **Hermes ⟹ `--profile creator-engine`**: extend `HARNESS_FULL_PERMISSION_FLAGS` with the Hermes
  binding, and add a valid Hermes seat-contract example using `permission_mode_flag: "--profile
  creator-engine"`. A Hermes seat in `full_permission_mode` declaring any other flag (e.g. the
  refused `--yolo`) is rejected with `VAL-SEAT-PERMISSION-FLAG` (covered by a new invalid fixture).
- **OpenClaw = SEAM**: add a valid OpenClaw seat-contract example with `full_permission_mode:
  false` and **no** `permission_mode_flag`; `openclaw` is intentionally **absent** from
  `HARNESS_FULL_PERMISSION_FLAGS` (a seam runs no in-seat full-permission posture, so there is no
  flag to bind). The rest of the governed posture (`ring_0`, `model_pin`, `strict_mcp_config`,
  `operator_visible`, the refused-modes floor, a `ring_1` defeasible required hook-pack) still
  applies.
- **No new validation surface.** The only edit to the landed `harness_seat_contract.py` is the
  `HARNESS_FULL_PERMISSION_FLAGS` dict (+ docstring); the existing `VAL-SEAT-PERMISSION-FLAG` rule
  and `RISK-RV2-007-FULL-PERMISSION` already cover the new binding. No new `VAL-SEAT-*` code, no new
  `@register`, no `checks/__init__.py` change, and no schema change (the `harness` enum and optional
  `permission_mode_flag` already admit every case).
- **Operator-required class (OD-15).** Per-harness landing binds `governance`+`identity`;
  `required_ratifier_role: operator`, `privileged: true`. Execution proceeds under an
  Operator-ratified prompt; review/merge remain separate ratified batches (review in a distinct
  CE-governed reviewer venue, submitting through the now-live `reviewer_authority_envelope` seam).

### Deferred alternative

A stricter rule rejecting any `openclaw` seat that declares `full_permission_mode: true` (a new
`VAL-SEAT-SEAM` code + `RISK-RV2-007-SEAM` + an `invalid-openclaw-*` fixture) was considered and
**deferred** to keep this slice minimal and avoid new-VAL/risk-coverage restructuring. The current
model encodes the OpenClaw=seam disposition by example + binding absence; the stricter assertion can
be added later if desired.

## Consequences

- All four harnesses (`claude_code`/`codex`/`hermes`/`openclaw`) now have a validated seat-contract
  instance on one harness-agnostic shape; the Controller seat remains a *role*, not a product.
- Hermes's governed full-permission posture is recorded faithfully (profile pin, not an
  approval-skip flag), and the `--yolo` refusal is documented at the seat-contract layer.
- The OpenClaw=seam invariant is represented declaratively (no in-seat full-permission, no flag).

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no runtime, no modification of
the live hook-pack/settings/launcher/`hook_check.py`, no privileged-floor relaxation, no agent
ratification, and binds no concrete vendor/harness account identity as normative. `permission_mode_flag`
records launch flags by name only — never a secret.
