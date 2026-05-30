# Creator Engine Agentic SDLC Operating Model

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: REFERENCE. This document defers to
the constitution at `.specify/memory/constitution.md` and to the
Feature 001 spec status lifecycle (FR-013a) where they overlap. It is
authoritative for SDLC mechanics within Feature 002's scope — the
25-state SDLC state machine, the 24-transition matrix, the Phase 1 /
Phase 2 boundary, the `/speckit-implement` policy, and the Assignment
Envelope linkage — as ratified by Feature 002.

Where the source spec at
`specs/002-canonical-docs-and-operating-model/spec.md` and this
document disagree, the source spec wins until Feature 002 is amended.

## Doctrine: deterministic syscall layer over probabilistic agents

Creator Engine is deterministic scaffolding over probabilistic
agentic engines. The intent is to retain the learning, reasoning, and
breadth that probabilistic agents provide while imposing
predictability, stability, reproducibility, traceability, and
auditability on the work they produce. Without that layer,
agent-authored output is fit for exploration; with it, agent-authored
work can carry the same enterprise-scale SDLC discipline that
human-authored work is expected to carry.

Architecturally, the operating model is closer to an operating-system
kernel and syscall boundary than to an ad hoc chatbot workflow:

- Probabilistic agentic engines (Claude Code, Codex, and any future
  governed implementer or reviewer) are the userland processes —
  broad capability, non-deterministic execution, no inherent guarantee
  of repeatability.
- Creator Engine is the kernel boundary — a finite, named set of
  states (the 25-state SDLC machine in §a), transitions (the
  24-transition matrix in §b), authorizing gates, required evidence
  artifacts, and ratifiers (the authority matrix referenced in §e and
  in [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)).
- The Assignment Envelope (§d) is the call-site contract that crosses
  the boundary: declared scope, allowed mutation classes, prohibited
  surfaces, required validation, evidence requirements, and stop
  conditions. The envelope makes each crossing auditable before,
  during, and after execution.

Two consequences follow from the boundary framing:

1. The unit of agent work shifts from "agents do tasks" to "agents
   participate in a governed state machine." Agent capability inside
   the envelope is unconstrained by Creator Engine; the envelope
   itself is what governance binds.
2. Creator Engine must practice the SDLC governance discipline it
   productizes. Mutations to this operating model, to the Feature 001
   substrate, or to the constitution are themselves
   Creator-Engine-governed mutations (privileged `governance` class
   per Feature 001 FR-008), subject to the same spec/plan/tasks
   triple, evidence, and human ratification any other privileged
   mutation requires.

Two invariants make the boundary load-bearing rather than ornamental:

- **CI verifies; CI does not ratify.** Mechanical validation produces
  evidence for the audit chain; it never authorizes a privileged
  transition. See §b T17 and
  [`../devops/CI_CD_STRATEGY.md`](../devops/CI_CD_STRATEGY.md).
- **Agents produce evidence; agents do not ratify privileged
  mutations.** Source remains the Phase 1 ratifier for every
  privileged boundary (FR-008 classes: `deploy`, `governance`,
  `identity`, `security`, `attestation`, `redaction`). Agent review
  output, agent-drafted attestations, and agent-authored architect or
  implementer artifacts are all evidence in the audit chain, never
  ratification. See §c, §e, and
  [`./agent-interaction-model.md`](./agent-interaction-model.md) §e.

Phase 2 may introduce governed autonomy expansions under ratified
policy (see §c). It does not exist yet. Until a Phase 2 amendment is
itself Source-ratified per §g, the syscall boundary described above is
**procedurally enforced**: the gates, transitions, evidence
requirements, and ratifier rules are upheld by human discipline plus
the offline validator and CI checks defined in the Feature 001
substrate. A typed runtime executor that mechanically denies
out-of-envelope syscalls — a gate/syscall executor that rejects
unauthorized mutation classes, prohibited surfaces, or missing
ratifications at call time — is a plausible future implementation
shape, not a v0.1 capability. The syscall metaphor is explanatory
architecture doctrine for the current procedural enforcement; it is
not permission to implement runtime automation in advance of
ratification.

## a. The 25-state SDLC machine (FR-001)

The Creator Engine SDLC state machine is the backbone of the
operating model: every governed mutation passes through exactly the
following ordered states from `Idea/Intent` to `Post-release Evidence
Recorded`.

