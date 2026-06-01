# Harness seat-contract + hook-pack template substrate

## Goal

G2.007.0 defines the v2 **harness seat-contract**: the harness-agnostic, validatable shape
for a governed Controller seat, plus a reusable hook-pack template. It generalizes the
Claude-Code-specific seat-contract prose into a `seat_contract` record that any harness
(`claude_code`/`codex`/`hermes`/`openclaw`) instantiates — CE does not privilege a harness.
It depends on the merged `G2.002.0` (operating-mode) and `G2.006.0` (extension + hook
contract), is class O (`governance`+`identity`; OD-15), and is the dependency floor for
`G2.007.1` (per-harness promotions).

## Scope

Adds `schemas/harness-seat-contract.schema.yaml`, the `harness_seat_contract` validator
(registered via `checks/__init__.py`), `templates/hook-pack.template.yaml`, example fixtures,
the prose contract `docs/operations/HARNESS_SEAT_CONTRACT.md`, and this spec + sidecar + ADR.
Shape-and-validation only: no runtime, no `ce` command, no launcher change, and **no
modification** of `.claude/**`, `hook_check.py`, the existing Claude-Code seat-contract doc,
or the G2.006.0 `extension_hook_contract` check (reuse by import). A valid example describes
the committed Claude Code seat. Carries no secret values.

## Functional requirements

### FR-001 — Seat-contract shape

The substrate MUST define a `seat_contract` record: `seat_id`, `harness` (bounded enum),
`launch_posture`, `refused_modes`, `enforcement_ring`, an embedded `required_hook_pack`,
`emitting_role`, `operating_mode`, `recorded_at`, optional `metadata`. Objects closed except
`metadata`.

### FR-002 — Required posture

The validator MUST enforce: `setting_sources` includes `project` and excludes `local`;
`strict_mcp_config: true`; `terminal_visibility: operator_visible`; `model_pin: true`;
`enforcement_ring: ring_0` (`VAL-SEAT-POSTURE`). Unknown `harness` is refused
(`VAL-SEAT-HARNESS`).

### FR-003 — Refused-modes floor

`refused_modes` MUST include every posture-defeating mode (`bare`/`print_headless`/
`background_agents`/`remote_control`/`settings_local_weakening`) (`VAL-SEAT-PROHIBITED`).

### FR-004 — Full-permission-mode invariant + harness flag binding

`full_permission_mode` is the efficient, sanctioned Controller mode (NOT a refused mode); if
true it MUST require `ring0_hook_pack_confirmed: true` (`VAL-SEAT-FULL-PERMISSION`). For known
harnesses the `permission_mode_flag` MUST bind (`claude_code` ⟹ `--dangerously-skip-permissions`;
`codex` ⟹ `--yolo`) (`VAL-SEAT-PERMISSION-FLAG`); `hermes`/`openclaw` are bound by G2.007.1.

### FR-005 — Required hook-pack reuse

`required_hook_pack` MUST be a valid G2.006.0 `extension_contract` of kind `hook_pack` at
`ring_1` with defeasible/fail-open hooks (`VAL-SEAT-HOOKPACK`), reusing the
`extension_hook_contract` vocabulary by import.

### FR-006 — Role/mode + secret/inline floors; decoupling

Reject non-canonical `emitting_role` (`agent_ratifier`/`source` reserved-inactive) and
unknown `operating_mode` (`VAL-SEAT-ROLE`/`VAL-SEAT-MODE`); reject inline secret values
(`VAL-SEAT-SECRET`) and inline Markdown metadata (`VAL-SEAT-NO-INLINE`). Modify no existing
schema/check, `.claude/**`, `hook_check.py`, the existing seat-contract doc, or `ce_cli.py`;
implement no runtime. `templates/hook-pack.template.yaml` independently validates against the
G2.006.0 `extension_hook_contract`.

## Success criteria (G2.007.0)

- `ce check validators/examples/harness-seat-contract` and the unit/examples tests: the valid
  example (modeling the Claude Code seat) passes; each invalid fixture is refused with its
  specific `VAL-SEAT-*` code (incl. `VAL-SEAT-FULL-PERMISSION` and `VAL-SEAT-PERMISSION-FLAG`).
