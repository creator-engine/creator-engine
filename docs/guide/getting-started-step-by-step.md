# Getting Started, Step by Step — A Beginner Walkthrough

*This is the linear, hands-on guide. If you have never used Creator Engine
before, open this, start at the top, and follow it through to the end. It assumes
you can write code and that you know how a backlog, sprints, and acceptance
criteria work — but it assumes **nothing** about CE. Every new concept and every
command is explained the first time it appears, along with exactly what you'll
see and what each step produces.*

> **Where this fits.** [`welcome.md`](./welcome.md) is the front door (the big
> picture). [`understanding-ce.md`](./understanding-ce.md) is the plain-language
> tour of CE's vocabulary. This guide is the thing you *do*: a start-to-finish
> walkthrough. When a step touches a concept those guides explain more deeply,
> we link to them rather than repeat them.

---

## Phase 0 — Orientation (read this once, then start)

### What Creator Engine is, in one paragraph

Creator Engine (CE) runs **your own coding agent — under governance.** You keep
using the agent you already use; CE wraps a structured, auditable workflow around
it so real work is planned, checked, reviewed, and merged **on purpose**, and so
the risky things an agent can attempt are refused until a human says yes. The
single idea to hold onto: **the thing that decides whether work is good lives
*outside* the agent.** You judge artifacts — a plan, a diff, the evidence, the
pull request — never a chat transcript. For the why behind this, read
[`understanding-ce.md`](./understanding-ce.md).

### If you already know Agile/SCRUM

You'll find the muscle memory transfers. A constitution is your team's
non-negotiable Definition-of-Done standards, set once. The spec-driven pipeline
is grooming a PRD into a refined, dependency-ordered backlog. A **Scope** is a
single well-formed backlog item with explicit acceptance criteria. **Ratify** is
the sprint-planning "yes, we commit to this." The build loop is the work itself,
with review and merge gates you already recognize. The difference is that an AI
agent does the building, and CE enforces the gates from outside it.

### Mini-glossary (the words you'll meet below)

| Term | What it means |
| --- | --- |
| **Governed seat / governed session** | Your normal coding-agent session, but with CE's governance wrapped around it. Looks like your usual agent; refuses privileged actions until you approve. |
| **The gate** | The check that sits *outside* the agent and holds a privileged action (push, merge, secret access) until a human ratifies it. CI can turn the gate green, but only a human opens it. |
| **Constitution** | Your project's non-negotiable standards (testing rigor, review rules, what "done" means). Set first; it flows down into every spec, plan, and task. |
| **Scope** | One small, ratifiable unit of work: a Goal, the "Done-when" checks, and a Budget you set. CE's backlog item. |
| **Done-when** | The acceptance criteria for a Scope — the checks that get *graded* to decide if the work is finished. |
| **Ratify** | The explicit human "yes, commit to this bet." Nothing privileged proceeds without it. |
| **spec / plan / tasks** | The three artifacts the spec-driven pipeline produces from your PRD: what to build, how, and the dependency-ordered task list. |
| **TDD-mandatory** | For critical-infrastructure components, your constitution can require tests be written *first* and no merge without them. |

You don't need to memorize this. Refer back as the terms appear.

---

## Phase 1 — Launch your governed session

**What this is and why.** Before you can do anything, you need a *governed
session*: your normal coding agent, running inside CE's governance wrapper. This
is the moment CE becomes real for you.

**Do this:**

```bash
ce launch
```

> First time on a new machine? Run `ce onboard` instead — it walks setup end to
> end (checks the host, verifies the install, puts CE on your `PATH`, initializes
> local state) and then drops you into a governed pane automatically. After
> that, `ce launch` is the everyday entry point. The full first-host setup is in
> the [Quickstart](./zero-to-governed-seat-quickstart.md).

**What you'll see.** *Not* a new CE app. There is no CE dashboard, chat window,
or editor. `ce launch` opens **your own coding agent in its normal terminal UI**
— the exact Claude Code or Codex session you already know — inside a visible
terminal pane. You type prompts to your agent exactly as you always have.

