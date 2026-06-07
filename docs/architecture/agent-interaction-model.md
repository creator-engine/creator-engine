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

**Terminology (current CE canon).** This document's prose uses current
CE terminology: the **Operator** is the human ratifying authority, and
the **Controller** is the orchestrating author / coordination role. The
Feature 001/002 contracts this document defers to retain the legacy
machine-role names `source` (→ Operator) and `Hermes`-the-role
(→ Controller); the v2 terminology canon (`ce_terminology_v2`) accepts
those legacy names *on import* in `specs/001`/`002` and enforces
`operator` only on new `specs/v2/` artifacts. Crucially, the **Hermes
harness** — the CE CLI / `.hermes/` toolchain / seat-launch substrate —
is a *tool* the Controller runs on, NOT the Controller role; the §a
matrix's "Nefarious / Hermes" actor names that operator machine + that
harness, distinct from the Controller. The §a Actor/Tool Ownership
Matrix below mirrors the Feature 002 actor *names* verbatim (so the
cross-reference and the actor-parity posture in §h hold); everywhere
else this document uses Operator / Controller.

The deterministic syscall / governed-state-machine doctrine that
underlies these interaction patterns is canonized in
[`./agentic-sdlc-operating-model.md`](./agentic-sdlc-operating-model.md)
under "Doctrine: deterministic syscall layer over probabilistic
agents." The seven interaction patterns below describe how named
actors cross that syscall boundary in practice: probabilistic agents
operate inside Assignment Envelopes, evidence flows through the
audit chain, and ratification of privileged mutations remains
Operator's responsibility.

## a. Actor/Tool Ownership Matrix (cross-reference)

Feature 002 names nine actors/tools with explicit presence categories:

| Actor / Tool | Presence category |
|---|---|
| Source | Operationally active. |
| Nefarious / Hermes | Operationally active. |
| Claude Code | Operationally active. |
| Codex | Governed first-class actor; identity record deferred with upstream placeholder/unbound provider/tool/model/host/account semantics. Phase 1 authoring posture follows Operator-ratified per-batch role assignment between `architect` and `implementer`; `codex-architect` is a tenant/public overlay alias only, not a new baseline role. |
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

Batch 2A ratified Codex Option C: Codex may be represented as a
governed first-class actor whose Phase 1 authoring role is selected by
the Operator-ratified envelope for the specific batch. An
architect-class envelope authorizes architect authoring; an
implementer-class envelope authorizes implementer authoring. This is
architect parity as authoring parity only: it is not ratification
authority, not merge authority, and not deploy authority. The authority
remains envelope-bound, not personality-bound.

## b. Actor-to-actor interaction patterns

The operating model recognizes seven primary interaction patterns.
Each pattern names participants, the surface(s) used, and the
governance artifact produced.

### b.1 Operator ↔ Controller (intent capture, ratification)

- **When**: T1 (Idea/Intent → Discovery); T3, T5, T10, T19, T20, T22
  (ratification points); any Phase 2-promotion amendment.
- **Surface**: Operator-authored or Operator-approved commit messages;
  ratification records under `ratification_storage_path`; PR review
  comments where the authority matrix designates that surface as a
  ratification surface for the relevant mutation class.
- **Artifact**: working-note or tracker entry citing Operator intent;
  ratification record YAML per Feature 001 FR-016 and FR-020a.
- **Invariants**: Controller never ratifies its own work; Operator's
  ratification is the human anchor and is not subject to Phase 2
  autonomy expansion.

### b.2 Controller → governed author (envelope handoff)

- **When**: T11–T13 (envelope authoring → consumption).
- **Surface**: the Assignment Envelope YAML file under the
  tenant-declared envelope directory.
- **Artifact**: the envelope itself (FR-005 fields populated; author
  is the Controller role; consumer is the Claude Code role, Codex role, or
  another Operator-ratified governed author role named by the envelope).
- **Invariants**: author MUST ≠ consumer (FR-006); envelope is
  single-use (FR-007); privileged-class envelopes require Operator
  ratification before consumption (FR-008).

