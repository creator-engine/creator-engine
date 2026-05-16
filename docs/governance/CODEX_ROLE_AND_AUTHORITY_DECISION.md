# CFC follow-on Batch 2A — Codex Role and Authority Decision Request

**Batch id**: `post-sprint-0/cfc-2a-codex-role-decision`
**Batch**: CFC follow-on Batch 2A (decision-request, docs/governance only)
**Mutation class**: `governance` / `docs`
**Ratifier**: `source` only
**Status**: Decision request — Source has not yet selected an option.

## 1. Purpose

This document is a **Source decision-request artifact**, not a final
decision. It exists to let Source explicitly decide Codex role and
authority semantics **before** any downstream CFC follow-on batch
mutates an architecture actor/tool matrix, a Codex identity record,
a review/architect-evidence schema, a validator, a template, an
example, a provider/tool/model/host/account binding, or any expansion
of Codex authority.

Batch 2A produces only this decision document and minimal coherence
updates to the four existing delivery/governance files listed in §10.
Source ratification of one of the options in §3 and the seven
discrete decisions in §6 is the gate that any subsequent Batch 2B,
2C, or 2D consumes. Until Source ratifies, no role/authority claim in
this document is in effect.

## 2. Source priority restatement

Source has expressed the priority that **Codex should become a
first-class architect like Claude Code, not merely a passive
reviewer.** This document treats that priority as the anchor for
recommendation in §5, but it does not encode the priority as a
ratified decision. The priority is what Source has signaled as
desired direction; the discrete decisions in §6 are what Source must
ratify to make that direction operative.

"Architect parity" in this document means **authoring parity** under
the Feature 001 / Feature 002 substrate: Codex would be authorized to
author the same artifact classes Claude Code may author for the
batches it is dispatched to, under the same envelope discipline, the
same mutation-class boundaries, and the same Source-only ratification
gate. Architect parity is **not** ratification authority, merge
authority, or deploy authority. That distinction is itself one of the
seven discrete decisions in §6.

## 3. Candidate `role_category` mappings for Codex

The seven baseline `role_category` enum values in
`docs/contracts/authority-matrix.md` (`source`, `ratifier`,
`reviewer`, `architect`, `implementer`, `verifier`, `observer`) and
their per-row coverage rules under FR-015 are **not amended by Batch
2A**. Batch 2A surfaces the policy decision of which existing baseline
role (or which Source-introduced new role) Codex should be treated as
when it acts as a governed actor. The decision in §6.1 determines
which row of the baseline authority matrix governs Codex's authoring
authority once Codex identity is later instantiated under a
Batch 2C `identity`-class envelope; it does not by itself create that
identity record, and it does not by itself rewrite the
authority-matrix YAML.

The candidate mappings below are exhaustive for Batch 2A purposes.
Each option is described under the same headings:

- **Allowed mutation class implications** — which Feature 001 baseline
  mutation classes the role would be authorized to author under the
  Codex identity record's eventual `allowed_mutation_classes`. All
  options preserve the Feature 001 FR-008 privileged-class rule: every
  privileged class (`governance`, `identity`, `schema`, `security`,
  `attestation`, `redaction`, `deploy`) is Source-ratified regardless
  of who authors.
- **Preserved invariants** — invariants that **must** hold under the
  option. These are non-negotiable across all options in Batch 2A;
  they are listed under each option only to make the option's
  acceptance posture explicit. The invariants are:
  - Source-only ratification (Feature 001 FR-008).
  - No merge authority for Codex.
  - No deploy authority for Codex.
  - Verifies-not-ratifies (Feature 001 FR-013 / Feature 002 FR-013):
    review or architect evidence authored by Codex never substitutes
    for Source ratification.
  - One-driver-per-worktree
    (`docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md`).
  - Codex-only worktree isolation
    (`docs/governance/CODEX_FIRST_CLASS_SCOPE.md` §4.4 and
    `docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md` §2).
  - No writes to an active Claude Code worktree.
- **Downstream consequences** — what the option implies for the next
  CFC follow-on batches:
  - **Batch 2B** — architecture actor/tool matrix update under
    `docs/architecture/` (governance-class).
  - **Batch 2C** — Codex identity record under
    `docs/contracts/identity-record.md` semantics
    (`identity`-class, privileged).
  - **Batch 2D** — review/architect-evidence schema for
    Codex-authored evidence (`schema`-class, privileged).
