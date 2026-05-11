# Creator Engine Agent Interaction Model

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: REFERENCE. This document defers to
the Feature 001 authority matrix (FR-015) and ratification flow
(FR-016) — see
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
and the Feature 001 contracts at
[`../contracts/authority-matrix.md`](../contracts/authority-matrix.md).
The SDLC mechanics live in
[`./agentic-sdlc-operating-model.md`](./agentic-sdlc-operating-model.md);
parallel pair behavior lives in
[`./parallel-agent-development-model.md`](./parallel-agent-development-model.md).
The Actor/Tool Ownership Matrix at
`specs/002-canonical-docs-and-operating-model/spec.md` §Actor/Tool
Ownership Matrix is normative; this document references it and binds
its rows to interaction patterns.

## a. Actor/Tool Ownership Matrix (cross-reference)

Feature 002 names nine actors/tools with explicit presence categories:

| Actor / Tool | Presence category |
|---|---|
| Source | Operationally active. |
| Nefarious / Hermes | Operationally active. |
| Claude Code | Operationally active. |
| Codex | Named; governed identity record deferred to Feature 004. |
| QA agent | Named; governed identity record deferred to Feature 004. |
| security agent | Named; governed identity record deferred to Feature 004. |
| release agent | Named; governed identity record deferred to Feature 006. |
| CI | Named as tool/system; automation deferred to Feature 003. |
| GitHub | Named as tool/system; `.github/`, PR templates, branch protection deferred to Feature 003; environment gates deferred to Feature 006. |

The normative per-actor fields (allowed instruction sources, allowed
mutation classes, allowed communication surfaces, required ratifier,
required audit artifacts, Phase 1 authority, Phase 2-eligible
authority, prohibited actions) live in the Feature 002 spec
§Actor/Tool Ownership Matrix and the role-level summary in
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md).
This document does not restate them; instead, the rest of this file
describes how these actors interact during a governed mutation.

## b. Actor-to-actor interaction patterns

The operating model recognizes seven primary interaction patterns.
Each pattern names participants, the surface(s) used, and the
governance artifact produced.

### b.1 Source ↔ Hermes (intent capture, ratification)

- **When**: T1 (Idea/Intent → Discovery); T3, T5, T10, T19, T20, T22
  (ratification points); any Phase 2-promotion amendment.
- **Surface**: Source-authored or Source-approved commit messages;
  ratification records under `ratification_storage_path`; PR review
  comments where the authority matrix designates that surface as a
  ratification surface for the relevant mutation class.
- **Artifact**: working-note or tracker entry citing Source intent;
  ratification record YAML per Feature 001 FR-016 and FR-020a.
- **Invariants**: Hermes never ratifies its own work; Source's
  ratification is the human anchor and is not subject to Phase 2
  autonomy expansion.

### b.2 Hermes → Claude Code (envelope handoff)

- **When**: T11–T13 (envelope authoring → consumption).
- **Surface**: the Assignment Envelope YAML file under the
  tenant-declared envelope directory.
- **Artifact**: the envelope itself (FR-005 fields populated; author
  is the Hermes role; consumer is the Claude Code role).
- **Invariants**: author MUST ≠ consumer (FR-006); envelope is
  single-use (FR-007); privileged-class envelopes require Source
  ratification before consumption (FR-008).

### b.3 Claude Code ↔ Hermes (evidence reporting)

- **When**: T14–T15 (local validation complete → attestation
  drafted).
- **Surface**: validator output captured on the feature branch; test
  logs; lint/typecheck output; Creator Engine validator output; the
  evidence return path the envelope declares.
- **Artifact**: pre-merge attestation YAML drafted by Hermes per
  Feature 001 FR-004 and FR-020a.
- **Invariants**: Claude Code MUST NOT ratify its own work; Claude
  Code reports evidence and Hermes drafts the attestation; the
  attestation gate is privileged (`attestation` class) and remains
  Phase 1.

### b.4 Codex → Hermes (independent review)

- **When**: T16 (attestation drafted → independent review complete).
- **Surface**: review findings records (schema deferred to Feature
  004); PR review comments recorded as review evidence.
- **Artifact**: review findings record under the future Feature 004
  schema; pre-Feature-004, review evidence is recorded in
  repository-visible artifacts per constitution Principle VIII.
- **Invariants**: review evidence is NEVER ratification for
  privileged classes (FR-013, FR-017); Codex writes only to a
  separate Codex-only worktree if fallback implementation is
  authorized (Codex never writes to the active Claude worktree).

### b.5 CI → ratifier audit chain (mechanical evidence)

- **When**: T17 (independent review complete → CI evidence
  complete).
- **Surface**: CI status checks; CI run logs; validator outputs;
  build artifacts. Workflow definitions deferred to Feature 003.
- **Artifact**: status check records and validator outputs linked to
  T17.
- **Invariants**: CI verifies but does NOT ratify (FR-013); changes
  to CI policy or workflow files are themselves privileged
  `governance`/`security`/`deploy` mutations per FR-008.