**What it produced / where it lives.** A live governed session. CE keeps its
working state in a local `.ce/state` directory in your project; you'll see it
referenced but you won't edit it by hand.

**The day-one "aha" — your first refusal.** Keep working normally. The first
time the agent reaches for something **privileged** — pushing to a remote,
reading a credentials file, touching a protected surface — CE steps in and the
agent **refuses through its own native permission channel, with the reason
spelled out** (the exact rule that denied it). That refusal does not come from
the agent grading itself; it comes from a small governance check that sits
*outside* the agent and inspects every privileged action before it happens. That
is "governance from outside the agent," and it's the moment the whole idea
clicks:

> *My normal AI coding session — except it just refused the dangerous thing and
> told me exactly why.*

**Your role here.** Just start working. When the gate holds something, read the
reason; you'll approve (or not) at the points described below.

---

## Phase 2 — Establish your project constitution (do this first)

**What this is and why it comes first.** A **constitution** is your project's set
of non-negotiable standards — your testing rigor, your review rules, what "done"
means for your codebase. It comes *first*, before you break work down, because it
**propagates downstream**: every spec, plan, and task generated later is checked
against it. Set the standard once, and everything inherited respects it. (This is
the same instinct as agreeing your Definition of Done before sprint one — except
here it's machine-enforced.)

**Rigor is set per component.** A constitution doesn't force one bar on
everything. For **critical-infrastructure / high-assurance components** it can
make **TDD mandatory** — tests written first, and no merge without them. For
lower-risk components it can run lighter. You decide which parts of your system
warrant which bar, and you encode that in the constitution.

> **You may not be authoring from scratch.** For many projects a constitution is
> **already drafted for you to review and ratify.** If so, this step is "read the
> draft, adjust anything that doesn't fit your project, then ratify" — not
> "write one from a blank page." Either way, the command below is how you do it.

**Do this** (inside your governed session, as a slash command to your agent):

```text
/speckit-constitution
```

**What you'll see.** Your agent loads the constitution at
`.specify/memory/constitution.md`. If a draft already exists, it walks you
through its principles and any placeholders to confirm. If one doesn't exist yet,
it's initialized from the project template and your agent helps you fill it in.
You'll be asked to confirm or adjust each principle, the version, and the
governance rules (how amendments happen, who reviews).

> **⚠️ Don't ratify a constitution with open placeholders — finish your
> decisions first.** Before you ratify, your constitution will have a short
> **"Decisions You Must Make"** checklist at the top: the choices only you (the
> domain owner) can make — such as test-coverage targets, performance budgets,
> and any safety-trip conditions for critical components. **Work through each
> item, replace its placeholder with your decision, and only then ratify.** A
> pre-drafted constitution gets you most of the way there; these are the last
> calls that are yours, and they're the ones everything downstream inherits. If
> you ratify with placeholders still open, you've locked in blanks. Don't blow
> past this step.

**What it produced / where it lives.** The ratified constitution at
`.specify/memory/constitution.md`, plus a "Sync Impact Report" recorded at the
top of that file noting what changed and which downstream templates were kept in
sync. From now on, the spec/plan/tasks steps below honor it automatically.

**Your role here.** This is a human decision point. Read the principles, make
sure the rigor bars (especially TDD-mandatory for your critical components)
reflect what you actually want, adjust, and **ratify** — that ratification is
your explicit "these are our standards."

---

## Phase 3 — Turn your PRD into a roadmap and tickets

**What this is and why.** You have a product idea or a PRD. This phase runs the
**spec-driven pipeline**: a chain of slash commands that takes natural language
all the way to a dependency-ordered set of GitHub issues — your product backlog.
Each command consumes the previous one's output and produces the next artifact.
Run them in order. Think of it as: draft the spec, refine it, plan it, break it
into tasks, sanity-check, then file the tickets.

All artifacts land in a per-feature folder under `specs/`, named like
`specs/NNN-short-name/` (for example `specs/003-user-auth/`).

### Step 3.1 — `/speckit-specify` (PRD → spec)

**What it does.** Turns your natural-language feature description into a written
specification.

```text
/speckit-specify <describe your feature in plain language>
```

**What you'll see.** Your agent creates the feature folder, writes the spec, and
generates a requirements quality checklist. If anything is too vague to pin down,
it may ask you up to a few quick multiple-choice questions.

**What it produced.** `specs/NNN-short-name/spec.md` (the spec) and
`specs/NNN-short-name/checklists/requirements.md` (a quality checklist). A
feature branch is also created for this work.

### Step 3.2 — `/speckit-clarify` (resolve gaps ≈ backlog refinement)

**What it does.** Finds the underspecified or ambiguous areas in the spec and
bakes the answers back into it. This is the closest analog to backlog refinement
/ grooming — pinning down the fuzzy bits before anyone plans against them.

```text
/speckit-clarify
```

**What you'll see.** This is the interactive one. Your agent asks up to **five**
targeted questions, **one at a time**, each with a recommended answer. Answer
them in plain language.

**What it produced.** The same `spec.md`, now richer — with a `## Clarifications`
section logging the dated Q&A and the relevant requirements tightened.

### Step 3.3 — `/speckit-plan` (spec → plan)

**What it does.** Runs the implementation-planning workflow and produces the
design artifacts. This is where your **constitution is enforced** — the plan is
checked against the standards you ratified in Phase 2.

```text
/speckit-plan
```

**What you'll see.** Your agent reads the spec and the constitution and writes
the plan. It won't run a long Q&A loop; instead it stops and reports if the work
violates a constitution gate or still has unresolved clarifications.

**What it produced.** `specs/NNN-short-name/plan.md`, plus supporting design
artifacts in the same folder: `research.md`, `data-model.md`, a `contracts/`
folder, and `quickstart.md` (some are skipped if not applicable).

### Step 3.4 — `/speckit-tasks` (plan → tasks)

**What it does.** Generates the actionable, **dependency-ordered** task list from
the design artifacts — your refined backlog.

```text
/speckit-tasks
```

**What you'll see.** Your agent writes a structured task list organized into
phases (setup → foundational → one phase per user story → polish), each task
numbered and labeled with the file it touches.

**What it produced.** `specs/NNN-short-name/tasks.md`. Note: **where your
constitution made TDD mandatory, the test tasks are ordered *before* their
implementation tasks** — so the backlog itself enforces tests-first for those
components.

### Step 3.5 — `/speckit-analyze` (consistency check)

**What it does.** A non-destructive, read-only audit across the three core
artifacts (spec, plan, tasks) plus the constitution — does everything line up?

```text
/speckit-analyze
```

**What you'll see.** A findings report in the conversation: a table of any
inconsistencies by severity, a coverage summary, and metrics. It **writes
nothing** — it only reports, and at the end offers to suggest fixes (it never
applies them on its own).

**What it produced.** No files. A verdict you act on: if it surfaces gaps, loop
back and fix the spec/plan/tasks, then re-run. When it's clean, continue.

### Step 3.6 — `/speckit-taskstoissues` (tasks → product backlog)

**What it does.** Converts the tasks into GitHub issues — your actual,
trackable product backlog.

```text
/speckit-taskstoissues
```

**What you'll see.** Your agent reads `tasks.md` and your git remote, then
creates one GitHub issue per task in your repository. It will only file issues in
the repo your remote actually points at.

**What it produced.** A set of GitHub issues, dependency-ordered, that mirror
`tasks.md`. **This is your product backlog.** You're now ready to work a ticket.

**Your role across Phase 3.** You answer the clarify questions (3.2), you read
and accept the analyze verdict (3.5), and you sanity-check the resulting backlog.
The agent drives the mechanics; the judgment calls are yours.

---

## Phase 4 — Work your first ticket: the governed build loop

This is the heart of CE: taking one ticket from intent to a merged, reviewed,
evidence-backed change. The loop is **Frame → Shape → Build → Review → Ship**,
and you drive it with the `cev3` command. Pick one issue from the backlog you
just created, and follow these steps in order.

> **A note on the commands.** Many `cev3` commands are **plan-by-default**: they
> show you what *would* happen and change nothing until you add `--apply`. That's
> deliberate — you always see the plan before anything privileged occurs.

### Step 4.1 — `cev3 scope` (Frame + Shape your bet)

**What it does.** Crystallizes the ticket into a **Scope**: its Goal, its
**Done-when** acceptance criteria, a Budget you set, and the change type. This is
the unit CE governs.

```bash
cev3 scope my-first-ticket \
  --goal "What you're trying to accomplish, in one line" \
  --done-when "First acceptance criterion" \
  --done-when "Second acceptance criterion" \
  --budget S \
  --change-type code
```

**What you'll see.** A Scope card with the canon fields filled in — Goal,
Done-when (each criterion you gave), Budget, Change-type — and a **Ready** flag
that turns to ✓ once the card is complete and valid.

**What it produced.** A filed Scope in your local CE state. Nothing privileged
has happened yet; you've only described the bet.

**Key concept — Done-when = acceptance criteria.** The Done-when criteria are
not decoration. They are **what gets graded** at Review time to decide whether
the work is finished. Write them the way you'd write good acceptance criteria:
concrete and checkable. **You set the Budget** — it's a fixed cap on effort you
commit, not a time estimate; the agent never decides how much you'll spend.

> Not sure your Scope is well-formed? `cev3 shape my-first-ticket` runs a
> "grill-me" pass that points out gaps and asks what's missing before you commit.

### Step 4.2 — `cev3 ratify` (the human gesture)

**What it does.** Places the bet. Ratification is the **explicit human "yes"** —
the front gate. Nothing builds until a Ready Scope is ratified.

```bash
cev3 ratify my-first-ticket --approver-ref <64-hex-digest>
```

**Why you generate a ref.** The `--approver-ref` is a **value-free 64-hex opaque
digest** — a fingerprint that records *that a human ratified*, without ever
embedding a raw account or secret. It's how CE proves a human approved this bet
without leaking who or any credential. You generate one fresh, for example:

```bash
openssl rand -hex 32
```

and pass that value to `--approver-ref`.

**What you'll see.** Confirmation that the Scope is ratified and the bet is
placed. The gate is now open for *this specific* Scope.

**What it produced.** A recorded ratification bound to your Scope. This is the
moment of human authority — the thing CI can never do for you.

**Your role here.** This is *the* human decision in the loop. Ratifying means
"yes, build this." Don't ratify a Scope whose Done-when you wouldn't accept.

### Step 4.3 — `cev3 drive` (Build — tests-first, then code)

**What it does.** Dispatches one governed, sandboxed run that does the work. The
front gate refuses unless the Scope is Ready *and* ratified, and your Budget
becomes the run's hard spend cap.

```bash
cev3 drive my-first-ticket --spawn
```

(`--spawn` launches a real governed seat to do the build; without it, `drive`
just assembles the dispatch so you can inspect it first.)

**What you'll see.** A governed agent run executing the task. **Because your
constitution makes TDD mandatory for critical-infrastructure components, for
those the agent writes the tests first, watches them fail, then writes the code
to pass them** — exactly the order your tasks list encoded in Phase 3.4.

**What it produced.** An authored branch with the work on it, ready to become a
pull request — built inside the budget and boundary you set.

### Step 4.4 — `cev3 pr` (open the pull request)

**What it does.** Pushes the run's authored branch and opens its pull request
through CE's governed forge path.

```bash
cev3 pr my-first-ticket --run <run-id> --branch <authored-branch> \
  --manifest-path <changed-path> --app-config <path-to-github-app-config> --apply
```

(Plan-by-default: omit `--apply` first to preview the push and PR without doing
anything. The `<run-id>` is printed by `cev3 drive`.)

**What you'll see.** The PR opened on GitHub. Importantly, CE opens it as the
**App bot identity, not as you** — which is what makes the next step's
independent review possible on a solo repo.

**What it produced.** A real pull request: the artifact you'll judge.

### Step 4.5 — `cev3 review` (independent review — no self-approval)

**What it does.** Dispatches a **distinct** governed reviewer to evaluate the
opened PR against the Scope's Done-when.

```bash
cev3 review my-first-ticket --run <run-id> --reviewer-actor <reviewer-login> --spawn
```

**Why this matters — no self-approval.** Branch protection enforces that the
author can't approve their own work. Because the PR was opened as the bot
identity (Step 4.4), **you are a valid, independent reviewer** even on a solo
repo. The reviewer checks the artifacts — the diff, the evidence, the tests —
against what *you* declared "done," not against a transcript.

**What you'll see.** A reviewer venue examining the PR and producing a verdict.

**What it produced.** Independent review evidence attached to the PR.

### Step 4.6 — `cev3 merge` (the gated merge)

**What it does.** Performs the governed squash-merge of the PR — the back gate.

```bash
cev3 merge my-first-ticket --run <run-id> --apply
```

(Plan-by-default: run it without `--apply` first to *read the gate* — it tells
you exactly what's required and whether it's satisfied.)

**The crucial distinction.** Green CI is **required** but green does **not
authorize** the merge — **ratification does.** A green build proves the change is
well-formed and in policy; it does not grant the authority to land it. That
authority came from your Phase-4.2 ratification and the independent review. CI
verifies; humans ratify.

**What you'll see.** The gate read (what's satisfied / what's blocking), and on
`--apply`, the squash-merge landing.

**What it produced.** Your first governed change, merged. The branch is squashed
into a single clean commit with a full evidence chain behind it.

### Step 4.7 — `cev3 report` (the demo / evidence)

**What it does.** Renders the per-run **Completion Report** — the evidence
summary, your "sprint demo" artifact for this ticket.

```bash
cev3 report my-first-ticket --run <run-id>
```

**What you'll see.** A compact report like:

```text
┌─ ◆ CE COMPLETION REPORT · run <run-id> · Scope my-first-ticket ──────
│ Outcome   PR opened → #N (merged)
│ Verdict   Done-when 3/3 met · tests green · in scope ✓ · 14% of Budget S
│ Next      → (done)
│ Inspect   gh pr view N  |  cev3 show my-first-ticket  |  cev3 artifacts <run-id>
└──────────────────────────────────────────────────────────
```

**What it produced.** The shareable evidence record: what was delivered, how it
scored against your Done-when, that tests were green, that the diff stayed in
scope, and how much of the Budget it used. Inspect anything further with
`cev3 show <scope>` and `cev3 artifacts <run-id>`.

**Your role across Phase 4.** You write the Done-when (4.1), you ratify (4.2),
you review the PR against your own criteria (4.5), and you read the report (4.7).
The agent builds; you hold the gate and the judgment.

---

## Phase 5 — Your daily rhythm

Once the first ticket is through, every day looks the same shape:

1. **Pick a ticket** from your backlog (the GitHub issues from Phase 3).
2. **Scope it** — `cev3 scope` with a clear Goal, real Done-when, and a Budget.
3. **Ratify it** — `cev3 ratify` — your explicit "yes, build this."
4. **Drive it** — `cev3 drive --spawn` — the agent builds (tests-first where
   your constitution requires it).
5. **Open + review + merge** — `cev3 pr`, then `cev3 review`, then `cev3 merge`
   — independent review, gated merge; green is necessary but ratification is what
   authorizes.
6. **Report** — `cev3 report` — capture the evidence, move on.

New big initiative? Go back to **Phase 3** and run the spec-driven pipeline again
to groom it into tickets. Changing your standards? Re-run **`/speckit-constitution`**
in Phase 2 and re-ratify — the change flows downstream from there.

Throughout, the constant is the one idea from Phase 0: **you judge artifacts, the
agent does the work, and the gate sits outside the agent.** That's the whole
loop. Welcome aboard.

---

## Where to go next

| You want to… | Read |
| --- | --- |
| The big picture / front door | [`welcome.md`](./welcome.md) |
| The workflow and its vocabulary | [`understanding-ce.md`](./understanding-ce.md) |
| The shortest command sequence to a governed seat | [`zero-to-governed-seat-quickstart.md`](./zero-to-governed-seat-quickstart.md) |
| The full install-to-ship pilot | [`pilot-runbook.md`](./pilot-runbook.md) |
| Contribute to CE itself | [`contributing-to-ce.md`](./contributing-to-ce.md) |