- **FR-015 / baseline authority-matrix coverage consequence** —
  what the option implies for FR-015 coverage. **In every option,
  the seven-row baseline authority-matrix rule under FR-015 is not
  amended by Batch 2A.** Any change to row count, role enum, or
  per-row coverage is a separately Source-ratified privileged
  amendment outside the Batch 2A boundary.

### 3.1 Option A — `architect`

Codex is mapped to the existing baseline `architect` role.

- **Allowed mutation class implications**: under the existing
  `architect` baseline row, Codex would be authorized to author the
  same artifact classes the baseline `architect` row already covers
  (spec/plan/contract design, generic contract docs and schemas,
  governance docs subject to Source ratification). Privileged classes
  remain Source-ratified per FR-008; Codex never becomes a ratifier.
- **Preserved invariants**: all invariants enumerated in §3 apply.
  Codex never ratifies, never merges, never deploys, only acts inside
  a Codex-only isolated worktree under a Source-ratified envelope.
- **Downstream consequences**:
  - Batch 2B adds a Codex row to the architecture actor/tool matrix
    where Codex is named as an `architect`-class governed actor next
    to Claude Code.
  - Batch 2C instantiates a Codex identity record whose
    `role_category` is `architect`.
  - Batch 2D specifies a Codex architect-evidence schema (with the
    Source-ratified review-evidence framing decision from §6.5
    informing whether legacy review-evidence semantics are retained,
    renamed, or absorbed).
- **FR-015 / baseline coverage consequence**: the baseline
  `architect` row already exists; no new row is required. Tenant
  overlay rows (FR-015 overlay rule) MAY name a tenant-specific
  `tenant_role_name` for Codex, but the baseline file remains
  seven rows. The seven-row rule is not amended.

### 3.2 Option B — `implementer`

Codex is mapped to the existing baseline `implementer` role.

- **Allowed mutation class implications**: Codex would be authorized
  to author code, schema, and docs that fulfill an approved
  spec/plan/tasks triple, mirroring Claude Code's current
  Sprint-0-era implementer posture. Privileged classes remain
  Source-ratified per FR-008.
- **Preserved invariants**: all invariants enumerated in §3 apply.
- **Downstream consequences**:
  - Batch 2B adds Codex to the architecture actor/tool matrix as a
    second governed `implementer` next to Claude Code; spec/plan
    authoring authority is retained by the existing `architect` row
    occupants.
  - Batch 2C instantiates a Codex identity record whose
    `role_category` is `implementer`.
  - Batch 2D specifies a Codex implementer-evidence schema (or
    extends the existing review-evidence framing per §6.5).
- **FR-015 / baseline coverage consequence**: the baseline
  `implementer` row already exists; no new row is required. The
  seven-row rule is not amended.
- **Note vs. Source priority**: this option is the **narrower**
  reading of architect parity. It treats Codex as authoring parity
  at the implementer layer rather than at the architect layer. It
  does not, by itself, satisfy the Source priority restated in §2
  unless Source explicitly elects this narrower reading.

### 3.3 Option C — `architect` and `implementer` (per-batch role assignment)

Codex is mapped to **both** baseline roles, with per-batch role
assignment determined by the Source-ratified envelope for that batch.

- **Allowed mutation class implications**: Codex's authoring posture
  is **envelope-determined**. For an architect-class envelope, Codex
  authors as `architect`; for an implementer-class envelope, Codex
  authors as `implementer`. The Codex identity record would either
  carry a multi-valued `role_category` (if the substrate permits) or
  a primary baseline `role_category` with per-envelope role overlay
  semantics defined under Batch 2C.
- **Preserved invariants**: all invariants enumerated in §3 apply.
  The per-batch assignment never grants ratification, merge, or
  deploy authority; assignment selects authoring scope only.
- **Downstream consequences**:
  - Batch 2B adds Codex to the architecture actor/tool matrix with
    per-batch role notation.
  - Batch 2C must decide the identity-record encoding for a
    dual-role identity. The current `identity-record.md` baseline
    treats `role_category` as a single enum value; if the substrate
    requires single-valued `role_category`, this option must encode
    per-batch role assignment as an envelope attribute rather than
    as an identity attribute. Either path is a privileged
    `identity`-class decision deferred to Batch 2C.
  - Batch 2D specifies the schema for whichever evidence class
    (review, architect, implementer) Codex authors under each
    envelope.
