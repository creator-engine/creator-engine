# Feature Specification: Creator Engine v0.1-docs — Canonical Product, Architecture, and Agentic SDLC Operating Model

**Feature Branch**: `002-canonical-docs-and-operating-model`
**Created**: 2026-05-11
**Status**: Draft
**Input**: User description: Creator Engine v0.1-docs — define the canonical product, architecture, governance, quality, devops, and security documentation set for Creator Engine, and the full agentic SDLC operating model that turns Creator Engine from a Spec Kit validator into the agentic SDLC control plane. Feature 001 builds the law (governance substrate); Feature 002 defines the civilization (the full operating model that future SDLC automation must obey). Specification-only feature: canonical docs are specified but not yet authored.

## User Scenarios & Testing *(mandatory)*

<!--
  Feature 002 is a SPECIFICATION feature. Its users are humans and agents who
  must understand the Creator Engine agentic SDLC operating model and the set
  of canonical documents that future implementation work must produce. Each
  user story is independently testable against the spec itself: a reader of
  the spec must be able to answer the questions the story poses without
  consulting external systems.
-->

### User Story 1 - SDLC State Machine Defined End-to-End (Priority: P1)

A tenant adopting Creator Engine MUST be able to read the canonical SDLC
operating model and identify every state a work item passes through from
product intent to post-release evidence, the responsible actor/tool for each
transition, and the gate that authorizes the transition. The state machine is
the backbone of the Creator Engine control plane: without it, Creator Engine
remains a collection of validators rather than a real SDLC operating system.

**Why this priority**: Every other Feature 002 concept (assignment envelopes,
parallel-agent development, ratification, attestation, conflict taxonomy)
hangs off named states in the SDLC state machine. If the states are not fixed
first, downstream concepts cannot be coherently anchored. This is the highest-
priority user story because it is the load-bearing artifact of Feature 002.

**Independent Test**: A reviewer with `git clone` and the Feature 002 spec
artifacts can list every SDLC state in order, name the actor/tool responsible
for each transition, name the gate that authorizes the transition, and state
whether the transition is Phase 1 only or Phase 2 eligible. Verified by
walking the full state machine from `Idea/Intent` to `Post-release Evidence
Recorded` without referring to any other system.

**Acceptance Scenarios**:

1. **Given** the canonical SDLC operating model document specified by
   Feature 002, **When** a reviewer reads it, **Then** they can enumerate
   every state in `Idea/Intent → Discovery → PRD Drafted → PRD Ratified →
   Architecture Drafted → Architecture Ratified → Feature Spec Drafted →
   Spec Clarified → Plan Drafted → Tasks Generated → Batch Approved →
   Agent Assigned → Worktree Created → Implementation Complete → Local
   Validation Complete → Attestation Drafted → Independent Review
   Complete → CI Evidence Complete → Scope Audit Complete → Ratification
   Complete → Merge Approved → Release Candidate Created → Deployment
   Approved → Deployment Complete → Post-release Evidence Recorded`.
2. **Given** any single SDLC state, **When** a reviewer asks "who advances
   this work item to the next state?", **Then** the operating model names
   exactly one responsible actor/tool (Source, Hermes, Claude Code, Codex,
   future QA/security/release agent, CI, or GitHub) and the gate that must
   pass.
3. **Given** any transition between SDLC states, **When** the operating
   model is consulted, **Then** it is labelled either `Phase 1` (assignment-
   based, ratification-heavy) or `Phase 2-eligible` (autonomy expansion
   target); transitions whose Phase 2 form has not been ratified MUST remain
   Phase 1 only.

---

### User Story 2 - Assignment Envelope Is the Governed Unit of Agent Work (Priority: P1)

A Hermes operator MUST be able to read the Assignment Envelope specification
and author a fully-formed envelope that authorizes a single Claude Code
`/speckit-implement` invocation within a bounded scope. Without the envelope,
Claude Code MUST NOT invoke `/speckit-implement` for any Creator-Engine-
governed work. The envelope is the contract that binds an agent's actions to
an approved batch, an approved set of mutation classes, an approved set of
surfaces, and a set of stop conditions.

**Why this priority**: The Assignment Envelope is the operational seam where
Creator Engine governance meets Spec Kit implementation mechanics. If the
envelope is not first-class, `/speckit-implement` becomes an unbounded
instruction and the governance substrate is bypassed at exactly the moment
the agent acts on the repo.

**Independent Test**: A Hermes operator reads the Assignment Envelope spec,
authors one envelope by hand against a hypothetical Feature 003 batch, and a
reviewer confirms the envelope contains every required field, names the
correct author/consumer roles, and would be rejected (per the spec's stated
rules) if any field were missing or any prohibited surface were included.

**Acceptance Scenarios**:

1. **Given** the Assignment Envelope specification, **When** a Hermes
   operator drafts an envelope, **Then** the envelope declares at minimum:
   envelope id, spec ref, feature branch, worktree path, approved task
   batch (IDs or globs), allowed mutation classes, prohibited surfaces,
   required validation commands, evidence requirements, stop conditions,
   prohibited external actions, conflict policy (whether the consuming
   agent may rebase/merge/resolve-conflicts and where it must escalate),
   the author actor id (Hermes role), and the consuming actor id (Claude
   role).
2. **Given** an envelope authored by an actor who would also be its
   consumer, **When** the envelope is reviewed against the operating
   model, **Then** the operating model MUST classify the envelope as
   malformed and MUST require future envelope schemas and validators to
   reject it; an actor MUST NOT both author and consume the same
   envelope.
3. **Given** an envelope whose `allowed mutation classes` declare a class
   that the Feature 001 mutation-class taxonomy reserves for human
   ratification (`deploy`, `governance`, `identity`, `security`,
   `attestation`, `redaction`), **When** the envelope is reviewed,
   **Then** the spec MUST require explicit Source ratification of the
   envelope itself before Claude may consume it.
4. **Given** a Claude Code session that has received an envelope, **When**
   Claude invokes `/speckit-implement`, **Then** the operating model MUST
   require Claude to operate only inside the envelope's declared scope and
   stop at the declared stop conditions, without commit/push/PR/merge/
   deploy unless the envelope explicitly authorizes those external actions.

---

### User Story 3 - `/speckit-implement` Policy Is Bound to the Envelope (Priority: P1)

A reader of the operating model MUST be able to state Creator Engine's
`/speckit-implement` policy precisely: once Feature 002 is ratified,
`/speckit-implement` is the mandatory implementation command for Creator-
Engine-governed work, and it MUST be invoked only inside a Hermes-authored
Assignment Envelope. Out-of-envelope `/speckit-implement` invocation is a
contract violation. Hermes authors/scopes envelopes; Claude consumes them;
Source ratifies privileged integration.

**Why this priority**: This policy is what closes the gap identified in the
"speckit implementation command gap report": absent an explicit policy,
`/speckit-implement` is either ignored (leaving Spec Kit's implementation
mechanics on the table) or invoked outside any governance envelope (giving
the agent unbounded write authority). The policy makes the bounded usage
contractual.

**Independent Test**: A reviewer reads the operating model, picks a candidate
Feature 003 implementation scenario, and states (without referring to any
external system): which actor authors the envelope, which actor invokes
`/speckit-implement`, which actor ratifies any privileged action, and what
the operating model says happens if Claude invokes `/speckit-implement`
outside an envelope.

**Acceptance Scenarios**:

1. **Given** the operating model, **When** a reviewer reads the
   `/speckit-implement` policy section, **Then** it states unambiguously
   that `/speckit-implement` is mandatory for Creator-Engine-governed
   implementation and is invoked only inside a Hermes-authored Assignment
   Envelope.
2. **Given** a Claude Code session that attempts to invoke
   `/speckit-implement` without an envelope in scope, **When** the
   operating model is consulted, **Then** the operating model classifies
   the attempt as an authority conflict (per the conflict taxonomy in
   User Story 7), hard-stops the work, and requires Source ratification
   to proceed.
3. **Given** the operating model, **When** a reviewer asks "may
   Hermes self-consume an envelope it authored?", **Then** the operating
   model answers no: author/approver separation forbids the envelope's
   author from also being its consumer.
4. **Given** the operating model, **When** a reviewer asks "what is
   `/speckit-implement` allowed to do?", **Then** the operating model
   names the exact list of permitted actions (Spec Kit implementation
   mechanics: read approved spec/plan/tasks artifacts, edit code/tests
   within the envelope's allowed mutation classes, run required
   validation, mark tasks `[X]` only after local validation, report
   evidence) and the exact list of prohibited actions (commit, push,
   open PR, merge, close ticket, deploy, alter secrets, alter governance,
   alter identity, expand mutation class set, exceed prohibited
   surfaces) absent envelope-level explicit authorization.

---

### User Story 4 - Actor/Tool Ownership Model Names Every Responsible Party (Priority: P1)

A reader of the operating model MUST be able to identify, for each named
actor or tool (Source, Nefarious/Hermes, Claude Code, Codex, future
QA/security/release agents, CI, GitHub), the actor's allowed instruction
sources, allowed mutation classes, allowed communication surfaces, required
ratifier, and required audit artifacts. The operating model MUST state the
invariant that CI verifies but does not ratify, and that agent-authored
review text MUST NOT count as ratification for privileged mutation classes.

**Why this priority**: The actor/tool ownership table is what binds the SDLC
state machine (User Story 1) to specific roles. Without it, "who advances
this state?" cannot be answered consistently. Future Features 003–006 will
register additional governed identities (Codex review agent, QA agent,
release agent) against this same ownership model.

**Independent Test**: A reviewer reads the actor/tool ownership table and
picks any state transition from the SDLC state machine; the reviewer can
state which actor performs the transition, which actor ratifies the
transition (if ratification is required), and which audit artifact records
the transition. Verified across all 24 transitions (the 25 SDLC states
produce 24 transitions; see the `SDLC Transition Matrix` section).

**Acceptance Scenarios**:

1. **Given** the operating model's actor table, **When** a reviewer looks
   up `Source`, **Then** the table names Source as final ratifier for the
   privileged mutation classes enumerated in Feature 001 (`deploy`,
   `governance`, `identity`, `security`, `attestation`, `redaction`)
   and for canonical-branch integration; Source's allowed surfaces and
   audit artifacts (commit messages, ratification records) are listed.
