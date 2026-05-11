# Session Continuity Protocol

**Status**: Upstream Creator Engine protocol for fresh-session continuity in
deployed instances. Source-ratified.

## Purpose

A fresh Hermes operator session must be able to recover the state of a deployed
Creator Engine instance quickly, without relying on chat memory or transient
runtime context. This protocol defines the minimum start/end checks and the
local-state schema each instance maintains.

Creator Engine upstream ships this protocol and a generic state template. Each
deployed instance derives its own local state file from the template. Upstream
does not track instance-local runtime facts.

## Source of truth

1. Committed upstream repository content is canonical for Creator Engine
   protocols, schemas, templates, validators, and governance.
2. Each instance maintains its own local continuity snapshot at
   `.hermes/session-state/STATE.md`, derived from the template at
   `templates/hermes/session-state/STATE.template.md`. This file is
   instance-local and MUST remain ignored by upstream Git tracking.
3. `.hermes/handoffs/` MAY contain instance-local handoffs. Items that cannot
   be lost MUST be reflected in the local `STATE.md`.
4. Chat transcripts are non-canonical until promoted into a committed upstream
   artifact (governance, protocol, schema, validator, or template change) or
   into an explicit instance-local handoff.

If these disagree, committed upstream repo content wins until the Source
authority of that instance ratifies a correction.

## Upstream/local boundary

The following are instance-local and MUST NOT be committed to upstream
Creator Engine:

- absolute filesystem paths of any instance worktree or repository clone;
- live branch names tied to a specific in-flight instance batch;
- live PR numbers, PR URLs, merge commit SHAs of instance work;
- tmux pane identifiers, session names, or other runtime/terminal identifiers;
- active role assignments per pane or per agent;
- the instance's immediate next step;
- carry-forward items naming specific in-flight instance work;
- tenant-specific runtime fixtures, secrets, tokens, or credentials.

The following are upstream-worthy and MAY land in committed upstream content:

- protocol changes such as this document;
- schema and validator changes;
- template changes under `templates/`;
- generic or synthetic examples;
- governance, security, quality, and operations documentation;
- amendments to the constitution under its governance procedure.

A reusable rule, schema, or template belongs upstream. A fact about what is
running right now in one instance belongs in that instance's ignored local
state.

## Start-of-session checklist

At the beginning of any fresh Creator Engine instance session:

1. Run `git status --short --branch --untracked-files=all`.
2. Run `git log -1 --oneline --decorate`.
3. Read this protocol.
4. Read the instance-local `.hermes/session-state/STATE.md`, if present. If it
   does not exist, initialize it from
   `templates/hermes/session-state/STATE.template.md`.
5. Compare the observed branch/head with the local state snapshot.
6. If the local snapshot is stale, reconcile it before any repo mutation.
7. Inspect live panes/agents if a terminal multiplexer is involved.
8. Confirm that no repo-writer agent acts without a ratified assignment
   envelope.
9. Continue only the local state file's immediate next step, unless the
   instance's Source authority changes direction.

## End-of-session checklist

Before ending or handing off a Creator Engine instance session:

1. Record `git status` and current HEAD in the local state file.
2. Record PR state and merge state for any relevant PRs in the local state
   file.
3. Record active panes/agents and whether they are idle, architect,
   doc-writer, or repo-writer.
4. Record ratified decisions that affect the next session.
5. Add deferred cleanup or unresolved decisions to the carry-forward queue.
6. Set exactly one immediate next step.
7. Keep the local state file concise; move detailed reports into instance
   handoffs or PR comments and link them.
8. Do not commit/push/merge state changes unless the instance's Source
   authority has authorized the change boundary or it is part of a ratified
   PR workflow scoped to upstream-worthy artifacts.
9. Confirm the local state file is still covered by `.gitignore` and is not
   staged for upstream commit.

## Local state schema

`.hermes/session-state/STATE.md` MUST contain these sections:

1. `## Repository snapshot`
2. `## PR state`
3. `## Ratification state`
4. `## Active roles and panes`
5. `## Immediate next step`
6. `## Carry-forward queue`
7. `## Last updated`

The file should stay under roughly 80 lines. Overflow belongs in an
instance-local handoff file or PR comment referenced from the state file.

Use the template at `templates/hermes/session-state/STATE.template.md` to
initialize new instances. The template MUST be kept generic upstream;
instance-specific values are filled in locally.

## Ratification rule

Observable state updates, such as PR merged/open and pane idle/busy, are
routine continuity updates and MAY be applied to the local state file by the
operator without an explicit ratification round.

A change that authorizes repo mutation, changes the next task, changes
governance, or clears a carry-forward item requires explicit ratification
from the instance's Source authority, or inclusion in a ratified PR scoped to
upstream-worthy artifacts.

## Anti-bureaucracy guardrails

- Do not create new feature numbers for session continuity itself.
- Do not duplicate canonical upstream document bodies into the local state
  file; reference them.
- Do not use session protocol files as a substitute for assignment envelopes.
- Do not let carry-forward items accumulate without periodic review.
- Do not claim a sprint or milestone complete merely because this protocol or
  the local state file exists.

## Upstream constraint

This protocol is upstream-worthy and reusable across Creator Engine
deployments. Any change that re-introduces instance-local live facts into
upstream-tracked files violates the upstream/local boundary above and MUST be
reverted or relocated to instance-local ignored files.
