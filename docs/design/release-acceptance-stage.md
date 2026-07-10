# Release Acceptance Stage

## Status

Design-only proposal. This document does not implement a validator, create a
schema, mutate release automation, close any ticket, or authorize deploy. It
defines the release-acceptance stage that should sit after the existing merge
gate and before any release ticket is allowed to close as shipped.

## Problem

Creator Engine has a merge gate: a change can be bounded, reviewed, validated,
ratified, and merged. That is not the same thing as a ship gate. A release can
still be marked complete without proving that a fresh tenant can consume the
candidate, that the release candidate was promoted from durable evidence, or
that the release ticket's closure is bound to acceptance evidence.

The release-acceptance stage closes that gap. It answers three questions from
durable artifacts:

1. Which canonical commit or artifact is the release candidate?
2. Which evidence promoted that release candidate?
3. Why was the release ticket allowed to close?

## Decision Summary

1. Add a release-acceptance state machine between release-candidate creation
   and release-ticket closure.
2. Treat a release candidate as an immutable reference plus a repository-visible
   release-acceptance record, not as a chat declaration or ticket label.
3. Make fresh-tenant rehearsal evidence the default required promotion evidence,
   using the existing `deploy/rehearsal/` harness contract rather than replacing
   it.
4. Refuse release-ticket closure unless the ticket links to the promoted
   release-acceptance record and all deploy-class claims are backed by ratified
   persistent-state probes.
5. Make the ring-0 dogfood seat the first consumer of a promoted candidate
   before broader tenant-facing release.

## State Model

### Where State Lives

Future implementation should introduce one repository-visible record per
release candidate:

```text
.ce/release-acceptance/<rc-id>.yml
```

`<rc-id>` is the normalized RC tag or release-candidate identifier. The record
is the authoritative state object. Source-host labels, issue status, GitHub
release drafts, and local operator notes are mirrors only.

Minimum fields:

```yaml
schema_version: "1"
rc_id: "vX.Y.Z-rcN"
rc_ref: "refs/tags/vX.Y.Z-rcN"
source_commit: "<40-hex canonical commit>"
artifact_manifest_sha256: "<64-hex digest or null>"
release_ticket_ref: "<source-host issue or repo-local ticket ref>"
state: "rc_marked"
state_updated_at: "<ISO-8601 UTC>"
promotion_evidence:
  fresh_tenant_rehearsal_ref: null
  ring0_dogfood_ref: null
  persistent_state_probe_refs: []
ratification_ref: null
closure_ref: null
supersedes_rc_id: null
superseded_by_rc_id: null
```

The record is updated only by governed changes. Every state transition that
changes authority, promotion, closure, deploy posture, or rollback posture is a
governed mutation and carries the same author/approver separation as the rest
of Creator Engine.

### RC Marker

An RC is marked only when all of these are true:

- The canonical commit is known and immutable by SHA.
- The RC reference is immutable. Existing release policy permits tenant-specific
  tag formats; re-pointing a tag is forbidden. A changed candidate is a new RC.
- The acceptance record exists with `state: rc_marked`.
- The release ticket is linked in the acceptance record.
- The artifact manifest digest is recorded when an artifact exists. If the RC is
  source-only, the record explicitly stores `artifact_manifest_sha256: null`.

This preserves the existing release-tag policy while adding the missing
acceptance state. The tag identifies the candidate; the acceptance record
explains whether it can ship.

### State Machine

```text
none
  -> rc_marked
  -> rehearsal_required
  -> rehearsal_passed
  -> promotion_ratified
  -> promoted
  -> ring0_consumed
  -> closure_ready
  -> closed
```

Failure and replacement states:

```text
rehearsal_required|rehearsal_passed -> held
held -> rehearsal_required
rc_marked|rehearsal_required|held -> superseded
promoted|ring0_consumed|closure_ready|closed -> reopened
```

State meanings:

| State | Meaning | Entry evidence |
| --- | --- | --- |
| `rc_marked` | The candidate exists and is immutable. | RC tag/ref, source commit, initial acceptance record, release ticket ref. |
| `rehearsal_required` | The ship gate is waiting for acceptance evidence. | Record transition after RC marking. |
| `rehearsal_passed` | Fresh-tenant rehearsal evidence has passed the gate. | Valid rehearsal JSON from the existing harness family, zero failures, no disallowed stubs, candidate identity bound to the RC. |
| `promotion_ratified` | Source or the ratified release authority has reviewed the acceptance evidence. | Ratification record linked in `ratification_ref`. Deploy-class authority remains Source-only. |
| `promoted` | The RC is accepted for first consumption. | Promotion ratification plus immutable evidence links. |
| `ring0_consumed` | The ring-0 dogfood seat consumed the exact promoted candidate. | Ring-0 evidence bound to `rc_id`, `source_commit`, and artifact digest. |
| `closure_ready` | The release ticket may close. | Promoted state, ring-0 evidence, closure integrity checks, persistent-state probes for deploy-class claims. |
| `closed` | The release ticket was closed with linked acceptance evidence. | Closure reference and final acceptance record update. |
| `held` | Promotion is blocked pending repair or rerun. | Failing rehearsal, missing evidence, probe drift, ambiguous identity, or ratification refusal. |
| `superseded` | A newer RC replaces this candidate before promotion. | New RC record links back through `supersedes_rc_id`. |
| `reopened` | A promoted or closed release has a post-acceptance defect. | Source-ratified reopen or rollback record. |

Only `closed` is terminal. `superseded` is terminal for that RC but not for the
release ticket. `reopened` starts a new governed release or rollback path; it
does not mutate the original evidence into success.

## Fresh-Tenant Rehearsal Gate

The release-acceptance stage consumes the existing fresh-tenant rehearsal
harness at `deploy/rehearsal/`. It does not redesign that harness. Slice 1
already defines:

- the runner entrypoint `deploy/rehearsal/run-rehearsal.sh`;
- the evidence format at `deploy/rehearsal/evidence-format.md`;
- the ordered first-hour stage list;
- fail-closed live mode;
- explicit `stub` accounting for stages not yet live-covered.

Promotion evidence must use that contract as the first input. A rehearsal bundle
is acceptable for promotion only when all of these hold:

- `schema_version` is a supported version.
- `harness_version` is recorded and belongs to the ratified harness lineage.
- `summary.failed == 0`.
- `summary.stubbed == 0`, unless Source ratifies a release-specific exception
  that names the stubbed stage and why it is not relevant to this RC.
- The stage list includes the first-hour stages expected by the harness version.
- The candidate under test is bound to the acceptance record by `rc_id`,
  `source_commit`, and artifact digest or source-only null digest.
- The live container or fresh tenant context is not a mounted copy of the
  developer checkout.
- The container image is digest-pinned for promotion runs, or the record names a
  ratified exception.
- The installed CLI/package version observed by the harness matches the RC's
  candidate identity or is otherwise bound by a recorded artifact manifest.

Slice 1 bundles with `stubbed > 0` remain valuable development evidence, but
they are not ship-gate evidence by default. A later harness slice can add fields
or stronger binding, but the release-acceptance gate should remain a consumer of
the harness evidence rather than a parallel rehearsal implementation.

## Promotion Evidence

Promotion requires an evidence packet referenced by the acceptance record:

1. Fresh-tenant rehearsal bundle.
2. Validation evidence for the RC artifact or source commit.
3. Review or verifier evidence for the acceptance packet itself.
4. Ratification record for promotion.
5. Persistent-state probe evidence for any deploy-class or live-state claim.
6. Ring-0 dogfood consumption evidence after promotion and before closure.

The acceptance record stores references and digests, not prose summaries alone.
The release ticket may quote the summary, but the gate reads the acceptance
record.

## Closure Integrity

The release ticket cannot close merely because a PR merged, CI passed, or a
human said the release is done. Closure requires a linked acceptance record in
`closure_ready` or `closed` state.

DoD evidence at closure is an integrity check, not a narrative convention. The
release ticket's closing action must point at the exact acceptance record and
evidence refs that satisfy the release's Definition of Done; otherwise the
ticket remains open or moves to `held`.

The closure gate should enforce:

- `release_ticket_ref` in the acceptance record matches the ticket being closed.
- `state` is `closure_ready` before closure and `closed` only after the closure
  reference is recorded.
- `promotion_evidence.fresh_tenant_rehearsal_ref` is non-null and resolves to
  accepted rehearsal evidence.
- `promotion_evidence.ring0_dogfood_ref` is non-null and binds the ring-0
  consumption to the same RC.
- `ratification_ref` resolves to the promotion ratification record.
- Every deploy-class claim in the ticket, release notes, or acceptance record
  has a linked persistent-state probe.
- No linked evidence is only local terminal output, an unstructured transcript,
  or an external dashboard screenshot without a repository-visible digest and
  probe record.