- `templates/hook-pack.template.yaml` validates against the G2.006.0 `extension_hook_contract`.
- `--list-checks` includes `harness_seat_contract`; the full validator suite introduces no new
  failures.
- No runtime, no `.claude/**`/`hook_check.py`/existing-doc/existing-check/existing-schema/
  `ce_cli.py` change; no credential/secret value committed; `specs/v2/_crosswalk.yml` and the
  v0.1 baseline taxonomy unchanged.
- PR review, approval, merge, and cleanup remain separate ratified batches (review in a
  distinct CE-governed reviewer venue, not author self-review).

# G2.007.2 — reviewer-venue side-effect-authority seam

## Goal

G2.007.2 builds the runtime seam that lets a distinct CE-governed reviewer venue legitimately
perform the `pr_review` restricted mechanic: a bounded, auditable `reviewer_authority_envelope`
that the Ring-2 hook (`hook_check`) honors for exactly one mechanic on exactly one PR. It resolves
the governance debt from PR #106 (whose distinct-venue review was correctly hard-denied submission
and landed once via an Operator override). It depends on the merged `G2.006.0` + `G2.007.0`, is
class O (`governance`+`identity`+`security`), and is the runtime continuation of the 007 seat line
(sequenced before `G2.007.1`).

## Scope

Adds `schemas/reviewer-authority-envelope.schema.yaml`, the `reviewer_authority_envelope` validator
(registered via `checks/__init__.py`), the prose contract `docs/operations/REVIEWER_VENUE_AUTHORITY.md`,
examples, and this spec slice + ADR. **Modifies the Ring-2 enforcement engine `hook_check.py`**
(authority resolution + the restricted-mechanic decision) — the first gate to do so — but **not**
`.claude/**` (Ring-1 wrapper/settings), `ce launch`/the launcher, or any other existing check.
Backward-compatible: with no valid envelope, behavior is unchanged. The launcher minting path and
hook-side head/actor verification are deferred.

## Functional requirements

### FR-007 — Reviewer-authority envelope shape

The substrate MUST define a `reviewer_authority_envelope` record: `envelope_id`, `mechanic`
(`pr_review`), `pr_number`, `head_sha`, `actor`, `ratified_prompt_sha`, `emitting_role`,
`operating_mode`, `recorded_at`, optional `metadata`. The validator MUST reject unknown mechanics
(`VAL-RVA-MECHANIC`), missing bindings (`VAL-RVA-BINDING`), non-canonical roles/unknown modes
(`VAL-RVA-ROLE`/`VAL-RVA-MODE`), inline secrets (`VAL-RVA-SECRET`), and inline Markdown metadata
(`VAL-RVA-NO-INLINE`).

### FR-008 — Bounded authority resolution + decision

`hook_check.build_context` MUST resolve `side_effect_authority` from a validated bounded envelope
(not a raw loose token), and `_mechanics_would_deny` MUST allow a restricted mechanic ONLY when the
envelope's `mechanic` equals the classified action AND (for `pr_review`) the command's target PR
number equals `pr_number`. Wrong PR / wrong mechanic / no envelope MUST deny; merge/push/comment/
`ce launch` MUST stay denied.

### FR-009 — Backward compatibility + decoupling

With no/invalid envelope, governed restricted mechanics MUST be denied exactly as before; all other
hook behavior MUST be unchanged (only the one loose-token test is updated). The gate MUST modify no
`.claude/**`, launcher, other existing check/schema, or `ce_cli.py`, and carry no secret value.

## Success criteria (G2.007.2)

- `ce check validators/examples/reviewer-authority-envelope` + the tests: the valid example passes;
  each invalid fixture is refused with its specific `VAL-RVA-*` code.
- Hook-decision tests: `gh pr review` is denied without authority, allowed only with a valid matching
  envelope, denied on a wrong PR / wrong mechanic; `gh pr merge`/`git push`/`gh pr comment`/`ce launch`
  remain denied under a `pr_review` envelope.
- `--list-checks` includes `reviewer_authority_envelope`; the full suite introduces no new failures;
  the existing `hook_check` tests stay green except the one updated loose-token test.
- No `.claude/**`/launcher/other-check/`ce_cli.py` change; `_crosswalk.yml` + the v0.1 baseline
  taxonomy unchanged; no secret committed.
