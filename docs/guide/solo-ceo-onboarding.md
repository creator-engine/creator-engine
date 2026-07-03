# Solo + CEO Mode Onboarding

*This guide is for a solo developer who has chosen **CEO mode**: you frame your
intent and ratify each gate; the agent does the rest. You do not type slash
commands — the agent drives the CE Scope/Shape/build loop under the hood,
assembles the plan and tasks, builds the work, and surfaces each decision point
for your ratification. If you prefer to drive the pipeline yourself with explicit
`cev3` commands, see [`solo-dev-onboarding.md`](./solo-dev-onboarding.md) for
the Solo + Dev path.*

> **You are in: Solo + CEO mode.** In this cell you Frame the problem and Ratify
> each gate. The agent owns inception through execution — planning, tasking,
> building, reviewing — and brings decisions to you rather than waiting for you
> to type commands. Your irreducible gestures are: framing intent, confirming
> the Scope, ratifying the bet, reviewing artifacts, and gating the merge. All
> the mechanical pipeline steps happen under the hood.

---

## How CEO mode differs from Dev mode

The five-stage loop — **Frame → Shape → Build → Review → Ship** — is the same
in every CE mode. What changes is who drives the stages and how:

| Stage | Solo + Dev (you type commands) | Solo + CEO (agent drives; you ratify) |
| --- | --- | --- |
| **Frame** | You describe the problem to the agent | Same — you describe the problem conversationally |
| **Shape** | You drive the Scope/Shape loop with `cev3 scope` and `cev3 shape` — see [`solo-dev-onboarding.md`](./solo-dev-onboarding.md) | The agent drives the Scope/Shape loop; it assembles the Scope and presents it to you for review |
| **Build** | You trigger the build after ratifying | Same — the build runs after you ratify; you don't need to start it |
| **Review** | You dispatch a reviewer, then read the PR artifacts | Same — you read the PR artifacts and judge them against the Done-when you confirmed |
| **Ship** | You run `cev3 merge --apply` | Same — `cev3 merge --apply` is the human-gated finish |

The key difference is **Shape**: in CEO mode you never run the Scope/Shape loop
by hand. The agent does that work on your behalf and surfaces the result — a
drafted Scope with its Goal, Done-when, Budget, and Change-type filled in — for
your review before anything is ratified.

---

## Phase 0 — What you need before you start

You need a CE install and a governed session. If you have not done either, follow
the install steps in [`zero-to-governed-seat-quickstart.md`](./zero-to-governed-seat-quickstart.md)
first. Once installed, `ce launch` is your daily entry point.

### The one concept to anchor on

In CEO mode the agent is your executor, not your co-typist. Instead of running
`cev3 scope` and `cev3 shape` yourself, you tell it *what you want to build*, in
plain language. It translates that intent into the governed pipeline, then brings you
the artifact to ratify. You are the CEO of the work: you set direction, you
approve gates, you own the outcome. The agent handles the mechanics.

---

## Phase 1 — Launch your governed session

```bash
ce launch
```

This opens your coding agent in a governed terminal pane — exactly the session
you already know, with CE's governance layer around it. There is no separate
CEO-mode dashboard or interface; everything flows through the normal agent
conversation. The governance layer is what changes the behavior.

What you will see is your normal agent session. Tell it you want to work in CEO
mode if it does not already know from your project configuration, and frame your
first piece of work.

---

## Phase 2 — Frame your intent (your first gesture)

In your governed session, describe what you want to build in plain language.
This is a conversational act — no commands to type. For example:

> "I want to add rate limiting to the public login API: per-IP throttling with
> configurable limits and a clear 429 response for authenticated traffic."

The agent will ask any clarifying questions it needs. Answer them. This is the
**Frame** stage: you are helping the agent understand the problem well enough to
plan it.

**What you do here:** Talk to the agent as you would to a capable colleague.
The agent handles the rest of the planning pipeline — specification, clarification,
planning, and task generation — internally. You do not need to run any step by
hand.

---

## Phase 3 — Review and ratify the Scope (your second gesture)

