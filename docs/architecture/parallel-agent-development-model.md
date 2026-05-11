# Creator Engine Parallel-Agent Development Model

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: REFERENCE. This document defers to
[`./agentic-sdlc-operating-model.md`](./agentic-sdlc-operating-model.md)
for SDLC mechanics, to
[`./agent-interaction-model.md`](./agent-interaction-model.md) for
actor-to-actor patterns, and to the conflict taxonomy at Feature 002
FR-017/FR-018. It is authoritative for the parallel-pair runtime
pattern within Feature 002's scope.

This document is intentionally separate from the operating model per
Feature 002 FR-022: User Story 6 promotes parallel-agent development
to a first-class operating-model concern; folding it into
`agentic-sdlc-operating-model.md` would either swell that document
past readability or force readers interested only in parallelization
to also load the full state machine.

## a. One-driver-per-worktree rule (the permanent rule)

The permanent operating rule is: **one driver per physical worktree;
many isolated writers across separate branches/worktrees, each
operating under its own Assignment Envelope, with canonical-branch
integration serialized and Source-ratified.**

A physical worktree is a single directory tree resolved by `git
worktree` (or an equivalent isolated checkout) and bound to exactly
one branch. The driver is the actor authorized to write to that
worktree under the current envelope.

Rule statements:

1. **Two Claude Code sessions MUST NOT write concurrently to the same
   physical worktree.** This is non-negotiable. Concurrent writes
   from two drivers to the same worktree produce interleaving
   changes that no envelope can govern and no validator can untangle
   after the fact.
2. **Two Hermes+Claude pairs MAY work on different features in
   parallel** provided each pair has its own worktree, its own
   branch, and its own envelope, and the envelopes' scopes do not
   overlap (or declare an explicit integration dependency per the
   conflict taxonomy).
3. **The canonical branch (e.g., `main`) MUST be protected from
   concurrent writers.** Canonical-branch integration is serialized;
   privileged-class mutations are Source-ratified at T19 and
   Source-authorized at T20.
4. **Codex, when fallback implementation is authorized, writes only
   to a separate Codex-only worktree.** Codex never writes to the
   active Claude worktree.

**Rationale**: A single isolated writer per physical worktree is the
minimum mechanism that makes git history and the Creator Engine
scope-audit chain meaningful. With multiple concurrent writers per
worktree, an attestation record cannot bind a mutation to a single
author, the scope audit cannot enforce envelope boundaries, and the
conflict taxonomy collapses (every conflict becomes textual + some
other class simultaneously). One driver per worktree is the
architectural cost of preserving auditability under parallel
agentic work.

## b. Parallel-pair pattern (isolated branch + isolated worktree +
isolated envelope)

A "parallel pair" is the operational unit of parallel work:

- **One Hermes pane** authoring and auditing on Source's behalf.
- **One Claude Code pane** consuming a single envelope.
- **One feature branch** (e.g., `feat/foo-…`).
- **One physical worktree** at a unique path (e.g.,
  `/home/<operator>/projects/creator-engine-<slice-or-feature>`).
- **One Assignment Envelope** declaring scope, allowed mutation
  classes, prohibited surfaces, required validation, evidence
  requirements, stop conditions, and the conflict policy.

Multiple parallel pairs MAY run concurrently. Each pair satisfies the
one-driver-per-worktree rule because each pair owns its own worktree
end-to-end. Each pair's envelope is single-use per FR-007.

Pair coordination invariants:

- **Non-overlapping scope**: two concurrent envelopes MUST NOT claim
  the same task ids or the same file globs unless an explicit
  integration dependency is declared (see §e and the conflict
  taxonomy).
- **Author/approver separation persists across pairs**: a Hermes
  identity authoring envelope A MUST NOT be the consuming identity of
  envelope B in the same logical mutation chain when that would
  collapse FR-007 separation across the chain.
- **Stop conditions are local**: a pair stops when its envelope's
  stop conditions are met; a pair does NOT continue work on another
  pair's behalf without a new envelope.

## c. Integration path (serialized, Source-ratified canonical-branch
integration)

The canonical branch is the single integration point for parallel
work. Integration is serialized:

1. **PR per feature branch**. Each pair opens a PR from its feature
   branch into the canonical branch after Hermes verification and
   pre-merge attestation drafting (T15).
2. **Source ratification at T19**. Source ratifies the mutation per
   the privileged- or non-privileged-class rules. For privileged
   classes, ratification is Source-only.
