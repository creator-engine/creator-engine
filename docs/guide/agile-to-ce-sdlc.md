# From Agile/SCRUM to Creator Engine — Your Spec-Driven, Verification-Gated Day

*You already run an Agile/SCRUM workflow: a PRD becomes user stories in a
backlog, the team refines them, you plan a sprint, you build and test, you
integrate and review, you demo, you retro, you repeat. This guide maps **each of
those moves onto its Creator Engine equivalent** so you can be productive on day
one. It assumes you've read the front door
([`welcome.md`](./welcome.md)) and the plain-language tour
([`understanding-ce.md`](./understanding-ce.md)); this is the SCRUM-fluent
contributor's companion to both. For the install-to-ship walkthrough, the
[Pilot Runbook](./pilot-runbook.md) is the end-to-end tour.*

> **Who this is for.** A developer fluent in Agile/SCRUM who wants to drive real
> work through CE on their own repo — pointing their own governed coding agent
> (Claude Code or Codex) at a PRD and getting a planned, tested, reviewed,
> merged result. Everything below works for **any** project; we occasionally use
> a sample project for flavor.

> **You are in: Solo + Dev mode.** This guide is written for the **Solo + Dev**
> cell: you type `/speckit-*` slash commands yourself to drive the pipeline, and
> you hold the Frame + Shape decisions explicitly at each step. If you are in
> **Solo + CEO** mode — where the agent runs the pipeline under the hood and
> your interaction is framing intent, reviewing the Scopes and plans the agent
> assembles, and ratifying each gate — see
> [`solo-ceo-onboarding.md`](./solo-ceo-onboarding.md) instead.

---

## TL;DR — the mapping at a glance

Read this table first. The rest of the guide is just these rows, expanded with
the exact commands.

| SCRUM concept you know | CE equivalent | How you do it |
| --- | --- | --- |
| **PRD / product brief** | The feature **specification** (`spec.md`) | `/speckit-specify "<your PRD or idea>"` writes `specs/<NNN>-<name>/spec.md` |
| **Product owner breaks the PRD into stories/tasks** | The **plan + tasks** generation pipeline | `/speckit-plan` → `plan.md`; `/speckit-tasks` → `tasks.md` (dependency-ordered, grouped by user story) |
| **Backlog refinement (clarify ambiguity, sanity-check)** | Spec **clarification** + cross-artifact **analysis** | `/speckit-clarify` (asks up to 5 targeted questions, folds answers into the spec); `/speckit-analyze` (read-only consistency check across spec/plan/tasks) |
| **Populating the GitHub/Jira backlog** | **Tasks → GitHub issues** | `/speckit-taskstoissues` opens one issue per task in your repo |
| **A user story / backlog task** | A **Scope** — CE's ratifiable unit of work | `cev3 scope <id> --goal … --done-when … --budget … --change-type …` |
| **Definition of Ready (story is well-formed)** | The Scope reads **Ready ✓** (Goal · Done-when · Budget · Change-type all valid) | CE shows `Ready ✓` on the Scope card when the four fields are filled and valid |
| **Sprint planning / committing to the story** | **Ratifying** the Scope — placing the bet | `cev3 ratify <id> --approver-ref <digest>` (the human-only front gate) |
| **Acceptance criteria you write before coding** | **Done-when** criteria on the Scope (the graded checks) | the `--done-when` lines you set at Shape time — they are what gets graded |
| **Sprint execution (the dev does the work)** | The governed **Build** run | `cev3 drive <id>` (assemble the gate); `cev3 drive <id> --spawn` (launch the governed agent) |
| **Continuous integration / automated checks** | **CI verifies** — the gate set (`ce validate-pr`) | CI runs the same checks you can run locally; *green proves well-formed, not authorized* |
| **QA / integration / code review** | The **Review** stage: a PR + an independent reviewer | `cev3 pr` opens the PR; `cev3 review` dispatches a distinct reviewer; you judge artifacts |
| **Definition of Done** | The **Done-when** verdict + the governed merge gate | the Completion Report shows Done-when N/N met; `cev3 merge <id> --apply` is the gated finish |
| **Sprint review / demo** | The **◆ CE Completion Report** + the evidence chain | `cev3 report <id>` renders Outcome · Verdict · Next; `cev3 artifacts <run>` enumerates the proof |
| **Retrospective / continuous improvement** | The compounding **evidence + learnings** loop | every run's artifacts persist under `.ce/state`; nothing relies on chat memory |
| **The Scrum Master removing impediments / enforcing process** | **Governance from outside the agent** | the gate refuses privileged actions and holds them for a human — automatically, every run |