### b.3 Claude Code ↔ Controller (evidence reporting)

- **When**: T14–T15 (local validation complete → attestation
  drafted).
- **Surface**: validator output captured on the feature branch; test
  logs; lint/typecheck output; Creator Engine validator output; the
  evidence return path the envelope declares.
- **Artifact**: pre-merge attestation YAML drafted by Controller per
  Feature 001 FR-004 and FR-020a.
- **Invariants**: Claude Code MUST NOT ratify its own work; Claude
  Code reports evidence and Controller drafts the attestation; the
  attestation gate is privileged (`attestation` class) and remains
  Phase 1.

### b.4 Codex ↔ Controller (per-batch governed authoring and review)

- **When**: T11–T16, when a Operator-ratified envelope names Codex as
  the consuming actor for architect-class authoring, implementer-class
  authoring, or independent review. Without that envelope, Codex has
  no standing write authority.
- **Surface**: the Assignment Envelope YAML for architect/implementer
  authoring; review findings records (schema deferred to Feature 004)
  and PR review comments when Codex is acting as reviewer.
- **Artifact**: Codex-authored architect or implementer artifacts under
  the envelope's allowed paths and mutation classes; review findings
  records when Codex acts as reviewer. Architect-class artifacts are
  attested through the ordinary attestation flow; review evidence
  remains a separate Phase 1 artifact class and never substitutes for
  ratification.
- **Invariants**: Codex has no ratification authority, no merge
  authority, and no deploy authority. Codex verifies-not-ratifies:
  review evidence and Codex-authored architect/implementer evidence are
  evidence only. Codex writes only inside a separate Codex-only
  worktree under one-driver-per-worktree isolation and never writes to
  the active Claude Code worktree or the canonical main worktree.

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

### b.6 Controller ↔ Operator (scope audit and ratification)

- **When**: T18–T20 (scope audit → ratification → merge approval).
- **Surface**: scope audit summary committed to the feature branch
  or attached to the PR; ratification record; merge authorization
  record.
- **Artifact**: scope audit summary citing envelope id, batch ids,
  and mutation-class boundaries; ratification record YAML;
  merge-authorization record (may share the ratification record for
  same-class mutations).
- **Invariants**: Controller may execute merge mechanics only when
  explicit Operator authorization is recorded; for privileged classes
  the ratifier MUST be Operator (FR-008).

### b.7 release agent ↔ Operator / Controller (deploy and post-release
finalization)

- **When**: T21–T24 (release candidate → deploy → deployment
  complete → post-release evidence).
- **Surface**: release tags; deploy logs; deploy attestations;
  rollback evidence; post-release attestation records.
- **Artifact**: per-stage attestation records and ratification
  records. Schemas for deploy attestation, rollback evidence, and
  post-release evidence are deferred to Feature 006.
- **Invariants**: the `deploy` mutation class is Operator-only per
  FR-008; the release agent never ratifies the `deploy` class. Until
  Feature 006 instantiates the release agent identity, Controller acts
  on Operator's explicit authorization for T21 and audits attestation
  finalization for T24.

## c. Communication surfaces

The operating model uses these surfaces. Per Feature 001 FR-015 a
surface that appears in a role's `allowed_communication_surfaces` is
permitted to *carry* governance artifacts; whether a surface counts
as a *valid ratification surface* for a given mutation class is
governed by the Feature 001 ratification-flow contract.

- **Tmux sessions**: live operator surface where Controller and Claude
  Code panes coordinate. Conversations and command output on tmux
  are NOT canonical governance artifacts. Anything load-bearing MUST
  be promoted into a repository artifact (commit, sidecar, envelope,
  attestation, ratification record).
- **Repository surfaces**:
  - `repo_pr` — pull requests.
  - `repo_review` — PR review comments.
  - `repo_commit_message` — commit messages (Operator-authored or
    Operator-approved commits count as Operator-surface artifacts).
  - `repo_issue` — issues / tickets.
  - `repo_attestation_record` — YAML records under
    `attestation_storage_path`.
  - `repo_ratification_record` — YAML records under
    `ratification_storage_path`.