Once the agent has run the pipeline, it will present you with a **Scope** — the
governed unit of work. A Scope has five fields:

| Field | Meaning |
| --- | --- |
| **Goal** | what you are building, in one line |
| **Done-when** | the acceptance criteria that get graded at Review time |
| **Budget** | the effort cap you commit — the agent cannot spend beyond this |
| **Change-type** | what kind of change this is (code, docs, deploy, etc.) |
| **Ready** | CE flags this when all four fields are valid and the Scope is ratifiable |

**Read the Scope carefully.** The Done-when criteria are the most important part:
they are what the external grader will check against at Review time, not a
transcript of what the agent says. Make sure they reflect what you would actually
accept as done. If anything is wrong, tell the agent and it will revise the Scope.

When the Scope looks right and reads **Ready**, ratify it:

```bash
cev3 ratify <scope-id> --approver-ref <opaque-64-hex-digest>
```

Generate a fresh approver ref with `openssl rand -hex 32` and pass that value.
The `--approver-ref` is a value-free fingerprint: it records that a human
ratified this Scope without encoding who or any credential.

**Ratification is your explicit "yes — build this."** Nothing builds until a
Ready Scope is ratified. The agent cannot ratify on its own behalf.

> You can inspect any Scope before ratifying with `cev3 show <scope-id>`, and
> see what is queued with `cev3 status`.

---

## Phase 4 — Build and Review (the agent's lane; you watch and judge)

Once ratified, the agent drives the **Build** and opens the pull request. You
do not need to intervene. While it runs:

- The gate **refuses** any privileged action (push to a remote, access to
  credentials) and holds it for you — you will see the refusal in the session,
  with the exact rule that denied it. That is governance from outside the agent.
- Your Budget becomes the run's hard spend cap. The agent cannot exceed it.

When the build finishes, the agent opens the pull request and dispatches an
independent reviewer. You will see the PR URL in the session.

**Now you judge artifacts.** Read the PR: the diff, the test evidence, the
manifest-scoped changeset. Ask yourself: do the changes satisfy the Done-when
criteria you confirmed in Phase 3? You are not grading a transcript — you are
reading a real diff against the criteria you wrote.

---

## Phase 5 — Gate the merge (your third gesture)

When the PR looks right and the gate is green, you perform the gated merge:

```bash
cev3 merge <scope-id> --run <run-id> --apply
```

Without `--apply`, this command reads the gate and tells you exactly what is
satisfied and what is blocking — you can run it plan-only as many times as you
like. With `--apply`, it performs the gated squash-merge through branch
protection.

**The merge gate checks:** ratification bound to this Scope, independent review
on the PR, CI green. Green CI is required — it is never sufficient. Ratification
is what authorizes the merge; CI just verifies the change is well-formed.

---

## Phase 6 — The Completion Report (evidence, not memory)

After the merge:

```bash
cev3 report <scope-id> --run-id <run-id>
```

This renders the **CE Completion Report** — a compact record of what was
delivered, how it scored against your Done-when criteria, that tests were green,
that the change stayed in scope, and what fraction of the Budget it used. The
report looks like:

```text
┌─ CE COMPLETION REPORT · run <run-id> · Scope <scope-id> ──────
│ Outcome   PR opened → #N (merged)
│ Verdict   Done-when 3/3 met · tests green · in scope · 14% of Budget
│ Next      → (done)
│ Inspect   gh pr view N  |  cev3 show <scope-id>  |  cev3 artifacts <run-id>
└──────────────────────────────────────────────────────────────
```

This is your "sprint review" artifact. The evidence is durable — it persists
under `.ce/state` and is replayable from a git clone. The next piece of work
starts from artifacts, not from memory.

---

## Your decision inbox

In CEO mode the agent may surface items that require your attention between
Phases: escalations, gate holds, or items waiting for human input. These land in
your **decision inbox**:

```bash
cev3 inbox --repo <owner/repo>
```

This is a read-only view of items awaiting operator decision. Check it when the
agent flags something or when you want to see what is queued for you. Each item
in the inbox has a decision the agent cannot make on its own — your input is what
unblocks it.

---

## Your daily rhythm in CEO mode

