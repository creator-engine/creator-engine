# Ratification Authorization Binding Design

## Status

Design-only artifact. This document does not grant authority, change product
code, or change validator behavior by itself.

## Problem

Today, Scope ratification stores a syntactically valid digest, not a proof that
an operator authorized the act.

Verified current-state facts in this worktree:

- The v3 CLI defines `approver_ref` as a value-free 64-hex digest at
  `validators/creator_engine_validator/v3_cli.py:128`.
- `ce ratify` rejects only non-hex values, then writes only
  `approver_ref` and `ratified_scope_sha` into the Scope at
  `validators/creator_engine_validator/v3_cli.py:826` and
  `validators/creator_engine_validator/v3_cli.py:841`.
- The parser requires `--approver-ref HEX64` at
  `validators/creator_engine_validator/v3_cli.py:4239`.
- The Scope schema requires only `approver_ref` and `ratified_scope_sha`, with
  the same 64-hex pattern, at
  `validators/creator_engine_validator/schemas/scope.schema.yaml:226`.
- The `ce_scope` check accepts the same shape-only pair at
  `validators/creator_engine_validator/checks/ce_scope.py:138`.
- The dispatch gate calls `is_ratified`, which checks only the two 64-hex fields
  at `validators/creator_engine_validator/coordination.py:151`, and
  `assemble_dispatch` refuses only when that predicate is false at
  `validators/creator_engine_validator/coordination.py:256`.
- Runtime ratification evidence is also currently shaped as opaque
  `approver_ref`, `ratified_prompt_sha`, and `binding_ref` digests at
  `validators/creator_engine_validator/runtime_evidence_spine.py:77` and
  `validators/creator_engine_validator/schemas/runtime-evidence.schema.yaml:305`.
- The existing unit helper for the scope-to-run path programmatically invokes
  `ce ratify` with a fixture hex digest at
  `validators/tests/unit/test_v3_cli.py:547`. The e2e-like unit path proceeds
  from scope to ratify to drive to PR to merge at
  `validators/tests/unit/test_v3_cli.py:3595`.
- The advisory hook mechanic list is a hardcoded command classifier at
  `validators/creator_engine_validator/hook_check.py:187`. This layer is useful
  for early refusal, but the binding below must hold in validators and gates.
- `ce merge --apply` is a live side-effect path: the CLI labels `--apply` as the
  gated merge act at `validators/creator_engine_validator/v3_cli.py:2486`,
  routes through `authority_resolver.MergeDecision` at
  `validators/creator_engine_validator/v3_cli.py:2511`, and reports a merge
  after `merge_for_run` succeeds at
  `validators/creator_engine_validator/v3_cli.py:2534`.
- `merge_for_run` performs the final live PR read, drift classification, and
  apply-mode merge call at `validators/creator_engine_validator/v3_forge_join.py:827`.
  The underlying forge merge function refuses malformed or ungated requests and
  sends the head-pinned merge request only in apply mode at
  `validators/creator_engine_validator/forge/merge.py:176`.
- The existing approval-capability wall provides the right template: capability
  markers are HMAC signed, value-only, and verified against live identity claims
  in `validators/creator_engine_validator/forge/approval_capability.py:25`,
  `validators/creator_engine_validator/forge/approval_capability.py:43`,
  and `validators/creator_engine_validator/forge/approval_capability.py:378`.
  Its production secret supplier is already shaped around
  `SecretIdentityBackend` and materialized secret custody at
  `validators/creator_engine_validator/forge/approval_capability.py:252`.

## Goal

Bind agent-invoked ratification and merge apply to a recorded operator
authorization event. The agent may invoke `ce ratify` or `ce merge --apply`, but
those commands must verify an authorization event that was created from the
operator's natural-language approval and signed by a capability key unavailable
to normal worker execution.

The binding must be value-free in public artifacts: durable records may carry
opaque refs, event digests, key ids, channel names, and timestamps, but must not
store raw account identifiers, credentials, machine-specific location data, or
installation ids.

## Authorization Event

### Lifecycle

1. A ready Scope or apply-ready merge candidate produces a
   `pending-ratification` item.