Persistent-state probes for deploy-class claims are RATIFIED doctrine. A claim
such as "installed", "running", "promoted", "deployed", "serving", "rollback
ready", or "environment healthy" is a live-state claim. It must be proved by a
probe that reads durable state after the action, records the observed state, and
binds that observation to the RC. The probe must be read-only, repeatable where
the environment permits, and stored or referenced from the acceptance record.

Closure is refused if the persistent state cannot be probed. The correct state
is `held`, not `closed with caveat`.

## Ring-0 Dogfood Seat

The first consumer of a promoted RC is the ring-0 dogfood seat. This is not a
public release channel and not a substitute for fresh-tenant rehearsal. It is
the first real CE-operated consumer after promotion.

Ring-0 evidence must show:

- the exact `rc_id`;
- the exact `source_commit`;
- the artifact manifest digest when an artifact exists;
- the command or governed action that consumed the candidate;
- the persistent state observed after consumption;
- the rollback or downgrade path known to the seat.

If ring-0 consumption fails, the RC moves to `held` or `reopened` depending on
whether broader closure already occurred. A new RC is required if the candidate
changes.

## Decisions And Rationale

### Decision 1: State Lives In Repo Records, Not Ticket Labels

Ticket labels and source-host release drafts are useful mirrors, but they are
not the acceptance state. The state lives in `.ce/release-acceptance/<rc-id>.yml`.

Rationale: the existing governance substrate favors repository-visible records
that can be audited from a clone. A ticket-only ship gate would require source
host credentials and would be easier to close accidentally.

Rejected alternative: use a GitHub issue label such as `promoted` as the state
machine. This was rejected because labels are mutable out-of-band and do not
carry evidence digests.

### Decision 2: Fresh-Tenant Rehearsal Is Required Promotion Evidence

The existing rehearsal harness is the default promotion evidence path.

Rationale: the ship gate should prove tenant consumption, not merely internal
test success. Reusing the harness keeps one rehearsal contract and lets later
slices strengthen live coverage without replacing the release gate.

Rejected alternative: write a separate release smoke-test runner. This would
split evidence formats and invite a weaker path around the fresh-tenant gate.

### Decision 3: Promotion And Closure Are Separate

`promoted` means the RC is accepted for first consumption. `closed` means the
release ticket has been closed with linked acceptance evidence after ring-0
consumption and closure checks.

Rationale: a release can pass rehearsal and still fail first consumption or
closure integrity. Keeping the states separate makes the failure visible.

Rejected alternative: treat promotion as ticket closure. This hides the
ring-0 dogfood step and makes post-promotion failures look like post-release
incidents even when no closure should have happened.

### Decision 4: Deploy-Class Claims Need Persistent-State Probes

Any deploy-class or live-state claim in the acceptance path must link to a
persistent-state probe.

Rationale: transcripts and human summaries prove what was attempted, not what
state persisted after the attempt. Release acceptance needs the latter.

Rejected alternative: accept terminal logs when they show a successful command.
This was rejected because command success can precede failed persistence,
rollback, partial install, or wrong-target mutation.

### Decision 5: Ring-0 Dogfood Is First Consumer, Not Final Evidence

Ring-0 dogfood consumption follows promotion and precedes closure.

Rationale: CE should consume its own candidate before broader release, but
ring-0 is not a fresh tenant and should not replace the clean rehearsal gate.

Rejected alternative: use ring-0 dogfood as the only acceptance gate. This was
rejected because it cannot prove first-hour fresh-tenant viability.

## Non-Goals

- No implementation of `.ce/release-acceptance/` records or schemas in this
  design unit.
- No changes to `deploy/rehearsal/` or its slice-1 harness.
- No release, deploy, rollback, or GitHub environment automation.
- No source-host webhook or issue-closing bot design beyond the closure
  integrity contract.
- No new release-agent identity.
- No public signing, artifact publication, or installer trust-chain change.
- No weakening of the existing merge gate, Definition of Done, review gate, or
  deploy-class Source-only rule.
- No use of chat transcripts, local pane state, or external tracker status as
  authoritative release acceptance state.

## Implementation Notes For Follow-On Work

The first implementation slice should add a schema and validator for the
release-acceptance record, plus a dry-run closure check that can evaluate a
ticket reference and explain why closure is allowed or refused. A later slice
can wire source-host enforcement. The rehearsal harness should evolve on its
own path; the release-acceptance validator should consume its evidence format
by version.
