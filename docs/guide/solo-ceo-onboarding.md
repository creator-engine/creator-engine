# Solo + CEO Mode Onboarding

*This guide is for a solo developer who has chosen **CEO mode**: you frame the
work in plain language, authorize each gate, and judge the delivered artifacts.
The governed agent turns that direction into scoped work, builds inside the
approved envelope, and brings decisions back to you.*

If you prefer the command-driven path where you operate the pipeline yourself,
use [`solo-dev-onboarding.md`](./solo-dev-onboarding.md).

> **You are in: Solo + CEO mode.** Your irreducible gestures are intent,
> authorization, artifact review, and final shipping approval. The agent handles
> the mechanical pipeline steps and tells you when a decision needs a human.

---

## How CEO mode differs from Dev mode

The five-stage loop -- **Frame -> Shape -> Build -> Review -> Ship** -- is the
same in every CE mode. What changes is who drives the mechanics.

| Stage | Solo + Dev | Solo + CEO |
| --- | --- | --- |
| **Frame** | You describe the problem and drive the next commands. | You describe the problem conversationally. |
| **Shape** | You operate the Scope and Shape loop yourself. | The agent drafts the Scope and presents it for your review. |
| **Build** | You trigger the build after ratifying. | The agent starts the build after you authorize it. |
| **Review** | You inspect the PR and its evidence. | Same: you judge the PR against the accepted criteria. |
| **Ship** | You operate the merge gate directly. | You authorize the agent to apply the merge gate. |

The key difference is **Shape**. In CEO mode the agent assembles the Scope and
brings you the three fields that matter:

| Field | Meaning |
| --- | --- |
| **Goal** | what you are building, in one line |
| **Done-when** | the acceptance criteria that get graded at Review time |
| **Change-type** | what kind of change this is, such as code, docs, or deploy |

You review that trio before anything is authorized. If it is wrong, say what to
change. If it is right, authorize the agent to proceed.

---

## Phase 0 -- What you need before you start

You need a CE install and a governed agent session. If you have not done either,
start with [`quickstart.md`](./quickstart.md).

There is no separate CEO dashboard. You work in the normal agent conversation;
the difference is that you state intent and authorization while the agent runs
the governed mechanics on your behalf.

<details><summary>For technical readers -- starting the session</summary>

The quickstart shows the exact launch command for your environment. Once the
session is open, the CEO-mode flow in this guide happens through conversation.

</details>

---

## Phase 1 -- Frame your intent

Start by telling the agent what you want built. Use normal language and include
the outcome you care about.

> "I want to add rate limiting to the public login API: per-IP throttling with
> configurable limits and a clear 429 response."

The agent may ask clarifying questions. Answer them directly. This is the
**Frame** stage: you are helping the agent understand the problem well enough to
shape a responsible unit of work.

Good CEO-mode framing usually includes:

- the user-visible goal
- the boundary of the change
- any acceptance criteria you already know
- any risk or rollout concern the agent should account for

You do not need to name internal steps. The agent will translate your intent into
the governed pipeline.

---

## Phase 2 -- Review the Scope

The agent will present a Scope before building. Read it as an authorization
document, not as a transcript. The Scope should clearly state:

- **Goal:** the change you intend to ship
- **Done-when:** the evidence that will make the work acceptable
- **Change-type:** the kind of work being performed

If the Scope is too broad, too vague, or missing an acceptance criterion, say so:

> "Tighten the Done-when so it includes a test for the 429 response body."

or:

> "Limit this Scope to the login API. Do not include signup throttling yet."

The agent revises the Scope and shows it again. Nothing should build until the
Scope describes the work you are willing to authorize.

---

## Phase 3 -- Authorize the build

When the Scope is ready and the Goal, Done-when, and Change-type are correct,
authorize the agent in plain language:

> "This Scope looks right. Go ahead and build it."

or:

> "Approved: build the login rate-limiting Scope as written."

That authorization is the CEO-mode equivalent of saying "yes, build this." The
agent records your approval and starts the build inside the ratified envelope.
The agent cannot authorize its own work.

<details><summary>Under the hood -- what the agent records</summary>

The agent records your authorization against the ready Scope using the ratify
operation and a fresh approver reference. That reference is a value-free
fingerprint: it records that a human approved the Scope without embedding a
credential or personal identity in the command.

</details>

---

## Phase 4 -- Build and Review

After authorization, the agent builds the change and opens a pull request. While
it runs, the governance layer may refuse privileged actions and require the agent
to surface the reason to you. If that happens, read the hold and decide whether
to authorize, redirect, or stop.

When the build finishes, the agent gives you the PR link and the validation
evidence. Now your job is artifact review:

- read the diff
- read the tests or other validation evidence
- compare the result to the Done-when criteria you accepted
- ask for changes if the PR does not satisfy the Scope

