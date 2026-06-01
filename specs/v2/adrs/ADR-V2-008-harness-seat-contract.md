# ADR-V2-008: Harness seat-contract + hook-pack template substrate

## Status

Accepted for G2.007.0 draft substrate.

## Context

CE's Controller-seat posture exists today as Claude-Code-specific prose
(`CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md`: §4 required posture, §5 prohibited flags, §6
required hook-pack presence). There is **no harness-agnostic, validatable seat-contract
record** and no reusable hook-pack template, so the posture lives only in prose and is bound
to one harness. G2.007.0 generalizes it — the Controller seat is a *role*, not a product —
building on the merged G2.006.0 extension + hook contract, and is the floor for G2.007.1
(Codex/Hermes/OpenClaw promotions).

## Decision

G2.007.0 adds `schemas/harness-seat-contract.schema.yaml`, the `harness_seat_contract`
validator (registered via `checks/__init__.py`), `templates/hook-pack.template.yaml`,
examples, a prose contract, spec, and this ADR.

Key boundary decisions:

- **Shape-only substrate.** Schema + validator + template + examples + docs only. No runtime,
  no `ce` command, no `ce launch`/launcher change, and **no modification** of `.claude/**`,
  settings, `hook_check.py`, the existing Claude-Code seat-contract doc, or the G2.006.0
  `extension_hook_contract` check (reuse by import). A valid example must *describe* the
  committed Claude Code seat.
- **Harness-agnostic by design.** The `seat_contract` is keyed by a bounded `harness` enum
  (`claude_code`/`codex`/`hermes`/`openclaw`); the schema/validator are identical across
  harnesses. `claude_code` is the reference instance; `G2.007.1` promotes the others.
- **Full-permission mode is the efficient Controller mode, not a refused flag.** A Controller
  needs full permissions to work without per-action human approval. `full_permission_mode` is
  a first-class, sanctioned `launch_posture` field — it does not defeat enforcement (hooks
  still fire; `permissions.deny` outranks hook output). The headline invariant
  (`VAL-SEAT-FULL-PERMISSION`) is `full_permission_mode: true` ⟹ `ring0_hook_pack_confirmed:
  true` — the Ring 0 hook-pack confirmation is the safety substitute for per-action approval.
  Implementation varies by harness, so the generalization (`full_permission_mode`) is retained
  while the concrete flag (`permission_mode_flag`) is recorded and bound per known harness
  (`claude_code` ⟹ `--dangerously-skip-permissions`; `codex` ⟹ `--yolo`;
  `VAL-SEAT-PERMISSION-FLAG`).
- **Required posture + refused-modes floor.** `setting_sources` project-not-local,
  `strict_mcp_config`, `operator_visible`, `model_pin`, and `enforcement_ring: ring_0` are
  required; the genuinely posture-*defeating* modes (`bare`/`print_headless`/
  `background_agents`/`remote_control`/`settings_local_weakening`) must be refused.
- **Required hook-pack reuse.** The embedded `required_hook_pack` must be a valid G2.006.0
  `extension_contract` of kind `hook_pack` at `ring_1` with defeasible/fail-open hooks
  (reuse by import; `VAL-SEAT-HOOKPACK`). `templates/hook-pack.template.yaml` is the generic
  scaffold and independently validates against the G2.006.0 check.
- **Operator-required class (OD-15).** The seat-contract binds `governance`+`identity`;
  `required_ratifier_role: operator`, `privileged: true`. Execution proceeds under an
  Operator-ratified prompt; review/merge remain separate ratified batches (review in a
  distinct CE-governed reviewer venue).

## Consequences

- The Controller-seat posture is declarative, validatable, and harness-agnostic on a stable
  substrate that `G2.007.1` (per-harness promotions) builds on.
- The committed Claude Code seat remains the untouched reference implementation; later work
  can emit/validate seat-contract records for each harness against this schema.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no runtime, no
modification of the live hook-pack/settings/launcher, no privileged-floor relaxation, and no
agent ratification.