- **Assignment Envelope YAML**: the explicit handoff surface from
  Controller to the governed author named by the envelope.
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
- Operator MUST NOT ratify Operator's own authored mutation; another
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

Codex, the future QA agent, and the future security agent are not
ratifiers. When Codex acts as reviewer, its review evidence is not
ratification. When Codex acts under a Operator-ratified architect or
implementer envelope, its authored artifacts and evidence are still not
ratification. Even if findings recommend merge, the merge gate (T20)
still requires Operator authorization for privileged classes.

## f. Envelope handoff sequence (Controller → governed author)

The envelope handoff is the operational seam where Creator Engine
governance meets governed authoring mechanics. Every FR-005 field
is exercised exactly once per handoff.

1. **Batch approval recorded** (T10). Operator records the approved
   task batch in a batch approval record. For privileged-class
   batches, Operator is the only approver.
2. **Envelope authoring** (T11). Controller drafts an Assignment Envelope
   referencing the approved batch. Controller populates every required
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
   - `created_by_actor_id` — Controller role.
   - `consuming_actor_id` — Claude Code role, Codex role, or another
     approved governed author role selected by the Operator-ratified
     envelope.
3. **Operator ratification for privileged-class envelopes** (FR-008).
   If `allowed_mutation_classes` declares any privileged class, the
   envelope is committed only with Operator ratification recorded; the
   consumer MUST NOT begin work until ratification is present.
4. **Worktree/branch provisioning** (T12). Controller provisions the
   worktree at `worktree_path` and ensures the branch
   `feature_branch` exists from the agreed base.
5. **Envelope consumption** (T13). The envelope's consuming actor
   begins work inside the worktree. `/speckit-implement` reads the
   approved spec/plan/tasks artifacts when the envelope invokes Spec
   Kit implementation mechanics; the consumer mutates only inside
   `allowed_mutation_classes` and outside `prohibited_surfaces`;
   tasks are marked `[X]` only after local validation per FR-010.
6. **Stop on stop_conditions** (T13 → T14). When stop conditions are
   met, the consumer halts; it does NOT extend scope and does NOT
   reuse the envelope for follow-up batches.
7. **Local validation** (T14). The consumer runs every command in
   `required_validation` and captures outputs as the envelope's
   `evidence_requirements` specify.
8. **Evidence return** (T14 → T15). The consumer reports evidence to
   Controller per the envelope's return path; Controller drafts the
   pre-merge attestation in §b.3.

The handoff is single-use. If new work is needed (a follow-up batch
or a conflict-resolution sub-batch), a new envelope is issued with a
new `envelope_id` and fresh approval.

## g. Escalation paths to Operator via the conflict taxonomy

The four conflict classes in
[`./parallel-agent-development-model.md`](./parallel-agent-development-model.md)
§e (and at Feature 002 FR-017, FR-018) anchor every escalation:

| Conflict class | Detector | Resolver | Escalation to Operator? |
|---|---|---|---|
| `textual` | git merge/rebase | integration agent or Controller | No (unless resolution requires scope expansion). |
| `file/task ownership` | envelope/claim protocol | Controller (via serialization or explicit dependency order) | No (unless overlap signals a deeper scope conflict). |
| `semantic` | review / test / architecture audit | architect review; possibly Operator ratification if Feature 001 contracts are touched | Yes, if substrate contract semantics are affected. |
| `authority` | operating model / future substrate validators | Operator (HARD-STOP) | Yes — always. |

`authority` conflicts hard-stop work. The agent MUST NOT continue,
revert, or rebase to conceal an `authority` conflict; the case
escalates to Operator for ratification, and Operator either ratifies the
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
authority, and prohibited actions. Per the terminology note above, the
current-canon **Operator** and **Controller** used in this document's
prose map one-to-one onto that matrix's legacy `Source` and
`Nefarious / Hermes` rows (mirrored verbatim in §a), so the
actor-parity is exact. The role-level summary in
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
is the navigational entry point.