3. **Merge authorization at T20**. The ratification record (or an
   attached approval) authorizes merge. Hermes may execute merge
   mechanics only when authorization is recorded.
4. **One merge at a time**. Even when multiple PRs are ready, merges
   to the canonical branch are sequenced: each PR is rebased or
   re-merged onto the latest canonical-branch tip and re-validated
   before the next merge. Concurrent merges are not permitted.
5. **Post-merge attestation finalization**. After merge, the
   pre-merge attestation is finalized with the merge reference per
   FR-004.

For deploy-class mutations, integration continues through T21–T24
with Source ratification at T22 and post-release evidence at T24;
Feature 006 owns the automation but the serialization rule remains.

## d. Git vs Creator Engine conflict-labor division

Creator Engine treats conflicts at two layers and assigns them to
different resolvers.

- **Textual conflicts**: handled by git (merge / rebase). The
  resolver is the integration agent (Hermes, in v0.1 manual mode, or
  a Source-ratified integration role under future Feature 005
  automation). Evidence: re-run tests on the rebased branch.
- **Semantic / authority / file-task-ownership conflicts**: handled
  by Creator Engine. Git cannot detect these; review, validators,
  architect audit, and the conflict taxonomy do.

The boundary is intentional. Git is excellent at detecting line-level
overlaps and reliably produces a textual conflict that a human or
automation can resolve. Git is silent about whether two non-textually-
conflicting branches are semantically consistent (e.g., one branch
adds a lifecycle status and another branch writes validators
assuming the old set), whether two envelopes both claim the same
file glob, or whether an agent has touched a privileged surface
absent ratification.

Creator Engine adds the second layer. The conflict taxonomy in §e
names the resolver for each.

## e. Conflict taxonomy (Feature 002 FR-017, FR-018)

Every observed conflict MUST be classifiable as one of exactly four
classes. Each class names the detector, the resolver, and the
required evidence.

### e.1 `textual` conflict

- **Detector**: git merge / rebase.
- **Resolver**: the integration agent (Hermes in v0.1; future
  Feature 005 dispatcher under Source-ratified policy).
- **Required evidence**: re-run tests and required validation on
  the rebased / merged branch; the merged branch passes Definition
  of Done (FR-014).
- **Authority impact**: low. Resolution is mechanical unless it
  requires scope expansion (in which case escalate per §e.2 or
  §e.4).

### e.2 `file/task ownership` conflict

- **Detector**: the envelope / claim protocol (two envelopes claim
  the same task id or the same file glob).