- **FR-015 / baseline coverage consequence**: no change to the
  seven-row baseline. Both rows already exist. The seven-row rule
  is not amended.

### 3.4 Option D — `reviewer` (status quo)

Codex remains a `reviewer`, as currently described in
`docs/architecture/agent-interaction-model.md` §a / §b.4 and
`docs/governance/CODEX_FIRST_CLASS_SCOPE.md`.

- **Allowed mutation class implications**: Codex authors review
  evidence only. Codex does not author spec/plan/contract artifacts
  and does not author implementation artifacts. Privileged classes
  remain Source-ratified per FR-008.
- **Preserved invariants**: all invariants enumerated in §3 apply.
- **Downstream consequences**:
  - Batch 2B leaves the architecture actor/tool matrix substantively
    unchanged with respect to Codex's role label, though it may add
    or refine a Codex row consistent with the existing reviewer
    posture.
  - Batch 2C instantiates a Codex identity record whose
    `role_category` is `reviewer`.
  - Batch 2D specifies the review-evidence schema as previously
    contemplated in `docs/governance/CODEX_FIRST_CLASS_SCOPE.md`
    §3.2 and §5.
- **FR-015 / baseline coverage consequence**: no change. The
  seven-row rule is not amended.
- **Note vs. Source priority**: this option is the **status-quo**
  reading. It does not satisfy the Source priority restated in §2.
  It is listed for completeness because the decision is Source's,
  not this document's.

### 3.5 Option E — new `role_category` (e.g., `codex-architect`)

Codex is mapped to a **new** `role_category` enum value introduced
into the baseline (e.g., `codex-architect` or another Source-chosen
name).

- **Allowed mutation class implications**: a new role row would have
  to be authored with `allowed_mutation_classes`,
  `allowed_instruction_sources`, `required_ratifier_role`,
  `allowed_communication_surfaces`, and `required_audit_artifacts`
  fields per `docs/contracts/authority-matrix.md` §"Per-row shape".
  Privileged classes remain Source-ratified per FR-008.
- **Preserved invariants**: all invariants enumerated in §3 apply.
- **Downstream consequences**:
  - Batch 2B updates the architecture actor/tool matrix to name the
    new role.
  - Batch 2C instantiates a Codex identity record whose
    `role_category` is the new enum value.
  - Batch 2D specifies an evidence schema scoped to the new role.
- **FR-015 / baseline coverage consequence**: this option **would
  require** a separately Source-ratified amendment to the baseline
  authority matrix (row count, role enum, per-row coverage). That
  amendment is **outside the Batch 2A boundary** and is **not
  performed here**. Batch 2A does not mutate
  `docs/contracts/authority-matrix.yml`,
  `docs/contracts/authority-matrix.md`, or
  `docs/contracts/identity-record.md`.
- **Note**: this option is recorded for completeness. It is the
  heaviest option in coverage cost because it touches the baseline
  authority-matrix rule that the Feature 001 substrate publishes.

## 4. Invariants preserved under every option

The following invariants apply regardless of which option Source
ratifies under §6.1. They are restated here to make this document
self-contained and to make the §3 option blocks compact.

1. **Source-only ratification** (Feature 001 FR-008). Source is the
   sole ratifier for every privileged mutation class. No option in
   §3 makes Codex a ratifier.
2. **No merge authority for Codex.** Merge remains a Source-ratified
   gate per Feature 001 FR-008 and the Slice F policy in
   `docs/delivery/MERGE_APPROVAL_CHECKLIST.md`.
3. **No deploy authority for Codex.** The `deploy` class remains
   Source-only per Feature 001 FR-008 and the Slice F policy in
   `docs/delivery/DEPLOYMENT_APPROVAL_POLICY.md`.
4. **Verifies-not-ratifies** (Feature 001 FR-013 / Feature 002
   FR-013). Codex-authored evidence — whether review evidence or, in
   future, architect/implementer evidence — never substitutes for
   Source ratification.
5. **One-driver-per-worktree.** A worktree occupied by Codex is not
   simultaneously occupied by Claude Code or by Nefarious for
   tracked-file authoring, per
   `docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md`.