2. **Given** the operating model's actor table, **When** a reviewer looks
   up `Nefarious/Hermes`, **Then** the table names Hermes as orchestrator
   and auditor: authoring assignment envelopes, creating branches and
   worktrees, running independent verification, opening PRs after
   verification, generating attestations, and enforcing approval gates.
   Hermes MUST NOT be the consumer of an envelope it authored.
3. **Given** the operating model's actor table, **When** a reviewer looks
   up `Claude Code`, **Then** the table names Claude Code as primary
   implementation agent: consumes envelopes, invokes `/speckit-implement`
   inside the envelope, runs local validation, reports evidence. Claude
   Code MUST NOT self-assign work, ratify its own work, merge PRs, alter
   secrets, alter governance, alter identity, or invoke
   `/speckit-implement` outside an envelope.
4. **Given** the operating model's actor table, **When** a reviewer looks
   up `Codex`, **Then** the table names Codex as independent reviewer:
   reads diffs, surfaces findings, may implement only in a separate
   worktree under an envelope explicitly authorizing fallback
   implementation. Codex review text MUST be recorded as review evidence
   but MUST NOT count as ratification for privileged mutation classes.
5. **Given** the operating model's actor table, **When** a reviewer looks
   up future QA, security, and release agents, **Then** the table states
   each role's scope, surfaces, ratifier, and required audit artifact;
   the actors themselves are NOT instantiated in Feature 002 (they are
   deferred to Features 004 and 006).
6. **Given** the operating model's actor table, **When** a reviewer looks
   up `CI`, **Then** the table names CI as mechanical validator: runs
   tests, lint, typecheck, build, Creator Engine validator, schema
   validation. CI MUST NOT ratify product correctness, strategic
   decisions, trading-risk decisions, or governance authority. CI output
   becomes attestation evidence but never a ratification record.

---

### User Story 5 - Canonical Document Set Is Specified, Not Yet Authored (Priority: P1)

A reader MUST be able to find, in the Feature 002 spec, the complete list of
canonical Creator Engine documents that future implementation work will
author, including each document's purpose, required sections, source-of-
truth relationship to Feature 001 contracts, and acceptance criteria for
what "exists and is sufficient" means. Feature 002 specifies the doc set;
it does not author the documents themselves (that is the implementation
phase that follows Feature 002).

**Why this priority**: Without a fixed canonical doc set, future Creator
Engine work cannot agree on what "the docs" are or what an addition is
proposing to add. The doc set is the namespace the operating model lives
in; specifying it before authoring prevents premature divergence between
contributors.

**Independent Test**: A reviewer reads the Feature 002 spec, lists every
canonical document by path, states each document's purpose in one sentence,
and identifies which Feature 001 contract each document defers to (if any).
Verified by walking the full doc set without inventing additional documents.

**Acceptance Scenarios**:

1. **Given** the Feature 002 spec, **When** a reviewer reads the
   canonical-doc-set section, **Then** the spec enumerates exactly the
   documents listed in `Key Entities → Canonical Document Set` below, no
   more and no fewer, and assigns each a purpose, required sections,
   source-of-truth relationship, and acceptance criteria.
2. **Given** any one canonical document specified by Feature 002,
   **When** a reviewer asks "what makes this document done?", **Then**
   the spec answers in terms of required sections and content
   completeness rather than file existence alone (a stub file does not
   satisfy the acceptance criterion).
3. **Given** the canonical-doc-set section, **When** a reviewer looks
   for documents that duplicate Feature 001 contracts, **Then** the spec
   declares the deferral relationship: the canonical doc summarizes and
   references the Feature 001 contract; it MUST NOT redefine or compete
   with the Feature 001 contract.
4. **Given** the canonical-doc-set section, **When** a reviewer looks
   for an authored body in Feature 002, **Then** the spec confirms that
   no canonical document body is authored in Feature 002; Feature 002
   ships specification only.

---

### User Story 6 - Parallel-Agent Development Model Replaces the Emergency Freeze (Priority: P2)

A reader MUST be able to read the parallel-agent development model and
confirm that Creator Engine governs (not prevents) parallel agent work. The
permanent rule is: one driver per physical worktree, but many isolated
writers across separate branches/worktrees, each operating under its own
Assignment Envelope, with canonical-branch integration serialized and
Source-ratified. The temporary one-writer-globally rule from the May 10
coordination incident is explicitly NOT the permanent model.

**Why this priority**: This story corrects the emergency freeze from
becoming Creator Engine's architecture. It is P2 (not P1) because Feature
002 lands the doc set and SDLC operating model first; parallel-agent
scaling becomes operationally critical when Feature 003+ begins shipping in
parallel batches.

**Independent Test**: A reviewer reads the parallel-agent development model
and walks a scenario in which two Hermes+Claude pairs work on different
features simultaneously; the reviewer states which writes each pair may
make, where each pair's writes land, and how the writes integrate without
either pair overwriting the other's work.

**Acceptance Scenarios**:

1. **Given** the parallel-agent development model, **When** a reviewer
   asks "may two Claude sessions write to the same physical worktree
   concurrently?", **Then** the answer is no — one driver per physical
   worktree.
2. **Given** the parallel-agent development model, **When** a reviewer
   asks "may two Hermes+Claude pairs work on different features in
   parallel?", **Then** the answer is yes, provided each pair has its
   own worktree, branch, and Assignment Envelope, and the envelopes'
   scopes do not overlap (or declare an explicit integration dependency).
3. **Given** the parallel-agent development model, **When** a reviewer
   asks "how is the canonical branch protected from concurrent writers?",
   **Then** the model states that canonical-branch integration is
   serialized and Source-ratified; git handles textual conflicts during
   integration, and Creator Engine handles semantic/authority conflicts
   via the conflict taxonomy (User Story 7).
4. **Given** the parallel-agent development model, **When** a reviewer
   asks "is the temporary May 10 freeze the permanent model?", **Then**
   the model answers no and references the source decision: "Creator
   Engine should not prevent parallel agent development; it should govern
   it. Many isolated writers, one governed integration path."

---

### User Story 7 - Conflict Taxonomy Names Resolution Paths (Priority: P2)

A reader MUST be able to read the conflict taxonomy and classify any
real conflict into one of four classes — textual, file/task ownership,
semantic, or authority — and follow the named resolution path. Each class
names how it is detected, who resolves it, and what evidence the resolution
must produce.

**Why this priority**: Without a conflict taxonomy, parallel-agent work
(User Story 6) produces undefined behavior the moment two branches diverge
in any non-textual way. The taxonomy turns "the agents disagree" into a
governed resolution path rather than an escalation by exhaustion.

**Independent Test**: A reviewer reads the conflict taxonomy and is given
three example scenarios; for each scenario the reviewer classifies the
conflict, names the resolver, and states the required evidence.

**Acceptance Scenarios**:

1. **Given** two branches that edit overlapping lines in the same file,
   **When** integration is attempted, **Then** the taxonomy classifies
   this as a textual conflict, names git merge/rebase as the detector,
   names the integration agent or Hermes as the resolver, and requires
   re-run tests as evidence.
2. **Given** two assignment envelopes that both claim the same task ID
   or the same file glob, **When** the envelope/claim protocol runs,
   **Then** the taxonomy classifies this as a file/task ownership
   conflict, names the envelope/claim protocol as the detector, names
   Hermes as the resolver (via serialization or explicit dependency
   order), and requires an updated envelope as evidence.
3. **Given** one branch changes lifecycle statuses while another branch
   writes validators assuming the old statuses, **When** the validators
   run or review notices the drift, **Then** the taxonomy classifies
   this as a semantic conflict, names review/test/architecture audit as
   the detector, names architect review (and possibly Source
   ratification) as the resolver, and requires an integration-branch
   diff and re-validated tests as evidence.
4. **Given** an agent attempts to modify identity, authority matrix,
   `.github/`, redaction gate, CI/deploy settings, or ratification
   semantics without approval, **When** the operating model (or future
   substrate validators per Feature 001) is consulted on the attempt,
   **Then** the taxonomy classifies this as an authority conflict, the
   operating model directs a hard-stop pending Source ratification, and
   requires the offending change to be reverted if not ratified.

---

### User Story 8 - Source-of-Truth Hierarchy Is Defined While Feature 001 Matures (Priority: P2)

A reader MUST be able to identify, for any Creator Engine concept that
appears in both Feature 001 and Feature 002 (mutation classes, authority
matrix, attestation records, ratification flow, identity model), which
artifact is authoritative. Feature 002 docs MUST defer to Feature 001
contracts where they overlap; if Feature 002 requires a substrate concept
that Feature 001 has not yet shipped, the doc MUST flag the dependency
rather than invent a competing contract.

**Why this priority**: Feature 001 and Feature 002 are intentionally
parallel work tracks (law and civilization). Without an explicit hierarchy,
the canonical docs risk drifting from the substrate contracts, and the
substrate validators risk pointing at concepts that the docs have
silently redefined.

**Independent Test**: A reviewer picks any concept that appears in both
Feature 001 artifacts and Feature 002 docs (e.g., the mutation-class
taxonomy or the spec status lifecycle), reads both, and confirms that
Feature 002 references Feature 001 as the authority rather than restating
or redefining the contract.

**Acceptance Scenarios**:

1. **Given** the source-of-truth hierarchy, **When** a reviewer asks
   "what is the order of precedence?", **Then** it is:
   constitution (`.specify/memory/constitution.md`) > Feature 001
   governance substrate artifacts (when ratified) > Feature 002
   canonical docs > tenant fixtures (`tenants/<name>/`) > working notes
   and handoffs.
2. **Given** a Feature 002 canonical document that needs to describe the
   mutation-class taxonomy, **When** the document is read, **Then** it
   MUST reference the Feature 001 mutation-class contract as
   authoritative; it MUST NOT redefine the baseline classes or their
   action vocabulary.
3. **Given** Feature 002 requires a concept that Feature 001 has not yet
   shipped (for example, a release-attestation schema), **When** the
   relevant canonical document is read, **Then** the document MUST flag
   the dependency on a future feature (e.g., Feature 006) rather than
   invent a competing contract.

---

### User Story 9 - Phase 1 vs Phase 2 Autonomy Boundaries Are Explicit (Priority: P2)

A reader MUST be able to identify, for every SDLC state transition, whether
it is Phase 1 (assignment-based, ratification-heavy, every privileged gate
human-ratified) or Phase 2-eligible (autonomy expansion target: low-risk
auto-merge, autonomous batch pulling, policy-bound automation). Feature 002
defines the boundary; Feature 002 does NOT implement Phase 2 expansion. A
transition that has not been ratified for Phase 2 MUST remain Phase 1 only.