1. `Idea/Intent`
2. `Discovery`
3. `PRD Drafted`
4. `PRD Ratified`
5. `Architecture Drafted`
6. `Architecture Ratified`
7. `Feature Spec Drafted`
8. `Spec Clarified`
9. `Plan Drafted`
10. `Tasks Generated`
11. `Batch Approved`
12. `Agent Assigned`
13. `Worktree Created`
14. `Implementation Complete`
15. `Local Validation Complete`
16. `Attestation Drafted`
17. `Independent Review Complete`
18. `CI Evidence Complete`
19. `Scope Audit Complete`
20. `Ratification Complete`
21. `Merge Approved`
22. `Release Candidate Created`
23. `Deployment Approved`
24. `Deployment Complete`
25. `Post-release Evidence Recorded`

The 25 states produce exactly 24 transitions (T1–T24).

## b. The 24-transition matrix (FR-002, FR-003)

This matrix is normative. Every transition has a responsible
actor/tool, an authorizing gate, a Phase 1 / Phase 2 label, and a
required evidence artifact. Privileged transitions (those touching
the mutation classes named in Feature 001 FR-008: `deploy`,
`governance`, `identity`, `security`, `attestation`, `redaction`)
remain Phase 1 in Feature 002 regardless of any future Phase 2-eligible
labelling.