6. **Codex-only worktree isolation.** Codex acts only inside a
   Codex-owned isolated worktree separately authorized for that
   batch, per `docs/governance/CODEX_FIRST_CLASS_SCOPE.md` §4.4 and
   `docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md` §2.
7. **No writes to an active Claude Code worktree.** Codex never
   writes to the active Claude Code worktree or to the canonical
   main worktree; the same isolation rule applies in reverse to
   Claude Code with respect to an active Codex worktree.
8. **Author/approver separation** (Feature 001 FR-007). The actor
   who authors a mutation is not its ratifier. Architect parity
   does not relax FR-007.

## 5. Recommended option and rationale

Anchored in the Source priority restated in §2 — Codex should become
a first-class architect like Claude Code, not merely a passive
reviewer — the **recommended option is Option C: per-batch role
assignment between `architect` and `implementer`** (§3.3), with
Option A (`architect`-only, §3.1) as the conservative fallback.

Rationale:

1. **Satisfies the priority.** Both Option C and Option A give Codex
   authoring parity at the architect layer, which is what
   distinguishes "first-class architect" from "passive reviewer".
   Options B and D do not satisfy the priority; Option E satisfies
   it but at the cost of a baseline authority-matrix amendment that
   is heavier than the priority requires.
2. **Preserves the seven-row baseline.** Options A and C reuse
   existing baseline rows; the seven-row FR-015 rule is not
   amended. Option E would require a separate Source-ratified
   amendment, which is outside the Batch 2A boundary.
3. **Mirrors the existing Sonnet/Opus envelope discipline.** The
   policy "Opus shapes the envelope when the envelope itself
   matters; Sonnet executes the envelope when the envelope is
   already settled" cited in
   `docs/governance/CODEX_FIRST_CLASS_SCOPE.md` §1 already
   distinguishes architect-class and implementer-class authoring at
   the envelope layer. Option C extends the same envelope-level
   role assignment to Codex, with per-batch granularity. Option A
   collapses that distinction by treating every Codex envelope as
   architect-class, which is simpler but slightly less expressive.
4. **Does not preempt Batch 2B / 2C / 2D.** Both Option C and
   Option A leave the identity record encoding, the architecture
   actor/tool matrix shape, and the evidence schema framing to be
   Source-ratified in their own bounded envelopes. Option C
   surfaces an additional Batch 2C question — single-valued vs.
   multi-valued `role_category` encoding — but that question is a
   legitimate identity-record decision that Source should have the
   chance to make explicitly.
5. **Conservative fallback.** If Source prefers a simpler initial
   surface area, Option A (architect-only) is the recommended
   fallback. It satisfies the Source priority, preserves the
   seven-row baseline, and leaves the implementer-class option open
   to be re-ratified later as an explicit role-broadening
   amendment.

This recommendation is **non-binding**. Source's ratification of one
of the §6.1 options is what selects the role.

## 6. Required Source decisions

Each item below is a discrete decision Source is asked to ratify
under Batch 2A. The decisions are independent; Source MAY ratify
them individually or as a single bundle. Each item lists the
candidate values and the recommended value.

### 6.1 Codex `role_category`

- **Candidate values**:
  - Option A — `architect` (§3.1).
  - Option B — `implementer` (§3.2).
  - Option C — `architect` and `implementer` with per-batch
    assignment (§3.3).
  - Option D — `reviewer` / status quo (§3.4).
  - Option E — new `role_category` (§3.5).
- **Recommended value**: Option C, with Option A as conservative
  fallback (see §5).
- **Effect of ratification**: selects which baseline row (or new
  row, under Option E) will be cited by the Codex identity record
  authored under Batch 2C, and which architecture actor/tool
  matrix row will be authored under Batch 2B. No identity record
  is authored under Batch 2A.

### 6.2 Codex allowed mutation classes for Phase 1

- **Candidate values**:
  - Phase-1 allowed classes = `governance` and `docs` only
    (matches the current CFC-1 Batch 1 posture under
    `docs/governance/CODEX_FIRST_CLASS_SCOPE.md` §3.4).
  - Phase-1 allowed classes = `governance`, `docs`, and `code`
    (broadens to implementer-class authoring under §6.1 Option B
    or §6.1 Option C).
  - Other Source-specified subset of the baseline mutation classes,
    drawn from the nine baseline class names enumerated in
    `docs/contracts/authority-matrix.md`.