**Why this priority**: Without an explicit phase boundary, future work
risks either freezing Creator Engine permanently in Phase 1 (downgrading
agents below human capability) or auto-promoting transitions into Phase 2
without ratification. The boundary forces every autonomy expansion to be
an explicit, ratified decision.

**Independent Test**: A reviewer reads the Phase 1/Phase 2 section and,
for any chosen transition from the SDLC state machine, can state whether
the transition is currently Phase 1 only and what conditions would have
to be met (ratified policy, evidence trail) to make it Phase 2 eligible.

**Acceptance Scenarios**:

1. **Given** the Phase 1/Phase 2 section, **When** a reviewer asks "what
   does Phase 1 mean operationally?", **Then** the spec answers:
   assignment-based dispatch via Hermes-prepared envelopes, human
   ratification of every privileged gate, Source merges (or Hermes
   merges only after explicit Source authorization), Claude does not
   self-assign, Codex does not ratify.
2. **Given** the Phase 1/Phase 2 section, **When** a reviewer asks "what
   does Phase 2 mean operationally?", **Then** the spec answers:
   expanded autonomy bounded by ratified policy (e.g., low-risk auto-
   merge if CI passes, Codex passes, mutation class is non-privileged,
   no governance/identity/security/deploy changes, PR matches approved
   task) and autonomous batch-pulling under named conditions; the spec
   names these as targets, not as implemented behavior.
3. **Given** any specific SDLC state transition, **When** a reviewer
   consults the operating model, **Then** the transition is labelled
   `Phase 1` or `Phase 2-eligible`; transitions involving privileged
   mutation classes (deploy, governance, identity, security,
   attestation, redaction) MUST remain Phase 1 in Feature 002.
4. **Given** the Phase 1/Phase 2 section, **When** a reviewer looks for
   Phase 2 implementation, **Then** the spec confirms Phase 2 expansion
   is OUT OF SCOPE for Feature 002 and will be addressed by a later
   feature explicitly ratified for autonomy expansion.

---

### User Story 10 - Automation Deferrals Are Explicit (Priority: P3)

A reader MUST be able to read, in Feature 002, the explicit list of
automation surfaces that are deferred to later features, so that the
absence of those surfaces in v0.1-docs is understood as intentional
sequencing rather than oversight. Specifically: GitHub Actions / CI
workflows are deferred to Feature 003; Codex/QA/release governed
identities to Feature 004; dispatcher/worktree runtime to Feature 005;
release/deploy automation to Feature 006.

**Why this priority**: Without an explicit deferrals section, readers may
assume Creator Engine's roadmap is missing CI, QA, dispatch, or release
governance; with the deferrals section, the v0.1-docs scope is clearly
the operating model layer that future automation features must obey.

**Independent Test**: A reviewer reads the deferrals section and can
state, for each named surface (CI, Codex/QA, dispatcher, release/deploy),
which future feature owns it and why Feature 002 does not.

**Acceptance Scenarios**:

1. **Given** the deferrals section, **When** a reviewer looks for
   `.github/` workflows in Feature 002, **Then** they find a deferral
   to Feature 003 with a one-sentence rationale; no `.github/` content
   is authored in Feature 002.
2. **Given** the deferrals section, **When** a reviewer looks for Codex
   or QA or release agent identity records, **Then** they find a
   deferral to Feature 004 (Codex/QA) or Feature 006 (release); the
   roles appear in the actor/tool ownership table as named-but-not-yet-
   instantiated.
3. **Given** the deferrals section, **When** a reviewer looks for a
   worktree or sandbox dispatcher implementation, **Then** they find a
   deferral to Feature 005; Feature 002 specifies the parallel-agent
   development model that the future dispatcher must obey, but the
   dispatcher itself is not built.
4. **Given** the deferrals section, **When** a reviewer looks for
   release/deploy gates, **Then** they find a deferral to Feature 006;
   Feature 002 specifies the SDLC states from `Release Candidate
   Created` through `Post-release Evidence Recorded` as Phase 1 only,
   without authoring release/deploy automation.

---

### Edge Cases

- A document already exists at a canonical path with different content from
  what Feature 002 specifies (for example, a pre-existing top-level
  `README.md`): Feature 002 MUST state how that document is reconciled —
  the canonical-doc-set spec applies on the next authoring pass; pre-
  existing content is treated as draft material for that pass, not as a
  competing contract.
- A canonical document specified by Feature 002 needs to reference a
  Feature 001 concept that is still in `draft` status at Feature 001's
  lifecycle: the document MUST cite the Feature 001 artifact by path and
  mark the dependency as pending Feature 001 ratification; the document
  MUST NOT silently advance past the Feature 001 lifecycle.
- A Hermes operator authors an Assignment Envelope and then attempts to
  consume it (e.g., the same human operating both panes): Feature 002
  MUST require role separation, not just session separation — the
  envelope records distinct author and consumer actor ids, and the
  operating model MUST require future envelope schemas and validators to
  treat an envelope whose author == consumer as malformed.
- Two Assignment Envelopes claim overlapping file globs: the conflict
  taxonomy classifies this as a file/task ownership conflict; the
  envelopes MUST either be serialized or an explicit integration
  dependency MUST be declared before any consumer may begin work.
- A future Phase 2 promotion is proposed: the proposal MUST itself be a
  ratified change to the operating model (specifically, to the Phase 1/2
  boundary table); operating-model amendment follows the same governance
  rules as any other privileged mutation.
- A canonical document specified by Feature 002 would, if authored,
  duplicate a Spec Kit substrate file: Feature 002 MUST favor referring
  to the Spec Kit substrate rather than restating it (preserving
  principle X, Spec Kit compatibility).
- An attempt is made to consume an Assignment Envelope after its stop
  conditions have been satisfied: the operating model MUST require the
  envelope be re-issued (a new envelope id, fresh approval) rather than
  reused; envelopes are single-use authorizations.
- A `/speckit-implement` invocation is observed outside an envelope (for
  example, an operator forgets the envelope): the operating model
  classifies this as an authority conflict, requires hard-stop, and
  requires Source ratification before any resulting changes may merge.

## Requirements *(mandatory)*

### Functional Requirements

**SDLC state machine**

- **FR-001**: Feature 002 MUST specify the canonical Creator Engine SDLC
  state machine containing exactly the following states in order:
  `Idea/Intent`, `Discovery`, `PRD Drafted`, `PRD Ratified`,
  `Architecture Drafted`, `Architecture Ratified`, `Feature Spec
  Drafted`, `Spec Clarified`, `Plan Drafted`, `Tasks Generated`, `Batch
  Approved`, `Agent Assigned`, `Worktree Created`, `Implementation
  Complete`, `Local Validation Complete`, `Attestation Drafted`,
  `Independent Review Complete`, `CI Evidence Complete`, `Scope Audit
  Complete`, `Ratification Complete`, `Merge Approved`, `Release
  Candidate Created`, `Deployment Approved`, `Deployment Complete`,
  `Post-release Evidence Recorded`.
- **FR-002**: For each transition in the SDLC state machine, Feature 002
  MUST name the responsible actor/tool (one of: Source, Nefarious/Hermes,
  Claude Code, Codex, future QA/security/release agent, CI, GitHub) and
  the gate that authorizes the transition (e.g., Definition of Ready,
  Definition of Done, attestation completeness, Source ratification, CI
  pass).
- **FR-003**: Feature 002 MUST label each SDLC state transition as either
  `Phase 1` (assignment-based, human-ratified) or `Phase 2-eligible`
  (autonomy expansion target). Privileged transitions (those touching
  the mutation classes named in FR-008: `deploy`, `governance`,
  `identity`, `security`, `attestation`, `redaction`) MUST remain Phase
  1 in Feature 002 regardless of any future Phase 2-eligible labelling.
- **FR-004**: Feature 002 MUST relate the SDLC state machine to the
  Feature 001 six-state spec lifecycle (`draft → ready → in_progress →
  verified → ratified → done`): Feature 002 MUST identify which Feature
  001 lifecycle states correspond to which SDLC states, MUST defer to
  the Feature 001 lifecycle as authoritative where they overlap, and
  MUST NOT redefine Feature 001's lifecycle transitions.

**Assignment Envelope**

- **FR-005**: Feature 002 MUST define the Assignment Envelope as the
  governed unit of agent work. The envelope schema MUST require, at
  minimum: `envelope_id`, `spec_ref`, `feature_branch`, `worktree_path`,
  `approved_task_batch` (task IDs or file globs), `allowed_mutation_
  classes` (drawn from the Feature 001 baseline taxonomy and any
  ratified tenant extensions), `prohibited_surfaces` (paths or
  globs), `required_validation` (commands), `evidence_requirements`,
  `stop_conditions`, `prohibited_external_actions`, `conflict_policy`
  (rebase/merge/conflict-resolution authority and escalation rules),
  `created_by_actor_id` (author, MUST be the Hermes role), and
  `consuming_actor_id` (consumer, MUST be a Claude Code role or other
  approved implementer role).
- **FR-006**: The Assignment Envelope MUST be subject to author/approver
  separation: `created_by_actor_id` and `consuming_actor_id` MUST be
  distinct. The operating model MUST require future envelope schemas
  and validators (instantiated by Feature 001 or a later feature) to
  reject envelopes where author == consumer as malformed. Feature 002
  does not implement the validator; it specifies the requirement the
  validator must enforce.
- **FR-007**: The Assignment Envelope MUST be single-use: an envelope
  whose stop conditions have been satisfied MUST NOT be reused; a new
  envelope (new id, fresh approval) MUST be issued for any subsequent
  batch.
- **FR-008**: Where the Assignment Envelope's `allowed_mutation_classes`
  declare any class that the Feature 001 contract reserves for human
  ratification (`deploy`, `governance`, `identity`, `security`,
  `attestation`, `redaction`), the envelope itself MUST require Source
  ratification before any consumer may begin work on it.

**`/speckit-implement` policy**

- **FR-009**: Feature 002 MUST state that, once Feature 002 is ratified,
  `/speckit-implement` is the mandatory implementation command for
  Creator-Engine-governed work, and MUST be invoked only inside a
  Hermes-authored Assignment Envelope. Out-of-envelope
  `/speckit-implement` invocation MUST be classified by the operating
  model as an authority conflict (FR-018); the operating model MUST
  require future enforcement (dispatcher Feature 005, CI Feature 003,
  and Hermes audit) to hard-stop such invocations pending Source
  ratification. Feature 002 does not implement that enforcement; it
  specifies the policy enforcement must obey.
