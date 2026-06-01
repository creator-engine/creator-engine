# Extension + Hook Contract (G2.006.0 substrate)

The **extension + hook contract** is the declarative, validatable shape for a CE
*extension* (e.g. a Claude Code hook-pack) and the *hooks* it binds. It formalizes the
three-ring model so the model's core safety property is machine-checkable rather than
prose-only.

This is **shape-and-validation only** (`G2.006.0`): a schema + the
`extension_hook_contract` validator + examples. It **formalizes — and does not
replace** — the running hook machinery (`CLAUDE_CODE_HOOK_PACK.md` /
`CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md`, the `.claude/**` scripts, and the Ring 2
`hook_check.py` bridge). It defines no runtime, mutates no `.claude/**`, and carries no
secret/credential values.

## 1. The three rings

- **Ring 0 — HARD kernel floor.** The `ce launch` / `ce lane launch` kernel (CC-G-D):
  non-defeasible; refuses before any side effect. `enforcement_strength: hard` lives
  here and only here.
- **Ring 1 — RUNTIME, launch-pinned, DEFEASIBLE hook-pack.** The committed
  `.claude/settings.json` hooks (PreToolUse, Stop) wrapping the Ring 2 validator. Strong
  while it runs, but **defeasible** (bypassable via `--bare`, `settings.local.json`,
  `disableAllHooks`) and **fail-open** by contract.
- **Ring 2 — VALIDATOR bridge.** `creator_engine_validator hook-check`: the
  deterministic allow/deny/block decision engine the Ring 1 hooks call.

## 2. The record

An `extension_contract` (`schemas/extension-hook-contract.schema.yaml`) declares:

- `extension_id` (`^ext-…`), `extension_kind` (`hook_pack`/`connector`/`directive_pack`),
- `ring` (`ring_0`/`ring_1`/`ring_2`), `enforcement_strength`
  (`hard`/`runtime`/`defeasible`),
- `emitting_role` (canonical non-ratifying role), `operating_mode`
  (`strict`/`auto`/`transcendence`), `recorded_at`, optional `metadata`,
- and a `hooks[]` array, each hook declaring `event`
  (`PreToolUse`/`PostToolUse`/`Stop`/`UserPromptSubmit`/`SessionStart`), optional
  `matcher`, `decision_protocol` (`allow_deny`/`allow_deny_block`/`advisory`),
  `failure_posture` (`fail_open`/`fail_closed`), optional `validator_binding`, and
  `defeasible`.

The committed CC-G-C hook-pack is describable by this shape — see
`validators/examples/extension-hook-contract/valid-extension-hook-contract.ce.yml`.

## 3. The three-ring coherence invariant (headline rule)

A flat schema cannot express cross-field coherence; the validator enforces it
(`VAL-EXT-RING-COHERENCE`):

- `enforcement_strength: hard` is valid **only** at `ring_0` (the HARD floor is the
  kernel).
- A `ring_1` extension is RUNTIME/DEFEASIBLE: it MUST NOT claim `hard`; every Ring 1
  in-band hook MUST be `defeasible: true` and `failure_posture: fail_open`.

A hook that claims `hard`/non-defeasible/fail-closed at Ring 1 misrepresents the model
and is rejected.

## 4. Invariants (fail-closed validator)

- `VAL-EXT-SCHEMA` — malformed records.
- `VAL-EXT-KIND` / `VAL-EXT-RING` — unknown `extension_kind` / `ring` /
  `enforcement_strength`.
- `VAL-EXT-HOOK` — unknown hook `event` / `decision_protocol` / `failure_posture`.
- `VAL-EXT-RING-COHERENCE` — the three-ring invariant (§3).
- `VAL-EXT-ROLE` / `VAL-EXT-MODE` — non-canonical emitting role (`agent_ratifier`/
  `source` reserved-inactive) / unknown operating mode.
- `VAL-EXT-SECRET` — any inline secret/credential value (reference by name only).
- `VAL-EXT-NO-INLINE` — inline contract metadata in Markdown bodies.

## 5. Out of scope of the substrate (G2.006.0)

The harness seat-contract + hook-pack template (`G2.007.0`, which builds on this
contract), any `ce` runtime for extensions, modifying the live hook-pack/settings or
`hook_check.py`, and per-harness promotion (`G2.007.1`).
