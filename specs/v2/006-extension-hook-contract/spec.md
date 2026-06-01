# Extension + hook contract substrate

## Goal

G2.006.0 defines the v2 **extension + hook contract**: the shape-only, validatable
declaration of a CE extension (e.g. a Claude Code hook-pack) and the hooks it binds. It
formalizes the three-ring model (Ring 0 HARD kernel, Ring 1 RUNTIME/DEFEASIBLE
hook-pack, Ring 2 VALIDATOR bridge) so the model's core safety property is
machine-checkable. It is the dependency floor for `G2.007.0` (Harness seat-contract +
hook-pack template). It depends only on the merged `G2.001.*` foundation and `G2.002.0`
operating-mode substrate, and is class C (non-privileged `governance`; OD-16
Controller-decidable).

## Scope

Adds `schemas/extension-hook-contract.schema.yaml`, the `extension_hook_contract`
validator check (registered via `checks/__init__.py`), example fixtures, the prose
contract `docs/operations/EXTENSION_HOOK_CONTRACT.md`, and this spec + sidecar + ADR.
Shape-and-validation only: it implements no runtime, adds no `ce` command, and **does
not modify** the live hook-pack (`.claude/**`, `.claude/settings.json`) or the Ring 2
`hook_check.py` runtime — it formalizes them, with a valid example that describes the
committed hook-pack. Reuses existing validator helpers (role/secret/inline-metadata) by
import; imports no CE-event/PCL/connector/distributed-identity runtime; carries no
secret values.

## Functional requirements

### FR-001 — Extension contract shape

The substrate MUST define an `extension_contract` record: `extension_id`,
`extension_kind` (`hook_pack`/`connector`/`directive_pack`), `ring`
(`ring_0`/`ring_1`/`ring_2`), `enforcement_strength` (`hard`/`runtime`/`defeasible`),
`emitting_role`, `operating_mode`, `recorded_at`, optional `metadata`, and a non-empty
`hooks` array. Objects are closed except `metadata`.

### FR-002 — Hook contract shape

Each hook MUST declare `event` (a supported Claude Code event), optional `matcher`,
`decision_protocol` (`allow_deny`/`allow_deny_block`/`advisory`), `failure_posture`
(`fail_open`/`fail_closed`), optional `validator_binding`, and `defeasible`. Unknown
enum values are refused (`VAL-EXT-SCHEMA`/`VAL-EXT-KIND`/`VAL-EXT-RING`/`VAL-EXT-HOOK`).

### FR-003 — Three-ring coherence invariant

The validator MUST enforce the cross-field invariant: `enforcement_strength: hard` is
valid ONLY at `ring_0`; a `ring_1` extension MUST NOT claim `hard`, and its hooks MUST
be `defeasible: true` and `failure_posture: fail_open`. Violations are refused
(`VAL-EXT-RING-COHERENCE`).

### FR-004 — Role / mode floors

The substrate MUST reject non-canonical emitting roles (`agent_ratifier`/`source` are
reserved-inactive and may not emit) and unknown operating modes
(`VAL-EXT-ROLE`/`VAL-EXT-MODE`).

### FR-005 — No secrets / no inline metadata

The substrate MUST reject any inline secret/credential value (`VAL-EXT-SECRET`;
validators/credentials referenced by name only) and inline contract metadata in
Markdown bodies (`VAL-EXT-NO-INLINE`).

### FR-006 — Describable reality + decoupling

A valid example MUST model the committed CC-G-C hook-pack (Ring 1, defeasible,
fail-open PreToolUse + Stop hooks bridging `hook-check`). The substrate MUST NOT modify
any existing schema/check, `.claude/**`, `hook_check.py`, or `ce_cli.py`, and MUST NOT
implement a runtime.

## Success criteria (G2.006.0)

- `ce check validators/examples/extension-hook-contract` and the unit/examples tests:
  the valid example passes; each invalid fixture is refused with its specific
  `VAL-EXT-*` code (incl. the schema-valid ring1-claims-hard rejected by
  `VAL-EXT-RING-COHERENCE`).
- `--list-checks` includes `extension_hook_contract`; the full validator suite
  introduces no new failures.
- No runtime, no `.claude/**`/`hook_check.py`/existing-schema change, and no
  credential/secret value committed; `specs/v2/_crosswalk.yml` and the v0.1 baseline
  taxonomy are unchanged.
- PR review, approval, merge, and cleanup remain separate ratified batches (review in a
  distinct CE-governed reviewer venue, not author self-review).