The single biggest shift: **SCRUM times-boxes work into sprints and asks humans
to do the building; CE runs a continuous governed flow where the agent does the
building and the human frames, shapes, and *ratifies*.** There is no fixed
two-week box — there is a stream of small, ratifiable Scopes, each one
individually planned, built, checked, and shipped.

---

## 1. The CE agentic SDLC in one picture

CE wraps your coding agent in a five-stage loop. The stages are plain words for
*what you're doing right now*, and they work at any size — a one-line fix or a
whole roadmap:

**Frame → Shape → Build → Review → Ship**

1. **Frame** — *understand the problem.* Just thinking and chatting. Nothing is
   tracked. (Your SCRUM analog: reading the PRD and forming intent.)
2. **Shape** — *turn it into a bet.* You crystallize the work into a **Scope** —
   Goal, Done-when, Budget, Change-type — and place the bet. (Analog: writing the
   story with acceptance criteria, then committing to it in planning.)
3. **Build** — *do the work.* The agent executes the bet in one governed,
   sandboxed run. (Analog: sprint execution — except the agent codes.)
4. **Review** — *check it.* The result is graded against the Done-when you wrote,
   with evidence, plus an independent reviewer on the PR. (Analog: QA + code
   review.)
5. **Ship** — *land it.* A governed, branch-protected merge — or delivered
   research, or a reasoned "no change needed." (Analog: the increment is done.)

Three principles run underneath, and they are what make CE *different* from a
normal SCRUM toolchain:

- **Spec-driven.** You write the spec, the plan, and the tasks *before* code.
  The artifacts are the source of truth, not a transcript or a memory.
- **Test-driven.** CE genuinely practices TDD: when the spec calls for tests, the
  build writes and runs the **tests before the code** (`/speckit-implement` is
  explicitly "tests before code"), and a task isn't done until its tests pass. On
  top of that, the gate enforces it — you declare **Done-when** acceptance
  criteria up front, the project's example-and-test corpus must pass, and the gate
  **refuses any new test failure**. So "done" means "the checks are met, with
  evidence," never "the agent says it's fine." (Full detail in §6.)
- **Governance lives outside the agent.** The thing that decides whether work is
  good — and whether a privileged action is allowed — sits *outside* the agent
  and inspects every artifact and every privileged action. The agent can make a
  change *safer* on its own, but only **you** can make it riskier, and only
  **you** ratify the bet and the merge.

> **How this differs from SCRUM, concretely.** No fixed timeboxed sprint; a
> continuous flow of ratifiable Scopes. The agent does the doing; you do the
> framing, shaping, and ratifying. "Done" is an evidence verdict against
> criteria you wrote, not a status someone moves on a board. And the
> impediment-remover isn't a person reminding the team of the process — it's a
> gate that enforces it on every run.

---

## 2. SCRUM → CE, role by role

A quick re-grounding for each SCRUM ceremony, before the worked example.

- **PRD → spec.** Your product brief becomes a real, versioned artifact:
  `specs/<NNN>-<name>/spec.md`. It is the contract the rest of the flow reads.
- **Backlog breakdown → plan + tasks.** Instead of a product owner manually
  splitting stories, `/speckit-plan` produces the design plan and
  `/speckit-tasks` produces a dependency-ordered, by-user-story `tasks.md`.
- **Backlog refinement → clarify + analyze.** `/speckit-clarify` surfaces the
  ambiguities a refinement session would catch and folds the answers back into
  the spec; `/speckit-analyze` is the read-only consistency review across all
  three artifacts (spec/plan/tasks) that flags gaps before you build.
