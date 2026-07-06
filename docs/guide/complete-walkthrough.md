# Complete Walkthrough

*This guide shows the whole Creator Engine loop in one continuous path. For the
canonical copy-paste command path, start with [`quickstart.md`](./quickstart.md).
For the concepts, read [`how-ce-builds-software.md`](./how-ce-builds-software.md).
If you want the full pilot operator checklist, read
[`pilot-runbook.md`](./pilot-runbook.md).*

## 1. The Promise

Creator Engine runs your own coding agent under governance. You keep using
Claude Code, Codex, or the agent you already know. CE adds a visible workflow
around it so work is bounded before it starts, checked after it runs, and gated
before it lands.

The useful mental model is simple:

> You describe the change. CE turns it into a Scope. Your agent builds inside
> that Scope. The result is graded against the Scope, not against the agent's
> confidence.

If you get stuck at any point, start with `ce --help` or
`ce <command> --help`, then follow the linked docs for the stage you are in. If
a gate is still unclear, ask your operator which decision is missing before you
continue.

---

## 2. Get Running

There are two supported rails. They end in the same place: a governed agent
session on your machine.

| Rail | Use it when | Start here |
| --- | --- | --- |
| **Fast local install** | You want the shortest path from terminal to CE | [`zero-to-governed-seat-quickstart.md`](./zero-to-governed-seat-quickstart.md) |
| **Agent-native install** | You want your coding agent to fetch and follow the signed install spec | [`../llms-install.md`](../llms-install.md) |

The fast path is:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
ce onboard
```

`ce onboard` checks the host, verifies the installed CE surface, initializes
local state, and drops you into a governed agent pane. For daily work after
that, use:

```bash
ce launch --backend host
```

That pane is still your normal coding agent. CE is not a separate dashboard or
editor. It is the wrapper around the session: it tracks the work, records the
evidence, and holds privileged actions until the right human decision is made.

---

## 3. Meet The Loop

CE names the work loop with five words. They are the user-facing skin over a
more precise machine, and they match the canon in
[`stage-vocabulary.md`](../architecture/stage-vocabulary.md).

| Stage | Plain meaning | What CE is protecting |
| --- | --- | --- |
| **Frame** | Understand the problem and why it matters | The work is not tracked until the problem is clear |
| **Shape** | Turn the problem into a ratifiable Scope | The Scope has Goal, Done-when, and Change-type; Ready is the ratifiable state |
| **Build** | Let the agent execute the ratified Scope | The run stays inside the approved Scope |
| **Review** | Grade the result against Done-when | Evidence matters more than transcript confidence |
| **Ship** | Land the governed outcome | Merge, no-change, or delivered research happens through the gate |

If you know BMAD, the rough bridge is:

| BMAD shape | CE stage |
| --- | --- |
| Analysis | Frame |
| Planning + solutioning | Shape |
| Implementation | Build |
| Review and release tail | Review + Ship |

The extra CE tail is deliberate. Review and Ship are first-class because the
grader lives outside the agent, and shipping is a governed outcome, not the
agent declaring itself done.

---

## 4. The Worked Example

We will use Dev mode: you drive the pipeline explicitly with `ce` commands from
inside the governed pane. In CEO mode, you can ask the agent to drive more of
the mechanics for you, but the same human boundaries remain: you ratify the
Scope, judge the artifacts, and authorize privileged gates.

The synthesized ticket:

> Add a lightweight empty-state message to the project activity page so a new
> repository does not show a blank panel before its first run.

### Frame

**What you do.** You tell the agent what feels wrong and what outcome would make
it better:

```text
The activity page is blank before the first governed run. Frame a small docs/UI
ticket for adding an empty state. Keep it narrow: copy only, no backend changes.
```

If the problem still feels fuzzy, keep the work in Frame and ask your operator
which outcome, boundary, or acceptance criterion must be decided before you
Shape it.

**What CE does.** CE keeps this as conversation until there is a real unit of
work. It does not create a Scope just because you chatted. When the agent has
enough context, it summarizes the candidate work and asks whether to Shape it.

**What you see.**

```text
◆ CE · Frame
Problem: activity page is blank before first run.
Likely change: add empty-state copy in the existing activity view.
Boundary: no backend data model or API changes.
Next: Shape a Scope? › yes
```

Frame ends when the problem is bounded enough to become a Scope.

### Shape

**What you do.** You create the Scope: the Goal, the Done-when checks, and the
Change-type.

```bash
ce scope activity-empty-state \
  --goal "Show a helpful empty state on the activity page before the first run" \
  --done-when "A new project activity page shows empty-state copy instead of a blank panel" \
  --done-when "The copy points users back to launching their first governed run" \
  --done-when "Existing populated activity pages are unchanged" \
  --budget 1 \
  --budget-unit % \
  --budget-window per_run \
  --change-type code