| # | from_state | to_state | responsible actor/tool | authorizing gate | phase | required evidence / audit artifact |
|---|---|---|---|---|---|---|
| T1 | Idea/Intent | Discovery | Source | Source records product intent; Hermes captures the intent into a working note or tracker entry on Source's behalf | Phase 1 | working-note or external tracker entry citing Source intent (captured by Hermes) |
| T2 | Discovery | PRD Drafted | Claude Code | discovery complete; Hermes assigns Claude Code as PRD drafter via informal envelope | Phase 1 | draft PRD on feature branch |
| T3 | PRD Drafted | PRD Ratified | Source | Source PRD ratification (governance-class privileged) | Phase 1 (privileged — remains Phase 1) | ratification record citing PRD path |
| T4 | PRD Ratified | Architecture Drafted | Claude Code | PRD ratification present; Hermes assigns Claude Code as architecture drafter | Phase 1 | architecture draft (SAD) on feature branch |
| T5 | Architecture Drafted | Architecture Ratified | Source | Source architecture ratification (governance-class privileged) | Phase 1 (privileged — remains Phase 1) | ratification record citing architecture doc |
| T6 | Architecture Ratified | Feature Spec Drafted | Claude Code | `/speckit-specify` invoked by Claude Code inside a Hermes-prepared spec envelope | Phase 1 | `spec.md` and Spec Kit quality checklist on feature branch |
| T7 | Feature Spec Drafted | Spec Clarified | Claude Code | `/speckit-clarify` invoked by Claude Code; Source provides answers to clarification questions; Definition of Ready check per Feature 001 FR-013 | Phase 1 | updated `spec.md` with Clarifications session recorded (Source answers included) |
| T8 | Spec Clarified | Plan Drafted | Claude Code (planner) | `/speckit-plan` inside envelope | Phase 1 | `plan.md` and supporting design artifacts |
| T9 | Plan Drafted | Tasks Generated | Claude Code (planner) | `/speckit-tasks` inside envelope | Phase 1 | `tasks.md` and `tasks.creator-engine.yml` sidecar |
| T10 | Tasks Generated | Batch Approved | Source | batch scope review against mutation-class taxonomy; privileged classes Source-only per FR-008; non-privileged classes may use a Source-delegated ratifier per the Feature 001 authority matrix once delegation is ratified | Phase 1 (Phase 2-eligible target: autonomous batch-pulling under ratified policy for non-privileged classes only) | batch approval record citing approved task IDs and mutation classes |
| T11 | Batch Approved | Agent Assigned | Nefarious-Hermes | Hermes drafts Assignment Envelope from approved batch | Phase 1 | Assignment Envelope YAML (author = Hermes role; consumer = Claude Code role; FR-005 fields complete) |
| T12 | Agent Assigned | Worktree Created | Nefarious-Hermes | envelope validation; worktree/branch provisioning | Phase 1 | worktree path recorded in envelope; branch exists |
| T13 | Worktree Created | Implementation Complete | Claude Code (envelope consumer) | `/speckit-implement` reaches envelope stop conditions inside envelope (FR-009, FR-010) | Phase 1 (Phase 2-eligible target: scoped autonomy expansion under ratified policy; privileged classes excluded) | changed-file list within envelope scope; tasks marked `[X]` only after local validation |
| T14 | Implementation Complete | Local Validation Complete | Claude Code (envelope consumer) | every `required_validation` command in the envelope passes | Phase 1 | recorded validator outputs (test logs, lint/typecheck output, Creator Engine validator output) |
| T15 | Local Validation Complete | Attestation Drafted | Nefarious-Hermes | independent verification + attestation drafting per Feature 001 FR-004 (touches attestation class — privileged) | Phase 1 (privileged — remains Phase 1) | pre-merge attestation YAML record per Feature 001 FR-020a |
| T16 | Attestation Drafted | Independent Review Complete | Codex (named in Feature 002; governed identity record deferred to Feature 004) | independent read-only review per envelope policy | Phase 1 (Phase 2-eligible target: independent review evidence becomes auto-merge input under ratified Feature 004+ policy for non-privileged classes only) | review findings record (review evidence schema deferred to Feature 004) |
| T17 | Independent Review Complete | CI Evidence Complete | CI (named in Feature 002; automation deferred to Feature 003) | mechanical validation pass (tests, lint, typecheck, build, Creator Engine validator, schema validation) | Phase 1 (Phase 2-eligible target: CI pass becomes auto-merge precondition under ratified Feature 003+ policy; CI never ratifies) | CI status check records and validator outputs (CI verifies-not-ratifies invariant, FR-013) |
| T18 | CI Evidence Complete | Scope Audit Complete | Nefarious-Hermes | scope audit against approved batch, allowed mutation classes, prohibited surfaces | Phase 1 (Phase 2-eligible target: mechanical scope audit under ratified policy for non-privileged classes only) | scope audit summary citing envelope id, batch ids, and mutation-class boundaries |
| T19 | Scope Audit Complete | Ratification Complete | Source | ratification decision recorded against mutation class; privileged classes Source-only per FR-008; non-privileged classes may use a Source-delegated ratifier per the Feature 001 authority matrix once delegation is ratified | Phase 1 — privileged classes remain Phase 1 per FR-003; non-privileged classes Phase 2-eligible target only under a future ratified delegation policy | ratification record YAML per Feature 001 FR-016 and FR-020a |
| T20 | Ratification Complete | Merge Approved | Source | merge eligibility check against ratification record; Hermes may execute the merge mechanics only when explicit Source authorization is recorded in the ratification record or an attached approval | Phase 1 — privileged classes remain Phase 1; non-privileged classes Phase 2-eligible target (low-risk auto-merge under named conditions per FR-028) | merge authorization record |
| T21 | Merge Approved | Release Candidate Created | Nefarious-Hermes | release-candidate tagging policy (specified by Feature 002 RELEASE_AND_DEPLOYMENT_STRATEGY.md; automation deferred to Feature 006); once Feature 006 instantiates the release agent identity, the release agent assumes T21 ownership | Phase 1 | RC tag and release notes draft |
| T22 | Release Candidate Created | Deployment Approved | Source | Source deploy ratification (deploy class — privileged per FR-008) | Phase 1 (privileged — remains Phase 1) | deploy ratification record |
| T23 | Deployment Approved | Deployment Complete | future release agent (named in Feature 002; identity and automation deferred to Feature 006) | deploy execution under deploy automation (deferred Feature 006) | Phase 1 (privileged — remains Phase 1) | deploy attestation record |
| T24 | Deployment Complete | Post-release Evidence Recorded | future release agent | post-release evidence gathering policy (rollback evidence, observability artifacts); Hermes audits the resulting attestation finalization on Source's behalf until Feature 006 instantiates the release agent identity | Phase 1 | post-release attestation record finalizing the merge reference per Feature 001 FR-004 |

Notes:

- The matrix is normative. Transitions labelled `Phase 1 (privileged —
  remains Phase 1)` touch a privileged mutation class per FR-008 and
  remain Phase 1 in Feature 002 regardless of any future Phase 2
  ratification. Transitions carrying a `Phase 2-eligible target`
  annotation are candidates for future autonomy expansion under named
  conditions; the label is a planning marker, not a permission.
- Phase 2 expansion is OUT OF SCOPE for Feature 002 per FR-028.

## c. Phase 1 / Phase 2 boundary policy (FR-003, FR-027, FR-028)

**Phase 1 (the operational default in v0.1)** means:

- Assignment-based dispatch via Hermes-prepared envelopes.
- Human ratification of every privileged gate.
- Source merges; Hermes merges only after explicit Source
  authorization recorded in the ratification record.
- Claude Code does not self-assign.
- Codex (and future QA / security / release agents) does not ratify.

**Phase 2 (target only; not implemented in Feature 002)** means:

- Expanded autonomy bounded by ratified policy. Examples named only as
  targets:
  - Low-risk auto-merge if every condition holds: CI passes, Codex
    passes, mutation class is non-privileged (no `deploy`,
    `governance`, `identity`, `security`, `attestation`, `redaction`
    changes), no governance/identity/security/deploy changes, the PR
    matches the approved task batch, and the operating-model policy
    explicitly names auto-merge as ratified.
  - Autonomous batch-pulling under named conditions: Claude Code may
    pull approved non-privileged batches from a Source-ratified queue
    without per-batch Hermes envelope authorship; the queue itself is
    a ratified governance object.

Phase 2 expansion is OUT OF SCOPE for Feature 002. Any Phase 2
promotion is itself a ratified amendment to this operating model
(FR-029).

**Privileged transitions remain Phase 1** regardless of Phase 2
labelling: T3, T5, T15, T19 (for privileged classes), T20 (for
privileged classes), T22, T23, T24. Any future amendment must respect
this floor.

## d. `/speckit-implement` policy and Assignment Envelope linkage
(FR-005 through FR-011)

The `/speckit-implement` command is the mandatory implementation
command for Creator-Engine-governed work after Feature 002 ratification
and MUST be invoked only inside a Hermes-authored Assignment Envelope.

### d.1 Assignment Envelope schema (FR-005)

An Assignment Envelope is a YAML document under a tenant-declared
envelope directory. It MUST declare at minimum:

- `envelope_id`
- `spec_ref` (path or id of the Creator Engine spec the work
  fulfills)
- `feature_branch`
- `worktree_path`
- `approved_task_batch` (task IDs or file globs)
- `allowed_mutation_classes` (drawn from the Feature 001 baseline
  taxonomy and any ratified tenant extensions)
- `prohibited_surfaces` (paths or globs)
- `required_validation` (commands the consumer MUST run)
- `evidence_requirements` (what the consumer MUST return to Hermes)
- `stop_conditions` (the consumer MUST stop when these are met)
- `prohibited_external_actions` (e.g., commit, push, PR, merge,
  deploy, GitHub-settings mutation — unless explicitly authorized)
- `conflict_policy` (rebase/merge/conflict-resolution authority and
  escalation rules — typically: textual conflicts resolved by Hermes
  or the integration agent; semantic/authority conflicts escalated to
  Source via the conflict taxonomy)
- `created_by_actor_id` (author, MUST be the Hermes role)
- `consuming_actor_id` (consumer, MUST be a Claude Code role or other
  approved implementer role)

### d.2 Author/approver separation (FR-006)

`created_by_actor_id` and `consuming_actor_id` MUST be distinct. The
operating model MUST require future envelope schemas and validators
(instantiated by Feature 001 or a later feature) to reject envelopes
where author equals consumer as malformed. Feature 002 does not
implement the validator; it specifies the requirement.

### d.3 Single-use semantics (FR-007)

An envelope whose stop conditions have been satisfied MUST NOT be
reused. A new envelope (new id, fresh approval) MUST be issued for any
subsequent batch.

### d.4 Privileged-class envelopes require Source ratification (FR-008)

Where `allowed_mutation_classes` declares any class that Feature 001
reserves for human ratification (`deploy`, `governance`, `identity`,
`security`, `attestation`, `redaction`), the envelope itself MUST
require Source ratification before any consumer may begin work.

### d.5 Out-of-envelope `/speckit-implement` is an authority conflict
(FR-009)

If `/speckit-implement` is invoked outside a Hermes-authored
Assignment Envelope, the operating model classifies the invocation as
an authority conflict per the conflict taxonomy in
[`./parallel-agent-development-model.md`](./parallel-agent-development-model.md)
§e and at Feature 002 FR-018. Work HALTS, the case escalates to Source
for ratification, and Source EITHER ratifies an explicit amendment OR
directs the offending change to be reverted.

### d.6 Permitted vs prohibited actions (FR-010)

Inside an envelope, `/speckit-implement` is permitted to:

- read approved spec/plan/tasks artifacts;
- edit code/tests within the envelope's `allowed_mutation_classes`
  and outside its `prohibited_surfaces`;
- run the envelope's `required_validation` commands;
- mark tasks `[X]` only after local validation;
- report evidence to Hermes per the envelope's `evidence_requirements`.

Absent envelope-level explicit authorization, `/speckit-implement`
MUST NOT:

- commit (the envelope MAY or MAY NOT authorize local commits; if it
  does, the commit is still inside the worktree branch);
- push;
- open a PR;
- merge;
- close a ticket;
- deploy;
- alter secrets;
- alter governance, identity, attestation, or redaction surfaces;
- expand the mutation-class set;
- mutate any surface declared in `prohibited_surfaces`.

### d.7 No self-assignment (FR-011)

Claude Code MUST NOT self-assign envelopes. Hermes authors and scopes
envelopes; Claude consumes them; Source ratifies privileged
integration. A self-assigned envelope is malformed.

### d.8 Operating-mode runtime carriers (G2.002.1)

G2.002.0 landed the operating-mode policy substrate (the `strict` /
`auto` / `transcendence` mode enum, the `autonomy_class` enum, the
`operating-mode-policy` schema and validator). G2.002.1 propagates that
substrate into the runtime as **pure carriers** — they record posture
and never mint authority:

- **Assignment Envelope representation.** The envelope's declared
  operating mode, autonomy class, and (for elevated modes or privileged
  lane kinds) an inherited ratification-evidence pointer ride the
  Active-Work Ledger carrier fields below; no standalone
  assignment-envelope schema is introduced. The Assignment Envelope and
  Operator ratification remain the substantive authority.
- **Active-Work Ledger records.** The record schema carries optional
  `operating_mode`, `autonomy_class`, `lane_kind`, and
  `ratification_evidence_ref` fields, with `schema_version` extended to
  `"4"`. The fields are additive; pre-v4 records validate unchanged.
- **`lane_kind`** enumerates `read-only`, `implementation`, `review`,
  `approval`, `merge`, and `audit` — distinct from `pane_label`. It lets
  a downstream reviewer/approver/merger lane be a *different* lane kind
  from the implementer lane. G2.002.1 only carries the field;
  **PR-review, approval, and merge enforcement are downstream** and are
  not implemented here. Author/approver separation continues to be
  preserved operationally by an implementer lane stopping at PR creation.
- **`ce lane launch` default and refusals.** `--operating-mode` defaults
  to `strict`. `auto`/`transcendence` are refused unless an
  Operator-ratified tenant policy ratifies the requested mode, and a
  privileged class naming `agent_ratifier` or an advisory role as the
  ratifier is refused. Every such refusal is raised *before* any tmux
  spawn, Pane Registry write, or ledger write (the `G2-*` refusal family,
  mirroring the existing `G3-*` ordering).

The Operator-only privileged floor holds in every mode: no privileged
relaxation, no agent ratification, advisory-only `agent_reviewer`,
reserved-inactive `agent_ratifier`, and Operator-only emergency override.
Absent or migrated carriers resolve to `strict`; migration never infers
elevation. The `operating_mode_runtime_carriers` validator enforces this
floor, reusing the `operating_mode_policy` substrate helpers. See
[`../../specs/v2/adrs/ADR-V2-002-1-operating-mode-runtime-carriers.md`](../../specs/v2/adrs/ADR-V2-002-1-operating-mode-runtime-carriers.md).

## e. Actor/tool ownership matrix linkage

The full actor/tool ownership matrix lives in
[`./agent-interaction-model.md`](./agent-interaction-model.md) and the
source spec at
`specs/002-canonical-docs-and-operating-model/spec.md` §Actor/Tool
Ownership Matrix. The role-level authority is summarized in
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md).

The matrix enumerates, for each of Source, Nefarious/Hermes, Claude
Code, Codex, future QA agent, future security agent, future release
agent, CI, and GitHub: allowed instruction sources, allowed mutation
classes, allowed communication surfaces, required ratifier, required
audit artifacts, Phase 1 authority, Phase 2-eligible authority, and
prohibited actions. The matrix also assigns each actor/tool a presence
category per FR-014 (operationally active; named with identity record
deferred; named with automation deferred).

## f. Feature 001 lifecycle correspondence (FR-004)

The Feature 001 six-state spec lifecycle
`draft → ready → in_progress → verified → ratified → done` (FR-013a)
maps onto the SDLC state machine as follows. The Feature 001 lifecycle
is authoritative where they overlap.

