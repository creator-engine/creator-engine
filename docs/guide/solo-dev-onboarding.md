# Solo + Dev Mode Onboarding

*This guide is for a solo developer who has chosen **Dev mode**: you work
directly in your own coding-agent terminal while Creator Engine wraps that
session with governance. If you prefer a less hands-on tour, see
[`solo-ceo-onboarding.md`](./solo-ceo-onboarding.md) instead.*

> **You are in: Solo + Dev mode.** You still type prompts to Claude Code or
> Codex yourself. CE's job is to start the governed session, keep the local
> state healthy, and hold privileged actions until the right human approval is
> present.

---

## The day-one shape

The first run is deliberately small:

1. Prepare the host and repository.
2. Run `ce onboard`.
3. Use the governed agent pane that opens.
4. Return later with `ce launch --backend host`.

The detailed Frame -> Shape -> Build -> Review -> Ship loop happens inside that
governed session. On day one, you do not need to memorize a command table before
you can get value.

---

## Prerequisites

Before onboarding, make sure these are true:

- A supported coding-agent CLI is installed and usable from your shell, such as
  Claude Code or Codex.
- The repository ignores CE's local Hermes state:

  ```gitignore
  .hermes/
  ```

- You have a CE install. If you have not installed yet, follow
  [`zero-to-governed-seat-quickstart.md`](./zero-to-governed-seat-quickstart.md)
  first.

The `.hermes/` ignore rule matters because CE refuses to create tracked local
runtime state during onboarding. Add it before the first run, commit the ignore
change through your normal project process if needed, then continue.

---

## Phase 0 - First run: onboard

From the repository you want to use with CE, run:

```bash
ce onboard
```

`ce onboard` performs the first-run sequence: it verifies the local install,
checks host readiness, initializes local CE state, prepares your path, and opens
the first governed agent pane unless you explicitly opt out.

If you want to prepare the host and state without opening the pane yet, run:

```bash
ce onboard --no-launch
```

If onboarding refuses, read the refusal text and fix that specific prerequisite
before trying again. Re-run support is still being tightened; do not assume
`ce onboard` is a general recovery command for partially reused state.

---

## Phase 1 - Daily entry point: launch

After onboarding has completed, return to the governed session with:

```bash
ce launch --backend host
```

`ce launch --backend host` opens or attaches the visible governed terminal
launcher for your agent. It is the daily entry point after the repository has
been onboarded; it is not the first command on a fresh host.

For a dry-run of the launcher plan without opening a pane, use:

```bash
ce launch --backend host --dry-run
```

---

## Phase 2 - Work in the pane

Inside the governed pane, work the way you normally work with your coding
agent:

1. Describe the change you want.
2. Answer clarifying questions.
3. Read the proposed work boundary and acceptance criteria.
4. Approve only the privileged actions you actually intend.
5. Review the resulting diff, tests, and pull request evidence before anything
   ships.

CE stays quiet until it has a reason to intervene. The important moment is when
the agent reaches for something privileged, such as source-host mutation or
credential access. CE refuses or holds that action outside the agent and tells
you why.

If you arrive with an existing PRD or requirements document, start Shape from
that context instead of retyping it:

```bash
ce shape --from docs/prd/onboarding.md
```

CE previews one first Scope, cites `Source PRD: docs/prd/onboarding.md`, and
waits for explicit confirmation before it records anything.

For the in-product vocabulary tour, run:

```bash
ce guide
```

For a host/environment preflight, run:

```bash
ce doctor
```

---

## Repo-connected install rail

`ce onboard` is the quick first-run rail for getting a governed local session.
Connecting CE to a repository it can ship to is a separate, human-approved
install rail. When you have the verified install artifacts and answers file, the
shape is:

```bash
ce install \
  --spec <verified-spec> \
  --answers ce-install.answers.yaml \
  --plan
```

Then, only after the plan is acceptable:

```bash
ce install \
  --spec <verified-spec> \
  --answers ce-install.answers.yaml \
  --apply --non-interactive
```

The full version of that flow, including trust roots, anchors, and answer
schema paths, lives in
[`zero-to-governed-seat-quickstart.md`](./zero-to-governed-seat-quickstart.md).

---

## Your irreducible gestures

CE is designed so that a small set of decisions stays with you:

| You always decide | The agent handles |
| --- | --- |
| What change is worth making | Drafting a concrete implementation path |
| What "done" means | Producing the diff and test evidence |
| Whether a privileged action is acceptable | Surfacing the refusal or approval point |
| Whether the pull request satisfies your intent | Preparing the evidence for review |
| Whether to connect CE to a repo through the install rail | Running only the planned, approved install steps |

In Dev mode you stay close to the shell and the agent pane. The governance layer
is outside the agent, so the agent cannot reason around it.

---

## Where to go next

| You want to... | Read |
| --- | --- |
| The front door and big picture | [`welcome.md`](./welcome.md) |
| The canonical command path | [`quickstart.md`](./quickstart.md) |
| How CE builds software | [`how-ce-builds-software.md`](./how-ce-builds-software.md) |
| The plain-language vocabulary tour | [`understanding-ce.md`](./understanding-ce.md) |
| The Solo + CEO path | [`solo-ceo-onboarding.md`](./solo-ceo-onboarding.md) |
| A worked SCRUM-to-CE mapping | [`agile-to-ce-sdlc.md`](./agile-to-ce-sdlc.md) |
| The full install-to-ship pilot runbook | [`pilot-runbook.md`](./pilot-runbook.md) |
| Contribute to CE itself | [`contributing-to-ce.md`](./contributing-to-ce.md) |