2. The pending item lands in the operator's AWAITING-OPERATOR inbox. The current
   inbox read model already has an `awaiting_operator` bucket at
   `validators/creator_engine_validator/forge/controller_inbox.py:24`, and
   classifies pull requests into that bucket at
   `validators/creator_engine_validator/forge/controller_inbox.py:183`.
   Implementation should add the same concept for pending Scope and merge
   authorizations, not overload GitHub review state.
3. The operator responds in natural language on an approved channel. The product
   records a canonical authorization event and never asks the operator to type a
   raw `ce` command.
4. A trusted authorization issuer derives an HMAC-bound `approver_ref` or
   merge-apply marker from that event.
5. `ce ratify` or `ce merge --apply` consumes the event-derived binding and
   writes an `authorization_source` evidence record.

### Event Schema

The event is stored as a value-free YAML record under:

```text
.ce/state/authorization-events/<authorization_id>.authorization.yaml
```

Required fields:

```yaml
kind: authorization-event
record_type: authorization_event
schema_version: "1"
authorization_id: <hex64>
who: <operator-subject-ref>
when: <RFC3339 UTC timestamp>
scope_sha: <hex64>
utterance_digest: <hex64>
channel: <approved-channel-id>
decision: accept
operation: scope_ratify | merge_apply
target:
  scope_id: <scope-id>
  run_id: <run-id, merge_apply only>
  repo: <owner/name, merge_apply only>
  pr_number: <integer, merge_apply only>
  head_sha: <git sha, merge_apply only>
```

Canonicalization:

- `authorization_id = sha256(canonical_json(event without authorization_id))`.
- `utterance_digest = sha256(canonical_normalized_operator_utterance)`.
- `scope_sha` is the canonical Scope content digest already used by
  `ratification.ratified_scope_sha`.
- For merge apply, `scope_sha` is still required and `target.head_sha` is the
  exact head that `merge_for_run` will attempt to merge after its drift checks.

`who` is a stable operator subject reference, not a login copied from a chat
surface. The mapping from `who` to concrete account identity is private
operator-side state. Public evidence stores only the ref.

## Derived Approver Ref

For Scope ratification, `approver_ref` becomes:

```text
hex(HMAC-SHA256(ratification_binding_key,
  canonical_json({
    "domain": "ce.scope-ratification.approver-ref.v1",
    "scope_sha": <scope_sha>,
    "authorization_event_sha": <authorization_id>,
    "operation": "scope_ratify"
  })))
```

The derived ref remains 64 lower-case hex, so existing storage columns and
schema fields can migrate without a visible identifier leak. Unlike today's
free-form hex value, the gate can recompute it from the event and the key ring.

The HMAC input deliberately includes both the Scope digest and the
authorization event digest. Replaying an event for a different Scope changes
`scope_sha`; inventing a hex value without the key fails recomputation; editing
the operator utterance changes `utterance_digest`, which changes the event id.

## Key Custody And Rotation

Use the approval-capability mint system as the template, not a new secret
channel:

- A new authorization-binding issuer/verifier lives beside the existing
  approval capability issuer.
- Production key material is sourced through the same
  `SecretIdentityBackend` pattern used by the approval wall supplier. The
  supplier materializes a file-backed secret to the trusted mint/verify process
  and revokes after read, matching the existing custody seam at
  `validators/creator_engine_validator/forge/approval_capability.py:252`.
- Environment-secret fallback is allowed only for local bootstrap/manual
  controller utilities. It is not allowed for automatic production minting.
- Secrets are split by domain. The approval wall key and the ratification
  binding key are siblings in the same capability-mint system, never the same
  raw secret.
- The event and `authorization_source` record include `key_id`, not key
  material. Verifiers resolve `key_id` from the local key ring.

Rotation contract:

```yaml
kind: authorization-binding-keyring
schema_version: "1"
active_key_id: ratification-binding-2026-07
keys:
  - key_id: ratification-binding-2026-07
    status: active
    not_before: 2026-07-01T00:00:00Z
    not_after: 2026-10-01T00:00:00Z
  - key_id: ratification-binding-2026-04
    status: verify_only
    not_before: 2026-04-01T00:00:00Z
    not_after: 2026-08-01T00:00:00Z
```

