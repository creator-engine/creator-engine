# Guided Journey UX

This design defines the guided journey as the human command surface for a
governed factory. It is not a second control plane. It is the CEO-readable
projection of the same face the system already has: ONE governed state, ONE
operator relationship, ONE emission stream.

The product promise is simple: open the surface, know where the work is, see
what needs a human, ratify batches when the work is ready, and leave again
without inspecting per-artifact machinery.

## Executive Read

The guided journey is organized around the canonical path:

`Frame -> Shape -> Build -> Review -> Ship`

The surface answers four questions in that order:

1. Where is the portfolio right now?
2. What needs me?
3. What can I approve or reject as a batch?
4. What shipped while I was away?

The primary interaction point is the awaiting-operator inbox. Everything else
is context for that inbox. The journey arc explains why a decision is waiting;
the details pane explains what happens if the operator accepts or declines; the
completion feed explains what happened after earlier decisions. The operator
should never have to hunt through logs, branches, individual artifacts, or
internal tracker references to regain command.

The UI is a read-model and emission surface of the ONE face. It renders state,
decisions, evidence, and completion reports that already exist. It may focus,
filter, group, and explain them. It must not invent authority, maintain a
parallel backlog, store its own ratification truth, or become a chat-shaped
control plane.

## Product Shape

The first screen is a working surface, not a dashboard about a dashboard.

It has three stable regions:

- Journey rail: `Frame -> Shape -> Build -> Review -> Ship`, with counts,
  health, oldest waiting age, and the current portfolio marker.
- Awaiting-operator inbox: the action list, grouped for batch ratification and
  sorted by consequence, age, and dependency order.
- Emission feed: completion reports, refusals, blocked reports, and shipped
  outcomes, ordered newest first with stable artifact links.

The operator-facing vocabulary is product language. A row says "Approve the
checkout recovery plan" or "Decline deploy to production" before it exposes any
technical source. Internal ticket identifiers, queue implementation labels, and
worker transcript fragments are not user copy.

The journey rail is a map, not the workspace. The inbox is where work happens.
The feed is the memory of what happened.

## Journey Read-Model

The journey read-model is a fold over existing governed state. It computes a
stable projection for the UI and no more.

| Stage | What the human sees | What the surface must preserve |
| --- | --- | --- |
| Frame | Proposed or newly discovered work, stated as user value and current uncertainty. | No Scope exists until the operator confirms intent or another governed source creates one. |
| Shape | Ratifiable Scopes and plans, with Goal, Done when, Budget, Change type, Ready, and missing fields. | Shape cannot dispatch Build until the governed ready predicate and ratification are satisfied. |
| Build | Active governed runs, their goal, elapsed time, budget posture, and current blocker if any. | The UI does not steer the worker directly; it renders the run state and authorized decision requests. |
| Review | Independent review state, test evidence, scope fidelity, and unresolved findings. | Review evidence is not ratification. It is evidence for the back gate. |
| Ship | Items ready for final ratification, delivered research, merged changes, no-change outcomes, and blocked terminal reports. | Ship remains the governed terminal delivery surface, not a shortcut around merge, approval, or authority rules. |

Each item carries a human title, stage, recommended next action, consequence
class, evidence summary, and absolute references. A technical drawer may expose
machine fields, but the row must be understandable without opening it.

Absolute references are first-class. The operator sees exact paths such as
`/workspace/acme-store/docs/product/checkout-recovery.md`,
`/workspace/acme-store/app/routes/checkout.tsx`, and
`/var/tmp/ce-runs/2026-07-10-120455/completion-report.md` when those artifacts
are relevant. Relative paths are acceptable only as secondary display inside a
repo context already made explicit by an absolute root.

## Awaiting-Operator Inbox

The awaiting-operator inbox is the core interaction point because it is the only
place the system asks the human to exercise judgment.

An inbox item must answer:

- What decision is being requested?
- Why did CE pause here?
- What will happen if I accept?
- What will happen if I decline?
- What will CE not do without my decision?
- Which absolute files, reports, or external URLs support the request?

The list is grouped by decision shape:

- Shape ratification: approve or reject one or more ready Scopes or plans.
- Risk ratification: accept a proposed higher-consequence action.
- Review disposition: accept a resolution path after independent review
  evidence exists.
- Ship ratification: authorize a terminal delivery, no-change outcome, or
  blocked closeout.
- Human-only input: provide a missing credential, account step, policy answer,
  product decision, or external fact.

Rows use product nouns first and implementation detail second. The operator does
not review per-artifact work in fleet mode. They ratify batches of prepared,
graded decisions.

## Batch Ratification Ergonomics

Batch ratification is not a bulk checkbox bolted onto a queue. It is a prepared
decision packet.

A batch has a title, included decisions, shared rationale, excluded decisions,
aggregate risk, blocking dependencies, and a preview of the resulting emission
feed entries. The operator can accept the whole packet, decline the whole
packet, or split out specific rows that are not ready for a common decision.

The default batch groups only decisions with the same decision type and
compatible consequence class. The UI may propose:

- "Approve 6 ready documentation Scopes."
- "Ship 4 reviewed research deliveries."
- "Decline 3 stale plans and keep 2 for re-shaping."

It must not hide heterogeneity. If one item needs production authority and
another is a documentation Scope, they do not share a one-click batch. If one
item is blocked by another, the dependency order is visible before ratification.

Every batch confirmation repeats the action in plain language, shows the count,
shows the highest consequence class, and links the absolute evidence roots. The
operator's decision emits a governed event; the UI only presents and submits the
prepared decision through the existing authority path.

## Vacation Test

The guided journey passes the vacation test when an operator can return after
days away and command the factory from the surface alone.

On return, the surface must replay:

- What was framed, shaped, built, reviewed, shipped, blocked, or declined while
  the operator was gone.
- Which decisions are currently waiting, how old they are, and what depends on
  them.
- Which batches are ready for ratification and which items were intentionally
  excluded from those batches.
- Which completion reports were emitted, with outcomes, verdicts, next actions,
  and absolute artifact references.
- Which runs stopped because CE lacked authority, evidence, credentials, or
  product judgment.
- Which assumptions changed since the operator last acted.

The surface must distinguish "nothing needs you" from "I cannot see whether
anything needs you." Silence is a state only when the read-model source is
healthy.

The test fails if the operator must ask a worker what happened, read transcripts
to find the next decision, infer state from branch names, or recognize internal
tracker identifiers to regain control.

## Completion Reports As Emission Feed

Completion reports are the feed. They are the canonical human-readable emissions
of governed work turns.

A feed entry renders:

- Outcome: PR opened, merged, review submitted, research delivered, no change,
  blocked, or refused.
- Verdict: Done-when status, validation posture, scope fidelity, review posture,
  and budget posture when available.
- Next: the next human or system step, including whether the item now appears in
  the awaiting-operator inbox.
- Artifacts: absolute paths and external links for the delivered work and
  evidence.
- Time and actor: when the report was emitted and which governed role produced
  it.

The feed is append-oriented. It can be filtered by stage, product area,
decision type, or outcome, but the UI must not rewrite prior reports into a new
story. Corrections appear as later emissions.

This gives the operator a durable narrative without turning transcripts into a
product primitive.

## Decisions

### Decision: One Face, Read-Model UI

The guided journey is a read-model and emission surface over the ONE governed
face.

Rationale: CE's safety and usefulness come from having one authority spine. A UI
that stores its own truth would create drift, conflicting answers, and unclear
ratification provenance. A read-model can still be rich: it can group, summarize,
prioritize, explain, and submit prepared decisions while preserving the governed
source.

Rejected alternatives:

- A standalone journey database that reconciles with CE later. Rejected because
  reconciliation would become a second authority.
- A chat-first command surface that interprets operator intent directly.
  Rejected because free-form control blurs ratification and weakens batch
  review.
- A per-worker dashboard. Rejected because the operator needs portfolio command,
  not artifact babysitting.

### Decision: Inbox Before Board

The awaiting-operator inbox is primary; the stage rail is explanatory context.

Rationale: the operator's scarce action is judgment. Stage counts help them
understand the factory, but decisions are where they spend attention. Putting
the inbox first turns CE from a status viewer into a command surface without
making the UI an authority.

Rejected alternatives:

- A stage-board-first surface. Rejected because it makes the operator traverse
  the factory to find decisions.
- A notification-only surface. Rejected because notifications lack the context
  required for ratification.
- A report-only surface. Rejected because the operator also needs to act on
  waiting decisions.

### Decision: Batch Ratification As Prepared Packets

Batch ratification is presented as typed, evidence-backed decision packets.

Rationale: fleet mode works only if the operator can approve or reject coherent
sets without reading every artifact. The UI must make the grouping logic visible
so the operator can trust the packet and split exceptions.

Rejected alternatives:

- One giant approve-all button. Rejected because it hides consequence and
  heterogeneity.
- Per-artifact review by default. Rejected because it does not scale and defeats
  the fleet premise.
- Automatic ratification from passing checks. Rejected because checks provide
  evidence; they are not the operator decision.

### Decision: Absolute References In Every Decision

Decision rows and feed entries carry full absolute references for supporting
artifacts.

Rationale: a returning operator needs unambiguous grounding. Absolute paths make
handoff, audit, and cross-worktree inspection reliable. They also prevent
ambiguous "see report.md" copy when multiple repos, runs, or worktrees are
active.

Rejected alternatives:

- Relative-only references. Rejected because they depend on hidden context.
- Transcript links as the primary evidence. Rejected because transcripts are too
  noisy and not structured as decision evidence.
- Internal tracker identifiers as the primary reference. Rejected because the
  product surface should describe the work, not require knowledge of the
  implementation queue.

### Decision: Completion Reports Are The Feed

The emission feed is built from completion reports rather than a separate
activity stream.

Rationale: completion reports already answer outcome, verdict, next, and
artifacts. Reusing them preserves one narrative and keeps the feed tied to
governed emissions.

Rejected alternatives:

- A social-style activity feed assembled from low-level events. Rejected because
  it buries decisions in noise.
- A hand-written status summary. Rejected because it creates editorial drift.
- Worker transcripts as history. Rejected because they are not CEO-first,
  stable, or ratification-shaped.

## Non-Goals

- No second brain, backlog, or planning authority.
- No chat-with-the-factory control plane.
- No per-artifact review requirement in fleet mode.
- No UI-owned ratification ledger.
- No hidden merge, approval, credential, or deployment authority.
- No internal ticket references as product copy.
- No transcript mining as the normal operator workflow.
- No replacement of the mechanical state machine or canonical stage vocabulary.
- No new lifecycle invented by the journey surface.

## Implementation Consequences

The implementation should have a sharp boundary:

- The model layer folds governed state into journey, inbox, batch, and feed
  read-models.
- The view layer renders those models, preserves stable sort and grouping, and
  submits prepared decisions through existing authority paths.
- The authority layer records ratification and refusal events; the UI does not
  mint or store them independently.
- The feed layer consumes completion reports as append-only emissions.

Every UI action should be explainable as either focus, filter, inspect, split
batch, submit prepared decision, or open artifact. Anything outside that list is
probably trying to become a second control plane.

The first useful slice is a read-only journey rail plus awaiting-operator inbox
and completion feed. Batch submission can follow once the read-model proves it
can group decisions without hiding consequence or dependency order.
