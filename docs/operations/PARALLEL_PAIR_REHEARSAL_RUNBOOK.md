# Parallel-Pair Rehearsal Runbook

**Status**: Internal operations runbook for manual two-lane authoring
rehearsals under Creator Engine Phase 1 governance. Operational only;
not a normative governance protocol. Subordinate to the Feature 001
substrate, the Feature 002 operating model, and the upstream
workflow-hardening protocols cited below. A fresh clone is sufficient
to apply this runbook; no external tracker, CI surface, or network
state is required.

## a. Purpose

A **parallel-pair rehearsal** is a deliberate, manually coordinated
authoring exercise in which two visible implementer panes each consume
a separate Source-ratified envelope at the same wall-clock time, each
inside its own isolated physical worktree, against disjoint authorized
path manifests. The rehearsal answers a single operational question:

> Can two implementer lanes author concurrently under Phase 1
> governance without violating the controller / implementer boundary,
> the path-manifest fidelity protocol, the pointer-only relay rule,
> or the transcript archive / hash / close protocol — and can the
> resulting two diffs be integrated canonically by a single serialized
> mechanics envelope afterwards?

This runbook names the operational steps and prohibitions that make
the answer reproducible. It does **not** introduce new ratification
authority, new role definitions, or new mutation classes; where it
overlaps with normative protocols, the upstream protocol controls.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) | Four-role boundary; only the implementer mutates tracked files under an envelope; the controller verifies, never authors. |
| [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md) | Per-lane authorized-path manifest count/hash preflight and final boundary verification. |
| [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md) | Pointer-only relay shape; each lane consumes a path-and-hash relay, never a pasted envelope body. |
| [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md) | Per-lane archive / hash / close discipline at the stop line. |
| [`./session-continuity-protocol.md`](./session-continuity-protocol.md) | Instance-local-vs-upstream split for transcripts and rehearsal artifacts. |
| [`../delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`](../delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md) §c.5 | Allowed-paths field shape and closed-set semantics each lane's envelope MUST carry. |
| [`../delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md`](../delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md) | Consumer-side preflight each lane's implementer runs before mutating. |
| [`../delivery/SCOPE_AUDIT_CHECKLIST.md`](../delivery/SCOPE_AUDIT_CHECKLIST.md) | Verifier-side scope audit run per-lane after the stop line and again at canonical integration. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) | Source ratification authority for each lane's envelope and for the serialized integration envelope. |

A parallel-pair rehearsal that cannot cite the upstream documents
above is not a governed rehearsal and MUST be halted.

## c. Shape of the rehearsal

A parallel-pair rehearsal is structured as:

| Element | Constraint |
|---|---|
| Lanes | Exactly two, labelled `Lane A` and `Lane B`. Additional lanes are out of scope for this runbook. |
| Source ratifications | One per lane. Each lane's envelope is independently Source-ratified per [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md). The two ratifications MUST NOT be folded into a single envelope. |
| Worktrees | One **physical** worktree per lane, on the local filesystem, at a path distinct from the canonical clone and from the other lane's worktree. |
| Branches | One feature branch per lane, branching from the same shared base commit. The two lanes' branches MUST NOT share commits with each other prior to canonical integration. |
| Drivers | One driver — one human-plus-pane combination acting as the lane's implementer — per physical worktree. No driver authors in both worktrees during the rehearsal window. |
| Path manifests | One closed authorized-path manifest per lane. The two manifests are **disjoint** at the file-path level (see §e). |
| Integration | Canonical integration is **serialized** after both lanes have reached their stop lines; it never runs concurrently with authoring (see §h). |