The envelope handoff sequence in §f exercises every FR-005 field
required by Feature 002.

## i. The v3 G-4 per-action substrate (as-built)

The interaction patterns above describe how named actors cross the
deterministic syscall boundary at the SDLC granularity. v3 G-4 adds the
**per-run, per-action** substrate underneath them — the typed contract a
governed run's individual agent actions are recorded and gated against. It
is additive and CI-pure; the live transport tap is a deferred seam.

The contract (built in `creator_engine_validator.runner.audit_overlay`,
recorded on the shared `runtime_evidence_spine`):

- **`AgentActionEvent`** — a frozen, two-axis event. `op` (`read`/`write`/
  `exec`/`egress`/`secret`/`vcs`) is the *"do we gate?"* axis (reads are
  observe-only); `mutation_class` (the shared `checks.mutation_class`
  taxonomy plus `none`) is the blast-radius axis. `fidelity` (`faithful`/
  `best_effort`/`inferred`) is the provenance marker — **stamped by the
  adapter, never the agent** — and is itself a policy input (lower fidelity
  earns stricter policy). `timing` is `pre` (preventive) or `post`
  (detective). `op` decides *whether* to block; `op × mutation_class ×
  fidelity` decides *how hard*.
- **`classify()`** — extended with a PURE `AgentActionEvent` branch:
  reads allow; a faithful mutating op is allowed iff its `(op,
  mutation_class)` cell is on the policy's `action_class_allowlist`, else
  deny-by-default; a non-faithful mutating op escalates.
- **`decide()`** — a deterministic, in-process, zero-token control-point
  over `classify()`: a built-in deny tier (survives even `full`), then Zed
  precedence over the policy's `gate_mode_ladder` `always_*` rules
  (`always_deny` > `always_confirm` > `always_allow`), then the per-cell
  gate mode (`deny`/`allowlist`/`ask`/`auto`/`full`). `auto` is
  advisory-only — it may downgrade an escalate→allow but never authorizes a
  deny-class action.
- **`runtime_agent_action` record** — every decision (allow/deny/escalate
  alike) is appended to the same tamper-evident hash chain as the lifecycle,
  outcome, and ratification records, on its own orthogonal axis. Each action
  becomes content-addressed, policy-bound, fidelity-tagged grader input.

This is the substrate the tokenomics gate (G-5, which reuses the
action-gate's escalation + evidence machinery) and the coordination layer
(G-6, which dispatches a ratified Scope into one G-4/G-5-governed run) sit
on. Authority remains external and deterministic — the in-run gate is
evidence + preventive enforcement, never the binding ratifier.

**Transport: Tier-B reuse is boundary-clean (v1 ⊥ v3).** The first
transport emitter is the OAuth/subscription-first-class Claude-Code hook
tier (`runner.cc_hook_adapter`: a PURE `PreToolUse`-payload →
`AgentActionEvent` derivation, `fidelity=best_effort`, `timing=pre`; the
live hook/stream-json tap is the deferred event source). The earlier
design phrasing "reuses `hook_check.py`" predates the G-3.9
`version_boundary`: `hook_check` is a **v1** module and `runner.*` is
**v3**, so a direct import would be a HARD boundary crossing. The adapter
therefore derives `mutation_class` through the **shared**
`checks.mutation_class` taxonomy, never the v1 `hook_check` runtime.
Reaching parity with `hook_check`'s nuanced secret/command heuristics is a
ratified follow-on (a shared extraction or a scoped v3 re-derivation), not
a silent boundary crossing. The ACP (Tier-A) and transcript (Tier-C)
adapters, plus the late-credential-minting / snapshot-hash-recheck
hardening, are deferred backlog.

## Acceptance posture for this document

This agent-interaction-model.md satisfies Feature 002 Canonical
Document Specification #7: every actor named in the Feature 002
Actor/Tool Ownership Matrix appears; the review-vs-ratification
distinction is explicit; the envelope handoff sequence covers every
FR-005 field; cross-references to the matrix and the conflict
taxonomy are present.