```

Budget is optional. The example opts into a paste-testable 1% per-run cap;
substitute the amount, unit, and window your operator gives you for your lane.

**What CE does.** CE checks whether the Scope is Ready. If the Scope is vague,
missing a testable Done-when, or under-declares risk, it tells you before the
Scope is ratified. You can run a sharpening pass:

```bash
ce shape activity-empty-state
```

If you already have a PRD or requirements document, seed Shape from that file:

```bash
ce shape --from docs/prd/onboarding.md
```

CE reads the document as context, identifies one first candidate Scope, runs the
same Shape grill, and previews Goal, Done-when gaps, and Change-type. It also
adds `Source PRD: docs/prd/onboarding.md` as the Scope note when you explicitly
confirm the shape; no Scope is recorded before that confirmation.

**What you see.**

```text
◆ CE · Shape → "activity-empty-state"
Goal        Show a helpful empty state on the activity page before the first run
Done-when   3 checks
Budget      1% per_run
Change-type code
State       Ready ✓

Front gate: ratify this Scope before Build.
```

Then you ratify the Scope:

```bash
ce ratify activity-empty-state --approver-ref 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

Ratification is the human "yes": this is the work, these are the Done-when
checks, and this is the risk tier.

### Build

**What you do.** You dispatch the governed run:

```bash
ce drive activity-empty-state --spawn
```

Then you watch for important prompts. Most mechanics belong to the agent and CE,
not to you.

**What CE does.** CE starts a boxed run against the ratified Scope. The agent
reads the codebase, edits inside the intended path set, runs the relevant
checks, and opens a pull request or reports why there is no change to make. If
the agent tries to step outside the envelope, CE refuses and explains the gate.

**What you see.**

```text
◆ CE · Build
Scope       activity-empty-state
Run         activity-empty-state-1
Envelope    Change-type code · Done-when 3

Agent plan:
1. Locate activity page rendering.
2. Add empty-state copy when the activity list is empty.
3. Preserve populated-state behavior.
4. Run focused tests and lint.
```

If the agent needs a privileged action, you see a refusal or an approval prompt
through the agent's normal terminal UI. When in doubt, run `ce drive --help` to
check the Build command surface, then ask your operator which approval is
missing.

### Review

**What you do.** You inspect the artifacts, not the transcript. Start with the
Completion Report and the PR:

```bash
ce report activity-empty-state --run-id activity-empty-state-1
ce artifacts activity-empty-state --run-id activity-empty-state-1
```

Then read the diff and evidence against the Done-when checks you wrote.

**What CE does.** CE grades the run against the Scope. It reports whether the
Done-when checks are met, whether checks passed, whether the diff stayed in
scope, and what remains for Ship.

**What you see.** A sample `ce report` render looks like:

```text
┌─ ◆ CE COMPLETION REPORT · run activity-empty-state-1 · Scope activity-empty-state ──────────────────
│ Outcome   — → #24
│ Verdict   Done-when 3/3 met · tests green · in scope ✓
│ Next      —
│ Artifacts PR #24 · Scope activity-empty-state · evidence-chain ✓ · spend
│ Inspect   gh pr view 24   |   ce show activity-empty-state   |   ce artifacts activity-empty-state --run-id activity-empty-state-1
└────────────────────────────────────────────────────────────
```

Review is where CE differs from a plain coding-agent run. The agent does not get
to mark itself done because it sounded confident. The external grade is based on
the Scope you ratified and the evidence the run produced.

### Ship

**What you do.** If the PR satisfies the Scope and the required review/checks
are green, you authorize the merge gate:

```bash
ce merge activity-empty-state --run activity-empty-state-1 --apply
```

If the result is not good enough, you send it back through Review with concrete
feedback tied to the Done-when checks.