- **Recommended value**: align with §6.1.
  - If Source ratifies §6.1 Option A: Phase-1 allowed classes =
    `governance` and `docs`.
  - If Source ratifies §6.1 Option C: Phase-1 allowed classes =
    `governance`, `docs`, and `code` (with `code` gated to
    implementer-class envelopes only).
  - If Source ratifies §6.1 Option D: Phase-1 allowed classes =
    none for authoring; review-evidence authoring only.
- **Effect of ratification**: pins the
  `allowed_mutation_classes` field that the Codex identity record
  authored under Batch 2C will carry. Privileged classes remain
  Source-ratified per FR-008 regardless of this field's contents.

### 6.3 Codex authority boundary

- **Statement to ratify**: **architect parity is authoring parity,
  not ratification authority, not merge authority, not deploy
  authority.**
- **Candidate values**:
  - Ratify the statement as written.
  - Ratify a Source-amended statement.
- **Recommended value**: ratify the statement as written. This
  statement is consistent with §4 (invariants under every option)
  and with `docs/governance/CODEX_FIRST_CLASS_SCOPE.md` §3.4 and
  §3.5.
- **Effect of ratification**: pins the boundary that any §6.1
  option must respect. Batch 2B, 2C, and 2D inherit this boundary
  unmodified.

### 6.4 Provider/tool/model/host/account binding posture

- **Candidate values**:
  - **Bind now**: identify the concrete provider, tool, model,
    host installation, and account under the Codex identity
    record authored in Batch 2C, treating binding as a separately
    Source-ratified `identity`-class decision (note: this is
    forbidden under Batch 2A itself).
  - **Placeholder/unbound identity semantics**: the Codex identity
    record authored under Batch 2C carries placeholder values for
    `provider_id`, `tool_id`, `model_id`,
    `source_host_installation_id`, and `agent_actor_id`, with
    binding deferred to a later deployment-overlay decision.
  - **Defer identity entirely**: Batch 2C is itself deferred until
    Source ratifies a binding decision.
- **Recommended value**: **placeholder/unbound identity
  semantics**. This is consistent with
  `docs/governance/CODEX_FIRST_CLASS_SCOPE.md` §3.7 (no binding
  under CFC-1 Batch 1) and with the Sprint 0 Slice D posture that
  "concrete tool / model / host / actor / account bindings are
  deployment-time overlay decisions and are not selected upstream
  by this slice".
- **Effect of ratification**: pins the binding posture that the
  Codex identity record authored under Batch 2C will adopt.
  **Batch 2A does not bind any provider/tool/model/host/account
  and does not author any identity record.**

### 6.5 Review-evidence semantics under architect framing

- **Candidate values**:
  - **Retain review evidence as-is**: Codex continues to author
    review evidence in the existing framing
    (`docs/governance/CODEX_FIRST_CLASS_SCOPE.md` §3.2;
    `docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md` §3), even
    when Codex acts as an architect under §6.1 Option A or
    Option C. Architect-class authoring is a separate artifact
    class from review evidence.
  - **Rename / replace with architect evidence**: the
    review-evidence framing is renamed to architect evidence (or
    implementer evidence) under §6.1 Option A / Option B /
    Option C. Batch 2D specifies the renamed schema.
  - **Absorb into attestation/ratification records**: review
    evidence is absorbed into the attestation record under
    `docs/governance/ATTESTATION_MODEL.md` and the ratification
    record under
    `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`,
    eliminating a separate review-evidence schema.
- **Recommended value**: **retain review evidence as-is** for
  Phase 1. Architect-class artifacts authored by Codex are
  attested via the ordinary attestation flow; review evidence
  remains a separate artifact class that any reviewer
  (Codex-as-reviewer or otherwise) may author. Renaming or
  absorbing can be re-ratified later if Source decides the
  separation is no longer useful.
- **Effect of ratification**: pins the schema framing that
  Batch 2D will instantiate. Batch 2A does not author any
  evidence schema and does not mutate
  `docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md`.

### 6.6 Public / tenant role label

- **Candidate values**:
  - `architect` (use the baseline `role_category` name directly as
    the public/tenant label).
  - `codex-architect` (alias the baseline `architect` row to a
    Codex-specific tenant label via the FR-015 overlay
    `tenant_role_name` field).
  - Another Source-chosen alias.