- **FR-010**: Feature 002 MUST enumerate the actions
  `/speckit-implement` is permitted to take inside an envelope (read
  approved spec/plan/tasks artifacts, edit code/tests within the
  envelope's allowed mutation classes, run required validation, mark
  tasks `[X]` only after local validation, report evidence) and the
  actions it MUST NOT take absent envelope-level authorization (commit,
  push, open PR, merge, close ticket, deploy, alter secrets, alter
  governance, alter identity, expand mutation class set, mutate
  surfaces declared prohibited).
- **FR-011**: Feature 002 MUST state that Claude Code MUST NOT
  self-assign envelopes; Hermes authors/scopes envelopes, Claude
  consumes them, and Source ratifies privileged integration.

**Actor/tool ownership model**

- **FR-012**: Feature 002 MUST publish an actor/tool ownership table that
  names, for each of `Source`, `Nefarious/Hermes`, `Claude Code`,
  `Codex`, future `QA agent`, future `security agent`, future `release
  agent`, `CI`, and `GitHub`: allowed instruction sources, allowed
  mutation classes (referencing the Feature 001 taxonomy), allowed
  communication surfaces, required ratifier, and required audit
  artifacts.
- **FR-013**: The actor/tool ownership table MUST state the invariant
  that CI verifies but does NOT ratify, and that agent-authored review
  text MUST NOT count as ratification for the privileged mutation
  classes named in FR-008. For non-privileged classes, agent review
  text MAY be recorded as review evidence per the Feature 001
  authority matrix.