- **DoR → the Scope reads Ready ✓ (and you ratify).** A story is "ready" in
  SCRUM when it's clear, estimated, and agreed. In CE, a **Scope** is Ready when
  Goal, Done-when, Budget, and Change-type are all valid — and the *commitment*
  is the explicit **ratify** gesture.
- **Sprint planning / commit → ratify.** Committing to a story = `cev3 ratify`.
  This is the human-only front gate. The agent cannot place its own bet.
- **DoD → Done-when verdict + the merge gate.** "Done" is the Done-when criteria
  met (with evidence) and a governed, independently-reviewed merge — not a
  checkbox someone ticks.
- **Sprint execution → the Build run.** `cev3 drive` dispatches one governed,
  cost-capped run. The Budget you set becomes the run's spend cap.
- **Integration/QA → CI + the Review stage.** CI **verifies** (well-formed,
  in-policy); the PR plus an independent reviewer is the **review**. Critically,
  **CI verifies; it does not ratify** — a green build never authorizes a merge by
  itself.
- **Sprint review/demo → the Completion Report + evidence.** `cev3 report`
  renders the verdict and `cev3 artifacts` enumerates the proof — the PR, the
  diff, the evidence chain, the spend.
- **Retro → the compounding loop.** Every run's evidence persists under
  `.ce/state`; the next piece of work starts from artifacts, not from someone's
  memory of last sprint.

---

## 3. Worked example: a PRD becomes an actionable roadmap + tickets

This is the spec-driven pipeline end to end. You run these as **slash commands
inside your `ce launch` (or `cev3 session`) agent pane** — they are the same
Claude Code / Codex session you already use, governed. Each command is real and
user-invocable; the artifact it writes is named.

> **One-time setup (optional but recommended).** Establish the project's guard
> rails once with `/speckit-constitution "<your project principles>"`. It writes
> `.specify/memory/constitution.md`, which `/speckit-plan` and `/speckit-analyze`
> later check against. Think of it as the team's standing working agreements,
> encoded so the tooling enforces them.

### Step 1 — PRD → spec

Point the agent at your PRD (paste it, or summarize it) and run:

```
/speckit-specify "Rate-limit the public login API: per-IP throttling, clear 429
responses, configurable limits, no impact on authenticated traffic."
```

**Produces:** a new feature directory `specs/<NNN>-<short-name>/` with
`spec.md` (the specification) and a `checklists/requirements.md` quality
checklist. The spec is the PRD turned into a structured, versioned artifact —
user scenarios, acceptance scenarios, and requirements.

*SCRUM analog:* the PRD is now a real backlog epic with written acceptance
scenarios, not a Google Doc.

### Step 2 — refine: clarify

```
/speckit-clarify
```

**Produces:** an updated `spec.md` with a `## Clarifications` section. CE asks up
to five targeted questions (one at a time) about the genuinely underspecified
bits and folds your answers straight back into the spec.

*SCRUM analog:* the backlog-refinement conversation — but the answers are
captured *in the artifact*, so they can't get lost.

### Step 3 — break it down: plan

```
/speckit-plan
```

**Produces:** `specs/<NNN>-<name>/plan.md` plus design artifacts
(`research.md`, `data-model.md`, `contracts/`, `quickstart.md`). This is the
implementation plan — the "how," checked against your constitution.

*SCRUM analog:* the product owner / tech lead turning the epic into a design and
an approach the team agrees on.

### Step 4 — the task list: tasks

```
/speckit-tasks
```

**Produces:** `specs/<NNN>-<name>/tasks.md` — an actionable, dependency-ordered
task list, **grouped by user story** (Setup → Foundational → per-story →
Polish), each task naming the files it touches.

*SCRUM analog:* the sprint backlog — the stories split into concrete tasks, in
the order they can actually be done.

### Step 5 — sanity-check: analyze

```
/speckit-analyze
```

**Produces:** a read-only **Specification Analysis Report** (it writes no
files): a findings table by severity, a coverage summary, constitution-alignment
issues, and unmapped tasks. Resolve any CRITICAL findings before you start
building.