Rules:

- New authorizations mint only with `active_key_id`.
- Gates verify with `active` and `verify_only` keys until the event expires or
  the migration window closes.
- A retired key cannot mint and cannot authorize new side effects. Historic
  records remain auditable through archived verifier evidence.
- Rotation is additive first, then cutover. A key cannot be deleted until all
  pending events signed by it are expired or replaced.

## Authorization Source Record

Every bound ratification writes an `authorization_source` record. There are two
placements:

- The Scope record embeds `ratification.authorization_source` so
  `coordination.is_ratified` and `ce_scope` can verify before dispatch.
- The runtime evidence chain appends a `runtime_authorization_source` record at
  run assembly or collect time so the authorization survives outside the Scope
  file. Runtime evidence chains are already content-addressed and linked at
  `validators/creator_engine_validator/runtime_evidence_spine.py:170` and
  `validators/creator_engine_validator/runtime_evidence_spine.py:205`.

Scope shape:

```yaml
ratification:
  approver_ref: <derived hex64>
  ratified_scope_sha: <scope sha hex64>
  authorization_source:
    kind: authorization-source
    record_type: authorization_source
    schema_version: "1"
    operation: scope_ratify
    authorization_id: <hex64>
    authorization_event_sha: <hex64>
    authorization_event_ref: .ce/state/authorization-events/<id>.authorization.yaml
    scope_sha: <hex64>
    utterance_digest: <hex64>
    channel: <approved-channel-id>
    authorized_at: <RFC3339 UTC timestamp>
    who_ref: <operator-subject-ref>
    key_id: <ratification-binding-key-id>
    approver_ref_alg: hmac-sha256/v1
```

Runtime chain shape:

```yaml
kind: runtime-authorization-source
record_type: runtime_authorization_source
schema_version: "1"
policy_sha: <hex64>
run_id: <run-id>
recorded_at: <RFC3339 UTC timestamp>
operation: scope_ratify | merge_apply
authorization_id: <hex64>
authorization_event_sha: <hex64>
scope_sha: <hex64>
utterance_digest: <hex64>
channel: <approved-channel-id>
who_ref: <operator-subject-ref>
key_id: <ratification-binding-key-id>
derived_ref: <approver_ref or merge_apply_ref>
derived_ref_alg: hmac-sha256/v1
target:
  scope_id: <scope-id>
  run_id: <run-id, merge_apply only>
  pr_number: <integer, merge_apply only>
  head_sha: <git sha, merge_apply only>
```

Verification at gate:

1. Load `authorization_source.authorization_event_ref`.
2. Verify the event schema and recompute `authorization_id`.
3. Verify `authorization_source.authorization_event_sha == authorization_id`.
4. Verify `scope_sha` equals the canonical Scope digest.
5. Verify `utterance_digest`, `channel`, `who_ref`, and `authorized_at` match
   the event.
6. Resolve `key_id` from the key ring.
7. Recompute the HMAC-derived ref and compare with `approver_ref` using
   constant-time comparison.
8. Refuse if the event is expired, already consumed for a single-use operation,
   operation-mismatched, target-mismatched, or key-unavailable.

## Merge Apply Capability Marker

`ce merge --apply` must receive the same capability-marker treatment as PR
approval capability markers.

Marker line:

```text
ce-merge-apply-capability: v1.<payload-b64>.<signature>
```

Claims:

```yaml
domain: ce.merge-apply.v1
repo: <owner/name>
pr_number: <integer>
scope_id: <scope-id>
run_id: <run-id>
head_sha: <git sha>
authorization_event_sha: <hex64>
scope_sha: <hex64>
issued_at: <unix seconds>
expires_at: <unix seconds>
policy_sha: <hex64 or policy id>
key_id: <merge-apply-key-id>
```

The marker is minted only after the operator authorization event exists. It is
public metadata like the approval wall marker, but its signature key is kept in
the authorization-binding key ring. Apply mode verifies the marker after
`merge_for_run` reads live PR state and before `forge.merge.merge` issues the
head-pinned merge PUT.