You are not grading how persuasive the agent sounds. You are judging whether the
artifact matches the Goal and Done-when.

---

## Phase 5 -- Authorize shipping

When the PR satisfies the Scope, review is complete, and the required checks are
green, authorize the agent to apply the merge gate:

> "The PR satisfies the Scope and the checks are green. Apply the merge gate."

or:

> "Ship this change."

The merge gate checks ratification, independent review, and green CI. Green CI is
required, but it is not enough by itself. Your authorization is what lets the
agent finish the change.

<details><summary>Under the hood -- what the agent applies</summary>

The agent reads the merge gate first. When the gate is satisfied and you have
authorized shipping, the agent applies the governed merge operation for the
ratified Scope and current run.

</details>

---

## Phase 6 -- Read the Completion Report

After shipping, the agent produces a Completion Report. Treat it as evidence,
not memory. It should tell you:

- what was delivered
- which PR carried the work
- whether the Done-when criteria were met
- which validation evidence was green
- whether the change stayed in scope

The next piece of work starts from these artifacts, not from a remembered chat
summary.

<details><summary>Under the hood -- report retrieval</summary>

The agent can render the report and related artifacts from the recorded Scope and
run. The report is durable enough to inspect from a fresh clone.

</details>

---

## Awaiting-decision items

Sometimes work pauses because the agent needs a human decision: a privileged
surface is held, a review asks for product judgment, or a change would exceed the
Scope you approved.

The agent surfaces these awaiting-decision items in the forge UI where the work
is already being reviewed, usually as PR comments, review threads, or issue
comments. Each item should explain:

- what decision is needed
- what the agent recommends, if anything
- what happens if you approve, reject, or revise the request

Answer in the forge or in the governed agent conversation. Your response unblocks
the next step; the agent then records and executes the authorized action.

---

## Your daily rhythm in CEO mode

Every piece of work follows the same shape:

1. **Frame** -- tell the agent what you want, in plain language.
2. **Review the Scope** -- inspect the Goal, Done-when, and Change-type.
3. **Revise if needed** -- correct the Scope before any build is authorized.
4. **Authorize the build** -- tell the agent to proceed once the Scope is right.
5. **Judge the PR** -- read the diff and evidence against the Done-when.
6. **Authorize shipping** -- tell the agent to apply the merge gate when the PR is ready.
7. **Read the report** -- keep the delivered evidence with the work.

New initiative? Tell the agent the larger goal. It can turn that into a backlog
of Scopes, but each Scope still needs its own review and authorization.

---

## Your irreducible gestures

CE is designed so that a small set of decisions always stays with you:

| You always decide | The agent handles |
| --- | --- |
| Whether the Scope's Goal, Done-when, and Change-type are acceptable | Drafting and revising the Scope |
| Whether to authorize the build | Building inside the approved envelope |
| Whether the PR satisfies the accepted Done-when | Producing the PR, validation evidence, and report |
| Whether to authorize shipping | Reading and applying the merge gate after authorization |
| Whether to allow privileged surfaces | Refusing privileged actions until you decide |

The agent executes; you govern.

---

## Working with a collaborator on your repo

Everything above describes working alone, but the mechanism attaches to your
repository, not to the number of people using it. When you add a collaborator,
their pull requests move through the same required checks and review gate.

Review becomes more familiar with two people: you can review each other's work
directly. The underlying rule does not change. The person who authored a change
does not clear its review.

Ratification stays personal. Your collaborator does not authorize work on your
behalf, and you do not authorize work on theirs. Merges that stay inside a
ratified Scope still go through the governed gate once review and CI are green.
Anything outside that envelope waits for a new explicit decision.

Because CE records each governance step -- framing, authorization, review, and
ship -- the evidence trail remains clear even when more than one person works in
the same repository.

---

## Where to go next

| You want to... | Read |
| --- | --- |
| The front door and big picture | [`welcome.md`](./welcome.md) |
| The canonical command path | [`quickstart.md`](./quickstart.md) |
| How CE builds software | [`how-ce-builds-software.md`](./how-ce-builds-software.md) |
| The plain-language vocabulary tour | [`understanding-ce.md`](./understanding-ce.md) |
| The Solo + Dev hands-on path | [`solo-dev-onboarding.md`](./solo-dev-onboarding.md) |
| The complete start-to-ship walkthrough | [`complete-walkthrough.md`](./complete-walkthrough.md) |
| A worked SCRUM-to-CE mapping | [`agile-to-ce-sdlc.md`](./agile-to-ce-sdlc.md) |
| The full install-to-ship pilot runbook | [`pilot-runbook.md`](./pilot-runbook.md) |
| Contribute to CE itself | [`contributing-to-ce.md`](./contributing-to-ce.md) |