| Feature 001 lifecycle state | Corresponds to SDLC states | Gate |
|---|---|---|
| `draft` | states 7–10 (`Feature Spec Drafted` through `Tasks Generated`) | Definition of Ready (Feature 001 FR-013) MUST pass before `draft → ready`. |
| `ready` | state 11 (`Batch Approved`) | Source batch approval per T10. |
| `in_progress` | states 12–14 (`Agent Assigned` through `Implementation Complete`) | Envelope is consumed by an authorized agent per FR-015. |
| `verified` | states 15–18 (`Local Validation Complete` through `Scope Audit Complete`) | Author records verification evidence per Definition of Done; actor MUST NOT be the ratifier (FR-007). |
| `ratified` | state 20 (`Ratification Complete`) — also state 21 (`Merge Approved`) when the merge authorization is the same artifact | Ratifier distinct from author per FR-007/FR-016/FR-017; privileged classes require human ratifier per FR-008. |
| `done` | state 21 (`Merge Approved`) onward — finalized at state 25 (`Post-release Evidence Recorded`) | Pre-merge attestation present per FR-004; mutation merged; attestation finalized with merge reference. |

Skipping or backfilling Feature 001 lifecycle states is a contract
violation surfaced by the validator (Feature 001 FR-027a); the same
rule applies to operating-model SDLC states: skipping or backfilling
SDLC transitions is an authority conflict per FR-018.

## g. Amendment procedure (FR-029)

Amendments to this operating model — the SDLC state machine, the
Assignment Envelope schema, the `/speckit-implement` policy, the
actor/tool ownership matrix, the Phase 1 / Phase 2 boundary, or any
Feature 002 normative section — follow the Creator Engine
constitution's amendment procedure:

1. A spec/plan/tasks triple proposing the amendment is authored under
   Spec Kit and the Creator Engine wrapper sidecars.
2. The amendment is a `governance`-class privileged mutation per
   Feature 001 FR-008. Source ratification is required.
3. Source approval is recorded in the amendment commit or in a
   repository artifact referenced by the commit.
4. The Sync Impact Report at the top of `.specify/memory/constitution.md`
   is updated if the amendment touches constitution-level rules; the
   version bump policy in the constitution Governance section
   applies.
5. Privileged transitions and the privileged-class list remain Phase 1
   floor regardless of any Phase 2 ratification in the amendment.

Phase 2 expansion is itself such an amendment (FR-028); Phase 2 is not
implemented by Feature 002.

## h. Prompt-file ratification phrase

Some governed handoffs are scoped by a prompt file: a handoff
document, an envelope draft committed to disk, or another file whose
contents define the scope of a ratifier-authorized action. Where a
ratifier authorizes work by reference to such a file, the canonical
human-readable ratification phrase is:

```text
Source ratifies prompt:<absolute prompt path> with SHA:<sha256>
```

Both arguments are required. `<absolute prompt path>` is the absolute
filesystem path of the prompt file at the moment of ratification.
`<sha256>` is the lowercase hexadecimal SHA-256 digest of the prompt
file's bytes at that same moment. Binding the ratification to the
digest closes the prompt file's contents: any subsequent edit produces
a different digest and therefore a different, un-ratified artifact.

This phrase is procedural, not ornamental. Its job is to give the
audit chain a single, locatable line that can be parsed and
cross-checked against the file on disk. It does NOT replace the
ratification record formats specified in Feature 001 (FR-016,
FR-020a); the YAML ratification record remains the canonical
artifact. Where the prompt-ratification phrase and the YAML
ratification record disagree, the YAML record wins.

The phrase belongs to the same authority rules as any other
ratification surface: it is valid only when uttered by a ratifier
authorized for the relevant mutation class per the Feature 001
authority matrix and Feature 002 §e, and the author/approver
separation rule (FR-006/FR-007) still applies — the ratifier MUST
NOT have authored the prompt file.

## Acceptance posture for this document

This agentic-sdlc-operating-model.md satisfies Feature 002 Canonical
Document Specification #6: all 25 states are named in order; the 24
transitions are tabled with responsible actor/tool, authorizing gate,
phase label, and required evidence; the Phase 1 / Phase 2 boundary is
present; the `/speckit-implement` policy is explicit; the Feature 001
lifecycle correspondence table is present; the amendment procedure
cites FR-029.
