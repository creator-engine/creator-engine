# How CE Builds Software

Creator Engine turns intent into governed software delivery by enforcing gates,
not by relying on agent convention. The Scope is the governing record: it says
what will change, what Done-when means, and what Change-type applies. Natural
language helps shape context; governed work begins at explicit `ce` verbs and
the Scope record.

## The Loop

CE uses the same loop for a tiny fix, a feature, or a larger project:

```text
Frame -> Shape -> Build -> Review -> Ship
              ^                 |
              |_________________|
```

Review can bounce work back. A Scope can spawn smaller Scopes. The stages are an
honest loop, not a waterfall.

| Stage | What happens | Artifact | Mandatory |
| --- | --- | --- | --- |
| Frame | Explore the goal, constraints, and repo context in plain language | Framing notes or no artifact yet | Optional before a Scope |
| Shape | Convert the framed goal into a Scope with Goal, Done-when, and Change-type | Scope record | Mandatory |
| Build | Execute the ratified Scope in a governed run | Run evidence, branch, artifacts, often a PR | Mandatory for change work |
| Review | Grade the result against Done-when and evidence | Review evidence and Completion Report | Mandatory |
| Ship | Land the governed terminal outcome | Merged PR, delivered research, or no-change record | Mandatory |

## Human Touchpoints

CE leaves three decisions with you:

1. Answer the shape questions so the Scope is concrete.
2. Ratify the Scope when the Goal, Done-when, and Change-type are right.
3. Review the artifacts and decide whether the result satisfies the Scope.

That is the CEO-mode framing: you set direction, approve the governing record,
and judge evidence. The agent handles mechanics inside the envelope.

## Scope Fields

The required user-facing fields are:

| Field | Meaning |
| --- | --- |
| Goal | What the work is trying to accomplish |
| Done-when | The checks the result must satisfy |
| Change-type | The risk class of the change, such as docs, code, schema, or deploy |
| Ready | CE has enough valid information to run after ratification |

Optional lane-aware cap: a Scope can also carry a cap when your lane requires
one. Use `%` for a subscription lane with rolling windows, or `$` for an API
lane. This is opt-in, not the default journey.

## Completion Report

CE reports the result in plain language:

| Section | Meaning |
| --- | --- |
| Outcome | What happened: PR opened, merged, research delivered, or no change needed |
| Verdict | Whether Done-when, checks, and scope stayed green |
| Next | The next human or CE action |

The report is evidence, not memory. Review the artifacts, not the transcript.

## Agile And Scrum Mapping

| Agile/Scrum | CE |
| --- | --- |
| Epic / Story | Scope |
| Sprint | Arc |
| Definition of Done | Done-when |
| Backlog | Ready Scopes |
| Sprint review | Completion Report + evidence |

## Existing PRD Pattern

An existing PRD becomes a docs-only Scope first. That Scope records the PRD as
context and does not authorize code by itself.

Child Scopes cite it when they shape real work:

```bash
ce scope checkout-retry-copy \
  --goal "Clarify checkout retry copy from the approved PRD" \
  --done-when "The checkout retry screen matches the PRD language" \
  --change-type code \
  --note "Source PRD: docs/prd/checkout-retry.md"
```

The PRD informs the child Scope. The child Scope authorizes the governed run
only after you ratify it.

## Launch Posture

The proven tenant path today is:

```bash
ce brain init
ce launch --backend host
```

Contained-by-default launch is hardening in progress. Treat contained backends
as an operator-enabled path until your repo has been told otherwise.

## Anti-Drift Rule

Welcome packs link this concepts guide and [`quickstart.md`](./quickstart.md).
They should not duplicate the CE journey, stage definitions, Scope field
language, or Completion Report vocabulary.