*SCRUM analog:* the final refinement pass where the team confirms the stories
hang together and nothing is missing.

### Step 6 — fill the backlog: tasks → issues

```
/speckit-taskstoissues
```

**Produces:** one **GitHub issue per task**, dependency-ordered, in your repo.
(It only proceeds if your `origin` remote is a GitHub URL, and it creates issues
only in the matching repo.)

*SCRUM analog:* loading the refined sprint backlog into your tracker — except it
flows directly from the same artifacts you just generated, so the backlog and
the spec can't drift.

**At the end of §3 you have:** `spec.md`, `plan.md`, `tasks.md` under
`specs/<NNN>-<name>/`, and a GitHub backlog of issues. That's your PRD turned
into an actionable, traceable roadmap — the whole "product owner + refinement"
arc, automated and version-controlled.

---

## 4. The per-task governed Build loop

Now you pick a task (a GitHub issue / a `tasks.md` item) and take it through
Frame → Shape → Build → Review → Ship as a **Scope**. Launch the session frame
first:

```
cev3 session
◆ Creator Engine · governed session · repo <owner/repo> · state .ce/state
◆ CE · Frame 0 · Shape 0 · Build 0 · Review 0 · Ship 0  │  ctx 8%  │  spend —
```

### Shape — file the Scope and place the bet

Crystallize the task into a Scope. You set the **Budget** (your call, always);
the agent can draft the rest. The `--done-when` lines are your acceptance
criteria — **write them before you build**, because they are exactly what gets
graded:

```
cev3 scope rate-limit-login \
  --goal "Add per-IP rate limiting to the login API" \
  --done-when "429 returned after 100 requests/min from one IP" \
  --done-when "authenticated traffic is unaffected" \
  --done-when "unit tests cover the limiter and pass" \
  --budget 5 --budget-unit '$' \
  --change-type code
```

This writes the Scope record at `.ce/state/scopes/rate-limit-login.scope.yaml`
and prints the Scope card. When Goal · Done-when · Budget · Change-type are all
valid, the card reads **Ready ✓** — CE's Definition of Ready.