- **Resolver**: Hermes — by serialization (issue one envelope, wait,
  then issue the other) or by declaring an explicit integration
  dependency (envelope B depends on envelope A's merge).
- **Required evidence**: an updated envelope (new id, declared
  dependency, or sequenced order) committed before any consumer
  begins overlapping work.
- **Authority impact**: medium. If the overlap signals a deeper
  scope conflict (e.g., two features overlap because the underlying
  spec is contradictory), escalate to semantic.

### e.3 `semantic` conflict

- **Detector**: review (Codex), test failures on integration,
  architecture audit, or validators.
- **Resolver**: architect review; possibly Source ratification if
  Feature 001 contracts or Feature 002 normative sections are
  affected.
- **Required evidence**: an integration-branch diff demonstrating
  the resolved state, re-validated tests on the integration branch,
  and (if applicable) an updated contract document or spec.
- **Authority impact**: medium to high. If the resolution requires
  changes to Feature 001 contracts or Feature 002 normative sections,
  the resolution is itself a governance amendment per FR-029.

### e.4 `authority` conflict

- **Detector**: the operating model (and future substrate
  validators per Feature 001).
- **Resolver**: Source. WORK HALTS pending Source ratification.
- **Required evidence**: the offending change reverted unless
  Source ratifies it; a ratification record (or revert record)
  committed before any downstream SDLC transition advances.
- **Authority impact**: maximum. `authority` conflicts hard-stop
  every downstream transition.

Authority-conflict triggers include (without limitation):

- Agent attempts to mutate identity, the authority matrix,
  `.github/`, the redaction gate, CI/deploy settings, or
  ratification semantics absent ratification.
- `/speckit-implement` invocation outside an envelope (FR-009).
- Envelope author equals consumer (FR-006 violation).
- Envelope reuse after stop conditions met (FR-007 violation).
- Mutation-class expansion beyond `allowed_mutation_classes`.
- Mutation of a `prohibited_surfaces` path.

## f. Explicit non-permanence of the May 10 emergency freeze

On 2026-05-10 Source ratified a temporary coordination directive:
during an emergency, only one writer globally MAY be active to avoid
overlapping writes during the parallel-session coordination incident.

**This is NOT the permanent model.** The permanent model is the
parallel-pair pattern in §b: many isolated writers across separate
branches/worktrees/envelopes, one governed integration path.

Recorded position (Feature 002 FR-016, restated): "Creator Engine
should not prevent parallel agent development; it should govern it.
Many isolated writers, one governed integration path."

Treat the May 10 freeze as a tactical safeguard during a specific
coordination failure. It is not architecture. Any future tactical
freeze is itself a ratified amendment, not a default.

## g. Two-pair walkthrough

The following walkthrough demonstrates the parallel-pair pattern
end-to-end without referring to any external system. It exercises the
one-driver-per-worktree rule, the conflict taxonomy, and the
serialized integration path.

**Setup**:

- Pair A: Hermes-A pane authors envelope `env-A-001` for feature
  `feat/foo` with scope: implement Feature 003 PR template policy
  outline (non-privileged `docs` class). Worktree:
  `/home/<operator>/projects/creator-engine-feat-foo`. Branch:
  `feat/foo`. Consumer: Claude Code session A.
- Pair B: Hermes-B pane authors envelope `env-B-001` for feature
  `feat/bar` with scope: implement Feature 004 review evidence
  schema outline (non-privileged `docs` class). Worktree:
  `/home/<operator>/projects/creator-engine-feat-bar`. Branch:
  `feat/bar`. Consumer: Claude Code session B.

The envelopes' `allowed_mutation_classes` are both `[docs]`, but
their `approved_task_batch` (task ids) and `prohibited_surfaces`
(paths) do not overlap. Authors and consumers differ across pairs.

**Run**:

1. Both pairs proceed in parallel through T11–T14. Each consumer
   works only inside its own worktree; neither pair touches the
   other's worktree, branch, or envelope.
2. Each consumer runs local validation per its envelope's
   `required_validation`. Each marks tasks `[X]` only after local
   validation per FR-010.
3. Each consumer reports evidence to its own Hermes. Hermes-A drafts
   a pre-merge attestation for `env-A-001`. Hermes-B drafts a
   pre-merge attestation for `env-B-001`.

**Integration**:

4. Pair A opens PR A from `feat/foo`. Source ratifies the mutation
   at T19; merge is authorized at T20. Hermes-A executes the merge
   mechanics; the post-merge attestation is finalized with the
   merge reference.
5. Pair B opens PR B from `feat/bar`. Before merge, PR B is rebased
   onto the new canonical-branch tip. Local validation is re-run on
   the rebased branch. If a textual conflict appears during rebase,
   Hermes-B resolves it per §e.1; if a semantic conflict appears,
   architect review per §e.3 runs and the resolution is recorded.
6. Source ratifies PR B at T19; merge is authorized at T20.
   Hermes-B executes the merge mechanics; the post-merge
   attestation is finalized with the merge reference.

**Confirmation**:

- Each pair wrote only to its own worktree.
- Neither pair overwrote the other's work; canonical-branch
  integration was serialized.
- Conflicts (if any) were classified, resolved by the named
  resolver, and produced the required evidence.
- A reviewer with `git clone` can reconstruct the full sequence
  from the two attestation records, the two ratification records,
  the two envelopes, and the merged feature branches.

## h. Cross-reference to the conflict taxonomy

The full normative conflict taxonomy lives at Feature 002 FR-017 and
FR-018 in
`specs/002-canonical-docs-and-operating-model/spec.md`. The
authority-conflict hard-stop is enforced by the operating model
today and by future substrate validators per Feature 001. The
escalation paths from agents to Source via the conflict taxonomy
live in
[`./agent-interaction-model.md`](./agent-interaction-model.md) §g.

## Acceptance posture for this document

This parallel-agent-development-model.md satisfies Feature 002
Canonical Document Specification #9: the one-driver-per-worktree
rule is stated as permanent; the May 10 freeze is explicitly marked
non-permanent; the two-pair walkthrough is included; the conflict
taxonomy is linked; no guidance contradicts the conflict taxonomy or
the Actor/Tool Ownership Matrix.
