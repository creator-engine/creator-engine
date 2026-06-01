# Harness Seat-Contract (G2.007.0 substrate)

The **harness seat-contract** is the harness-agnostic, validatable shape for a governed
Controller seat: the harness occupying the seat, its required launch posture, the
posture-defeating modes it must refuse, the full-permission mode (the efficient Controller
operating mode) and its harness-specific flag, the enforcement ring, and the required
hook-pack.

CE does **not** privilege any harness — the Controller seat is a *role*, not a product.
`claude_code` is the reference instance; `codex`, `hermes`, and `openclaw` instantiate the
same contract (promoted in `G2.007.1`).

This is **shape-and-validation only** (`G2.007.0`): a schema + the `harness_seat_contract`
validator + a hook-pack template + examples. It **formalizes — and does not replace** — the
CC-G-* runtime (`CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md`, `.claude/**`, `hook_check.py`,
`ce launch`). It defines no runtime, mutates no `.claude/**`, and carries no secrets.

## 1. The record

A `seat_contract` (`schemas/harness-seat-contract.schema.yaml`) declares `seat_id`,
`harness` (`claude_code`/`codex`/`hermes`/`openclaw`), a `launch_posture`, a `refused_modes`
list, an `enforcement_ring`, an embedded `required_hook_pack` (a G2.006.0
`extension_contract`), `emitting_role`, `operating_mode`, `recorded_at`, optional `metadata`.

## 2. Required posture (§4)

The validator enforces (`VAL-SEAT-POSTURE`): `setting_sources` includes `project` and
**excludes** `local` (so `settings.local.json` cannot weaken the posture); `strict_mcp_config:
true`; `terminal_visibility: operator_visible` (a CE-observed pane, no hidden/headless seat);
`model_pin: true` (explicit model pin, no implicit default); `enforcement_ring: ring_0` (a
seat-contract is enforced at the HARD Ring 0 floor).

## 3. Refused-modes floor (§5)

`refused_modes` MUST refuse every genuinely posture-*defeating* mode (`VAL-SEAT-PROHIBITED`):
`bare`, `print_headless` (`-p`/`--print`), `background_agents`, `remote_control`,
`settings_local_weakening`. These defeat the enforcement layer and are never permitted.

## 4. Full-permission mode — the efficient Controller mode (headline)

A Controller needs **full permissions** to do its job efficiently, without stopping for
per-action human approval. `full_permission_mode` is therefore a first-class, **sanctioned**
`launch_posture` field — **not** a refused mode: it does not defeat enforcement (PreToolUse
hooks still fire under full permissions, and `permissions.deny` outranks hook output).

The headline cross-field invariant (`VAL-SEAT-FULL-PERMISSION`):

> `full_permission_mode: true` ⟹ `ring0_hook_pack_confirmed: true`.

The **Ring 0 hook-pack confirmation is the safety substitute for per-action approval** —
full permissions are safe only once Ring 0 has verified the hook-pack is active.

**Harness-specific accommodation.** Implementation varies by harness; CE keeps the
generalization (`full_permission_mode`) while recording the concrete flag in
`permission_mode_flag`. The validator binds it for known harnesses
(`VAL-SEAT-PERMISSION-FLAG`): `claude_code` ⟹ `--dangerously-skip-permissions`; `codex` ⟹
`--yolo`. `hermes`/`openclaw` accept any flag until `G2.007.1` promotes them.

## 5. Required hook-pack (§6)

`required_hook_pack` MUST be a valid G2.006.0 `extension_contract` of kind `hook_pack` at
`ring_1` with every hook `defeasible: true` and `failure_posture: fail_open`
(`VAL-SEAT-HOOKPACK`) — the seat's in-band enforcement depends on a committed, defeasible
Ring 1 hook-pack. `templates/hook-pack.template.yaml` is the generic scaffold a harness
instantiates.

## 6. Other floors

`VAL-SEAT-HARNESS` (unknown harness); `VAL-SEAT-ROLE`/`VAL-SEAT-MODE` (non-canonical emitting
role — `agent_ratifier`/`source` reserved-inactive — / unknown operating mode);
`VAL-SEAT-SECRET` (inline secret/credential value; reference flags/validators by name only);
`VAL-SEAT-NO-INLINE` (inline contract metadata in Markdown).

## 7. Out of scope of the substrate (G2.007.0)

The per-harness promotions (`G2.007.1` Codex/Hermes/OpenClaw), any `ce` runtime or
`ce launch` change, and modifying the live hook-pack/settings or `hook_check.py`.
