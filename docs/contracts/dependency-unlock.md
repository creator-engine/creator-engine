# Contract: Dependency Unlock

**Status:** Draft contract. Documentation-only vocabulary for future
forge-side dependency refresh slices. This document does not add runtime
enforcement, webhook handling, workflow wiring, repository mutation tooling,
credential grants, or validator behavior.

## Purpose

The dependency unlock contract names how a blocked work item declares the work
it waits on, which completed-work events make that declaration worth checking
again, and what a successful unlock means. The contract is vocabulary-first: it
defines blocker declarations, re-evaluation triggers, guardrails, and evidence
outputs so later slices can share one language without expanding authority.

An unlock check may discover that a work item no longer has a live blocker and
may propose the narrow readiness change described here. It does not close work,
move protected queues, change forge settings, bypass required checks, or grant
privileged action.

## Blocker Declarations

A blocked work item declares dependencies through bounded, parseable surfaces.
Free-form prose can explain context, but it is not the contract source unless it
also matches one of these forms.

| Declaration surface | Contract meaning | Readiness alignment |
| --- | --- | --- |
| Hold label | The work item is not eligible for pickup while a hold label is present. Dependency-qualified labels use the `blocked:<blocker-ref>` or `blocked/<blocker-ref>` family. | Aligns with the current readiness label families that produce `blocked_label`. |
| Structured dependency field | The work item names one or more blocker references in `blocked_by`, `blocked_by_issues`, `dependencies`, `depends_on`, or `required_issues`. | Aligns with the current dependency fields that produce `blocked_dependency`. |
| Markdown dependency line | The body contains a dependency phrase such as `Blocked by: #123`, `Depends on: #123`, or a fully qualified forge link. | Aligns with the current body patterns that produce `blocked_dependency`. |

A blocker reference SHOULD resolve to a single forge item. Bare numbers and
short references are interpreted only inside the same canonical project surface
that supplied the blocked work item. Fully qualified links or owner/name
references identify their own surface.

## Re-Evaluation Events

A dependency unlock candidate is re-evaluated when a possible blocker reaches a
terminal completed state.

| Event family | Re-evaluation subject | Minimum evidence |
| --- | --- | --- |
| Pull request merged | Open work items that name the merged pull request or its linked completed item as a blocker. | Repository, pull request number, merge SHA, linked item references, event timestamp. |
| Work item closed as completed | Open work items that name the completed item as a blocker. | Repository, item number, closed state reason when available, actor, event timestamp. |
| Blocker label changed | The changed item or its dependents when a hold or completion label changes. | Repository, item number, before/after labels, actor, event timestamp. |
| Scheduled replay | Open blocked work items whose blocker state may have changed while events were unavailable. | Replay window, scanned item set hash, current blocker snapshots. |

The check is subject-driven: the completed blocker event identifies candidates,
but each candidate's current body, labels, and blocker state must be read again
before any unlock mutation is proposed.

## Unlock Mutation

An unlock mutation is the smallest readiness change that turns a work item from
dependency-blocked to eligible:

- remove the dependency-specific hold label only when that label is present and
  all declared blocker references are completed;
- keep non-dependency hold labels in place;
- preserve dependency declarations in the body unless a later contract grants a
  body-edit authority; and
- emit eligibility evidence showing the candidate moved from blocked to
  ready-to-consider.

Eligibility is not assignment, launch, completion, queue movement, or privileged
action. It only means the dependency gate no longer prevents ordinary pickup
consideration.

## Dedup and Replay Guards

Every unlock check MUST derive a deterministic dedup key from stable evidence.
The minimum shape is:

```text
dependency_unlock + repository + blocked_item + blocker_ref + normalized_event_kind + evidence_hash + window
```

The `window` value is one of:

- `instant`: one completed-work event delivery or canonical payload hash;
- `short`: a burst window for duplicate label changes or repeated event
  deliveries;
- `replay`: a bounded scheduled scan period; and
- `state`: a current blocked-item body and label snapshot.

Retries with the same dedup key refresh evidence rather than producing a second
candidate mutation. A changed blocked-item snapshot, changed blocker state, or
changed event hash starts a new candidate only when the contract preconditions
still hold.

## Fail-Closed Rules

Dependency unlock is conservative:

- if a blocker reference cannot be parsed, the work item remains blocked;
- if a blocker reference cannot be resolved to exactly one item, the work item
  remains blocked;
- if any declared blocker is open, unknown, inaccessible, missing, or ambiguous,
  the work item remains blocked;
- if multiple dependency declarations disagree, the union of all parsed
  blockers is authoritative and every blocker must be completed;
- if current labels or body cannot be re-read immediately before mutation, the
  work item remains blocked;
- if the candidate has a non-dependency hold label, the work item remains
  blocked even when dependency blockers are complete;
- if the mutation target changed after evidence was computed, the candidate is
  stale and must be re-evaluated; and
- if required tooling, credentials, or egress are absent, the result is refusal
  evidence, not best-effort mutation.

## Evidence Outputs

Each dependency unlock candidate records:

- blocked work item identity;
- blocker declarations discovered from labels, structured fields, and markdown
  dependency lines;
- normalized blocker references and their live states;
- completed-work event identity or replay window;
- before/after readiness blocker reasons;
- dedup key and evidence hash;
- mutation proposal or refusal reason; and
- final eligibility interpretation.

## Non-Goals

This document does not define a webhook receiver, scheduler, queue adapter,
label manager, dependency graph store, issue template, pull request linker, or
validator check. Those require separately governed slices with explicit scope
and authority.
