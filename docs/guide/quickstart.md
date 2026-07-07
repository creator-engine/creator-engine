# Creator Engine Quickstart

This is the canonical, copy-paste path for a first governed change with
Creator Engine. It starts from the proven tenant path: initialize the local CE
brain once, launch your own coding agent through CE on the host backend, Shape a
Scope, ratify it, let CE drive the governed run, then review the Completion
Report.

Contained-by-default launch remains hardening work in progress. Today, use the
host backend unless your operator has explicitly told you a contained backend is
ready for your repo.

## 1. Initialize CE Brain Once

```bash
ce brain init
```

Artifact: a local CE brain store for this repo.

State after this step: CE can remember governed project context across sessions.
Run this once per repo, then leave it alone unless CE tells you to refresh it.

## 2. Launch Your Governed Agent Session

```bash
ce launch --backend host
```

Artifact: a governed terminal session around the coding agent you already use.

State after this step: you are in Frame. You can explore the goal in plain
language, ask questions, and inspect the repo. This exploration shapes context
only; it is not the contract for work.

Slash commands, harness skills, and agent-specific shortcuts can be convenient
sugar, but the canonical journey is the `ce` CLI.

## 3. Shape The Work

```bash
ce shape login-empty-state
```

Artifact: a sharpened candidate Scope boundary: goal, constraints, and
questions that must be answered before work can start.

State after this step: CE has enough context to draft a Scope, or it has named
the missing details you need to answer.

## 4. Create The Scope

```bash
ce scope login-empty-state \
  --goal "Show helpful copy when the login activity view has no events yet" \
  --done-when "A new repo shows empty-state copy instead of a blank panel" \
  --done-when "The copy points the user to launching the first governed run" \
  --done-when "Existing populated activity views are unchanged" \
  --budget 1 \
  --budget-unit % \
  --budget-window per_run \
  --change-type code
```

Artifact: a Scope record. The Scope is the governing contract for the run.

State after this step: the work is in Shape. CE can check whether the Scope is
Ready. The required fields are Goal, Done-when, Budget, and Change-type. Use the
smallest honest Change-type that describes the risk.

The example Budget is a paste-testable 1% per-run cap. Substitute the amount,
unit, and window your operator gives you for your lane.

## 5. Ratify The Scope

```bash
ce ratify login-empty-state --approver-ref 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

Artifact: a ratification record bound to the Scope.

State after this step: the front gate is open. CE may Build exactly this Scope.
If the goal, Done-when, or Change-type changes later, shape a revised Scope
instead of treating the chat transcript as authorization.

The literal above is valid 64-hex syntax for the example. In a real run,
generate a fresh approver ref with `openssl rand -hex 32` and pass that value.

## 6. Drive The Governed Run

```bash
ce drive login-empty-state --spawn
```

Artifact: a governed run with evidence, a changed branch, and usually a pull
request. If there is no change to make, the run records that outcome instead.

State after this step: CE is in Build, then Review. The agent works inside the
ratified Scope. If review finds a problem, the loop can go back to Shape or
Build; this is not a waterfall.

## 7. Read The Completion Report

```bash
ce report login-empty-state
```

Artifact: a Completion Report with three plain sections:

```text
Outcome   PR opened -> #24
Verdict   Done-when 3/3 met · tests green · in scope
Next      Review PR #24
```

State after this step: you have the evidence needed to Review. Judge the diff,
tests, and report against the Done-when you ratified.

## 8. Ship Or Loop

If the result satisfies the Scope and your review gate is green, ship through
the governed merge path your repo uses. If it does not satisfy the Scope, send
the work back with feedback tied to Done-when.

Artifact: a shipped outcome: merged PR, delivered research, or ratified
no-change.

State after this step: the Scope is done, or it has looped back with concrete
Review feedback.

## Anti-Drift Rule

Welcome packs must link this Quickstart and
[`how-ce-builds-software.md`](./how-ce-builds-software.md) instead of copying
their journey text. Tenant-specific packs may add local prerequisites and
contacts, but the CE journey itself lives here.