### b.6 Hermes ↔ Source (scope audit and ratification)

- **When**: T18–T20 (scope audit → ratification → merge approval).
- **Surface**: scope audit summary committed to the feature branch
  or attached to the PR; ratification record; merge authorization
  record.
- **Artifact**: scope audit summary citing envelope id, batch ids,
  and mutation-class boundaries; ratification record YAML;
  merge-authorization record (may share the ratification record for
  same-class mutations).
- **Invariants**: Hermes may execute merge mechanics only when
  explicit Source authorization is recorded; for privileged classes
  the ratifier MUST be Source (FR-008).

### b.7 release agent ↔ Source / Hermes (deploy and post-release
finalization)

- **When**: T21–T24 (release candidate → deploy → deployment
  complete → post-release evidence).
- **Surface**: release tags; deploy logs; deploy attestations;
  rollback evidence; post-release attestation records.
- **Artifact**: per-stage attestation records and ratification
  records. Schemas for deploy attestation, rollback evidence, and
  post-release evidence are deferred to Feature 006.
- **Invariants**: the `deploy` mutation class is Source-only per
  FR-008; the release agent never ratifies the `deploy` class. Until
  Feature 006 instantiates the release agent identity, Hermes acts
  on Source's explicit authorization for T21 and audits attestation
  finalization for T24.

## c. Communication surfaces

The operating model uses these surfaces. Per Feature 001 FR-015 a
surface that appears in a role's `allowed_communication_surfaces` is
permitted to *carry* governance artifacts; whether a surface counts
as a *valid ratification surface* for a given mutation class is
governed by the Feature 001 ratification-flow contract.

- **Tmux sessions**: live operator surface where Hermes and Claude
  Code panes coordinate. Conversations and command output on tmux
  are NOT canonical governance artifacts. Anything load-bearing MUST
  be promoted into a repository artifact (commit, sidecar, envelope,
  attestation, ratification record).
- **Repository surfaces**:
  - `repo_pr` — pull requests.
  - `repo_review` — PR review comments.
  - `repo_commit_message` — commit messages (Source-authored or
    Source-approved commits count as Source-surface artifacts).
  - `repo_issue` — issues / tickets.
  - `repo_attestation_record` — YAML records under
    `attestation_storage_path`.
  - `repo_ratification_record` — YAML records under
    `ratification_storage_path`.
- **Assignment Envelope YAML**: the explicit handoff surface from
  Hermes to Claude Code.
- **Validator outputs and test logs**: evidence-only surfaces; never
  ratification.

A "go ahead" message on a non-designated surface does NOT authorize
merge, deploy, publish, or any other reserved-restricted action per
Feature 001 FR-018.

## d. Author/approver separation enforcement (Feature 001 FR-007)

The author/approver separation rule applies at every layer of the
interaction model. The candidate v0.1 rule (anchored in
[`../contracts/authority-matrix.md`](../contracts/authority-matrix.md)
§Author definition) is: "the author identity for a mutation, for the
purposes of FR-007, is the union of every `author_actor_id` value in
the corresponding `tasks.creator-engine.yml`'s TaskEntries; a
ratifier MUST NOT equal any member of that set."

In operating-model practice:

- The Assignment Envelope's `created_by_actor_id` MUST be distinct
  from `consuming_actor_id` (Feature 002 FR-006).
- The actor recording `verified` MUST NOT be the ratifier (Feature
  001 FR-013a).
- The redaction approver MUST NOT be the author of the underlying
  tenant artifact (Feature 001 FR-021).
- Source MUST NOT ratify Source's own authored mutation; another
  authorized actor is required (Feature 001 FR-007).

Single-actor approval is invalid regardless of role, seniority, or
automation level (constitution Principle V).

## e. Review-vs-ratification distinction and invariants (FR-013, FR-017)

The interaction model treats review and ratification as separate
artifacts with separate authorities. Two invariants:

1. **CI verifies but does not ratify.** CI output is attestation
   evidence; it is never a ratification record. CI passing does not
   advance a privileged-class mutation past T19.
2. **Agent-authored review text is not ratification for privileged
   mutation classes.** For non-privileged classes, agent review text
   MAY be recorded as review evidence per the Feature 001 authority
   matrix, but it remains distinct from human ratification and never
   substitutes for it.

The Codex reviewer, the future QA agent, and the future security
agent are explicitly named as reviewers, not ratifiers. Even if a
reviewer's findings recommend merge, the merge gate (T20) still
requires Source authorization for privileged classes.

## f. Envelope handoff sequence (Hermes → Claude)

The envelope handoff is the operational seam where Creator Engine
governance meets `/speckit-implement` mechanics. Every FR-005 field
is exercised exactly once per handoff.

1. **Batch approval recorded** (T10). Source records the approved
   task batch in a batch approval record. For privileged-class
   batches, Source is the only approver.