The rehearsal is **manual**. No automation is permitted to schedule,
gate, or merge between the lanes during the authoring window;
automation is permitted only as read-only verification (the existing
validator checks per [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md)
§e and the role-boundary attribution check per
[`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
§f.1, run inside each worktree).

## d. One driver per physical worktree

Each lane has exactly one driver during the rehearsal window:

1. The lane's driver opens the lane's physical worktree in its own
   editor / shell context, distinct from the other lane's worktree.
2. The driver consumes the lane's pointer-only handoff, runs the
   per-lane preflight, and authors exactly the files in the lane's
   manifest.
3. The driver does **not** open the other lane's worktree, branch,
   handoff, transcript, or manifest during the authoring window.
4. The driver does **not** ratify, sign, or otherwise approve their
   own lane's work; that authority belongs to Source per
   [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
   §d bullet 4.

Treating the two lanes as a single multitasking session — one driver
flipping between two worktrees, one pane consuming both handoffs —
collapses author/approver separation and is a halt condition. If only
one driver is available, the rehearsal is run as two serialized
single-lane batches, not as a parallel pair.

## e. One branch per lane and disjoint allowed-path manifests

Per-lane branch discipline:

- Each lane's branch is named with a rehearsal-scoped prefix
  identifying the lane (for example, `rehearsal/<batch-slug>-lane-a`
  and `rehearsal/<batch-slug>-lane-b`). The names MUST be distinct.
- Both branches share the **same base commit** on the canonical
  branch. The base commit hash is recorded in each lane's handoff.
- Neither branch is rebased onto, merged with, or fast-forwarded into
  the other during the authoring window. The branches are independent
  until canonical integration in §h.

Per-lane manifest discipline:

- Each lane's envelope carries its own closed authorized-path manifest
  per [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md)
  §c, with its own `*_PATHS_COUNT` and `*_PATHS_SHA256` declarations.
- The intersection of the two manifests at the file-path level MUST
  be **empty**. A single file MUST NOT appear in both lanes' manifests;
  if both lanes need to mutate the same file, the rehearsal is not
  parallelizable and MUST be re-scoped or run serially.
- Disjointness is checked by the controller before relay: the
  controller computes the intersection of the two normalized
  manifests and halts the rehearsal if it is non-empty. The check is
  re-run at canonical integration in §h.

A manifest collision detected mid-rehearsal is a halt; the lanes are
not silently rebased or reconciled in the worktree by the driver.

## f. Pointer-only handoffs

Each lane consumes its envelope via the pointer-only relay shape per
[`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md):

1. The controller writes each lane's handoff to disk as a separate
   document at an instance-local path. The handoff records the
   ratified envelope's path on disk, the envelope's SHA256, the
   authorized-paths count and SHA256, the base commit hash, and the
   archive path the transcript will be written to per
   [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md)
   §c.
2. The controller relays each lane's handoff to its driver as a
   **path-and-hash pointer**, never as a pasted body. The two lanes'
   pointers are relayed independently; the controller MUST NOT bundle
   them into a single pointer.
3. Each driver re-reads the handoff from disk in their lane's
   worktree, recomputes the manifest count/hash per
   [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md)
   §c, and confirms the recomputed values match the handoff's
   declarations before any tool edits a tracked file.
4. A manifest-fidelity mismatch on either lane halts that lane; the
   other lane continues unaffected until its own preflight runs.

The handoff document is the only artifact that defines the lane's
scope. Chat instructions, screenshots, or summaries MUST NOT
substitute for the on-disk handoff per
[`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md).

## g. Cross-lane prohibited surfaces and stop-line / transcript discipline

### g.1 Cross-lane prohibited surfaces

While the rehearsal is in flight, each lane treats the **other lane's
manifest as a prohibited surface**, in addition to the surfaces
prohibited by the lane's own envelope:

- A lane MUST NOT create, modify, stage, or otherwise touch any file
  that appears in the other lane's authorized-path manifest.
- A lane MUST NOT read or paraphrase the other lane's handoff,
  envelope, transcript, or in-flight diff in order to coordinate
  authoring. Cross-lane coordination during the authoring window is
  done through Source, not through the panes.
- A lane MUST NOT modify shared substrate surfaces that would force
  the other lane to rebase mid-authoring. The canonical examples are
  enumerated in §i; in general, any index, ledger, or roadmap that
  both lanes' completion reports will need to update is deferred to
  the serialized integration step.
- A lane's controller MUST NOT relay the other lane's handoff,
  archive the other lane's transcript, or perform mechanics for the
  other lane within the same controller session, to preserve the
  per-lane evidence chain required by
  [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
  §d bullet 2.

A cross-lane prohibited-surface violation detected at any gate is a
halt. The remedy is the same as for any envelope-scope violation:
route the correction back to Source per
[`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
§e, never silently patch from the controller or driver seat.

### g.2 Stop-line / transcript archive discipline

Each lane independently runs the archive / hash / close sequence per
[`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md)
§d at its own stop line:

1. The driver halts at the lane's envelope-defined stop line and
   produces the report-back ending in that stop line. No subsequent
   text in the pane is part of the batch's transcript.
2. The controller flushes the lane's pane transcript to the archive
   path declared in the lane's handoff, hashes the archive byte-level
   per [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md)
   §e, records the hash in the handoff, and closes the pane for the
   batch.
3. The two lanes' transcripts are archived to **separate** files at
   separate instance-local paths. They MUST NOT be concatenated into a
   single archive, even if both lanes close at adjacent wall-clock
   times.
4. A lane that reaches its stop line first does **not** wait for the
   other lane to also reach its stop line before its archive / hash /
   close sequence runs. Per-lane closure is independent; canonical
   integration is the only serialized step.
5. A lane whose stop line is missing, malformed, or duplicated is a
   halt for that lane; the other lane's archive / hash / close
   sequence is unaffected and proceeds on its own evidence.

The transcripts live under the gitignored instance-local tree per
[`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md)
§c. Hashes and archive paths MAY be cited in tracked completion
reports; transcript bodies MUST NOT be committed.

## h. Serialized canonical integration after authoring

Canonical integration is the sole serialized step in a parallel-pair
rehearsal. It runs only after **both** lanes have:

1. Reached their envelope-defined stop lines.
2. Closed their transcripts per §g.2 and recorded archive hashes in
   their respective handoffs.
3. Passed their per-lane controller scope audit per
   [`../delivery/SCOPE_AUDIT_CHECKLIST.md`](../delivery/SCOPE_AUDIT_CHECKLIST.md).

Integration discipline:

- Canonical integration is performed under a **separate Source-ratified
  mechanics envelope**, distinct from the two authoring envelopes per
  [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
  §f rows for staging / commit / push / PR / merge. Authoring
  ratification does not imply integration ratification.
- Integration is **strictly serialized**: the controller integrates
  one lane's branch first, then the other. The two lanes' branches
  MUST NOT be merged concurrently, and MUST NOT be combined into a
  single integration commit that obscures lane-attribution.
- Before each lane's merge, the controller re-runs the manifest
  disjointness check from §e against the **then-current** canonical
  branch, since the canonical branch will have moved after the first
  lane's merge. If a previously disjoint manifest now overlaps with a
  file that the first merge introduced, the controller halts and
  routes back to Source.
- Integration mechanics — staging, commit, push, PR, merge — are
  controller-performed per
  [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
  §d bullet 2 under the separate mechanics envelope. Neither lane's
  driver performs mechanics for their own lane.
- A canonical integration that introduces conflicts that cannot be
  resolved without editing tracked files is a halt; conflict
  resolution is routed back to Source for an amended manifest, not
  resolved in the controller seat per
  [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
  §e.

The integration envelope's own boundary verification per
[`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md)
§g closes the rehearsal: the union of the two lanes' merged diffs MUST
equal the union of the two lanes' authorized-path manifests.

## i. Why ledger / index updates are deferred to serialized reconciliation

The following surfaces are **deferred** from each lane's authoring
manifest and reconciled only in a serialized reconciliation envelope
after canonical integration:

- `docs/delivery/BACKLOG.md`
- `docs/delivery/KANBAN.md`
- `README.md`
- `docs/delivery/README.md`
- `docs/product/ROADMAP.md`
- Any other shared index, ledger, or table-of-contents whose content
  is a function of the union of both lanes' authored artifacts.

The deferral is not a stylistic preference; it follows directly from
the policies above:

1. **Disjoint manifests rule out shared mutation surfaces.** If both
   lanes' completion reports update `BACKLOG.md`, the two manifests
   intersect on that file, violating §e. The remedy is not to silently
   carve up `BACKLOG.md` line-by-line — that re-introduces the
   paste-pipeline corruption class
   [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md)
   §a names — but to remove the file from both lanes' manifests and
   reconcile it after integration.
2. **Index content is a function of the integrated state.** A
   `KANBAN.md` row that names the rehearsal's outcome can only be
   written accurately after both lanes have closed and integrated; an
   in-flight update written from one lane is a prediction, not a
   record, and would have to be amended after the other lane lands.
   Amending a tracked ledger from outside an envelope to "fix" a
   prediction is the controller-seat-edit anti-pattern per
   [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
   §e.
3. **Author/approver separation prefers a single reconciliation
   envelope.** A single Source-ratified reconciliation envelope, with
   its own closed manifest naming exactly the ledger / index surfaces
   to be updated, is auditable as one batch with one implementer and
   one verifier. Two concurrent updates to the same ledger from two
   different lanes are not, regardless of how careful the drivers are.
4. **Roadmap and product surfaces follow ratification, not
   authoring.** `docs/product/ROADMAP.md` and similar surfaces record
   Source-level decisions about *what the project commits to*, not
   *what was authored in a single rehearsal*. They are updated under
   their own ratifications, not as a side-effect of either lane's
   manifest.

The serialized reconciliation envelope is itself a normal governed
batch and follows every protocol cited in §b. The parallel-pair
rehearsal contributes the *evidence* its reconciliation envelope
consumes — the two closed handoffs, the two transcript hashes, the
canonical integration commit hashes — but does not pre-author the
reconciliation surfaces themselves.

## j. Halt conditions specific to parallel-pair rehearsals

Beyond the per-lane halt conditions named in the cited protocols, the
following are halts unique to this runbook:

- **Manifest intersection non-empty** at any of: handoff publication,
  per-lane preflight, post-stop-line scope audit, or pre-integration
  re-check.
- **Driver overlap**: the same human-plus-pane combination is
  observed authoring in both lanes during the authoring window.
- **Cross-lane handoff consumption**: a lane's driver opens, reads,
  paraphrases, or otherwise consumes the other lane's handoff,
  transcript, or in-flight diff.
- **Shared-substrate mutation**: a lane authors a file that appears
  in any of the deferred ledger / index surfaces in §i without that
  file being explicitly carried in a separate reconciliation
  envelope's manifest.
- **Concurrent integration**: the controller attempts to merge both
  lanes' branches in a single mechanics action, or attempts to merge
  one lane's branch before the other lane has closed its transcript
  per §g.2.
- **Bundled mechanics envelope**: a single mechanics envelope is
  presented as authorizing both lanes' integration without naming
  per-lane scope; integration ratification is per-lane and per-merge.

A halt under any of the above terminates the rehearsal as a parallel
pair. Recovery is either re-scoping under fresh Source-ratified
envelopes or re-running the work as serialized single-lane batches.

## k. Acceptance posture

This document satisfies the Phase 1 operations requirement to add an
internal runbook for manual two-lane authoring rehearsals:

- Names one driver per physical worktree in §d.
- Names one branch per lane and disjoint allowed-path manifests in §e.
- Names pointer-only handoffs in §f.
- Names cross-lane prohibited surfaces and the stop-line / transcript
  archive discipline in §g.
- Names serialized canonical integration after authoring in §h.
- Names why `BACKLOG.md`, `KANBAN.md`, `README.md`,
  `docs/delivery/README.md`, `docs/product/ROADMAP.md`, and similar
  index surfaces are deferred to a separate serialized reconciliation
  envelope in §i.
- Defers all normative authority — ratification, role definition,
  manifest fidelity, transcript archive, controller boundary — to the
  upstream protocols cited in §b, so the runbook can evolve without
  re-opening Phase 1 governance.