- **FR-014**: The actor/tool ownership table MUST distinguish three
  states of presence in Feature 002:
  - **Operationally active**: `Source`, `Nefarious/Hermes`, and
    `Claude Code` — roles whose behavior is required by the operating
    model right now and whose identity records are governed by Feature
    001 contracts when those are ratified.
  - **Named in the operating model; governed identity record
    deferred**: `Codex`, `QA agent`, `security agent`, `release agent`
    — Feature 002 specifies their roles, surfaces, ratification
    boundary, and evidence responsibilities, but their governed
    identity records (per Feature 001's identity contract) are
    deferred to later features (Codex/QA/security: Feature 004;
    release: Feature 006). Naming an actor in the operating model is
    not the same as instantiating its governed identity record.
  - **Named as tool/system; automation deferred**: `CI` and `GitHub`
    — Feature 002 specifies the policy these tools must obey
    (verifies-not-ratifies, merge mechanics vs. ratification
    separation), but their automation (`.github/` workflows, branch
    protection, PR templates, CI checks, deploy automation) is
    deferred to Feature 003 (CI/branch-protection/PR templates) and
    Feature 006 (deploy environments).

**Parallel-agent development model**

- **FR-015**: Feature 002 MUST specify the parallel-agent development
  model under which Creator Engine governs (not prevents) parallel
  agent work: one driver per physical worktree, multiple writers
  allowed via isolated branches/worktrees/envelopes with non-overlapping
  scope (or an explicit declared integration dependency), and
  serialized Source-ratified canonical-branch integration.
- **FR-016**: Feature 002 MUST state that the temporary "one writer
  globally" rule from the May 10 coordination incident is NOT the
  permanent model; the permanent model is "many isolated writers, one
  governed integration path".

**Conflict taxonomy**

- **FR-017**: Feature 002 MUST specify a conflict taxonomy with exactly
  four classes — `textual`, `file/task ownership`, `semantic`, and
  `authority` — each declaring (a) how the conflict is detected, (b)
  who resolves it, and (c) what evidence the resolution must produce.
- **FR-018**: The `authority` conflict class MUST hard-stop work and
  require Source ratification before resolution; agent attempts to
  mutate identity, authority matrix, `.github/`, redaction gate, CI or
  deploy settings, ratification semantics, or any other privileged
  surface absent explicit ratification MUST be classified here.

**Source-of-truth hierarchy**

- **FR-019**: Feature 002 MUST publish the source-of-truth hierarchy:
  constitution (`.specify/memory/constitution.md`) > Feature 001
  governance substrate artifacts (when ratified) > Feature 002 canonical
  docs > tenant fixtures (`tenants/<name>/`) > working notes and
  handoffs.
- **FR-020**: Feature 002 canonical docs MUST defer to Feature 001
  contracts where the concepts overlap (mutation-class taxonomy,
  authority matrix, attestation record format, ratification flow,
  identity model). Feature 002 docs MUST NOT redefine Feature 001
  contracts.
- **FR-021**: Where a Feature 002 canonical doc requires a concept that
  Feature 001 has not yet shipped, the doc MUST flag the dependency
  (citing the future feature) rather than invent a competing contract.

**Canonical document set**

- **FR-022**: Feature 002 MUST specify the canonical document set under
  the project's documentation roots. The set MUST contain exactly the
  17 documents enumerated in `Key Entities → Canonical Document Set`
  below. The parallel-agent development model is kept as a separate
  document, `docs/architecture/parallel-agent-development-model.md`,
  rather than folded into `docs/architecture/agentic-sdlc-operating-
  model.md`. Rationale: User Story 6 promotes parallel-agent
  development to a first-class operating-model concern (one driver
  per worktree, isolated writers via separate branches/worktrees,
  conflict-class linkage, explicit correction of the temporary May 10
  freeze rule). Co-locating this content with the SDLC state machine
  would either swell `agentic-sdlc-operating-model.md` past the size at
  which it remains a single readable document, or force readers
  interested only in parallelization to also load the full state
  machine. A dedicated document keeps each architecture doc focused
  and cross-linkable.
- **FR-023**: For each canonical document, Feature 002 MUST specify:
  (a) the document's purpose in one sentence, (b) its required
  sections, (c) its source-of-truth relationship to Feature 001
  contracts (deferral, summary, reference), and (d) acceptance criteria
  for "exists and is sufficient" stated in terms of section
  completeness, not file existence.
- **FR-024**: Feature 002 MUST NOT author the canonical document
  bodies; only the specifications of those documents. Authoring is the
  implementation phase that follows Feature 002 ratification.

**Automation deferrals**

- **FR-025**: Feature 002 MUST explicitly defer the following automation
  surfaces, naming the future feature that will own each:
  - `.github/` workflows, CI validation checks, PR templates, branch
    protection: Feature 003 (GitHub CI Governance).
  - Codex reviewer identity, QA agent identity, review evidence
    schema, QA evidence schema: Feature 004 (Independent Review / QA
    Agent Evidence).
  - Hermes dispatcher, worktree lifecycle automation, sandboxing, safe
    parallelization runtime: Feature 005 (Dispatch / Worktree / Sandbox
    Runtime).
  - Release records, deploy attestations, rollback evidence, GitHub
    environments, Source-approved deploy gates: Feature 006 (Release /
    Deployment Governance).
- **FR-026**: Feature 002 MUST state that v1.0 (full governed agentic
  SDLC loop) is OUT OF SCOPE of Feature 002; v1.0 is the integration
  target the operating model points toward.

**Phase 1 vs Phase 2 autonomy**

- **FR-027**: Feature 002 MUST define Phase 1 as: assignment-based
  dispatch via Hermes-prepared envelopes, human ratification of every
  privileged gate, Source merges (or Hermes merges only after explicit
  Source authorization), Claude does not self-assign, Codex does not
  ratify.
- **FR-028**: Feature 002 MUST define Phase 2 as: expanded autonomy
  bounded by ratified policy (low-risk auto-merge under named
  conditions, autonomous batch-pulling under named conditions). Feature
  002 MUST NOT implement Phase 2 expansion; Phase 2 promotion is itself
  a ratified amendment to the operating model.

**Operating-model governance**

- **FR-029**: Amendments to the Feature 002 operating model (SDLC state
  machine, Assignment Envelope schema, actor/tool ownership, parallel-
  agent model, conflict taxonomy, source-of-truth hierarchy, canonical
  doc set, automation deferrals, Phase 1/2 boundary) MUST follow the
  Creator Engine constitution's amendment procedure: spec/plan/tasks
  triple, Source-approval, repo-visible record.
- **FR-030**: Feature 002 MUST itself be a Creator-Engine-governed
  spec: it is subject to the constitution at
  `.specify/memory/constitution.md` and to the Feature 001 governance
  contracts (once ratified). Feature 002 does not modify Feature 001
  artifacts.

### Key Entities *(include if feature involves data)*

- **SDLC State Machine**: the named, ordered set of 25 states
  (`Idea/Intent` through `Post-release Evidence Recorded`) and their
  transitions. Each transition has a responsible actor/tool, a
  gate, and a Phase 1 / Phase 2-eligible label. The state machine
  is the backbone the operating model is hung on.

- **Assignment Envelope**: the governed unit of agent work, recorded
  as a YAML document under a tenant-declared envelope directory. Fields
  per FR-005. Single-use (FR-007), author/approver-separated (FR-006),
  Source-ratified for privileged mutation classes (FR-008). The
  envelope is the precondition for `/speckit-implement` (FR-009).

- **Actor/Tool Ownership Entry**: one row of the actor/tool ownership
  table naming an actor or tool and stating its allowed instruction
  sources, allowed mutation classes, allowed communication surfaces,
  required ratifier, and required audit artifacts.

- **Conflict Class**: one of `textual`, `file/task ownership`,
  `semantic`, or `authority`. Each class carries a detector, a
  resolver, and a required evidence artifact.

- **Source-of-Truth Hierarchy**: the ordered precedence list
  constitution > Feature 001 substrate (ratified) > Feature 002 docs >
  tenant fixtures > working notes. Used to resolve any apparent
  conflict between artifacts.

- **Phase 1 / Phase 2 Boundary**: the table that labels each SDLC
  transition with its current autonomy phase. Privileged transitions
  remain Phase 1 in Feature 002; Phase 2 promotion requires a
  ratified operating-model amendment.

- **Canonical Document Set**: the exact list of canonical Creator
  Engine documents specified (not authored) by Feature 002. The set is:
  - `README.md` (top-level)
  - `docs/product/PRD.md`
  - `docs/product/ROADMAP.md`
  - `docs/product/REQUIREMENTS.md`
  - `docs/architecture/SAD.md`
  - `docs/architecture/agentic-sdlc-operating-model.md`
  - `docs/architecture/agent-interaction-model.md`
  - `docs/architecture/integration-map.md`
  - `docs/architecture/parallel-agent-development-model.md` *(kept as
    a separate document per FR-022; rationale recorded there)*
  - `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`
  - `docs/governance/MUTATION_CLASS_MODEL.md`
  - `docs/governance/ATTESTATION_MODEL.md`
  - `docs/quality/QA_STRATEGY.md`
  - `docs/quality/TESTING_STRATEGY.md`
  - `docs/devops/CI_CD_STRATEGY.md`
  - `docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`
  - `docs/security/SECURITY_MODEL.md`
  Each document carries a purpose, required sections, source-of-truth
  relationship to Feature 001 (deferral, summary, or reference), and
  acceptance criteria framed in terms of section completeness per
  FR-023.

- **Automation Deferral Entry**: a row in the deferrals table naming
  an automation surface (e.g., `.github/`, Codex identity,
  dispatcher, release/deploy automation), the future feature that
  owns it (Features 003 through 006), and the one-sentence rationale
  for the deferral.

## SDLC Transition Matrix *(normative)*

The 25 SDLC states (FR-001) produce exactly 24 transitions. The matrix
below is normative: every transition has a `responsible actor/tool`, an
`authorizing gate`, a `phase` label, and a `required evidence` artifact.
Phase labels follow FR-003: privileged transitions (those touching the
mutation classes named in FR-008) remain `Phase 1` in Feature 002
regardless of any future Phase 2-eligible labelling. Where a transition
is `Phase 1 (Phase 2-eligible target)`, the label means "Phase 1 today;
the transition is a candidate for autonomy expansion only after a future
feature ratifies a Phase 2 policy that names it".

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

- The matrix, not this prose note, is normative. Every transition is
  labelled. Transitions whose `phase` cell reads `Phase 1 (privileged
  — remains Phase 1)` carry a privileged mutation class per FR-008 and
  remain Phase 1 in Feature 002 regardless of any future Phase 2
  ratification. Transitions whose `phase` cell carries a
  `Phase 2-eligible target` annotation are candidates for future
  autonomy expansion under named conditions; the label is a planning
  marker, not a permission.
- Phase 2 expansion is OUT OF SCOPE for Feature 002 per FR-028.

## Actor / Tool Ownership Matrix *(normative)*

This matrix is normative for FR-012 through FR-014 and for SC-004.
Each entry names one actor or tool and populates the **five required
FR-012/SC-004 fields** — `Allowed instruction sources`, `Allowed
mutation classes`, `Allowed communication surfaces`, `Required
ratifier`, `Required audit artifacts` — plus the supplemental
authority/prohibition fields `Phase 1 authority`, `Phase 2-eligible
authority`, and `Prohibited actions` that complete the operating-model
picture. Each entry also carries a `Presence category` declaring
whether the actor/tool is operationally active, named with identity
record deferred, or named with automation deferred, per FR-014.

### Source

- **Presence category**: operationally active.
- **Allowed instruction sources**: Source's own product judgment; the
  Creator Engine constitution; ratified operating-model amendments.
  Source takes no governance instruction from agents.
- **Allowed mutation classes**: all baseline classes (`docs`, `code`,
  `schema`, `deploy`, `governance`, `identity`, `security`,
  `attestation`, `redaction`); Source personally ratifies every
  privileged class enumerated in FR-008.
- **Allowed communication surfaces**: ratification records (YAML per
  Feature 001 FR-020a); commit messages on Source-authored or
  Source-approved commits; PR review comments where the Feature 001
  authority matrix designates that surface as a ratification surface
  for the relevant mutation class; explicit Source approvals recorded
  in repository artifacts.
- **Required ratifier**: none (Source is the apex ratifier). Author/
  approver separation per Feature 001 FR-007 still applies: Source
  MUST NOT ratify Source's own authored mutation; a second authorized
  actor is required.
- **Required audit artifacts**: ratification records (YAML, per
  Feature 001 FR-016 and FR-020a) identifying the mutation, mutation
  class, evidence reviewed, decision, and date.
- **Phase 1 authority**: final ratifier for the privileged mutation
  classes named in FR-008 (`deploy`, `governance`, `identity`,
  `security`, `attestation`, `redaction`); ratifier of PRDs (T3),
  architecture (T5), task batches (T10), envelopes touching privileged
  classes (FR-008), canonical-branch merge (T19/T20), and deploy
  (T22).
- **Phase 2-eligible authority**: identical to Phase 1. Source
  ratification is the human anchor and is not subject to Phase 2
  autonomy expansion.
- **Prohibited actions**: ratifying Source's own authored work
  (author/approver separation per Feature 001 FR-007); approving
  privileged changes without recorded evidence (Feature 001 FR-014).

### Nefarious / Hermes

- **Presence category**: operationally active.
- **Allowed instruction sources**: Source approvals (batch approvals,
  envelope ratifications, operating-model amendments); the Feature 001
  governance substrate; the Feature 002 operating model itself.
- **Allowed mutation classes**: `docs`, `code`, `schema`, `attestation`
  (drafting only; ratification remains Source's), and `governance` only
  when the specific governance change has been Source-ratified.
  Hermes operates strictly within approved batch scope and cannot
  expand the class set unilaterally.
- **Allowed communication surfaces**: Assignment Envelope YAML files
  (as author); branch and worktree commits within approved batches;
  PR descriptions and review comments; pre-merge attestation drafts;
  scope audit summaries; the orchestrator audit ledger
  (`.hermes/ledger.md` / `.hermes/handoffs/`).
- **Required ratifier**: Source for any privileged mutation class
  (FR-008) and for canonical-branch integration; otherwise per the
  Feature 001 authority matrix. Hermes is never the ratifier of its
  own authored work (Feature 001 FR-007).
- **Required audit artifacts**: Assignment Envelopes (author =
  Hermes), scope audit summaries, attestation drafts, verification
  logs, integration evidence, envelope-vs-diff reconciliation
  records.
- **Phase 1 authority**: orchestrator and auditor; authors Assignment
  Envelopes (T11); creates branches and worktrees (T12); performs
  independent verification (T14–T18); generates attestation drafts
  (T15); runs scope audits (T18); opens PRs only after verification;
  enforces approval gates.
- **Phase 2-eligible authority**: under a future Source-ratified
  Phase 2 policy may execute low-risk auto-merge of non-privileged
  classes (FR-028); may automate textual conflict resolution per the
  conflict taxonomy; never auto-ratifies privileged classes.
- **Prohibited actions**: consuming an envelope that Hermes authored
  (FR-006); ratifying own work; merging privileged-class changes
  without explicit Source authorization; weakening governance,
  identity, security, attestation, or redaction gates; expanding
  envelope scope unilaterally.

### Claude Code

- **Presence category**: operationally active.
- **Allowed instruction sources**: Hermes-authored Assignment
  Envelopes (FR-005); the Spec Kit slash commands invocable inside the
  envelope's scope; Source clarifications routed through the envelope
  or through the spec's Clarifications section.
- **Allowed mutation classes**: only those declared in the active
  envelope's `allowed_mutation_classes` field; baseline candidates are
  `docs`, `code`, `schema`, and `code`-subset tests; privileged
  classes are permitted only when the envelope itself has been
  Source-ratified per FR-008.
- **Allowed communication surfaces**: code and test edits in the
  envelope's worktree; the tmux session in which the envelope is
  dispatched; evidence reports returned to Hermes; task-completion
  markers `[X]` written into `tasks.md` only after local validation.
- **Required ratifier**: Hermes verifies (T14–T18) and, for any
  privileged class, Source ratifies (FR-008). Claude Code never
  ratifies anything.
- **Required audit artifacts**: validator output, test logs,
  changed-file list, in-scope confirmation, evidence inputs that feed
  the attestation record Hermes drafts at T15.
- **Phase 1 authority**: primary implementation agent; consumes
  envelopes (T13); invokes `/speckit-implement` only inside a
  Hermes-authored envelope (FR-009); runs local validation (T14);
  reports evidence.
- **Phase 2-eligible authority**: under a future Source-ratified
  Phase 2 policy may pull approved batches autonomously for
  non-privileged classes (FR-028); never auto-ratifies; never merges
  privileged-class changes.
- **Prohibited actions**: self-assigning envelopes; invoking
  `/speckit-implement` outside an envelope (FR-009); ratifying own
  work; merging; altering secrets, governance, identity, attestation,
  or redaction gates; expanding the mutation-class set; mutating
  prohibited surfaces; commit/push/PR/deploy absent envelope-level
  authorization (FR-010).

### Codex

- **Presence category**: named in the operating model; governed
  identity record deferred to Feature 004.
- **Allowed instruction sources**: Hermes-authored review-only or
  fallback-implementation envelopes (the fallback variant only in a
  separate worktree where Claude is not the active consumer); Feature
  002 operating-model directives describing Codex's review role.
- **Allowed mutation classes**: `docs` (review findings); `code`
  only when a fallback envelope explicitly authorizes implementation
  in a separate Codex-only worktree.
- **Allowed communication surfaces**: review findings records (schema
  deferred to Feature 004); PR review comments recorded as review
  evidence (never ratification); a separate Codex-fallback worktree
  when explicitly assigned.
- **Required ratifier**: Codex never ratifies. For fallback
  implementation: Hermes verifies and Source ratifies any privileged
  mutation classes; otherwise per the Feature 001 authority matrix
  once Feature 004 instantiates Codex's identity record.
- **Required audit artifacts**: review-findings records (schema
  deferred to Feature 004); these records are attestation evidence
  inputs, never ratification records.
- **Phase 1 authority**: independent reviewer; reads diffs, surfaces
  findings, may implement fallback only in a separate worktree under
  an envelope that explicitly authorizes fallback implementation
  (Codex never writes to a worktree where Claude is the active
  consumer).
- **Phase 2-eligible authority**: under a future Source-ratified
  policy, Codex review evidence may be a precondition for auto-merge
  of non-privileged classes (FR-028); Codex never ratifies privileged
  classes regardless of phase.
- **Prohibited actions**: writing to the active Claude worktree;
  opening tickets; merging PRs; ratifying product, strategic,
  trading-risk, or governance decisions; overriding Source.

### QA agent

- **Presence category**: named in the operating model; governed
  identity record deferred to Feature 004.
- **Allowed instruction sources**: Hermes-authored QA envelopes
  (defined once Feature 004 instantiates the role); QA gate
  definitions referenced from Feature 002 QA_STRATEGY.md.
- **Allowed mutation classes**: `docs` (QA evidence records and
  triage notes); never `code`, `schema`, or any privileged class; QA
  agent never mutates source.
- **Allowed communication surfaces**: QA evidence records (schema
  deferred to Feature 004); test result logs; flaky-test triage
  notes; release-readiness check results attached to a PR or
  attestation.
- **Required ratifier**: Hermes verifies QA evidence presence;
  Source ratifies any change that weakens a QA gate (a
  governance-class privileged mutation per FR-008). QA agent itself
  never ratifies.
- **Required audit artifacts**: QA evidence records (schema deferred
  to Feature 004) linked to the SDLC transition the QA pass
  authorizes.
- **Phase 1 authority**: deferred to Feature 004 for instantiation;
  Feature 002 names the role and reserves its surfaces.
- **Phase 2-eligible authority**: under a future Source-ratified
  policy, QA evidence pass may be a precondition for auto-merge of
  non-privileged classes; QA never ratifies privileged classes.
- **Prohibited actions**: ratifying QA gates for privileged classes;
  merging; weakening QA gates; consuming envelopes outside the
  envelope-scoped QA work range.

### security agent

- **Presence category**: named in the operating model; governed
  identity record deferred to Feature 004.
- **Allowed instruction sources**: Hermes-authored security envelopes
  (defined once Feature 004 instantiates the role); the security
  policy in Feature 002 SECURITY_MODEL.md; Feature 001 redaction-
  gate policy (FR-019, FR-020).
- **Allowed mutation classes**: `docs` (security finding records,
  vulnerability reports); never the `security` mutation class itself
  (Source-only per FR-008); never `code`, `schema`, or any privileged
  class.
- **Allowed communication surfaces**: security finding records
  (schema deferred to Feature 004); vulnerability reports;
  redaction-gate scan results.
- **Required ratifier**: Source for any change to security or
  redaction policy (privileged per FR-008); Hermes verifies
  finding-evidence presence. The security agent itself never
  ratifies.
- **Required audit artifacts**: security finding records (schema
  deferred to Feature 004) linked to the SDLC transition or
  mutation class they evaluate.
- **Phase 1 authority**: deferred to Feature 004 for instantiation.
- **Phase 2-eligible authority**: under a future Source-ratified
  policy, security scan pass may become an auto-merge precondition
  for non-privileged classes; security agent never ratifies the
  `security` mutation class (Source-only per FR-008).
- **Prohibited actions**: ratifying `security`, `governance`,
  `identity`, `attestation`, or `redaction` mutation classes
  (Source-only); merging; weakening security or redaction gates;
  exporting tenant data outside the redaction-gate policy
  (Feature 001 FR-019).

### release agent

- **Presence category**: named in the operating model; governed
  identity record deferred to Feature 006.
- **Allowed instruction sources**: Hermes-authored release envelopes
  (defined once Feature 006 instantiates the role); Source-ratified
  deploy approvals (T22); Feature 002
  RELEASE_AND_DEPLOYMENT_STRATEGY.md.
- **Allowed mutation classes**: `docs` (release notes, post-release
  evidence); `deploy` only for execution under a Source-ratified
  deploy approval (release agent never ratifies the `deploy` class
  itself — Source-only per FR-008).
- **Allowed communication surfaces**: release tags; deploy logs;
  deploy attestations; rollback evidence; post-release evidence
  records (schema deferred to Feature 006).
- **Required ratifier**: Source for `deploy` and any release/deploy
  policy change (privileged per FR-008); Hermes audits deploy
  evidence and post-release finalization. The release agent itself
  never ratifies.
- **Required audit artifacts**: deploy attestations, rollback
  evidence records, post-release attestation finalizations (schema
  deferred to Feature 006) linked to T22–T24.
- **Phase 1 authority**: deferred to Feature 006 for instantiation.
  Until then, T21 and T24 are performed by Hermes acting under
  explicit Source authorization (T21), and T23/T24 await Feature 006
  instantiation.
- **Phase 2-eligible authority**: under a future Source-ratified
  policy and Source-approved deploy gates, may execute deploy steps
  after Source ratification of the deploy mutation; release agent
  never auto-ratifies deploy (Source-only per FR-008).
- **Prohibited actions**: ratifying deploy (Source-only); altering
  deploy or CI policy without Source ratification; weakening
  rollback or observability gates.

### CI

- **Presence category**: named as tool/system; `.github/` workflows
  and check definitions deferred to Feature 003.
- **Allowed instruction sources**: the workflow definitions ratified
  by Feature 003+ (deferred); CI receives no governance instruction
  from agents at runtime.
- **Allowed mutation classes**: none — CI does not mutate the
  repository. Status checks, CI logs, and validator output are
  evidence, not Creator Engine-classed mutations.
- **Allowed communication surfaces**: status checks; CI run logs;
  validator outputs; build artifacts. CI does not author governance
  comments.
- **Required ratifier**: Source ratifies any change to CI policy or
  workflow files (those changes are themselves a privileged
  `governance`/`security`/`deploy` mutation per FR-008). CI itself
  never ratifies.
- **Required audit artifacts**: status check records; CI run logs;
  validator outputs linked to T17.
- **Phase 1 authority**: mechanical validator. Runs tests, lint,
  typecheck, build, Creator Engine validator, schema validation when
  wired in Feature 003+. Verifies-not-ratifies invariant per FR-013.
- **Phase 2-eligible authority**: under a future Source-ratified
  Phase 2 policy, a CI pass may be a precondition for auto-merge of
  non-privileged classes; CI is never a ratifier regardless of
  phase.
- **Prohibited actions**: ratifying product correctness; ratifying
  strategic decisions; ratifying privileged mutation classes;
  mutating the repo (CI does not commit/push); changing branch
  protection or CI policy without Source ratification (those changes
  are themselves a `governance`/`deploy`/`security`-class privileged
  mutation).

### GitHub

- **Presence category**: named as tool/system; `.github/` content, PR
  templates, and branch protection deferred to Feature 003;
  environment gates deferred to Feature 006.
- **Allowed instruction sources**: protected-branch and PR-template
  ratifications under Feature 003+ (deferred);
  release/environment ratifications under Feature 006 (deferred).
  GitHub itself takes no governance instruction.
- **Allowed mutation classes**: none — GitHub provides PR/merge
  mechanics, not Creator Engine-classed mutations. Merges and tags
  are operations on the PR surface, not classified mutations.
- **Allowed communication surfaces**: PRs; comments; status checks;
  merges; release tags; environments; branch-protection settings
  (deferred).
- **Required ratifier**: Source for any change to branch protection,
  environment gates, or merge policy (those changes are themselves
  privileged `governance`/`deploy`/`security`-class mutations per
  FR-008). GitHub itself never ratifies.
- **Required audit artifacts**: PR records; merge commits; status
  check history; environment deployment records (when Feature 006
  wires environments).
- **Phase 1 authority**: source of truth for PRs, code review
  surfaces, merge mechanics, release tags, and environments. Branch
  protection, PR templates, and environment gates are deferred to
  Feature 003 (branch protection / PR templates) and Feature 006
  (deploy environments).
- **Phase 2-eligible authority**: GitHub mechanics are unchanged
  between phases; Phase 2 expansion lives in policy (auto-merge
  rules) rather than in GitHub itself.
- **Prohibited actions**: deciding governance authority; ratifying
  privileged mutation classes; substituting for human ratification.

## Canonical Document Specifications *(normative)*

This section is normative for FR-022, FR-023, and FR-024. The set is
exactly 17 documents (FR-022 keeps `parallel-agent-development-model.md`
separate). Each entry specifies: `path`, `purpose`, `required sections`,
`source-of-truth relationship to Feature 001`, and
`acceptance criteria for "exists and is sufficient"`. Acceptance
criteria are framed in terms of section completeness, not file
existence. Feature 002 does NOT author these documents; it specifies
them.

### 1. `README.md` (top-level)

- **Purpose**: One-page orientation that introduces Creator Engine and
  points readers to the canonical doc set, the constitution, and the
  Feature 001 governance substrate.
- **Required sections**: (a) what Creator Engine is, in one paragraph;
  (b) v0.1 scope summary (governance substrate + operating model);
  (c) repository layout overview; (d) index of all 17 canonical docs
  with one-line descriptions; (e) link to validators/README.md
  (Feature 001) for quickstart; (f) source-of-truth notice with link
  to `.specify/memory/constitution.md` and to the Feature 002 source-
  of-truth hierarchy.
- **Source-of-truth relationship**: REFERENCE — defers to constitution
  and Feature 001 contracts; never restates them.
- **Acceptance criteria**: README enumerates all 17 canonical doc
  paths; states v0.1 scope; states the source-of-truth hierarchy and
  amendment policy with links; contains no LIMITLESS-specific
  identifiers (Feature 001 FR-024); under 500 words excluding lists.

### 2. `docs/product/PRD.md`

- **Purpose**: Define Creator Engine's product vision, target tenants,
  problem statement, value proposition, primary use cases, non-goals,
  and version-scope summaries.
- **Required sections**: (a) product vision; (b) target tenants and
  users; (c) problem statement; (d) value proposition; (e) primary
  use cases; (f) explicit non-goals; (g) technology-agnostic success
  metrics; (h) version-scope summaries for v0.1, v0.2, v0.3, v0.4,
  v1.0 (cross-linked to ROADMAP.md).
- **Source-of-truth relationship**: REFERENCE — defers to ROADMAP for
  sequencing detail and to the operating model for SDLC mechanics.
- **Acceptance criteria**: every required section non-empty; non-goals
  enumerate at minimum CI automation (deferred Feature 003),
  Codex/QA/security identity records (deferred Feature 004),
  dispatcher runtime (deferred Feature 005), and release/deploy
  automation (deferred Feature 006); success metrics framed in terms
  of auditable mutations and ratifiable batches, not implementation
  metrics.

### 3. `docs/product/ROADMAP.md`

- **Purpose**: Sequence Features 001 through 006 and beyond toward
  v1.0, naming each feature's scope and deferral rationale.
- **Required sections**: (a) Feature 001 v0.1 governance substrate
  scope summary; (b) Feature 002 v0.1-docs operating model scope
  summary; (c) Feature 003 GitHub CI governance scope summary;
  (d) Feature 004 independent review / QA agent evidence scope
  summary; (e) Feature 005 dispatch / worktree / sandbox runtime
  scope summary; (f) Feature 006 release / deployment governance
  scope summary; (g) v1.0 end-to-end governed agentic SDLC loop as
  the integration target; (h) per-feature deferral rationale.
- **Source-of-truth relationship**: SUMMARY — summarizes Feature 001
  scope and forward-references the Features 003–006 scopes; never
  redefines them.
- **Acceptance criteria**: every feature 001–006 has a scope summary
  and a deferral rationale; v1.0 explicitly named as the integration
  target; sequencing matches Feature 002 FR-025 deferrals; no roadmap
  entry promises automation Feature 002 does not enable.

### 4. `docs/product/REQUIREMENTS.md`

- **Purpose**: Catalog load-bearing product requirements for Creator
  Engine v0.1-docs, with traceability from PRD problems to functional
  / operational requirements.
- **Required sections**: (a) requirement traceability summary;
  (b) functional product requirements; (c) non-functional product
  requirements (auditability, repo-native, offline validation per
  Feature 001 Principle II); (d) explicit non-requirements;
  (e) traceability map from product requirement to a Feature 001 FR
  id or a Feature 002 section anchor.
- **Source-of-truth relationship**: REFERENCE — defers to Feature 001
  FR-001 through FR-031 and to Feature 002 normative sections.
- **Acceptance criteria**: every load-bearing PRD problem has a
  tracing entry; traceability map links by id or anchor;
  non-requirements include automation surfaces deferred per FR-025.

### 5. `docs/architecture/SAD.md` (System Architecture Document)

- **Purpose**: Define Creator Engine's major components, data flows,
  storage model, integration boundaries, trust boundaries, and
  extension points.
- **Required sections**: (a) component inventory; (b) data flow
  across the SDLC; (c) repository-native storage model
  (Feature 001 FR-005, FR-020a); (d) integration boundaries (Spec
  Kit, GitHub, CI, trackers); (e) trust boundaries; (f) extension
  points (tenant fixtures, mutation-class extensions); (g) explicit
  dependencies on Feature 001 contracts; (h) explicit deferrals to
  Features 003–006.
- **Source-of-truth relationship**: REFERENCE — defers to Feature 001
  schemas/contracts for component shape and to the operating model
  doc for SDLC mechanics.
- **Acceptance criteria**: every component named in Feature 001
  (spec substrate adapter, identity registry, mutation taxonomy,
  authority matrix, validator, attestation store, etc.) appears;
  storage model section cites Feature 001 FR-005 and FR-020a; any
  new architecture concept absent from Feature 001 is flagged per
  FR-021.

### 6. `docs/architecture/agentic-sdlc-operating-model.md`

- **Purpose**: Canonicalize the SDLC state machine, transition
  matrix, gates, evidence flow, Phase 1/2 boundary, `/speckit-
  implement` policy, and Assignment Envelope linkage as a single
  reference document.
- **Required sections**: (a) the 25-state SDLC machine
  (FR-001); (b) the 24-transition matrix with actor/tool, gate,
  phase label, evidence (the `SDLC Transition Matrix` section of
  this spec); (c) Phase 1 / Phase 2 boundary policy
  (FR-003, FR-027, FR-028); (d) `/speckit-implement` policy and
  Assignment Envelope linkage (FR-005 through FR-011);
  (e) actor/tool ownership matrix linkage (cross-reference
  AUTHORITY_AND_RATIFICATION_MODEL.md and agent-interaction-model.md);
  (f) Feature 001 lifecycle correspondence (FR-004); (g) amendment
  procedure (FR-029).
- **Source-of-truth relationship**: REFERENCE — defers to the
  constitution and to Feature 001 spec status lifecycle (FR-013a);
  authoritative for SDLC mechanics within Feature 002's scope.
- **Acceptance criteria**: 25 states named in order; 24 transitions
  tabled with all required columns; Phase 1/2 boundary present;
  `/speckit-implement` policy explicit; Feature 001 lifecycle
  correspondence table present; amendment procedure cited.

### 7. `docs/architecture/agent-interaction-model.md`

- **Purpose**: Define how Source, Hermes, Claude Code, Codex, and the
  named QA/security/release agents interact across worktrees,
  branches, envelopes, and review surfaces.
- **Required sections**: (a) actor-to-actor interaction patterns;
  (b) communication surfaces (tmux, repo, PR comments, attestation
  records); (c) author/approver separation enforcement
  (Feature 001 FR-007); (d) review-vs-ratification distinction
  (FR-013, FR-017); (e) envelope handoff sequence (Hermes → Claude);
  (f) escalation paths from agent to Source via the conflict
  taxonomy (FR-017, FR-018); (g) cross-reference to the
  Actor/Tool Ownership Matrix.
- **Source-of-truth relationship**: REFERENCE — defers to Feature 001
  authority matrix (FR-015) and ratification flow (FR-016).
- **Acceptance criteria**: every actor named in the Feature 002
  Actor/Tool Ownership Matrix appears; review-vs-ratification
  distinction explicit; envelope handoff sequence covers every
  FR-005 field.

### 8. `docs/architecture/integration-map.md`

- **Purpose**: Map Creator Engine integrations with external systems
  (Spec Kit, GitHub, CI, work trackers) and define what is governed,
  what is integrated, and what is deferred.
- **Required sections**: (a) Spec Kit integration boundary
  (Feature 001 wrapper sidecars and Spec Kit-byte-identical
  invariant); (b) GitHub integration boundary (PR/merge mechanics;
  `.github/` deferred to Feature 003); (c) CI integration boundary
  (mechanical validation; verifies-not-ratifies); (d) tracker-
  agnostic work-item model; (e) per-integration deferrals citing
  Features 003–006; (f) trust boundaries summary.
- **Source-of-truth relationship**: REFERENCE — defers to Feature 001
  wrapper sidecar contracts and to the operating model doc.
- **Acceptance criteria**: every integration boundary row names
  ownership (Creator Engine governs vs external owns) and deferral
  status; `.github/` explicitly listed as Feature 003 deferral.

### 9. `docs/architecture/parallel-agent-development-model.md`

- **Purpose**: Specify the permanent rule "many isolated writers, one
  governed integration path"; explain how parallel Hermes+Claude
  pairs operate without overwriting each other and how textual,
  ownership, semantic, and authority conflicts are routed.
- **Required sections**: (a) one-driver-per-worktree rule and its
  rationale; (b) parallel-pair pattern (isolated branch + isolated
  worktree + isolated envelope); (c) integration path (serialized,
  Source-ratified canonical-branch integration); (d) git vs
  Creator Engine conflict-labor division (textual vs.
  semantic/authority/ownership); (e) explicit non-permanence of the
  May 10 emergency freeze; (f) walkthrough of a two-pair scenario;
  (g) cross-reference to the conflict taxonomy.
- **Source-of-truth relationship**: REFERENCE — defers to the
  operating model doc for SDLC mechanics and to the conflict
  taxonomy.
- **Acceptance criteria**: one-driver-per-worktree rule stated as
  permanent; May 10 freeze explicitly marked non-permanent; two-pair
  walkthrough included; conflict taxonomy linked; no guidance
  contradicts the conflict taxonomy or the Actor/Tool Ownership
  Matrix.

### 10. `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`

- **Purpose**: Summarize who may instruct whom, who ratifies what,
  and which mutation classes require Source ratification — as a
  navigable reference over Feature 001's authority matrix and
  ratification flow.
- **Required sections**: (a) summary of Feature 001 authority matrix
  (FR-015); (b) ratifier role taxonomy; (c) privileged mutation
  classes enumerated per Feature 001 FR-008; (d) review-vs-
  ratification invariants (Feature 002 FR-013, FR-017);
  (e) escalation policy; (f) link table from each SDLC transition to
  its ratifier role.
- **Source-of-truth relationship**: SUMMARY — Feature 001 authority
  matrix and ratification flow are authoritative; this doc
  summarizes and links.
- **Acceptance criteria**: privileged classes list matches Feature
  001 FR-006/FR-008 exactly; no role definition overrides Feature
  001 authority matrix; the link table covers every SDLC transition
  requiring ratification.

### 11. `docs/governance/MUTATION_CLASS_MODEL.md`

- **Purpose**: Summarize the Feature 001 baseline mutation-class
  taxonomy and explain how Feature 002 transitions and envelopes
  consume it.
- **Required sections**: (a) baseline class summary (`docs`, `code`,
  `schema`, `deploy`, `governance`, `identity`, `security`,
  `attestation`, `redaction`) per Feature 001 FR-006;
  (b) reserved-action vocabulary per Feature 001 FR-006;
  (c) tenant-extension overlay policy per Feature 001 FR-006;
  (d) privileged-class ratification rules per Feature 001 FR-008;
  (e) usage in Assignment Envelopes (Feature 002 FR-005);
  (f) usage in the SDLC Transition Matrix (Feature 002 normative
  matrix above).
- **Source-of-truth relationship**: SUMMARY — Feature 001 mutation-
  class contract is authoritative; this doc summarizes and applies
  it.
- **Acceptance criteria**: baseline class list matches FR-006
  exactly; privileged-class list matches FR-008 exactly; usage
  examples cite Feature 002 FR-005 and the transition matrix.

### 12. `docs/governance/ATTESTATION_MODEL.md`

- **Purpose**: Summarize the Feature 001 attestation record format
  and explain how attestations bind SDLC transitions to evidence.
- **Required sections**: (a) attestation record fields per
  Feature 001 FR-004; (b) pre-merge vs post-merge attestation states;
  (c) repository-native storage per Feature 001 FR-020a;
  (d) attestation linkage to SDLC transitions T15, T22, T23, T24;
  (e) ratification record vs attestation record distinction;
  (f) bootstrap record grandfathering policy (Feature 001
  constitution Principle VIII).
- **Source-of-truth relationship**: SUMMARY — Feature 001 attestation
  schema is authoritative; this doc summarizes and applies.
- **Acceptance criteria**: attestation record field list matches
  FR-004; storage layout matches FR-020a; bootstrap grandfathering
  policy cited; no new attestation field introduced without a flagged
  dependency on a Feature 001 amendment per FR-021.

### 13. `docs/quality/QA_STRATEGY.md`

- **Purpose**: Define which testing levels are required for which
  mutation classes and which agent role produces QA evidence; defer
  identity instantiation and evidence schema to Feature 004.
- **Required sections**: (a) testing levels (unit, integration, e2e,
  security, accessibility, performance, regression); (b) mapping of
  testing levels to mutation classes; (c) the QA agent role
  (named in Feature 002; identity deferred Feature 004);
  (d) QA evidence schema reference (deferred Feature 004);
  (e) flaky-test triage policy; (f) release-readiness checklist
  reference (deferred Feature 006).
- **Source-of-truth relationship**: REFERENCE — defers Feature 004
  for QA identity record and evidence schema; defers Feature 006
  for release-readiness checklist.
- **Acceptance criteria**: testing-level-to-mutation-class table
  covers all baseline classes; the QA agent role appears in the
  Feature 002 Actor/Tool Ownership Matrix; Feature 004 and Feature
  006 deferrals flagged per FR-021.

### 14. `docs/quality/TESTING_STRATEGY.md`

- **Purpose**: Define engineering testing practices Creator Engine
  expects: required validator coverage, test placement, evidence
  capture, and CI verification interface.
- **Required sections**: (a) when test writing is mandatory
  (Feature 001 FR-025 and operating-model transition T14);
  (b) test placement convention; (c) validator self-tests
  (Feature 001 FR-025–FR-027); (d) CI verification expectations
  (Feature 003 deferral); (e) evidence-capture format;
  (f) "agent says it works" rejection invariant (Feature 001
  FR-014).
- **Source-of-truth relationship**: REFERENCE — defers to
  Feature 001 Definition of Done (FR-014) and validator requirements
  (FR-025–FR-027); CI execution deferred to Feature 003.
- **Acceptance criteria**: every required section present;
  self-claim rejection invariant cited; Feature 003 CI execution
  deferral explicit; testing-level-to-mutation-class table aligned
  with QA_STRATEGY.md.

### 15. `docs/devops/CI_CD_STRATEGY.md`

- **Purpose**: Define what Creator Engine governs about CI/CD even
  though `.github/` automation is deferred to Feature 003.
- **Required sections**: (a) verifies-not-ratifies invariant
  (Feature 002 FR-013); (b) required CI checks (tests, lint,
  typecheck, build, Creator Engine validator) — specified, executed
  by Feature 003; (c) protected-branch policy summary (deferred
  Feature 003); (d) CI mutation-class ratification policy (CI
  changes are themselves a privileged mutation requiring Source
  ratification per Feature 001 FR-008); (e) CI evidence linkage to
  SDLC transition T17; (f) explicit Feature 003 deferral.
- **Source-of-truth relationship**: REFERENCE — Feature 003 ratifies
  CI workflow content; Feature 002 specifies the policy CI must
  obey.
- **Acceptance criteria**: verifies-not-ratifies invariant explicit;
  Feature 003 deferral explicit; CI evidence linkage to T17 stated;
  no `.github/` workflow content authored.

### 16. `docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`

- **Purpose**: Define release and deployment governance (environment
  gates, deploy ratification, release attestations, rollback
  requirements) even though release/deploy automation is deferred
  to Feature 006.
- **Required sections**: (a) environment taxonomy (local/staging/
  production); (b) deploy mutation-class ratification rule
  (Source-only per Feature 001 FR-008); (c) release-tag policy;
  (d) rollback evidence requirement; (e) secrets policy summary
  (defers to Feature 001 Principle XII); (f) observability
  requirement summary; (g) incident-response expectation summary;
  (h) Feature 006 deferral.
- **Source-of-truth relationship**: REFERENCE — Feature 006 ratifies
  release/deploy automation; Feature 002 specifies the policy
  release/deploy must obey.
- **Acceptance criteria**: deploy-as-privileged-class explicit;
  Feature 006 deferral explicit; environment gates table populated;
  no actual deploy automation authored.

### 17. `docs/security/SECURITY_MODEL.md`

- **Purpose**: Summarize how Creator Engine treats security and
  privacy as design constraints (Feature 001 Principle XII) and how
  the `security` mutation class is handled.
- **Required sections**: (a) security as design constraint
  (Principle XII); (b) security mutation class definition and
  Source-only ratification rule (Feature 001 FR-008); (c) redaction
  gate summary (Feature 001 FR-019, FR-020); (d) secrets policy
  summary; (e) credentials rotation policy summary;
  (f) security-finding-record schema reference (deferred Feature
  004); (g) escalation paths.
- **Source-of-truth relationship**: SUMMARY — Feature 001 security
  and redaction contracts are authoritative; this doc summarizes
  and links.
- **Acceptance criteria**: Principle XII cited; security mutation
  class explicit as Source-only; redaction gate summary present;
  secrets policy summary present; security-finding-record schema
  deferral to Feature 004 explicit.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer with `git clone` and the Feature 002 spec
  artifacts can list all 25 SDLC states in order, name the responsible
  actor/tool for each transition, and label each transition as Phase 1
  or Phase 2-eligible, without consulting any external system.

- **SC-002**: A Hermes operator who has never used the Assignment
  Envelope before can read the Assignment Envelope specification and
  author a complete envelope (all FR-005 fields populated) for a
  hypothetical Feature 003 batch in under thirty minutes; an
  independent reviewer can confirm the envelope is valid against the
  spec without external help.

- **SC-003**: A reader of the operating model can state, in one
  sentence each, why `/speckit-implement` MUST run only inside a
  Hermes-authored envelope, why Hermes MUST NOT consume an envelope
  it authored, and why CI MUST NOT ratify privileged mutation classes.

- **SC-004**: 100% of the actors named in FR-012 (`Source`,
  `Nefarious/Hermes`, `Claude Code`, `Codex`, `QA agent`, `security
  agent`, `release agent`, `CI`, `GitHub`) appear in the actor/tool
  ownership table with every required column populated (allowed
  instruction sources, allowed mutation classes, allowed communication
  surfaces, required ratifier, required audit artifacts).

- **SC-005**: 100% of the canonical documents enumerated in `Key
  Entities → Canonical Document Set` are specified by Feature 002 with
  purpose, required sections, source-of-truth relationship, and
  acceptance criteria; 0 document bodies are authored in Feature 002.

- **SC-006**: 0 Feature 001 artifacts (under
  `specs/001-v0-1-governance-substrate/`, `docs/contracts/`,
  `schemas/`, `validators/`, `templates/`, or
  `tenants/<name>/`) are modified by Feature 002 beyond what Spec Kit
  itself updates for feature metadata (e.g., `.specify/feature.json`).

- **SC-007**: A reader can classify any of the eight example
  conflicts in `Edge Cases` into one of the four named conflict
  classes (`textual`, `file/task ownership`, `semantic`, `authority`)
  and state the named resolver and required evidence.

- **SC-008**: The parallel-agent development model can be applied to a
  two-pair scenario (two Hermes+Claude pairs, two worktrees, two
  branches, two envelopes) such that a reviewer can confirm: each pair
  writes only to its own worktree, neither pair overwrites the other's
  work, and canonical-branch integration is serialized with Source
  ratification — all without consulting any external system.

- **SC-009**: The deferrals section names exactly Features 003 through
  006 as the owners of `.github/`, Codex/QA/release identities,
  dispatcher runtime, and release/deploy automation respectively. 0
  automation surfaces deferred by Feature 002 are implemented by
  Feature 002.

- **SC-010**: An auditor unfamiliar with Creator Engine can read
  Feature 002's source-of-truth hierarchy and, given any apparent
  conflict between a constitution rule, a Feature 001 contract, a
  Feature 002 canonical doc, a tenant fixture, and a working note,
  state which artifact wins and why — in their own words — without
  external help.

## Assumptions

- Feature 002 is the canonical operating-model layer of Creator Engine
  v0.1-docs. It is a specification feature; the 17 canonical documents
  it specifies are authored in the implementation phase that follows
  Feature 002 ratification, not within Feature 002 itself.

- Feature 001 is the authoritative governance substrate. Feature 002
  defers to Feature 001 contracts for mutation-class taxonomy,
  authority matrix, attestation record format, ratification flow,
  identity model, redaction gate, and spec status lifecycle. Where
  Feature 001 has not yet ratified a concept Feature 002 depends on,
  Feature 002 flags the dependency rather than redefining the
  concept.

- Phase 1 is the operational default in Feature 002: assignment-based
  dispatch via Hermes-prepared envelopes, human ratification of every
  privileged gate, Source-gated canonical-branch integration. Phase 2
  promotion is OUT OF SCOPE for Feature 002; any Phase 2 expansion is
  itself a ratified amendment to the operating model.

- `/speckit-implement` is, after Feature 002 ratification, the
  mandatory implementation command for Creator-Engine-governed work.
  Hermes authors Assignment Envelopes; Claude Code consumes them;
  Source ratifies privileged integration. Out-of-envelope
  `/speckit-implement` invocation is a contract violation, classified
  as an authority conflict.

- Parallel-agent development is the permanent target model: many
  isolated writers across separate branches/worktrees/envelopes, one
  governed integration path. The temporary May 10 freeze (one writer
  globally) is NOT the permanent model. Creator Engine governs
  parallel agent development; it does not prevent it.

- Feature 002 does not author, modify, or delete: `.github/`,
  validators, schemas, templates, tenant fixtures, Feature 001 spec
  artifacts, or any external document under
  `/home/nefarious/Documents/...`. The only repository mutations
  produced by Feature 002 are: this spec at
  `specs/002-canonical-docs-and-operating-model/spec.md`, any
  Feature 002 checklist files Spec Kit emits under
  `specs/002-canonical-docs-and-operating-model/checklists/`, and any
  Spec Kit feature-metadata updates (e.g., `.specify/feature.json`).

- The Spec Kit substrate is preserved (principle X, Spec Kit
  compatibility). Feature 002 references Spec Kit commands
  (`/speckit-specify`, `/speckit-plan`, `/speckit-tasks`,
  `/speckit-implement`) by their installed Claude hyphenated form;
  dot-form names are not used.

- Feature 002's canonical document set is the version-1.0 target for
  Creator Engine documentation. Future Features (003–006) may add
  documents but MUST NOT redefine the v1.0 set without an explicit
  Source-ratified amendment to Feature 002.

- "Done" for Feature 002 means the spec exists, is ratified, and
  answers every load-bearing operating-model question listed in
  `Success Criteria`; it does NOT require any canonical document body
  to be authored, any automation to be wired up, or any external
  pilot to have consumed the operating model.