- PR review/approval/merge remain separate ratified batches; this gate's own PR lands via a one-time
  logged Operator override (bootstrap), after which the seam is used legitimately.

# G2.007.1 — Codex / Hermes / OpenClaw harness promotions

## Goal

G2.007.1 promotes the remaining harnesses (`codex`/`hermes`/`openclaw`) onto the
harness-agnostic seat-contract shape landed in G2.007.0: it binds the per-harness
`permission_mode_flag` for the in-seat harnesses and ships a valid seat-contract instance for
each. It depends on the merged `G2.007.0` (substrate) and `G2.007.2` (reviewer-venue authority
seam), is class O (`governance`+`identity`; per-harness landing; OD-15), and closes the 007
harness line. The schema is unchanged — its `harness` enum already admits all four harnesses —
so this is a validator-binding + examples + docs slice, with no new `VAL-SEAT-*` code.

## Scope

Extends `HARNESS_FULL_PERMISSION_FLAGS` in the `harness_seat_contract` validator (adds the
Hermes binding) and adds three valid example seat-contracts (`codex`/`hermes`/`openclaw`) plus
one invalid fixture, this spec section, the `spec.ce.yml` slice update, and `ADR-V2-010`.
**No** schema change, **no** new check/`VAL-SEAT-*` code, **no** `checks/__init__.py` change,
**no** runtime/`ce`/`ce launch`/launcher change, and **no** modification of `.claude/**`,
`hook_check.py`, the `reviewer_authority_envelope` surface, the G2.006.0
`extension_hook_contract` check, or any other existing schema/check. Carries no secret values.

## Functional requirements

### FR-010 — Per-harness promotions

- **Codex** ⟹ `--yolo` (bound in G2.007.0): a valid Codex seat-contract with
  `full_permission_mode: true` and `permission_mode_flag: --yolo` passes
  (`VAL-SEAT-PERMISSION-FLAG` enforces the bound flag).
- **Hermes** ⟹ `--profile creator-engine`: Hermes realizes `full_permission_mode` through its
  **pinned governed profile**, not a skip-approval flag — the `--yolo` approval-bypass is
  *refused* by Hermes governance (`hermes_launch_spec.py`, `HM-D-2`). The validator binds
  `hermes ⟹ --profile creator-engine` (`VAL-SEAT-PERMISSION-FLAG`); a Hermes seat in
  `full_permission_mode` declaring any other flag (e.g. `--yolo`) is rejected.
- **OpenClaw** is a **SEAM** harness (never in-seat): it runs **no in-seat
  `full_permission_mode`** (`full_permission_mode: false`) and binds **no**
  `permission_mode_flag` (intentionally absent from `HARNESS_FULL_PERMISSION_FLAGS`), while
  still satisfying the rest of the governed posture. (A stricter rule rejecting any
  `openclaw` + `full_permission_mode: true` seat — `VAL-SEAT-SEAM` — is a deferred follow-up.)

All G2.007.0 invariants (required posture, refused-modes floor, the
`full_permission_mode ⟹ ring0_hook_pack_confirmed` headline invariant, the `ring_1` defeasible
required hook-pack, role/mode/secret/inline floors) hold unchanged for every promoted harness.

## Success criteria (G2.007.1)

- `ce check validators/examples/harness-seat-contract` + the tests: the new
  `valid-codex-seat.ce.yml` / `valid-hermes-seat.ce.yml` / `valid-openclaw-seat.ce.yml` pass;
  `invalid-hermes-flag-mismatch.ce.yml` is refused with `VAL-SEAT-PERMISSION-FLAG`; the
  `claude_code` reference example and all prior G2.007.0 fixtures stay green.
- `--list-checks` is unchanged (still `harness_seat_contract`; no new check or `VAL-SEAT-*`
  code); the full validator suite introduces no new failures.
- No schema change; no existing check changed beyond the `HARNESS_FULL_PERMISSION_FLAGS`
  dict + docstring; no `.claude/**`/`hook_check.py`/`checks/__init__.py`/`ce_cli.py` change;
  `specs/v2/_crosswalk.yml` + the v0.1 baseline taxonomy unchanged; no secret committed.
- PR review/approval/merge remain separate ratified batches; the review runs in a distinct
  CE-governed reviewer venue and is the first to submit through the now-live
  `reviewer_authority_envelope` seam (not an Operator override).
