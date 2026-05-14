# Creator Engine Dependency Map

**Status**: Sprint 0 Slices B and C are complete on the delivery
view. B1 (markdown control-plane scaffold) and B2 (Definition of
Ready, Definition of Done, dependency map, risk register) landed
previously; Slice C has since landed on the canonical branch as
PR #12 (`1cfb955 ci: add baseline governance validation controls`).
Part of the **minimum repo-native delivery control plane** and
**not a Jira clone**. Markdown-only by ratified posture. Layered on
top of, and subordinate to, the Feature 001 substrate and the
Sprint 0 execution sequence. Live GitHub branch protection settings
on the remote repository remain a separate privileged future
decision and are not mutated by PR #12. `sprint-0/slice-d` is the
next candidate envelope; Slice D implementation is not authorized
by this state and requires its own Source-ratified privileged
envelope.

**Scope**: This document maps dependencies across Sprint 0 slices and
post-Sprint-0 features as recorded in [`./BACKLOG.md`](./BACKLOG.md).
It does not introduce new work items; it makes the dependency edges
between existing items explicit.

## a. Source-of-truth relationship

[`./BACKLOG.md`](./BACKLOG.md) is the authoritative carrier of
backlog rows and their `dependencies / blockers` fields. This
document is a **navigational map** over those edges. Where this
document and `BACKLOG.md` disagree about a dependency, `BACKLOG.md`
controls until reconciled.

Upstream sources of truth for dependency facts:

| Upstream source | Role |
|---|---|
| [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §5 | Sprint 0 Slice A–F execution sequence and exit gates. |
| [`../product/ROADMAP.md`](../product/ROADMAP.md) §c–§g | Feature 003–006 scope summaries, deferrals, and v1.0 integration target. |
| Feature 001 substrate (`specs/001-v0-1-governance-substrate/`, `docs/contracts/`, `schemas/`, `validators/`, `examples/`, `tenants/`) | Privileged-class rule (FR-008), ratification flow (FR-016), lifecycle states (FR-013a). |
| Feature 002 spec at `specs/002-canonical-docs-and-operating-model/spec.md` | Operating-model deferrals (FR-025) and the Phase 1 / Phase 2 boundary. |
| [`./BACKLOG.md`](./BACKLOG.md) | Authoritative dependency edges on each work-item row. |
| Optional external trackers (Jira, Linear, GitHub Projects, etc.) | **Non-canonical** mirrors only. External tracker dependency claims are advisory; see §f. |

A fresh clone is sufficient to walk this map; no external tracker
credential or network state is required.

## b. Sprint 0 dependency chain

Sprint 0 slices are sequenced in alphabetical order. The chain is:

**A → B → C → D → E → F**

| Edge | Predecessor reaches | Successor becomes eligible for |
|---|---|---|
| A → B | `Done` (merged canonical-branch evidence) | `Ready` |
| B → C | `Ratified` or `Done` | `Ready`; privileged-class envelope still requires Source ratification (§e) |
| C → D | `Ratified` or `Done` | `Ready`; privileged `identity` envelope still requires Source ratification |
| D → E | `Ratified` or `Done` | `Ready`; privileged `governance` envelope still requires Source ratification |
| E → F | `Ratified` or `Done` | `Ready`; privileged `deploy` policy authoring still requires Source ratification |

Each edge satisfies the readiness criterion in
[`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b.7. A
predecessor at `In Progress`, `Verified`, or earlier does NOT unblock
its successor.

Slice A is `Done`
([`./BACKLOG.md`](./BACKLOG.md) §c.1 cites canonical-branch commits
as durable evidence). Slice B is `Done` on the delivery view because
B1 and B2 have both landed on the canonical branch (see §c.2.1 and
§c.2.2 durable evidence on
[`./BACKLOG.md`](./BACKLOG.md)); the parent `sprint-0/slice-b` row
is decomposed in §c. The B → C edge cleared first, Slice C was
subsequently consumed under a Source-ratified privileged envelope,
and Slice C has now landed on the canonical branch as PR #12
([`./BACKLOG.md`](./BACKLOG.md) §c.3). The C → D edge is therefore
cleared for delivery-view readiness, and `sprint-0/slice-d` is the
next candidate envelope (`Ready`); Slice D implementation is still
separately gated by a Source-ratified privileged `identity`
envelope per §h. Slices E and F remain `Blocked` until their
predecessor in the chain reaches `Ratified` or `Done` AND their own
privileged-class envelope is Source-ratified. The PR #12 baseline
is file-based only; live GitHub repository settings on the remote
remain a separate privileged future decision and are not implied by
the C → D edge clearing.

## c. Slice B internal dependencies

Slice B is internally decomposed into four sub-batches, only the
first two of which are in scope for Sprint 0 exit:

```
B1 (markdown control-plane scaffold) ──► B2 (DoR / DoD / dependencies / risk)
                                              │
                                              ├──► B3 (structured YAML backlog sidecars, deferred)
                                              └──► B4 (optional external-tracker mirror/adapter design, deferred)
```

### c.1 B1 → B2

- **Predecessor**: `sprint-0/slice-b/b1` — the markdown control-plane
  scaffold introduced under Slice B1
  ([`./BACKLOG.md`](./BACKLOG.md) §c.2.1).
- **Successor**: `sprint-0/slice-b/b2` — this batch
  ([`./BACKLOG.md`](./BACKLOG.md) §c.2.2).
- **Edge condition**: B1 reaches `Ratified` or `Done`.
- **Edge state**: **cleared**. B1 is `Done` on the canonical branch
  (see §c.2.1 durable evidence in
  [`./BACKLOG.md`](./BACKLOG.md)); the B1 → B2 dependency rule is
  satisfied and B2 itself has subsequently landed.
- **Why**: B2 introduces
  [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md),
  [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md), this
  document, and [`./RISK_REGISTER.md`](./RISK_REGISTER.md), all of
  which are layered onto the B1 README / Backlog / Kanban /
  next-task-protocol scaffold. Authoring B2 against an unratified
  scaffold would have risked codifying contracts whose underlying
  scaffold Source had not yet accepted; B1 ratification removes
  that risk.

### c.2 B2 → B3 (deferred)

- **Predecessor**: `sprint-0/slice-b/b2`.
- **Successor**: `sprint-0/slice-b/b3` — optional structured YAML
  backlog sidecars.
- **Status**: `Deferred` per [`./BACKLOG.md`](./BACKLOG.md) §c.2.3.
- **Edge condition**: B2 reaches `Ratified` or `Done` AND Source
  ratifies a sidecar schema. Until both clear, B3 remains
  `Deferred`.
- **Why deferred**: Sprint 0 exit gate #2 is satisfied by markdown
  artifacts alone; YAML sidecars are not required.

### c.3 B2 → B4 (deferred)

- **Predecessor**: `sprint-0/slice-b/b2`.
- **Successor**: `sprint-0/slice-b/b4` — optional external-tracker
  mirror/adapter design (Jira / Linear / GitHub Projects).
- **Status**: `Deferred` per [`./BACKLOG.md`](./BACKLOG.md) §c.2.4.
- **Edge condition**: B2 reaches `Ratified` or `Done` AND Source
  ratifies an adapter design. Implementation of any adapter is a
  further separately-ratified batch.
- **Why deferred**: External trackers are non-canonical mirrors only
  ([`./README.md`](./README.md) §d). A fresh clone MUST be
  sufficient to identify the next recommended task without any
  adapter wiring.

## d. Post-Sprint-0 feature dependencies

The downstream features 003–006 each depend on a specific Sprint 0
slice's policy outline. The implementation feature instantiates the
policy that the slice authored. Feature 002 instantiated the
canonical-doc specification consumed by Slice A; no further
post-Sprint-0 work depends on Slice A independently of Slice B's
completion.

### d.1 Feature 003 depends on `sprint-0/slice-c`

- **Edge**: `sprint-0/slice-c` reaches `Ratified` or `Done` →
  `feature-003` becomes eligible for shaping.
- **Edge state**: **cleared**. Slice C is `Done`
  ([`./BACKLOG.md`](./BACKLOG.md) §c.3); Feature 003 is eligible
  for shaping but remains `Deferred` until separately Source-
  ratified.
- **Scope link**: Slice C authors the thin GitHub / CI / PR governance
  policy outline ([`./BACKLOG.md`](./BACKLOG.md) §c.3); Feature 003
  instantiates that policy as `.github/workflows/`, the PR template,
  branch protection (and live GitHub settings if Source ratifies
  that mutation), review policy / CODEOWNERS, and the CI
  verifies-not-ratifies rule
  ([`../product/ROADMAP.md`](../product/ROADMAP.md) §c). PR #12
  landed the Slice C baseline (validation workflow, PR template,
  branch protection policy file) only; the live GitHub setting and
  any extension of the baseline remain Feature-003-or-later work
  under a separately ratified privileged envelope.
- **Privileged-class note**: Feature 003 mutations are privileged
  (`governance` / `security` / `deploy`) per Feature 001 FR-008;
  ratification is required per-batch per §h.

### d.2 Feature 004 depends on `sprint-0/slice-d`

- **Edge**: `sprint-0/slice-d` reaches `Ratified` or `Done` →
  `feature-004` becomes eligible for shaping.
- **Scope link**: Slice D authors the Codex reviewer identity record
  (or equivalent), the QA / review evidence template, and the
  review-gate definition ([`./BACKLOG.md`](./BACKLOG.md) §c.4);
  Feature 004 instantiates the governed Codex / QA / security
  identities and their evidence schemas
  ([`../product/ROADMAP.md`](../product/ROADMAP.md) §d).
- **Privileged-class note**: identity creation is a privileged
  `identity`-class mutation per Feature 001 FR-008; per-identity
  ratification is required per §e.

### d.3 Feature 005 depends on `sprint-0/slice-e`

- **Edge**: `sprint-0/slice-e` reaches `Ratified` or `Done` →
  `feature-005` becomes eligible for shaping.
- **Scope link**: Slice E authors the manual Assignment Envelope
  template, worktree / branch naming conventions, the
  one-driver-per-worktree rule, envelope consumption and scope-audit
  checklists, and dry-run evidence
  ([`./BACKLOG.md`](./BACKLOG.md) §c.5); Feature 005 implements the
  Hermes dispatcher, worktree lifecycle automation, sandboxing,
  parallel runtime, and conflict-detection mapping
  ([`../product/ROADMAP.md`](../product/ROADMAP.md) §e).
- **Privileged-class note**: dispatcher policy changes are privileged
  `governance`; per-batch Source ratification is required per §e.

### d.4 Feature 006 depends on `sprint-0/slice-f`

- **Edge**: `sprint-0/slice-f` reaches `Ratified` or `Done` →
  `feature-006` becomes eligible for shaping.
- **Scope link**: Slice F authors the release-candidate checklist,
  merge-approval checklist, deployment-approval policy,
  rollback / evidence expectations, explicit `deploy` mutation
  ratification rule, and the statement of currently absent
  deployment targets / environments
  ([`./BACKLOG.md`](./BACKLOG.md) §c.6); Feature 006 instantiates
  the release agent identity, the release / deploy / rollback
  records, GitHub environments, and the Source-approved deploy gates
  for SDLC transitions T22–T24
  ([`../product/ROADMAP.md`](../product/ROADMAP.md) §f).
- **Privileged-class note**: the `deploy` mutation class is
  Source-only per Feature 001 FR-008 regardless of any Feature 006
  automation. Feature 006 implements the execution surface;
  ratification of every deploy remains Source's.

## e. v1.0 integration target

v1.0 is an integration target reached when Features 001 through 006
have landed and Sprint 0 exit gates 1–12 are satisfied
([`../product/ROADMAP.md`](../product/ROADMAP.md) §g). Its
dependency closure is:

| Dependency | Required state |
|---|---|
| `sprint-0/slice-a` | `Done` |
| `sprint-0/slice-b` (B1 and B2) | `Done` |
| `sprint-0/slice-c` | `Done` |
| `sprint-0/slice-d` | `Done` |
| `sprint-0/slice-e` | `Done` |
| `sprint-0/slice-f` | `Done` |
| `feature-003` | `Done` (implements Slice C policy outline) |
| `feature-004` | `Done` (instantiates Slice D identities and schemas) |
| `feature-005` | `Done` (implements Slice E manual protocol as automation) |
| `feature-006` | `Done` (implements Slice F policy as release / deploy execution) |

v1.0 is not a feature in itself; it is the named state at which the
full SDLC state machine is exercised end-to-end with every privileged
gate human-ratified. The Phase 1 / Phase 2 boundary in Feature 002
applies: Phase 2 expansion is itself a ratified amendment and is not
implemented by v1.0.

## f. Reserved item — US3 A1

- **Item**: `us3/a1` ([`./BACKLOG.md`](./BACKLOG.md) §d).
- **Current status**: `Blocked` / `Deferred`.
- **Blockers**:
  1. Sprint 0 MUST reach exit (every Sprint 0 exit gate satisfied,
     including those that v1.0 depends on under §e).
  2. Source MUST explicitly ratify a future spec authorizing the US3
     A1 area before any implementation begins.
- **Why**: US3 A1 is recorded only as a referenceable id; its
  mutation class is to be determined by the future spec and MUST be
  treated as potentially privileged until classified. Starting work
  on US3 A1 before both blockers clear is an authority conflict per
  Feature 002 FR-018 and a contract violation of the Sprint 0
  execution sequence in
  [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
  §5.

## g. Dependency status table

This table summarizes the current state of each dependency edge
using the eight-column delivery-view status vocabulary from
[`./BACKLOG.md`](./BACKLOG.md) §a. It is a derivative view; rows
that change in `BACKLOG.md` MUST be re-derived here under the
post-merge update procedure in
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d.

| Predecessor | Successor | Predecessor delivery status | Edge state |
|---|---|---|---|
| `sprint-0/slice-a` | `sprint-0/slice-b` | `Done` | Cleared. |
| `sprint-0/slice-b/b1` | `sprint-0/slice-b/b2` | `Done` | Cleared; B1 landed on the canonical branch. |
| `sprint-0/slice-b/b2` | `sprint-0/slice-b/b3` | `Done` | B1 → B2 → B3 predecessor rule cleared by B2 landing; successor remains `Deferred` pending a Source-ratified sidecar schema. |
| `sprint-0/slice-b/b2` | `sprint-0/slice-b/b4` | `Done` | B1 → B2 → B4 predecessor rule cleared by B2 landing; successor remains `Deferred` pending a Source-ratified adapter design. |
| `sprint-0/slice-b` | `sprint-0/slice-c` | `Done` | Cleared; Slice B is complete on the delivery view. Successor `Done` as of PR #12 (`1cfb955`). |
| `sprint-0/slice-c` | `sprint-0/slice-d` | `Done` | Cleared; Slice C landed on the canonical branch. Successor `Ready` as the next candidate envelope. Slice D implementation still requires a Source-ratified privileged `identity` envelope per §h. |
| `sprint-0/slice-d` | `sprint-0/slice-e` | `Ready` | Successor `Blocked`. Privileged `governance` envelope still requires §h. |
| `sprint-0/slice-e` | `sprint-0/slice-f` | `Blocked` | Successor `Blocked`. Privileged `deploy` policy authoring still requires §h. |
| `sprint-0/slice-c` | `feature-003` | `Done` | Predecessor `Done`; successor remains `Deferred`. Live GitHub branch protection settings and any extension of the landed `.github/` baseline (CODEOWNERS, etc.) still require a separately ratified privileged envelope per §h. |
| `sprint-0/slice-d` | `feature-004` | `Blocked` | Successor `Deferred`. Privileged `identity` envelope still requires §e. |
| `sprint-0/slice-e` | `feature-005` | `Blocked` | Successor `Deferred`. Privileged `governance` envelope still requires §e. |
| `sprint-0/slice-f` | `feature-006` | `Blocked` | Successor `Deferred`. Privileged `deploy` envelope still requires §e. |
| Sprint 0 exit (gates 1–12) + Features 003–006 | `v1.0` | mixed (`Done` / `Deferred` / `Blocked`) | Successor `Deferred` until every dependency in §e is `Done`. |
| Sprint 0 exit + Source-ratified future spec | `us3/a1` | (not yet specced) | Successor `Blocked` / `Deferred` per §f. |

## h. Rule — privileged dependencies require ratification requests, not implementation shortcuts

A dependency is **privileged** when clearing it requires a mutation
in any of `deploy`, `governance`, `identity`, `security`,
`attestation`, or `redaction` per Feature 001 FR-008.

When the action required to clear a privileged dependency is itself
a privileged mutation, the next task is a **ratification request to
Source**, not the implementation. This rule mirrors
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.5 and is
restated here for the dependency map:

1. The implementer MUST NOT begin work on the privileged dependency
   simply because the upstream edge has cleared. The envelope must
   itself be Source-ratified before consumption (Feature 002 FR-008).
2. A passing CI run, agent review text, an external tracker green
   check, or a "go ahead" message on a non-designated surface MUST
   NOT substitute for Source ratification of the privileged envelope.
3. Author/approver separation (Feature 001 FR-007) applies: the
   actor who will author the privileged mutation MUST NOT be its
   ratifier.
4. The fastest path to unblock a downstream item that depends on a
   privileged predecessor is to land the predecessor under a
   Source-ratified envelope — not to shortcut the predecessor's
   readiness or done gate.

Examples in this map: every Slice C–F edge, every Feature 003–006
edge, and every privileged-class branch of v1.0 fall under this rule.

## i. Rule — external tracker dependencies are advisory unless mirrored in the repo-visible backlog

External tracker entries (Jira, Linear, GitHub Projects, or any
future adapter ratified under Slice B4) are **non-canonical** per
[`./README.md`](./README.md) §d. For the dependency map:

1. An external tracker entry MAY appear as an `external_tracker_ref`
   on a backlog row, but it is a non-canonical pointer. It does NOT
   introduce a dependency edge into this map.
2. A dependency claim that exists only in an external tracker is
   **advisory**. It MUST NOT block, unblock, or otherwise change the
   status of a repo-visible backlog item until the claim is mirrored
   into [`./BACKLOG.md`](./BACKLOG.md) and Source ratifies the
   updated row.
3. If an external tracker entry and the repo-visible backlog
   disagree about a dependency edge, the repo-visible backlog
   controls until Source ratifies an update. The disagreement is
   recorded per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.6 and
   resolves into either a backlog amendment or a tracker correction.
4. A fresh clone with no network access and no tracker credential
   MUST be sufficient to walk this map. Dependency edges that are
   only visible via an external tracker are not part of the map.

## j. Maintenance rules

1. New dependency edges are introduced by adding or amending the
   `dependencies / blockers` field on the relevant backlog row in
   [`./BACKLOG.md`](./BACKLOG.md). This document is then re-derived
   from that row under the post-merge update procedure in
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d.
2. The Sprint 0 chain **A → B → C → D → E → F** is a structural
   invariant of Sprint 0 execution
   ([`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
   §5). Any proposal to reorder the chain is a privileged
   `governance` amendment per §h.
3. The privileged-class note on each edge MUST NOT be silently
   dropped. A privileged envelope that lands without Source
   ratification recorded against it is a contract violation per
   Feature 002 FR-008 and an authority conflict per FR-018.
4. Instance-local facts (absolute filesystem paths, in-flight PR
   numbers, terminal pane identifiers, local session queues,
   secrets, credentials, tokens) MUST NOT enter this document. Only
   merged PR numbers in canonical-branch commit subjects MAY be
   cited as historical evidence.

## k. Acceptance posture for B2

This document satisfies the B2 envelope's dependency-map
requirements:

- Names the Sprint 0 dependency chain **A → B → C → D → E → F**
  (§b).
- Names the B1 → B2 edge inside Slice B and the B3 / B4 deferred
  successors of B2 (§c).
- Names the Feature 003 → Slice C, Feature 004 → Slice D, Feature
  005 → Slice E, and Feature 006 → Slice F edges (§d).
- Names the v1.0 dependency closure on Sprint 0 exit and Features
  003–006 (§e).
- Names the reserved US3 A1 item as `Blocked` until Sprint 0 exits
  and Source ratifies a future spec (§f).
- Provides a dependency status table using the eight delivery-view
  statuses (§g).
- States the rule that privileged dependencies require ratification
  requests, not implementation shortcuts (§h).
- States the rule that external tracker dependencies are advisory
  unless mirrored in the repo-visible backlog (§i).