Apply-mode refusal conditions:

- missing marker;
- malformed marker;
- signature mismatch;
- expired marker;
- `repo`, `pr_number`, `scope_id`, `run_id`, or `head_sha` mismatch;
- authorization event missing or schema-invalid;
- authorization event does not target `merge_apply`;
- merge gate is no longer eligible after the marker was minted.

Plan mode may report that a merge would be eligible, but it must not mint,
consume, or require a merge-apply marker.

## Smoke Test Coupling

The bootstrap smoke path must exercise this binding instead of bypassing it.

Test-mode seam:

- Provide an injectable `AuthorizationBindingIssuer` with fake clock, fake
  approved channel, and temporary in-memory or tmpdir key ring.
- The smoke helper creates a real authorization event with
  `channel: test-fixture`, `who: test-operator`, and a deterministic utterance
  digest from fixture text.
- The helper derives `approver_ref` through the same HMAC function as
  production.
- `ce ratify` and `ce drive` run the normal verifier path against the temporary
  event store and key ring.
- Merge smoke, when present, mints a real `ce-merge-apply-capability` marker
  from the same fixture event and verifies it before the fake merge runner is
  called.

This seam is not a bypass flag. Forbidden implementation patterns:

- `--allow-unbound-ratification`
- `--skip-authorization-binding`
- `CE_DISABLE_RATIFICATION_BINDING`
- accepting arbitrary 64-hex values in tests after the cutover

Tests may pass fixture issuers, fixture stores, and fixture clocks. Production
code must not expose a bypass switch.

## Enforcement Layering

Hooks remain advisory. They can teach early and refuse obvious commands, but a
Ring-1 user or agent can route around a PreToolUse hook through deferral,
different execution surfaces, or direct library calls. Therefore:

1. Schema layer: Scope and runtime evidence schemas add
   `authorization_source` and marker fields.
2. Validator layer: `ce_scope`, runtime evidence validation, and PR preflight
   reject unbound active ratifications after the migration window.
3. CLI layer: `ce ratify` refuses without an event-derived ref and source
   record; `ce merge --apply` refuses without a valid merge-apply marker.
4. Coordination layer: `coordination.is_ratified` calls the verifier, not only a
   regex.
5. Gate layer: `assemble_dispatch`, `authority_resolver.MergeDecision`, and
   `merge_for_run` enforce the binding immediately before side effects.
6. Hook layer: hook rules may add early warnings for unbound `ce ratify` and
   `ce merge --apply`, but passing hooks is never treated as authorization.

The validator/gate layers are the authority. Hooks are only a user-experience
and defense-in-depth layer.

## Migration

### Compatibility Window

Define three phases:

1. Observe: legacy 64-hex refs remain accepted, but validators emit a warning
   for ready-or-later Scopes and merge-ready records without
   `authorization_source`.
2. Replace: new ratifications must be derived. Existing active legacy refs must
   be re-authorized through AWAITING-OPERATOR. The operator's yes creates a new
   authorization event and replaces the legacy `approver_ref`.
3. Enforce: validator and gates reject active legacy refs. Historic legacy
   records remain readable but cannot authorize new dispatch or merge apply.

### Legacy Record Shape

Historic records that cannot be rebound may be annotated only as non-authorizing
history:

```yaml
authorization_source:
  kind: authorization-source
  record_type: authorization_source
  schema_version: "1"
  operation: legacy_scope_ratify
  legacy_unbound: true
  legacy_observed_ref: <hex64>
  observed_at: <RFC3339 UTC timestamp>
  authorization_event_sha: null
```

Rules:

- `legacy_unbound: true` is valid only for records created before the cutover
  timestamp.
- `legacy_unbound` never authorizes dispatch, merge apply, cost opt-out, or
  other future side effects after enforce phase.
- A migration command may list legacy active refs and open pending
  authorizations. It must not fabricate `utterance_digest` or `who_ref`.
- If the operator does not re-authorize, the Scope remains parked.

### Cutover Gate

The cutover gate fails if any changed active artifact introduces:

- `ratification.approver_ref` without `ratification.authorization_source`;
- `authorization_source.legacy_unbound: true` on a new active record;
- `ce merge --apply` evidence without a valid merge-apply marker;
- a test fixture that supplies raw `approver_ref` without using the fixture
  issuer.

## Threat Model

| Threat | Before | After |
| --- | --- | --- |
| Agent invents `approver_ref` | Any lower-case 64-hex string passes CLI, schema, and coordination checks. | HMAC recomputation fails without an authorization event and key. |
| Agent reuses an old ref for a new Scope | Regex accepts replay if shape matches. | HMAC input includes `scope_sha`; replay changes the expected digest. |
| Agent edits the Scope after authorization | `ratified_scope_sha` can catch content drift where checked, but `approver_ref` is still free-form. | `authorization_source.scope_sha`, event `scope_sha`, and `ratified_scope_sha` must all match the canonical Scope digest. |
| Agent writes fake authorization metadata | No metadata exists. | Event id, utterance digest, key id, and HMAC-derived ref are recomputed at gate. |
| Worker bypasses PreToolUse hook | Hook-only enforcement can be skipped by alternate execution paths. | Validator, coordination, and merge gates enforce immediately before side effects. |
| Test smoke silently bypasses consent | Fixture hex refs can be injected directly. | Test fixtures mint real authorization events through the same HMAC seam. |
| Merge apply happens after a stale yes | `ce merge --apply` relies on merge eligibility and ambient authority. | Merge marker binds authorization to repo, PR, run, scope, and exact head SHA; live drift invalidates it. |
| Key compromise | A static undocumented secret would have unclear blast radius. | Domain-separated key ids, active/verify-only rotation, short marker TTLs, and event expiry bound replay. |
| Historic legacy records block migration | Existing refs are indistinguishable from fresh invented refs. | Legacy records are explicitly marked non-authorizing after cutover and active work must be re-authorized. |

## Mergeable Slice Plan

### Slice 1: Schemas, HMAC Library, Validator

Scope:

- Add authorization event and authorization source schemas.
- Add pure HMAC derivation and verification helpers.
- Extend `ce_scope`, dispatch-record, and runtime-evidence checks.
- Add malformed and well-formed examples for derived refs, tampered events,
  wrong scope digests, missing key ids, and legacy records.

Acceptance evidence:

- Unit tests prove the derived ref is stable for the same event and changes on
  scope, utterance, key, or event mutation.
- Validator examples fail on invented hex refs after enforce-mode is enabled.
- Existing legacy examples pass only in observe-mode and emit the expected
  warning.

### Slice 2: Ratify Flow And Smoke Seam

Scope:

- Add pending-ratification inbox records for ready Scopes.
- Change `ce ratify` to consume an authorization event or an issuer-produced
  event-derived ref.
- Embed `authorization_source` in Scope ratification and append the runtime
  authorization-source record during dispatch/collect.
- Rework bootstrap smoke helpers to use a fixture issuer and fixture key ring.

Acceptance evidence:

- CLI test: arbitrary `--approver-ref a...` is refused unless backed by a valid
  event and source record.
- Smoke test: fixture authorization event is present, the derived ref verifies,
  and no bypass flag exists.
- Dispatch test: a tampered authorization event refuses before spawn.

### Slice 3: Merge Apply Marker And Cutover

Scope:

- Add `ce-merge-apply-capability` issuer/verifier using the same capability-mint
  custody model.
- Require a valid merge-apply marker in `ce merge --apply` immediately before
  the merge call.
- Add migration listing and cutover-mode validation for legacy refs.
- Update docs and guide examples to stop teaching raw 64-hex entry.

Acceptance evidence:

- Apply-mode merge test refuses missing, expired, wrong-head, wrong-run, and
  wrong-event markers.
- Plan-mode merge remains read-only and does not require or mint a marker.
- Cutover preflight fails when a changed active artifact introduces a legacy
  unbound ref.

## Non-Goals

- No raw operator utterance storage in public repo artifacts.
- No new hosted authorization service.
- No production bypass flags.
- No reliance on hook-only enforcement.
- No change to merge eligibility rules other than requiring authorization
  binding before apply-mode side effects.
