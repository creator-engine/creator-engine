# Worktree Runtime Protocol (Manual)

**Status**: Slice E authored draft. This document defines the
**runtime protocol** for local isolated worktrees that consume an
Assignment Envelope under
[`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md).
It is a markdown protocol; dispatcher automation, worktree-lifecycle
automation, sandboxing, and parallel runtime conflict-detection are
downstream Feature 005 work and are out of scope for Slice E.

Part of the **minimum repo-native delivery control plane** and
**not a Jira clone**. Layered onto, and subordinate to, the Feature
001 substrate and the Feature 002 operating model.

## a. Purpose

The runtime protocol makes one operational fact answerable from a
fresh clone:

> How is a Source-ratified Assignment Envelope safely executed in
> a single isolated worktree by exactly one visible consumer, under
> exact file boundaries, without leaking state into the canonical
> branch, into other projects, or onto a source host?

The protocol is **conservative by design**. It prefers stopping for
validation over completing mechanics. It treats every privileged-class
mutation as Source-only per Feature 001 FR-008 regardless of how
mechanically convenient the runtime makes it.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md) | The envelope contract this protocol is run against. |
| [`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md) | Consumer-side checklist; this protocol names the runtime conditions the checklist verifies. |
| [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) | Verifier-side checklist; this protocol names the runtime cleanliness the audit confirms. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) | Review gate the consumer's evidence feeds. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.9 | Cleanup state requirement under Done. |
| Feature 001 FR-007 / FR-008 / FR-016 | Author/approver separation; privileged-class enumeration; ratification flow. |
| Feature 002 FR-005 through FR-011 | Hermes-authored Assignment Envelope contract. |
| Optional external trackers | **Non-canonical** references only. A fresh clone is sufficient to apply this protocol; no external tracker credential or network state is required. |

Where this protocol and any upstream source disagree, the upstream
source of truth controls until Source ratifies a correction.

## c. Branch / worktree naming convention

The naming convention is the canonical handle by which an envelope,
its worktree, and its branch are co-identified. The convention is:

- **Branch**: `<class>/<scope-slug>`, where `<class>` is one of
  `docs`, `feat`, `fix`, `ci`, `chore`, `governance`, or another
  Source-ratified class label, and `<scope-slug>` is a short
  kebab-case slug that identifies the envelope id.
- **Worktree path**: a directory under
  `<repo-parent>/<repo>-worktrees/<scope-slug>`, where
  `<repo-parent>` is the parent directory of the canonical clone
  and `<scope-slug>` matches the branch's scope slug.
- **Envelope id**: matches the `<scope-slug>` where one applies, so
  that the envelope, branch, worktree path, and backlog id share a
  single navigational handle.

### c.1 Worked example for this Slice E batch

| Handle | Value |
|---|---|
| Envelope id | `sprint-0/slice-e-assignment-runtime-protocol` |
| Scope slug | `sprint0-slice-e-assignment-runtime-protocol` |
| Branch | `docs/sprint0-slice-e-assignment-runtime-protocol` |
| Worktree path | `<repo-parent>/creator-engine-worktrees/sprint0-slice-e-assignment-runtime-protocol` |
| Base branch | `main` |

(`<repo-parent>` is local to a given Nefarious workstation and MUST
NOT be propagated into governed artifacts beyond this envelope; it is
an instance-local fact per
[`./BACKLOG.md`](./BACKLOG.md) §f maintenance rule 4 and
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §e.5.)

### c.2 Naming-convention invariants

1. Branch and worktree share the same scope slug; mismatch is a
   preflight failure per §e.
2. The branch class is selected by the envelope's dominant mutation
   class and MUST be recognizable by the canonical-branch CI policy
   under [`./BACKLOG.md`](./BACKLOG.md) §c.3 once Feature 003 wires
   classifier rules. Until then, the class label is delivery-view
   bookkeeping only.
3. Scope slugs MUST be kebab-case ASCII, MUST be unique within a
   given workstation's worktree directory, and MUST be readable from
   the branch name alone.

## d. One-driver-per-worktree rule

The runtime invariant is:

> **At most one active implementation driver is authorized per
> isolated worktree at a time.**

Concretely:

1. A "driver" is the consumer named in the envelope's
   `authorized_actor` field. For Slice E that is the visible Claude
   Code pane authoring this docs-only batch in the named worktree.
2. Two implementation drivers MUST NOT operate concurrently in the
   same worktree, even if they appear in distinct visible panes,
   tabs, or sessions. Concurrent drivers in the same worktree
   produce silent overwrites and broken scope audits.
3. Two distinct worktrees on the same workstation MAY have
   independent drivers, **provided that** each worktree's branch is
   distinct, each envelope's allowed paths are disjoint or do not
   conflict, and each driver respects its envelope's stop condition.