**What CE does.** CE verifies that the PR still matches the ratified envelope,
that the required checks and review gate are satisfied, and that the change type
is allowed to ship through this path. Then it records the terminal outcome.

**What you see.**

```text
◆ CE · Ship
Outcome   Merged
Verdict   Scope satisfied · checks green · review complete · gate opened
Next      → Done
```

Ship can also mean "research delivered" or "no change needed" when that is the
ratified outcome. It is not only a merged PR.

---

## 5. The Daily Loop

After setup, most days are smaller than the full walkthrough:

1. Launch your governed pane with `ce launch --backend host`.
2. Talk to the agent about the next problem.
3. Let CE help Frame and Shape a small Scope.
4. Ratify the Scope when the Goal, Done-when, and Change-type are right.
5. Let the agent Build inside the envelope.
6. Review the Completion Report and PR evidence.
7. Ship through the gate, or send the work back with specific feedback.

Use one branch per Scope unless your team's policy says otherwise. If a request
starts to sprawl, split it before ratification. CE works best when the Scope is
small enough that Review can be honest.

The local help surface is useful throughout the loop:

```bash
ce --help
ce scope --help
ce merge --help
```

If help output does not explain the gate you are seeing, ask your operator and
include the Scope id, run id, and exact refusal text.

---

## 6. Your Irreducible Gestures

CE automates a lot, but it intentionally leaves a few decisions with you.

| You decide | CE and the agent handle |
| --- | --- |
| What problem is worth doing | Reading context and proposing a bounded Scope |
| Whether the Scope is ratified | Running only after the front gate is open |
| Whether risk increases are acceptable | Making changes safer inside the envelope |
| Whether evidence satisfies Done-when | Producing the report, artifacts, and PR |
| Whether the merge gate opens | Verifying checks, review, scope, and policy |

Those gestures are the point. CE gives the agent room to work without giving it
authority to decide what should be true.

---

## 7. Common Questions

### Why no time estimates?

Because CE is governed by Done-when and evidence, not clock predictions. If your
lane requires an explicit cap, that cap is a stop or split signal for the run; it
is still not a prediction about elapsed time.

### What if the agent wants to do more than I ratified?

That is a new Shape decision. The agent can make work safer inside the current
Scope, but increasing risk, broadening files, or changing the Goal needs your
explicit ratification.

### What if I do not know the right command?

Use `ce --help` or the command-specific help first:

```bash
ce report --help
ce artifacts --help
ce merge --help
```

If the next decision is still unclear, ask your operator which artifact or gate
they expect you to inspect before Ship.

### Do I need to understand the machine underneath?

Not to start. The five-stage vocabulary is the everyday interface. When you
want the deeper user-facing model, read
[`how-ce-builds-software.md`](./how-ce-builds-software.md).

---

## 8. Under The Hood

The friendly stage words are the surface. Under them is a conserved machine that
records Scope state, run evidence, review evidence, and terminal outcomes. You
do not need that layer to run your first Scope, but it is available when you
want to inspect how the governance works.

| You want to inspect | Read |
| --- | --- |
| Canonical command path | [`quickstart.md`](./quickstart.md) |
| How CE builds software | [`how-ce-builds-software.md`](./how-ce-builds-software.md) |
| Plain-language vocabulary | [`understanding-ce.md`](./understanding-ce.md) |

## 9. Where Next

| You want to understand | Read |
| --- | --- |
| The canonical command path | [`quickstart.md`](./quickstart.md) |
| How CE builds software | [`how-ce-builds-software.md`](./how-ce-builds-software.md) |
| The plain-language CE concepts | [`understanding-ce.md`](./understanding-ce.md) |
| The full install-to-ship pilot checklist | [`pilot-runbook.md`](./pilot-runbook.md) |
| The quick first-host path | [`zero-to-governed-seat-quickstart.md`](./zero-to-governed-seat-quickstart.md) |
| How Agile/SCRUM habits map to CE | [`agile-to-ce-sdlc.md`](./agile-to-ce-sdlc.md) |
| How to contribute to CE itself | [`contributing-to-ce.md`](./contributing-to-ce.md) |

Start with one small Scope. Frame it clearly, Shape it honestly, let the agent
Build, Review the evidence, and Ship only when the gate is truly green.
