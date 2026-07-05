# Welcome to Creator Engine — Start Here

*New to Creator Engine? This is the front door. It takes you from zero to
productive in one read, then hands you off to the deeper guides. Two paths run
through it: **you, a new user** who wants CE driving work on your own repo, and
**you, a new collaborator** who wants to contribute to CE itself. Follow the one
that fits — the early sections are shared.*

---

## What Creator Engine is, in one line

**Creator Engine runs your own coding agent — under governance.**

You keep using the coding agent you already use (Claude Code or Codex). CE wraps
a structured, auditable workflow around it so that real work is planned,
checked, reviewed, and merged **on purpose** — and so the dangerous things an
agent can attempt are refused until a human says yes.

The key idea: **the thing that decides whether work is good lives *outside* the
agent.** You judge artifacts — a plan, a diff, the evidence, the pull request —
not a chat transcript.

If you want the plain-language tour of the workflow and its vocabulary before
going further, read [`understanding-ce.md`](./understanding-ce.md). It is the
friendly companion to everything below.

---

## What CE looks like on day one (read this first)

The most important thing to know up front: **Creator Engine is invisible until
it gates something.**

There is **no CE dashboard, no CE chat window, and no CE editor.** After the
first `ce onboard` run, `ce launch` opens **your own coding agent in its normal
terminal UI** — the exact Claude Code or Codex session you already know —
inside a visible terminal pane. CE is the governance wrapper *around* that
session, not a replacement for it. (`ce hud` is just another name for the same
launcher; it is not a separate app.)

So a CE session *feels* like an ordinary coding-agent session:

1. You type prompts to your agent, exactly as you normally would.
2. Your agent reads, writes, and runs things, exactly as it normally would.
3. **The first time the agent reaches for something privileged** — say, pushing
   to a remote, or reading a credentials file — CE steps in and the agent
   **refuses through its own native permission channel, with the reason spelled
   out** (the exact rule that denied the action).

That third moment is the whole point, and it is the day-one "aha":

> *My normal AI coding session — except it just refused the dangerous thing and
> told me exactly why.*

That refusal does not come from the agent grading itself. It comes from a small
governance check that sits **outside** the agent and inspects every privileged
action before it happens. That is what "governance from outside the agent"
means in practice, and it is what you will feel the first time you use CE.

---

## Day One as a new user: install, launch, use it

### 0. Prepare

Before the first run:

- Install a supported coding-agent CLI such as Claude Code or Codex and confirm
  it is available from your shell.
- Make sure your repository ignores CE's local Hermes state before onboarding:

  ```gitignore
  .hermes/
  ```

CE refuses to create tracked local runtime state, so add the `.hermes/` ignore
rule before `ce onboard`.

### 1. Install

