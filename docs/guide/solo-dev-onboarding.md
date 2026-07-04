# Solo + Dev Mode Onboarding

*This guide is for a solo developer who has chosen **Dev mode**: you drive the
pipeline yourself by typing `ce` commands inside your governed agent session.
You hold the Frame + Shape decisions directly at each step. If you prefer the
agent to drive the pipeline under the hood while you frame intent and ratify
gates, see [`solo-ceo-onboarding.md`](./solo-ceo-onboarding.md) instead.*

> **You are in: Solo + Dev mode.** In this cell you type `ce` commands
> explicitly to move work through the pipeline: you file the Scope, optionally
> run the grill-me to sharpen it, ratify the bet, launch the build, review the
> artifacts, and gate the merge. Each gesture is a deliberate shell command —
> you see exactly what the governed pipeline is doing at every step.

---

## How Dev mode fits the five-stage loop

Every piece of CE work follows the same loop: **Frame → Shape → Build → Review
→ Ship**. In Dev mode you drive each stage explicitly with shell commands:

| Stage | What you do | Command |
| --- | --- | --- |
| **Frame** | Describe the problem conversationally with the agent | *(conversation)* |
| **Shape** | File a Scope; optionally run the grill-me to sharpen it | `ce scope`, `ce shape` |
| **Build** | Ratify the Scope; launch the governed run | `ce ratify`, `ce drive --spawn` |
| **Review** | Inspect the run's artifacts against your Done-when | `ce artifacts`, `ce show` |
| **Ship** | Read the merge gate; apply the gated merge | `ce merge`, `ce merge --apply` |

---

## Prerequisites

You need a CE install and a governed session. If you have not done either,
follow [`zero-to-governed-seat-quickstart.md`](./zero-to-governed-seat-quickstart.md)
first. Once installed, `ce launch` is your daily entry point.

---

## Phase 0 — Launch your governed session

```bash
ce launch
```

This opens your coding agent in a governed terminal pane. Everything flows
through the agent conversation, with CE's governance layer around it. You can
confirm the install is healthy with `ce status` — it will show an empty scope
list on a fresh workspace.

---

## Phase 1 — Frame your intent (conversational)

In your governed session, describe what you want to build in plain language.
This is a conversational act — no commands to type here. For example:

> "I want to add rate limiting to the public login API: per-IP throttling with
> configurable limits and a clear 429 response for authenticated traffic."

The agent will ask any clarifying questions it needs. Answer them. This is the
**Frame** stage: you are helping the agent understand the problem well enough
for you to write a precise Scope.

---

## Phase 2 — Shape: file the Scope

Once you have framed the problem, file a Scope — the governed unit of work.
Choose a stable slug (a short kebab-case identifier) for this piece of work:

```bash
ce scope rate-limit-login \
  --goal "Add per-IP rate limiting to the public login API with configurable limits and 429 responses" \
  --done-when "Rate limiter returns 429 with Retry-After header when per-IP limit exceeded" \
  --done-when "Limit thresholds are configurable via environment variable without code change" \
  --done-when "Tests cover the limit boundary and the 429 response shape" \
  --budget 5 \
  --change-type code
```

**Scope fields:**

| Field | Flag | Meaning |
| --- | --- | --- |
| Slug | positional | Stable identifier for this piece of work (kebab-case) |
| Goal | `--goal` | What you are building, in one line |
| Done-when | `--done-when` (repeatable) | Acceptance criteria the grader will check at Review time |
| Budget | `--budget` | Effort cap — the governed run cannot exceed this |
| Change-type | `--change-type` | Kind of change: `code`, `docs`, `schema`, `deploy`, etc. |

**The Done-when criteria are the most important part.** Write them as testable
statements. They become the grader's checklist at Review — not a description of
what the agent did, but a description of what you would accept as done.

### Optional: sharpen the Scope with the grill-me

If the Scope has gaps or you are unsure about any field, run the Shape
grill-me. It asks targeted questions and surfaces missing criteria:

```bash
ce shape rate-limit-login
```

Read the output and revise the Scope if the grill-me surfaces important gaps.
You can also inspect the Scope at any time with:

```bash
ce show rate-limit-login
```

When the Scope reads **Ready**, move to Phase 3.

---

## Phase 3 — Ratify the Scope (your "yes, build this")

**Read the Scope carefully** before ratifying. Once ratified, the governed run
is authorized to build inside the Scope's envelope. Generate a fresh approver
ref and pass it to `ce ratify`:

```bash
ce ratify rate-limit-login --approver-ref $(openssl rand -hex 32)
```

The `--approver-ref` is a value-free fingerprint. It records that a human
ratified this Scope without encoding who or any credential. The governed run
binds to this ratification: the agent cannot change the Scope or exceed the
Budget after ratification, and it cannot self-ratify on your behalf.

> **Nothing builds until a Ready Scope is ratified.** Ratification is your
> explicit authorization — the gate between planning and execution.

---

## Phase 4 — Drive: launch the governed run