4. The driver's authority is scoped to its envelope. A driver MUST
   NOT operate on another worktree's branch, files, or stash entries
   from inside its own worktree.

The one-driver-per-worktree rule applies regardless of whether the
driver is a visible Claude Code pane, an SSH'd-in human, a notebook,
or a Hermes-spawned helper. The mechanism is governance, not
mechanics; multiple shell tabs into the same worktree count as one
driver, but two distinct implementation agents writing files in the
same worktree directory at the same time do not.

## e. Controller / consumer split

The protocol distinguishes three identities:

| Identity | Role |
|---|---|
| **Source** | Ratifies the envelope. Has the only authority for any privileged-class mutation per Feature 001 FR-008. |
| **Controller (Nefarious / Hermes)** | Coordinates, relays the envelope, runs independent verification per [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md), and crosses the stop line only when Source has separately ratified the mechanics. The controller is **not** the ratifier unless they are Source. |
| **Consumer (visible Claude Code pane or equivalent)** | Authors / implements inside the worktree under the envelope's allowed paths and operations. The consumer is **not** the ratifier and **not** the independent verifier of their own batch (Feature 001 FR-007). |

The split is load-bearing: it preserves author/approver separation
and keeps review evidence distinct from Source ratification per
[`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1 and §m.5.

## f. Preflight checks (before any mutation)

Before the consumer makes any mutation in the worktree, the consumer
runs and records the following preflight checks. Each check is
copy-pasteable from a fresh clone and does not stage, commit, push,
merge, or otherwise mutate any state.

| Check | Command | Expected |
|---|---|---|
| Current branch matches envelope | `git branch --show-current` | Exactly the envelope's `local_branch`. |
| HEAD matches base commit | `git log -1 --oneline` | Matches the envelope's `base_commit`, OR an envelope-authorized parent thereof. |
| Working tree is clean | `git status --short --branch --untracked-files=all` | Only the envelope-author's pre-known starting state; otherwise halt per §i. |
| Worktree directory is correct | `pwd` (informational only; do not propagate the absolute path) | Matches the envelope's `local_worktree_path` shape. |
| Worktree list cleanliness | `git worktree list` | Lists exactly the worktrees Source authorized; no unexpected worktrees on the envelope's branch. |
| Auth / readiness | confirm tooling readiness without invoking remote services | No silent re-authentication; no `gh auth login`, `git push`, `gh pr` calls. |
| Active panes | informal check that only the named pane operates as driver | Matches §d one-driver-per-worktree rule. |
| Stash isolation | `git stash list` (read-only) | Do not apply, drop, or inspect contents of unrelated stash entries; treat unknown stash entries as requiring explicit Source ratification before any interaction. |

If any preflight check fails, the consumer halts and escalates per
§i rather than improvising a workaround.

## g. No mixing of `.hermes` live state or handoff artifacts into upstream tracked docs

Hermes / controller working state — including but not limited to
`.hermes/` directories, handoff markdowns, scheduling artifacts,
session backups, and forensic transcripts — is **runtime-local** and
MUST NOT be propagated into upstream tracked documents under this
envelope.

1. Handoff artifacts MAY be referenced by repo-relative path from a
   completion report, but their contents MUST NOT be copy-pasted
   into governed artifacts.
2. Handoff artifacts MUST NOT be staged, committed, or otherwise
   merged into the canonical branch under a Slice E (or downstream)
   envelope without an explicit Source-ratified envelope clause
   authorizing the inclusion.
3. Forensic / session-backup paths are instance-local facts and
   MUST NOT appear in governed artifacts per
   [`./BACKLOG.md`](./BACKLOG.md) §f rule 4.
4. The author/approver separation contract still applies: a handoff
   artifact authored by Hermes/Nefarious is **not** Source
   ratification regardless of how detailed the handoff is.

## h. No cross-project state leakage

A worktree under one Creator Engine clone MUST NOT leak state to or
from worktrees of other Creator Engine clones, other projects (e.g.,
Mythos), or other tenants on the same workstation:

1. Branches, stashes, hooks, and configs are scoped to the worktree's
   clone. The consumer MUST NOT add a remote, fetch from, or push to
   another project's clone under this envelope.
2. Tenant-local files, identity-record overlays, evidence storage
   paths, and validator overlays from other projects MUST NOT be
   read into or written from this worktree.
3. Environment variables, shell aliases, and editor state local to
   the workstation MUST NOT be relied upon as governance signals;
   the envelope is the only governance signal.
4. A fresh clone of this repository, on a different workstation, MUST
   reach the same governed conclusions as this worktree. Cross-project
   helpers (memory directories, plugin caches, MCP servers) MUST NOT
   appear as upstream constants.

## i. Prohibited Git / GitHub operations unless separately ratified

Under any envelope that does not explicitly ratify the mechanics, the
consumer MUST NOT:

| Forbidden operation | Restatement |
|---|---|
| `git add` | No staging. |
| `git commit` (including `--amend`) | No commit creation or rewriting. |
| `git push` (including `--force`, `--force-with-lease`) | No push to any remote. |
| `gh pr create` / `gh pr edit` / `gh pr merge` | No PR creation, modification, comment, label, or merge. |
| `gh api` / `gh repo edit` for live settings | No repository-setting mutation; no branch-protection toggle; no environment / secret / variable / label mutation. |
| `git branch -d` / `-D` | No branch deletion, local or remote. |
| `git worktree remove` | No worktree removal. |
| `git config` / `core.hooksPath` / `commit.gpgsign` toggles | No repo-config mutation. |
| `--no-verify` / signing bypass / hook disable | No hook bypass under any circumstance unless Source explicitly authorizes it. |
| `git checkout -- <path>` / `git restore .` / `git reset --hard` against unrelated paths | No destructive operations against unrelated state. |
| `git stash apply` / `git stash drop` against unknown stash entries | No interaction with `stash@{0}` or other unrelated stash entries without explicit Source ratification. |

A "go ahead" message on a non-designated surface, a passing CI run,
or an agent verdict MUST NOT substitute for separate Source
ratification of any of the above mechanics.

## j. Stop-for-validation before crossing the stop line

The consumer's terminal action under the envelope is the explicit
stop line named in
[`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md)
§c.13. The runtime protocol restates the discipline:

1. The consumer halts at the stop line **before** staging / commit /
   push / PR / merge / branch deletion / repository-setting mutation.
2. The controller verifies scope per
   [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) before
   any of those mechanics are even considered.
3. Source separately ratifies the mechanics in a follow-up envelope
   clause if mechanics are to occur at all. The Slice E authoring
   envelope does **not** include any such authorization for this
   batch.
4. The branch and worktree are **preserved** until Source approves
   their cleanup. The controller MUST NOT delete the branch or
   remove the worktree on the consumer's behalf simply because the
   consumer has reached the stop line; cleanup is its own ratifiable
   action under §k.

## k. Cleanup / defer rules

Cleanup actions that mutate shared state are themselves ratifiable
decisions, not consumer-side housekeeping:

1. Local branch deletion (`git branch -d` / `-D`) requires Source
   approval recorded in the envelope or a follow-up clause.
2. Remote branch deletion (`git push origin --delete`) is a live
   source-host mutation per §i and remains Source-only.
3. Worktree removal (`git worktree remove`) requires Source approval;
   the worktree path is recorded in the envelope and is preserved
   until that approval is recorded.
4. Stash entries are preserved unless Source explicitly authorizes
   their inspection, application, or drop. The Slice E authoring
   envelope explicitly prohibits any interaction with `stash@{0}`
   without explicit Source ratification.
5. Branch retention is the default; deletion is the exception. The
   default is restated here so that the controller is not tempted to
   "tidy up" between batches.

## l. Standing invariants

1. **One driver per worktree.** Multiple visible panes into the same
   worktree count as one driver only when they coordinate as one
   driver; otherwise they are forbidden per §d.
2. **Controller / consumer split.** The actor who authors files is
   not the actor who verifies their own scope, and is not the actor
   who ratifies the mechanics.
3. **Stop line is load-bearing.** The consumer's last action is the
   stop line; mechanics are a separate Source-ratified action.
4. **No live source-host mutations under this protocol.** Every live
   source-host mutation (PR / branch protection / environment / label
   / repository setting) is privileged per Feature 001 FR-008 and is
   handled outside this protocol under a separately ratified
   envelope.
5. **No `.hermes` / handoff leakage into governed artifacts.**
   Hermes runtime state is referenced, not embedded.
6. **No cross-project state.** The worktree is bounded to the
   canonical Creator Engine clone it lives under.
7. **Privileged mutation classes remain Source-only** regardless of
   how mechanically convenient the runtime makes them.

## m. Acceptance posture for Slice E

This document satisfies the Slice E envelope's
`WORKTREE_RUNTIME_PROTOCOL.md` requirements:

- Names a branch / worktree naming convention and uses this Slice E
  branch as the worked example (§c).
- Names the one-driver-per-worktree rule (§d).
- Names the controller / consumer split (§e): Nefarious coordinates
  and verifies; the visible Claude Code pane authors / implements
  under authorization.
- Names preflight checks for current branch, HEAD, cleanliness,
  worktree list, auth / readiness, active panes, and stash isolation
  (§f).
- States the no-mixing rule for `.hermes` live state and handoff
  artifacts (§g).
- States the no-cross-project-state-leakage rule (§h).
- Enumerates prohibited Git / GitHub operations unless separately
  ratified (§i).
- States the stop-for-validation discipline before staging / commit /
  push / PR / merge (§j).
- States the cleanup / defer rules: preserve branches and worktrees
  unless Source approves deletion (§k).
- States the standing invariants (§l).