- **Recommended value**: `codex-architect` as a tenant overlay
  alias, with the baseline `role_category` remaining `architect`
  per §6.1 Option A or Option C. This keeps the baseline
  authority-matrix row count and enum unchanged (preserving
  FR-015) while letting tenant-facing labels distinguish Codex
  from Claude Code.
- **Effect of ratification**: pins the `tenant_role_name` value
  the Codex identity record authored under Batch 2C will carry,
  if any. No tenant overlay is authored under Batch 2A.

### 6.7 Reaffirmation: `docs/contracts/authority-matrix.yml` is not mutated by Batch 2A

- **Statement to ratify**: **Batch 2A does not mutate
  `docs/contracts/authority-matrix.yml`. The seven-row baseline
  rule under FR-015 remains in effect unchanged.** Any amendment
  to the baseline matrix (e.g., under §6.1 Option E) is a
  separately Source-ratified privileged amendment outside the
  Batch 2A boundary.
- **Candidate values**:
  - Ratify the statement as written.
  - Ratify a Source-amended statement.
- **Recommended value**: ratify the statement as written.
- **Effect of ratification**: makes the non-mutation of the
  authority matrix part of the Batch 2A acceptance posture.

## 7. Does not authorize

Batch 2A explicitly does NOT authorize any of the following. Each
item below requires its own separately Source-ratified envelope:

1. **Codex identity record instantiation.** No Codex identity
   record is created or modified under Batch 2A. Identity-record
   authoring is a privileged `identity`-class mutation per
   Feature 001 FR-008 and is deferred to Batch 2C.
2. **Schema authoring.** No review/architect/implementer evidence
   schema is created or modified. Schema authoring is a
   `schema`-class privileged mutation and is deferred to Batch 2D.
3. **Architecture actor/tool matrix update.** No update is made to
   `docs/architecture/` actor/tool matrices. That update is
   deferred to Batch 2B.
4. **Codex authority expansion beyond authoring.** Codex acquires
   no ratification authority, no merge authority, and no deploy
   authority under Batch 2A regardless of which §6.1 option Source
   ratifies. Architect parity is authoring parity only (§6.3).
5. **Provider/tool/model/host/account binding.** No provider, tool,
   model, host installation, or account is bound under Batch 2A.
   Concrete bindings are deployment-time overlay decisions and are
   not selected upstream by this document.
6. **GitHub settings mutation.** No `.github/` content, branch
   protection settings, rulesets, CODEOWNERS, environments,
   visibility, topics, homepage, projects, wiki, merge-method
   settings, workflows, or secrets are mutated.
7. **Tenant record mutation.** No tenant record under `tenants/`
   is created or modified.
8. **Validator, template, or example mutation.** No validator
   under `validators/`, template under `templates/`, or example
   under `examples/` is modified. No `docs/contracts/`,
   `docs/architecture/`, or `specs/` content is modified.
9. **Dispatch automation.** No dispatch automation, Hermes
   dispatcher implementation, or worktree lifecycle automation is
   implemented. Feature 005 remains deferred.
10. **Deploy.** Nothing is deployed.

## 8. Cross-references

The following documents are cited as the substrate context for this
decision request. **None of these documents is modified by Batch 2A.**