Then **place the bet** — the human-only ratification gesture (your "commit to the
story" moment in planning):

```
cev3 ratify rate-limit-login --approver-ref <opaque-64-hex-digest>
```

Ratification pins the bet to the exact Scope content. **The agent cannot ratify
its own work** — this is the irreducible human gesture.

### Build — drive the governed run

```
cev3 drive rate-limit-login            # assemble the dispatch and read the gate
cev3 drive rate-limit-login --spawn    # launch the governed agent to do the work
```

The front gate **refuses unless the Scope is Ready *and* ratified.** The Budget
you set becomes the run's spend cap — cost-runaway protection is on by default.
The agent builds inside one sandboxed run.

### Review — open the PR, get an independent check

Open the PR through the governed forge, then dispatch a **distinct** reviewer
(independent review is required — you can't approve your own change):

```
cev3 collect rate-limit-login --run <run-id> --outcome pr_opened   # fold the run into evidence
cev3 pr rate-limit-login --run <run-id> --branch <head-branch> \
  --manifest-path src/api/ --app-config <your-app-config> --apply  # push + open the PR
cev3 review rate-limit-login --run <run-id> --reviewer-actor <reviewer-login> --spawn
```

Now you **judge artifacts, not a transcript**: read the PR, the manifest-scoped
diff, and the evidence. The grader lives outside the agent.

### Ship — the gated merge

Read the merge gate, then perform the gated, independently-reviewed merge:

```
cev3 merge rate-limit-login --run <run-id>           # read the gate (plan-only)
cev3 merge rate-limit-login --run <run-id> --apply   # the gated squash-merge
```

`--apply` is *your* gated act. Branch protection enforces the independent
review; "Ship" can also be delivered research or a ratified "no change."

### The demo: the Completion Report

```
cev3 report rate-limit-login --run-id <run-id> --done-when-total 3 --done-when-met 3 \
  --ci green --in-scope --cap 5 --unit '$'
```

This renders the **◆ CE Completion Report** — Outcome, Verdict (Done-when N/N
met, tests green, in scope, % of Budget used), and the Next step:

```
┌─ ◆ CE COMPLETION REPORT · run <run-id> · Scope rate-limit-login ─────
│ Outcome   PR opened → #N
│ Verdict   Done-when 3/3 met · tests green · in scope ✓ · 14% of Budget
│ Next      → Review PR #N  (Change-type code → your approval)
│ Inspect   gh pr view N   |   cev3 show rate-limit-login   |   cev3 artifacts <run-id>
└──────────────────────────────────────────────────────────
```

`cev3 artifacts <run-id>` and `cev3 show <scope>` enumerate every artifact with
its inspect command. That's your sprint review/demo and your audit trail in one.

---

## 5. A day working with CE

A narrative pass through a contributor's day, with the low-level commands inline.

**Morning — Frame & Shape.** You open `cev3 session` and chat with your agent
about the next chunk of the roadmap. For a fresh feature you run the §3 pipeline
(`/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` →
`/speckit-analyze` → `/speckit-taskstoissues`) and your backlog of issues
appears. For an already-specced feature you skip straight to picking the next
issue. Either way you crystallize the chosen task into a Scope with `cev3 scope`,
write three or four crisp **Done-when** lines (your acceptance criteria), set a
**Budget** you're comfortable spending, and confirm the card reads **Ready ✓**.
You place the bet: `cev3 ratify <id> --approver-ref <digest>`.

**Midday — Build.** `cev3 drive <id> --spawn` launches the governed run. You
watch the stage in the status line and the spend meter tick. The first time the
agent reaches for something privileged — pushing to a remote, touching
credentials — the gate **refuses it and names the rule**, then holds it for you.
That's governance you can feel, on every run.

**Afternoon — Review.** The run finishes; `cev3 collect` folds it into evidence
and `cev3 pr … --apply` opens the PR. You dispatch an independent reviewer with
`cev3 review … --spawn`, then read the PR and the manifest-scoped diff against
the Done-when you wrote this morning. You're judging *artifacts* — the diff, the
test evidence, the PR — not a chat log.

**End of day — Ship & demo.** Gate looks clean: `cev3 merge <id> --apply`
squash-merges through branch protection. `cev3 report <id>` prints the Completion
Report — your demo and your record. The evidence persists under `.ce/state`, so
tomorrow's work starts from artifacts, not from what you remember. Across the
day you may run this loop several times for several small Scopes — a continuous
governed flow rather than one big timeboxed push.

---

## 6. TDD in CE — tests-first at build, evidence-enforced at the gate

CE is genuinely **test-driven**, and it works at two reinforcing levels: the
agent writes and runs tests *first* while building, and the gate enforces that
with verification evidence before anything ships. If you already practice TDD,
you'll feel right at home.

**1. The spec-driven flow generates and executes tests *before* code.**

- When the spec calls for tests (or you ask for a TDD approach), `/speckit-tasks`
  emits the **test tasks before the implementation tasks** in each story's phase —
  for example, each interface contract gets a contract-test task that is ordered
  ahead of the code that satisfies it.
- `/speckit-implement` then **executes test tasks before their corresponding
  implementation tasks** — its build loop is explicitly "tests before code," and
  it validates that tests pass and coverage meets requirements before a task is
  considered complete. That is red-green-refactor in practice: write the failing
  test, make it pass, move on. **A task isn't done until its tests pass.**

> **The one honest nuance, not a hedge.** Test tasks are generated *when the spec
> requests them or you ask for TDD* — they're opt-in per spec, not force-fed onto
> a trivial docs tweak. For real feature work that's exactly what you want, and
> the practice is tests-first with tests-as-Done.

**2. The gate enforces it with verification evidence.**

On top of the tests-first build, CE's gate makes the discipline non-negotiable
at merge time:

- **Done-when criteria are declared up front.** The acceptance checks you wrote
  at Shape time *before* the Build run are exactly what the result is graded
  against — the executable definition of done.
- **Examples are tests.** Projects carry a corpus of well-formed and malformed
  examples the validator checks (well-formed must pass, malformed must be
  rejected). Behavioral changes are expected to include or update the tests and
  examples that cover them.
- **The gate refuses regressions.** The local preflight and CI run the project's
  test suite at both the base and your change and **fail on any *new* failure** —
  so a PR that adds failing tests or breaks existing ones is refused. Green is
  required to ship; **green never *authorizes* the ship** (that's ratification's
  job).
- **The lifecycle bakes it in.** A unit of work cannot reach `verified`/`done`
  without its tests passing and the completion evidence attached.

**3. Rigor scales to the domain — and critical-infrastructure work mandates TDD.**

The "tests when the spec requests them" posture above is the **default, routine**
stance — sensible for ordinary changes, where forcing a full test suite onto a
trivial tweak would be ceremony for its own sake. But CE lets a project set its
*own* standard, and raise it as high as the work demands:

- A team encodes its non-negotiable standards in the **project constitution**
  (`/speckit-constitution`, written to `.specify/memory/constitution.md`). The
  constitution holds the principles the whole flow must obey — stated as testable
  MUST rules, not vague guidance.
- For **critical-infrastructure / high-assurance components** — anything touching
  live external systems, money, safety, or any context where a defect in
  production is unacceptable — the constitution can make **TDD mandatory**:
  tests-first, red-green, and **no path to Done or merge without the required
  tests.** This is not opt-in for those components; it's the floor.
- The constitution **propagates downstream automatically.** When you amend it,
  `/speckit-constitution` syncs the dependent templates so the planning step's
  Constitution Check and the task generator's testing-discipline categories
  reflect the standard. The rigor is then applied for you in every later
  `/speckit-plan` and `/speckit-tasks` run — you don't have to remember to ask for
  it each time.
- The **gate then enforces it uniformly.** The same baseline-diff gate and
  Definition-of-Done attestation that hold all work also refuse a merge that
  lacks the tests a high-assurance constitution requires. One engine, one set of
  gates — the *bar* is what changes per project/component, not the machinery.

So the same engine governs both ends of the spectrum: routine work can opt into
tests, while critical-infrastructure work is held to tests-first-mandatory by its
own constitution and Definition of Done. Rigor is not one-size-fits-all — it is
set per project and component, and enforced uniformly.

So TDD here is **both practiced and enforced**, and **scaled to the stakes**:
tests-first when the agent builds, verification evidence when the gate decides,
and a hard tests-first-mandatory floor for the components that can't tolerate a
defect. The three reinforce each other — the build does the discipline, the
constitution sets the bar, and the gate proves it.

---

## 7. The human's role — your irreducible gestures

The agent automates the *doing*. A small set of judgments stay with you, by
design — these are the gestures CE will never make on your behalf:

| You always decide | The agent automates |
| --- | --- |
| The **Budget** on every Scope (your spend cap) | Drafting the Goal, Done-when, plan, tasks, and code |
| **Ratifying** the bet (`cev3 ratify`) — placing the Scope | Running the Build inside the ratified envelope |
| Making a change **riskier** (the agent may only make it safer) | Making a change *safer* within its envelope |
| **Judging the artifacts** at Review (diff, evidence, PR) | Producing the artifacts and the Completion Report |
| The **gated merge** (`cev3 merge --apply`) | Opening the PR and reading the merge gate |
| Authorizing **privileged surfaces** when the gate holds one | Refusing privileged actions and surfacing the reason |

Everything else — specifying, clarifying, planning, splitting into tasks,
building, testing, reporting — the agent does, under the gate. You bring intent
and judgment; CE brings the structure and the proof.

---

## Where to go next

- New to CE entirely? Start at [`welcome.md`](./welcome.md).
- Want the plain-language tour of the loop and the Scope card?
  [`understanding-ce.md`](./understanding-ce.md).
- Want the full install-to-ship walkthrough on your own repo?
  [`pilot-runbook.md`](./pilot-runbook.md).
- Here to contribute to CE itself? [`contributing-to-ce.md`](./contributing-to-ce.md).

Welcome aboard. Bring a PRD, shape a Scope, and let CE hold the gate.