First do a dry-run to confirm the dispatch envelope looks right:

```bash
ce drive rate-limit-login
```

This prints the governed dispatch envelope without launching anything. When it
looks right, spawn the run:

```bash
ce drive rate-limit-login --spawn
```

This launches the governed seat in the background. You can follow progress in
the governed session pane. The seat works within the ratified envelope — it
cannot push to a remote or access credentials without the gate surfacing that
hold for you.

---

## Phase 5 — Review: inspect the artifacts

When the run finishes and the pull request is open, review what was produced.
The run identifier appears in the session output when the run completes.

Enumerate the artifacts:

```bash
ce artifacts rate-limit-login --run-id <run-id>
```

This lists the evidence chain: the diff, test output, the coverage file, and
any other artifacts the run produced.

Inspect the Scope state after the run:

```bash
ce show rate-limit-login
```

**Now judge the artifacts.** Read the PR diff and test evidence. Ask yourself:
do the changes satisfy the Done-when criteria you wrote in Phase 2? You are
reading a real diff against criteria you set — not evaluating a summary.

---

## Phase 6 — Gate the merge

When the PR looks right and CI is green, read the merge gate:

```bash
ce merge rate-limit-login --run <run-id>
```

Without `--apply`, this command reads the gate and tells you exactly what is
satisfied and what is blocking. Run it plan-only as many times as you like.
When everything is green, apply the gated merge:

```bash
ce merge rate-limit-login --run <run-id> --apply
```

**The merge gate checks:** ratification bound to this Scope, independent review
on the PR, CI green. Green CI is required but never sufficient — ratification
is what authorizes the merge.

---

## Phase 7 — Completion report (evidence, not memory)

After the merge, render the Completion Report:

```bash
ce report rate-limit-login --run-id <run-id>
```

This renders a compact record of what was delivered: how it scored against your
Done-when criteria, that tests were green, that the change stayed in scope, and
what fraction of the Budget it used. Save this as your sprint-review artifact —
the evidence is durable and replayable from a git clone.

---

## Your daily rhythm in Dev mode

Once you have done the first Scope, every piece of work follows the same shape:

1. **Frame** — describe what you want to build conversationally with the agent.
2. **Scope** — `ce scope <slug> --goal "..." --done-when "..." --budget N --change-type <type>`.
3. **Shape (optional)** — `ce shape <slug>` to sharpen criteria if needed.
4. **Ratify** — `ce ratify <slug> --approver-ref $(openssl rand -hex 32)` — your "yes, build this."
5. **Drive** — `ce drive <slug> --spawn` — launch the governed run.
6. **Review** — `ce artifacts <slug> --run-id <run-id>` — read the diff against your Done-when.
7. **Merge** — `ce merge <slug> --run <run-id> --apply` — gate and apply.
8. **Report** — `ce report <slug> --run-id <run-id>` — capture the evidence.

Check what is in flight at any time with `ce status`. Check items awaiting
your attention with `ce inbox --repo <owner/repo>`.

---

## Your irreducible gestures — what the agent cannot do for you

CE is designed so that a small set of decisions always stays with you:

| You always decide | The agent handles |
| --- | --- |
| The **Done-when** criteria on every Scope | Goal drafting, plan, tasks, code, and test execution |
| The **Budget** on every Scope | Spending within the ratified cap |
| **Ratifying** the Scope (`ce ratify`) | Running the build inside the ratified envelope |
| Making a change **riskier** | Making a change safer within its envelope |
| **Judging the artifacts** at Review | Producing the artifacts and the Completion Report |
| The **gated merge** (`ce merge --apply`) | Opening the PR and reading the merge gate |
| Authorizing **privileged surfaces** | Refusing privileged actions and surfacing the reason |

In Dev mode you drive each gesture explicitly. You see every step of the
pipeline. The governance layer is what checks the envelope — it is outside the
agent, so it cannot be reasoned around.

---

## A note on spec-kit

An earlier version of CE used `/speckit-*` slash commands to drive the Frame
and Shape stages. Spec-kit is being retired. The `ce scope` / `ce shape` loop
replaces it: it is the same conceptual pipeline with a governed shell interface
instead of slash commands. If you have an existing project with spec-kit
artifacts, they remain valid inputs to the agent conversation; you do not need
to migrate them.

---

## Where to go next

| You want to… | Read |
| --- | --- |
| The front door and big picture | [`welcome.md`](./welcome.md) |
| The plain-language vocabulary tour | [`understanding-ce.md`](./understanding-ce.md) |
| The Solo + CEO path (agent drives; you ratify) | [`solo-ceo-onboarding.md`](./solo-ceo-onboarding.md) |
| A worked SCRUM-to-CE mapping | [`agile-to-ce-sdlc.md`](./agile-to-ce-sdlc.md) |
| The full install-to-ship pilot runbook | [`pilot-runbook.md`](./pilot-runbook.md) |
| Contribute to CE itself | [`contributing-to-ce.md`](./contributing-to-ce.md) |