Once you have done the first Scope, every piece of work follows the same shape:

1. **Frame** — tell the agent what you want to build, in plain language.
2. **Review the Scope** — read the Goal and Done-when the agent assembled;
   adjust if needed; confirm the Budget.
3. **Ratify** — `cev3 ratify <id> --approver-ref <digest>` — your "yes, build this."
4. **Watch the build** — the agent drives; the gate holds privileged actions for you.
5. **Judge the PR** — read the diff and evidence against your Done-when.
6. **Gate the merge** — `cev3 merge <id> --run <run-id> --apply`.
7. **Read the report** — `cev3 report <id> --run-id <run-id>` — capture the evidence, move on.

New initiative? Tell the agent about the bigger goal; it will run the full
planning pipeline and produce a backlog of Scopes. Your job is still to ratify
each one individually — the agent cannot batch-ratify on your behalf.

---

## Your irreducible gestures — what the agent cannot do for you

CE is designed so that a small set of decisions always stays with you:

| You always decide | The agent handles |
| --- | --- |
| The **Budget** on every Scope | Goal, Done-when, plan, tasks, code, and test execution |
| **Ratifying** the Scope (`cev3 ratify`) | Running the build inside the ratified envelope |
| Making a change **riskier** | Making a change safer within its envelope |
| **Judging the artifacts** at Review | Producing the artifacts and the Completion Report |
| The **gated merge** (`cev3 merge --apply`) | Opening the PR and reading the merge gate |
| Authorizing **privileged surfaces** | Refusing privileged actions and surfacing the reason |

In CEO mode the agent handles significantly more of the mechanical work — it
drives the Scope/Shape/build loop, drafts the plan, and manages the build and
review pipeline. But the boundary is the same: you ratify, you judge artifacts,
and you hold the privileged floor. The agent executes; you govern.

---

## Working with a collaborator on your repo

Everything above describes working alone, but none of it is a solo-only
mechanism — governance attaches to your **repository**, not to the number of
people using it. The moment you add a collaborator, their pull requests move
through the same required checks and the same review gate yours do. There is
no separate setup for a second contributor: the branch protection you already
have applies to everyone with write access, including you.

One thing does change in practice. Earlier, review worked even though you were
the only human involved because CE opens every pull request under its own
identity, never as you directly — that separation is what let you be a valid,
independent reviewer of your own agent's work. With a collaborator, you get a
more familiar shape on top of that: the two of you can review each other's
work directly, so cross-review between people replaces the single-human
pattern. The underlying rule does not change — whoever authored a change is
still not the one who clears its review.

Ratification stays exactly as personal as before. Your collaborator opening
and getting a Scope reviewed does not ratify anything on your behalf, and you
do not ratify on theirs. Merges that fall inside a Scope's ratified envelope —
budget, Done-when, change-type — still go through automatically once the gate
is green. Anything outside that envelope, from either of you, still waits for
an explicit, ratified decision. Adding a second person to the repo does not
widen anyone's envelope.

Because CE keeps identities distinct at every step — who framed the Scope, who
ratified it, who reviewed the PR, who the merge shipped as — the evidence
trail this produces is unambiguous even with two people working the same
repo. Nothing has to be reconstructed from memory or Slack afterward; it is
in the Completion Report and the PR history.

---

## Where to go next

| You want to… | Read |
| --- | --- |
| The front door and big picture | [`welcome.md`](./welcome.md) |
| The plain-language vocabulary tour | [`understanding-ce.md`](./understanding-ce.md) |
| The Solo + Dev hands-on path | [`solo-dev-onboarding.md`](./solo-dev-onboarding.md) |
| The Solo + Dev legacy step-by-step (speckit) | [`getting-started-step-by-step.md`](./getting-started-step-by-step.md) |
| A worked SCRUM-to-CE mapping | [`agile-to-ce-sdlc.md`](./agile-to-ce-sdlc.md) |
| The full install-to-ship pilot runbook | [`pilot-runbook.md`](./pilot-runbook.md) |
| Contribute to CE itself | [`contributing-to-ce.md`](./contributing-to-ce.md) |
