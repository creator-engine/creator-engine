# Contract: Computer-Use Authority Envelope

Gate: ce-ops#142, Phase 1 only
Validator check: `ce_computer_use_authority_envelope`
Schema: `schemas/computer-use-authority-envelope.schema.yaml`

## Purpose

A Computer-Use Authority Envelope is the machine-readable authority record for
one bounded browser-mediated UI side effect. It extends the
`reviewer-authority-envelope` pattern from PR review to UI mechanics while
keeping the same fail-closed posture: one envelope authorizes one mechanic on
one closed target class, under one ratified prompt digest.

Phase 1 defines the schema, prose contract, examples, and validator semantics.
It does not wire the live Ring-2 hook to honor these envelopes. That live
hook-honoring path is a Phase 2 follow-up for ce-ops#142.

## Envelope Fields

| Field | Rule |
| --- | --- |
| `envelope_id` | Stable `cua-*` id. |
| `mechanic` | Closed enum: `account_rename`, `app_rename`, `console_setting`. |
| `target` | Closed target object. Its `target_type` must match the mechanic. |
| `mutation_class` | The exact `scope.schema.yaml` taxonomy: `docs`, `code`, `schema`, `deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`, `none`. |
| `acceptance_criteria` | Non-empty list of testable criteria. Required by the DoR check. |
| `ratified_prompt_sha` | Lowercase 64-hex digest of the prompt that authorized this UI side effect. |
| `emitting_role` | Non-ratifying role that emits the envelope. |
| `ratifier_role` | Human-in-loop ratifier role class: `operator`, `source`, or `ratifier`. |
| `operating_mode` | `strict`, `auto`, or `transcendence`; it records the mode, it does not widen the target. |
| `recorded_at` | UTC timestamp. |
| `metadata` | Optional non-authority annotations. Metadata is still scanned for secret material. |

## Closed Mechanics And Targets

The target set is closed.

| Mechanic | Required target type | Required target fields |
| --- | --- | --- |
| `account_rename` | `account` | `current_login`, `desired_login` |
| `app_rename` | `app` | `app_slug`, `desired_app_name` |
| `console_setting` | `console_setting` | `console_surface`, `setting_key`, `desired_state_ref` |

The validator rejects:

- an unknown mechanic;
- an unknown `target_type`;
- a valid mechanic paired with the wrong valid target type;
- missing target-specific fields.

This keeps the envelope from becoming a general browser capability.

## Definition Of Ready

An envelope is DoR-complete only when it carries:

- one recognized mechanic;
- one closed target with all target-specific fields;
- a valid `mutation_class`;
- non-empty `acceptance_criteria`;
- a valid `ratified_prompt_sha`;
- `emitting_role`, `ratifier_role`, `operating_mode`, and `recorded_at`.

The `ce_computer_use_authority_envelope` check emits
`VAL-CUA-DOR-INCOMPLETE` for missing or empty DoR core fields even when the
schema also reports a shape error.

## Ratification Binding

The envelope is pinned to the ratified prompt by `ratified_prompt_sha`.
The digest must be lowercase 64-hex. The `ratifier_role` records the human
authority class that accepted the prompt; agents may not satisfy this field.

The binding is value-free: the envelope records the digest and role class, not
the human's credential, session token, 2FA code, or recovery code.

## Secret And 2FA Boundary

Account logins are allowed because they identify the UI target. Credential
material is not allowed anywhere in the envelope, including `metadata`.

Forbidden material includes:

- access tokens and token-shaped strings;
- passwords, API keys, client secrets, and private keys;
- 2FA/MFA/OTP values or recovery codes.

If a UI flow reaches sudo mode, 2FA/MFA, password re-entry, or recovery-code
handling, the worker harness must HALT for human-in-loop action. The envelope
does not authorize bypassing that boundary.

## Validator Behavior

`ce_computer_use_authority_envelope` scans envelope examples and contract docs
in scope. It validates YAML records against
`schemas/computer-use-authority-envelope.schema.yaml`, then applies semantic
predicates:

| Error code | Refusal |
| --- | --- |
| `VAL-CUA-SCHEMA` | Shape is invalid. |
| `VAL-CUA-MECHANIC-TARGET` | Mechanic is unknown or does not match the target type. |
| `VAL-CUA-TARGET` | Target type is outside the closed target set. |
| `VAL-CUA-RATIFICATION` | Ratified prompt binding or human ratifier role is absent or invalid. |
| `VAL-CUA-DOR-INCOMPLETE` | DoR core is missing or empty. |
| `VAL-CUA-ROLE` | Emitting role is not a canonical non-ratifying role. |
| `VAL-CUA-MODE` | Operating mode is not `strict`, `auto`, or `transcendence`. |
| `VAL-CUA-SECRET` | Secret, credential, 2FA/MFA/OTP, or recovery-code material appears. |
| `VAL-CUA-NO-INLINE` | Envelope metadata appears inline in Markdown instead of a sidecar/example. |

## Phase 2 Follow-Up

Live Ring-2 hook honoring is deferred. Phase 2 must make the hook consume a
validated envelope reference, classify the live UI mechanic and target, and
allow only when both exactly match the envelope. Until then this is a
schema-plus-validator contract only.