2. **Envelope authoring** (T11). Hermes drafts an Assignment Envelope
   referencing the approved batch. Hermes populates every required
   field:
   - `envelope_id` — fresh UUID or tenant-scheme id; never reused
     (FR-007 single-use).
   - `spec_ref` — id or path of the spec the work fulfills.
   - `feature_branch` — branch name.
   - `worktree_path` — physical worktree path.
   - `approved_task_batch` — task IDs or file globs from the
     approved batch.
   - `allowed_mutation_classes` — drawn from the active tenant
     taxonomy.
   - `prohibited_surfaces` — path/glob list.
   - `required_validation` — explicit commands the consumer MUST
     run.
   - `evidence_requirements` — what the consumer MUST report.
   - `stop_conditions` — when the consumer MUST stop.
   - `prohibited_external_actions` — commit, push, PR, merge,
     deploy, GitHub-settings mutation, etc., unless explicitly
     authorized.
   - `conflict_policy` — rebase/merge/conflict-resolution authority
     and escalation rules.
   - `created_by_actor_id` — Hermes role.
   - `consuming_actor_id` — Claude Code role (or another approved
     implementer role).
3. **Source ratification for privileged-class envelopes** (FR-008).
   If `allowed_mutation_classes` declares any privileged class, the
   envelope is committed only with Source ratification recorded; the
   consumer MUST NOT begin work until ratification is present.
4. **Worktree/branch provisioning** (T12). Hermes provisions the
   worktree at `worktree_path` and ensures the branch
   `feature_branch` exists from the agreed base.
5. **Envelope consumption** (T13). Claude Code begins work inside the
   worktree. `/speckit-implement` reads the approved spec/plan/tasks
   artifacts; the consumer mutates only inside
   `allowed_mutation_classes` and outside `prohibited_surfaces`;
   tasks are marked `[X]` only after local validation per FR-010.
6. **Stop on stop_conditions** (T13 → T14). When stop conditions are
   met, the consumer halts; it does NOT extend scope and does NOT
   reuse the envelope for follow-up batches.
7. **Local validation** (T14). The consumer runs every command in
   `required_validation` and captures outputs as the envelope's
   `evidence_requirements` specify.
8. **Evidence return** (T14 → T15). The consumer reports evidence to
   Hermes per the envelope's return path; Hermes drafts the
   pre-merge attestation in §b.3.

The handoff is single-use. If new work is needed (a follow-up batch
or a conflict-resolution sub-batch), a new envelope is issued with a
new `envelope_id` and fresh approval.

## g. Escalation paths to Source via the conflict taxonomy

The four conflict classes in
[`./parallel-agent-development-model.md`](./parallel-agent-development-model.md)
§e (and at Feature 002 FR-017, FR-018) anchor every escalation:

| Conflict class | Detector | Resolver | Escalation to Source? |
|---|---|---|---|
| `textual` | git merge/rebase | integration agent or Hermes | No (unless resolution requires scope expansion). |
| `file/task ownership` | envelope/claim protocol | Hermes (via serialization or explicit dependency order) | No (unless overlap signals a deeper scope conflict). |
| `semantic` | review / test / architecture audit | architect review; possibly Source ratification if Feature 001 contracts are touched | Yes, if substrate contract semantics are affected. |
| `authority` | operating model / future substrate validators | Source (HARD-STOP) | Yes — always. |

`authority` conflicts hard-stop work. The agent MUST NOT continue,
revert, or rebase to conceal an `authority` conflict; the case
escalates to Source for ratification, and Source either ratifies the
change as an explicit amendment or directs revert.

Common authority-conflict triggers:

- An agent attempts to mutate identity records, the authority
  matrix, `.github/`, the redaction gate, CI or deploy settings,
  ratification semantics, or any other privileged surface absent
  explicit ratification.
- `/speckit-implement` is invoked outside an envelope (FR-009).
- An envelope is reused after its stop conditions have been
  satisfied (FR-007 violation).
- An envelope's author equals its consumer (FR-006 violation).
- An agent expands the mutation-class set or extends prohibited
  surfaces unilaterally.

## h. Cross-reference to the Actor/Tool Ownership Matrix

Every actor and tool named in this document appears in the Feature
002 Actor/Tool Ownership Matrix at
`specs/002-canonical-docs-and-operating-model/spec.md` §Actor/Tool
Ownership Matrix with its allowed instruction sources, allowed
mutation classes, allowed communication surfaces, required ratifier,
required audit artifacts, Phase 1 authority, Phase 2-eligible
authority, and prohibited actions. The role-level summary in
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
is the navigational entry point.

The envelope handoff sequence in §f exercises every FR-005 field
required by Feature 002.

## Acceptance posture for this document

This agent-interaction-model.md satisfies Feature 002 Canonical
Document Specification #7: every actor named in the Feature 002
Actor/Tool Ownership Matrix appears; the review-vs-ratification
distinction is explicit; the envelope handoff sequence covers every
FR-005 field; cross-references to the matrix and the conflict
taxonomy are present.
