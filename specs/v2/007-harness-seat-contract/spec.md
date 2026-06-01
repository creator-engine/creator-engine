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