| Document | Relevance | Modified by Batch 2A? |
|---|---|---|
| [`./CODEX_FIRST_CLASS_SCOPE.md`](./CODEX_FIRST_CLASS_SCOPE.md) §3 | Lists what CFC-1 Batch 1 does **not** authorize (identity, schema, architecture matrix, authority expansion, binding, GitHub settings, dispatch). Batch 2A inherits these non-authorizations and surfaces the §3 boundaries as the inputs to the §6 decisions here. | Yes — §5 forward-scope row added for the Batch 2A gate; review-evidence-schema framing flagged as contingent on the §6.5 decision. No existing row is deleted. |
| [`./CODEX_FIRST_CLASS_SCOPE.md`](./CODEX_FIRST_CLASS_SCOPE.md) §5 | Forward scope table for Batch 2+ items: Codex identity record, review-evidence schema, architecture actor/tool matrix update, provider/tool/model/host/account binding, Codex authority expansion, Feature 005 dispatch automation. Batch 2A adds a forward-scope row for itself. | Yes — see row above. |
| [`../operations/CODEX_FIRST_CLASS_PROTOCOL.md`](../operations/CODEX_FIRST_CLASS_PROTOCOL.md) | Operational protocol companion: pointer-only handoff, Codex-only worktree isolation, evidence requirements, stop lines, verifies-not-ratifies, transcript archival. Batch 2A references this protocol as the operational posture any Codex-as-actor batch must continue to respect. | No — explicitly not modified by Batch 2A. |
| [`../architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md) §a | Actor/Tool Ownership Matrix cross-reference: names Codex with governed identity record deferred to Feature 004. Batch 2A's §6.1 decision determines how this row is restated under Batch 2B. | No — `docs/architecture/**` is not modified by Batch 2A. |
| [`../architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md) §b.4 | "Codex → Hermes (independent review)" interaction pattern: current reviewer framing of Codex, including verifies-not-ratifies wording. Batch 2A's §6.5 decision determines how this pattern is restated under Batch 2B / 2D. | No — `docs/architecture/**` is not modified by Batch 2A. |
| `../../specs/002-canonical-docs-and-operating-model/spec.md` Actor/Tool Ownership Matrix → Codex | Feature 002 canonical actor/tool ownership row for Codex (independent reviewer). Batch 2A's §6.1 and §6.5 decisions determine how this row is restated under a later spec amendment, which is outside the Batch 2A boundary. | No — `specs/**` is not modified by Batch 2A. |
| [`../contracts/identity-record.md`](../contracts/identity-record.md) | Identity record contract; defines what fields a future Codex identity record will carry. Batch 2A's §6.1, §6.2, §6.4, and §6.6 decisions pin field values that a future Batch 2C identity record will adopt. | No — `docs/contracts/**` is not modified by Batch 2A. |
| [`../contracts/authority-matrix.md`](../contracts/authority-matrix.md) | Authority matrix contract; defines the seven baseline `role_category` enum values and the FR-015 per-row coverage rule. Batch 2A's §3 options reference these enum values; §6.7 reaffirms non-mutation of the matrix under Batch 2A. | No — `docs/contracts/**` is not modified by Batch 2A. |
| [`./AUTHORITY_AND_RATIFICATION_MODEL.md`](./AUTHORITY_AND_RATIFICATION_MODEL.md) | Source-only ratification authority; verifies-not-ratifies invariant. Batch 2A's §4 invariants reference this document. | No — explicitly not modified by Batch 2A. |
| [`./MUTATION_CLASS_MODEL.md`](./MUTATION_CLASS_MODEL.md) | Authoritative mutation class definitions; basis for the §3 / §6.2 mutation-class implications. | No — not modified by Batch 2A. |
| [`../delivery/WORKTREE_RUNTIME_PROTOCOL.md`](../delivery/WORKTREE_RUNTIME_PROTOCOL.md) | One-driver-per-worktree rule. §4 invariant. | No — not modified by Batch 2A. |

## 9. Acceptance posture for Batch 2A

This document satisfies the Batch 2A decision-request boundary if:

1. It restates the Source priority (§2) without claiming Source has
   already selected an option.
2. It enumerates the §3 candidate `role_category` mappings
   (`architect`, `implementer`, both, `reviewer`, new role).
3. For each candidate it lists allowed mutation class implications,
   preserved invariants, downstream consequences for Batch 2B / 2C
   / 2D, and the FR-015 / baseline coverage consequence (including
   non-amendment of the seven-row rule).
4. It recommends one option (§5) with rationale anchored in the
   Source priority.
5. It lists seven required Source decisions (§6) as discrete items.
6. It cross-references the documents in §8 without modifying any of
   them (only the four delivery/governance files in §10 are
   modified by Batch 2A).
7. It includes a "does not authorize" block (§7).

## 10. Batch 2A allowed path manifest (informational)

Batch 2A mutates only these five tracked paths:

```text
docs/delivery/BACKLOG.md
docs/delivery/DEPENDENCIES.md
docs/delivery/KANBAN.md
docs/governance/CODEX_FIRST_CLASS_SCOPE.md
docs/governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md
```

This manifest is restated here for self-containment; it is also
recorded in the Source-ratified prompt and engineer handoff that
authorize this batch.
