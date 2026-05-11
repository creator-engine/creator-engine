# Session Continuity Protocol v0.1

**Status**: Source-ratified lightweight protocol for Creator Engine fresh-session continuity.

## Purpose

A fresh Hermes/Nefarious session must be able to recover Creator Engine state quickly without relying on chat memory. This protocol defines the minimum start/end checks and the durable state file used until Feature 002 promotes a fuller operating model.

## Source of truth

1. Committed repo content is canonical.
2. `.hermes/session-state/STATE.md` is the current continuity snapshot.
3. `.hermes/handoffs/` may contain supporting local handoffs, but `STATE.md` must carry any item that cannot be lost.
4. Chat transcripts are non-canonical unless promoted into a committed artifact.

If these disagree, committed repo content wins until Source ratifies a correction.

## Start-of-session checklist

At the beginning of any fresh Creator Engine session:

1. Run `git status --short --branch --untracked-files=all`.
2. Run `git log -1 --oneline --decorate`.
3. Read this file.
4. Read `.hermes/session-state/STATE.md`.
5. Compare the observed branch/head with the state snapshot.
6. If the snapshot is stale, reconcile it before repo mutation.
7. Inspect live panes/agents if tmux is involved.
8. Confirm that no REPO-WRITER acts without a Source-ratified assignment envelope.
9. Continue only the state file's immediate next step, unless Source changes direction.

## End-of-session checklist

Before ending or handing off a Creator Engine session:

1. Record `git status` and current HEAD.
2. Record PR state and merge state for any relevant PRs.
3. Record active panes/agents and whether they are idle, architect, doc-writer, or repo-writer.
4. Record ratified decisions that affect the next session.
5. Add deferred cleanup or unresolved decisions to the carry-forward queue.
6. Set exactly one immediate next step.
7. Keep `STATE.md` concise; move detailed reports into handoffs or PR comments and link them.
8. Do not commit/push/merge state changes unless Source has authorized the change boundary or it is part of a ratified PR workflow.

## STATE.md schema

`.hermes/session-state/STATE.md` must contain these sections:

1. `## Repository snapshot`
2. `## PR state`
3. `## Ratification state`
4. `## Active roles and panes`
5. `## Immediate next step`
6. `## Carry-forward queue`
7. `## Last updated`

The file should stay under roughly 80 lines. Overflow belongs in a handoff file or PR comment referenced by `STATE.md`.

## Ratification rule

Observable state updates, such as PR merged/open and pane idle/busy, are routine continuity updates. A change that authorizes repo mutation, changes the next task, changes governance, or clears a carry-forward item requires Source ratification or inclusion in a Source-ratified PR.

## Anti-bureaucracy guardrails

- Do not create new feature numbers for session continuity.
- Do not duplicate Feature 002 canonical document bodies here.
- Do not use session protocol files as a substitute for assignment envelopes.
- Do not let carry-forward items accumulate without review.
- Do not claim Sprint 0 complete because this protocol exists.

## Current transition

After this protocol is merged, the next fresh session should read `STATE.md`, preserve the carry-forward cleanup note, and formulate the Sprint 0 Execution Slice A assignment envelope for authoring the 17 Feature 002 canonical documents.
