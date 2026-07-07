# Understanding Creator Engine

Creator Engine runs **your own coding agent under governance.** You keep using
the agent you already know. CE adds a structured, evidence-backed loop around
real work so changes are shaped, ratified, built, reviewed, and shipped on
purpose.

Start with the canonical [`quickstart.md`](./quickstart.md) when you want
commands. Read [`how-ce-builds-software.md`](./how-ce-builds-software.md) when
you want the concepts behind the loop.

## What CE Is

The core idea is simple: the thing that decides whether work is good lives
outside the agent. You judge artifacts: a Scope, a diff, checks, review evidence,
and the Completion Report. You do not judge a transcript.

CE is CLI-anchored. The everyday path is `ce brain init` once, then
`ce launch --backend host` to open your governed agent session. Contained launch
is hardening in progress; use the host backend unless your operator tells you a
contained backend is ready for your repo.

## The Five Stages

CE names the loop with five plain words:

```text
Frame -> Shape -> Build -> Review -> Ship
```

1. **Frame** - understand the problem, why it matters, and what good would look
   like. This is exploration only; nothing is tracked yet.
2. **Shape** - turn the framed problem into a Scope with Goal, Done-when, and
   Change-type.
3. **Build** - let the agent execute the ratified Scope in a governed run.
4. **Review** - grade the result against Done-when and evidence.
5. **Ship** - land the governed outcome: merged PR, delivered research, or
   no-change.

This is a loop, not a waterfall. Review can send work back. A large Scope can
spawn smaller Scopes.

## The Scope

When exploration becomes real work, CE records a **Scope**. The Scope is the
contract for the run.

| Field | What it means |
| --- | --- |
| **Goal** | What you are trying to accomplish |
| **Done-when** | The checks that say the work is finished |
| **Change-type** | What kind of change this is and how risky it is |

Readiness is the ratifiable state, not a Scope field: CE marks the Scope Ready
when these fields are valid.

Optional lane-aware cap: your operator may ask you to add a cap for a specific
lane. Use `%` for a subscription lane with rolling windows, or `$` for an API
lane. This is opt-in and should not be front-loaded in the default path.

Nothing builds until you ratify a Ready Scope:

```bash
ce ratify <scope-id>
```

Natural-language chat can help shape the Scope, but it is not authorization.
Governed work begins at explicit `ce` verbs, and the Scope record is the
governing contract.

## The Completion Report

After a run, CE gives you a compact Completion Report:

```text
Outcome   PR opened -> #24
Verdict   Done-when 3/3 met · tests green · in scope
Next      Review PR #24
```

Review the artifacts against Done-when. If they satisfy the Scope, Ship through
the governed merge path. If they do not, send the work back with concrete Review
feedback.

## Welcome Pack Rule

Tenant welcome packs link the canonical Quickstart and concepts guide instead
of duplicating the journey. Packs can add local setup details, but the CE journey
stays in [`quickstart.md`](./quickstart.md) and
[`how-ce-builds-software.md`](./how-ce-builds-software.md).
