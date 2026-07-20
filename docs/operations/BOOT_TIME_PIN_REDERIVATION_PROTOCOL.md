# Boot-Time Pin Re-Derivation Protocol

**Status**: Mandatory controller resume-ritual protocol. Applies at every
fresh boot, `/clear`, relaunch, or handoff, before any binding act.

## a. Purpose

A resume-state record — a checkpoint, a handoff, a local continuity snapshot
— is a claim about the world at the moment it was written. It is not the
world. A controller that resumes from such a record and acts on its claims
without re-checking them against live, durable sources can act on state that
has since moved, was wrong when written, or was silently lost or overwritten
between the write and the resume.

This protocol closes that gap: before any binding act taken immediately after
a resume, `/clear`, or relaunch, every pin the incoming record claims MUST be
re-derived live and compared against the claim. A mismatch is a stop
condition, not a note-to-self.

## b. The rule

Before any binding act after a resume, `/clear`, or relaunch, re-derive every
pin the incoming resume-state record claims, directly from a live, durable
source — never from the resume-state text alone. Compare each re-derived pin
against the resume-state claim.

**Any mismatch between a resume-state claim and its live derivation is a
STOP**: halt, investigate the discrepancy, and correct the record before
taking the next act.

## c. Checklist — re-derive every pin live

1. **Git head and remote.** Re-derive the current head (e.g. `git rev-parse
   HEAD` in the resuming worktree) and the remote tip (e.g. `git ls-remote
   origin main`). Compare both against the resume-state's claimed head and
   branch. A mismatch means the record is stale, or the branch moved since
   the snapshot was written; do not assume the record is still current.
2. **Worktree porcelain for every claimed-staged branch.** For every branch
   the resume-state claims has staged or uncommitted work, re-derive its
   live porcelain status (e.g. `git status --short --branch
   --untracked-files=all` in that worktree) and compare it to the claim. A
   branch claimed clean that is dirty, or claimed dirty that is clean, is a
   mismatch.
3. **Open-PR set and approval states.** Re-list the live open-PR set and
   each PR's review/approval status from the source host, and compare
   against the resume-state's claimed PR set and states. A PR claimed
   open-and-approved that the live source shows merged, closed, or
   unapproved is a mismatch.
4. **Armed-policy state.** Re-check the live armed-policy status — including
   automerge status and whether any kill-switch is engaged — rather than
   trusting the resume-state's recollection of arming state.
5. **Daemon / wall / queue health.** Re-probe the live health of the
   approval wall daemon, merge queue, and any other standing daemon the
   resume-state references, rather than assuming the last-known-good state
   still holds.
6. **Fleet seat liveness.** Re-probe each seat or worker the resume-state
   claims is live, idle, blocked, or complete, against its actual live
   status.
7. **Newest resume-state file mtime vs. expected.** Confirm the resume-state
   file being loaded is in fact the newest one in the expected, currently
   owned state root, by mtime — not merely the most recently referenced one.
   A record loaded from a stale, frozen, or no-longer-owned mirror is not a
   valid resume source even when its content looks plausible.

This is the minimum set. A deployed instance MAY add instance-specific pins
to re-derive; it MUST NOT remove or skip any pin in this list.

## d. On mismatch: STOP

A mismatch between any resume-state claim and its live re-derivation is a
stop condition:

1. Halt before any binding act — any forge mutation, merge, approval, or
   gate decision.
2. Investigate the discrepancy: identify which side is stale — the record
   or the live source — and why.
3. Correct the record, or explicitly supersede it, before resuming action.
   Do not proceed on the unreconciled claim.

Silence is not reconciliation. An unresolved mismatch blocks the next binding
act until it is explained and the record is corrected.

## e. When this applies

Before any binding act taken immediately after:

- a fresh boot or process (re)start;
- a `/clear` or equivalent context reset;
- a relaunch of a controller or seat;
- resuming from a handoff or checkpoint written by a different session.

This is a mandatory pre-act ritual, not a one-time onboarding step: it runs
at every resume boundary, every time, regardless of how confident the
resuming session is in the record it is reading.

## f. Relationship to existing continuity protocols

This protocol composes with, and does not replace:

- [`./session-continuity-protocol.md`](./session-continuity-protocol.md),
  which defines the local resume-state schema and the fresh-session
  start/end checklist shape;
- the checkpoint procedure (the `ce-checkpoint` skill and
  [`../../playbooks/controller/briefs/checkpoint.md`](../../playbooks/controller/briefs/checkpoint.md)),
  which defines how a resume-state record is written and how each fact in it
  is labeled `probed`, `asserted`, or `unknown` before handoff.

Where those protocols say what to record and how to label it, this protocol
says what to re-verify live, against a durable source, before trusting the
record for any binding act.

## g. Origin

Ratified as a mandatory controller resume-ritual requirement (2026-07-19).
The rule is motivated by a state-root synchronization incident class in
which a resume-state record was silently clobbered by a stale, one-way
mirror sync that applied delete semantics against a live, owned state root —
destroying in-flight resume-state facts that a controller later trusted
without re-derivation. Treating a resume-state record as ground truth
without live re-derivation is exactly the failure mode this protocol closes.

## h. Scope boundary

This protocol defines the resume-side re-derivation ritual only. It does not
define or change the checkpoint-write procedure, the resume-state file
schema, gate mechanics, or merge/approval authority; see the source-of-truth
documents linked in §f for those.