The fastest start is the one-liner:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
```

This bootstraps Creator Engine into a user-local, verified install. It is
**inventory-only**: it sets CE up and takes stock of your environment, but it
does **not** by itself stand up a fully governed seat or open a pull request —
those come later, after you supply a few answers and explicitly approve them
(more on that below). You only ever need `curl` and `git` available on the host.

> **The on-brand alternative.** If you'd rather have your own agent perform the
> install under CE's governed-install flow, you can point it at the published
> install spec and let it verify and run the signed steps. Both paths end in the
> same place; the one-liner is simply the quickest.

For the full first-host walkthrough, including how to prepare your answers
upfront, follow the
[`Zero to Governed Seat Quickstart`](./zero-to-governed-seat-quickstart.md).

### 2. First run: `ce onboard`

The first time through, run the one-shot onboarder:

```bash
ce onboard
```

`ce onboard` walks the setup end to end in order — it checks your host is
healthy, confirms (and if needed acquires) the install, verifies the install is
genuine, puts CE on your `PATH`, initializes local state — and then **drops you
straight into a governed agent pane** so your first session is ready to go.
If onboarding refuses, fix the named prerequisite and try again. Re-run support
for partially reused onboarding state is still being tightened, so do not treat
`ce onboard` as a general recovery command unless the refusal text says it is
safe.

> **Two onboarding rails — don't mix them up.** `ce onboard` is the quick
> kernel one-shot that gets you to a working governed session on your machine.
> Standing up a **fully governed seat on a GitHub repo** — with the GitHub App
> connection and branch-protection floor — is a separate, deliberately
> human-approved flow (`ce install --spec <verified-spec> --answers ce-install.answers.yaml --plan`
> then `ce install --spec <verified-spec> --answers ce-install.answers.yaml --apply`), covered in the
> [Quickstart](./zero-to-governed-seat-quickstart.md) and the
> [Pilot Runbook](./pilot-runbook.md). Keep them distinct: the quick rail gets
> you using CE; the governed-seat rail connects CE to a repo it can ship to.

### 3. Use it exactly like your normal agent

Once you're in the pane, **just work.** Chat with your agent about what you
want. CE adds a structured loop around the work — **Frame → Shape → Build →
Review → Ship** — and surfaces only when it needs to:

- when a real change emerges, CE offers to capture it as a small, ratifiable
  unit of work (a **Scope** — your goal, what "done" means, and a budget you
  set), and
- when the agent attempts a privileged action, CE holds the gate until you
  approve.

You do not have to memorize any of this on day one. Type prompts; let CE narrate
the stage and ask only what it must. When you want the full picture of the loop
and the Scope card, read [`understanding-ce.md`](./understanding-ce.md).

After onboarding, use `ce launch` as the daily entry point for returning to the
governed agent pane.

---

## Your first real value

There are two milestones worth naming, because they happen in this order:

**1. The first deny — governance you can feel.** The very first time your agent
tries something privileged and is refused — with the reason named — you have
seen CE's core promise with your own eyes: the risky action was caught from
outside the agent, named, and held for a human. That is first value at its
smallest, and you'll usually hit it within minutes.

**2. The first governed change you ship.** The deeper milestone is taking a real
change all the way through the loop — Frame it, Shape it into a Scope you ratify,
let the agent Build it, Review the resulting pull request against what *you* said
"done" was, and Ship it through a governed, independently-reviewed merge. Setup
artifacts (the initial scaffold, the install commit) are onboarding evidence
only; **first value is the first real change that passes review and merges under
governance.**

When you're ready to walk that end-to-end path, the
[Pilot Runbook](./pilot-runbook.md) is the full guided tour of
Frame → Shape → Build → Review → Ship on your own agent and repo, and the
[Quickstart](./zero-to-governed-seat-quickstart.md) is the shortest command
sequence to get there.

---

## For collaborators: contributing to Creator Engine itself

If you're here to help build CE rather than to run it on your own project,
welcome — the on-ramp is a little more structured than a typical project,
because CE is a pre-1.0, ratification-governed substrate. Two principles will
orient you immediately:

- **CI verifies. Humans ratify.** A green build proves your change is
  well-formed and in-policy; it does **not** grant authority to land privileged
  changes. PRs carry proposed change; issues carry information; the right to
  ratify a privileged change is held by humans.
- **Authority is least-privilege and earned.** Contributors work as
  contributors first — small, well-scoped, evidence-backed changes — and grow
  along a trust ladder (contributor → trusted implementer/reviewer → area owner
  → peer ratifier). Higher trust comes from a ratified authority update, not
  from merge count alone.

What a brand-new collaborator does, in order:

1. **Read the model.** Skim the [README](../../README.md) for the product shape,
   then [`GOVERNANCE.md`](../../GOVERNANCE.md) for how verification and
   ratification differ, and at least one feature's `spec.md` / `plan.md` /
   `tasks.md` triple under [`specs/`](../../specs/) so the spec-driven flow makes
   sense.
2. **Set up local checks.** The same gates CI runs are offline and runnable on
   your machine before you ask for review — example validation, the path-manifest
   carrier, and the test suite. Setup is in [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
   and [`validators/README.md`](../../validators/README.md).
3. **Open a small, bounded PR.** Reference the issue or spec that authorizes it,
   declare its change type, keep the changed-file boundary tight, and add the
   per-PR path-manifest carrier when one applies. Independent review is required;
   you cannot approve your own PR.
4. **Stop at the boundaries.** Some surfaces — branch protection, the
   constitution, identity/secret material, and other privileged classes — require
   explicit maintainer authorization *before* you touch them. When in doubt, open
   an issue and ask first.

The full, detailed contributor journey — the trust-tier table, the governed
cycle for a contributor, the first-PR checklist, review independence, and the
boundary list — lives in [`contributing-to-ce.md`](./contributing-to-ce.md).
Start there once these four steps make sense.

---

## Where to go next

| You want to… | Read |
| --- | --- |
| **Follow a hands-on walkthrough start to finish (recommended first)** | [**`complete-walkthrough.md`**](./complete-walkthrough.md) |
| Understand the workflow and its words | [`understanding-ce.md`](./understanding-ce.md) |
| Map your Agile/SCRUM habits onto CE's SDLC | [`agile-to-ce-sdlc.md`](./agile-to-ce-sdlc.md) |
| Get to a governed seat fast | [`zero-to-governed-seat-quickstart.md`](./zero-to-governed-seat-quickstart.md) |
| Run CE from a Mac today | [`onboarding-macos-container.md`](./onboarding-macos-container.md) |
| Walk the full install-to-ship pilot | [`pilot-runbook.md`](./pilot-runbook.md) |
| Contribute to CE itself | [`contributing-to-ce.md`](./contributing-to-ce.md) |
| See the whole project at a glance | [`README`](../../README.md) · [`GOVERNANCE.md`](../../GOVERNANCE.md) |

Welcome aboard. Type a prompt, and let CE hold the gate.
