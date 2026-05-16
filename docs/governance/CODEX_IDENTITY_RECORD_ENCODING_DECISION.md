# CFC follow-on Batch 2C — Codex Identity Record Encoding Decision

**Batch id**: `post-sprint-0/cfc-2c-codex-identity-decision`
**Batch**: CFC follow-on Batch 2C (ratified, docs/governance only)
**Mutation class**: `governance` / `docs`
**Ratifier**: `source` only
**Status**: Source-ratified — eight §6 decisions ratified by Source; merged on canonical origin/main via PR #29 / merge commit `66a8074`.

## Source-ratified decisions (PR #29 / merge commit `66a8074`)

Source ratified the following eight §6 decisions as a bundle. Detailed candidate values and recommendation rationale are preserved in §3–§5 and each §6 subsection for historical context.

| Decision | Source-ratified posture |
|---|---|
| §6.1 Codex identity record encoding | Option A — single record, baseline `role_category = architect`. Option C (two separate records) retained as conservative fallback only if a future authoring envelope proves Option A incompatible with checked-in schema truth. Option B and Option D not selected. |
| §6.2 `authority_context` | Description text as written in §6.2. `governing_spec_refs`: the four cited paths in §6.2 plus `docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`. `ratifier_authority_refs`: `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md` and `docs/contracts/authority-matrix.md`. |
| §6.3 `human_ratifier_roles` | `["source"]`. |
| §6.4 `allowed_repositories` | Placeholder/unbound posture; no concrete repository binding. Literal placeholder wording deferred to the future authoring envelope. |
| §6.5 `signing_policy` | `commit_signing_required = false`, `commit_signing_method = none`, `attestation_signing_required = false`. Placeholder/unbound signing posture. |
| §6.6 Storage paths | Substrate-internal storage under a Codex-specific path beneath the §6.7 placeholder tenant slug. Literal path strings deferred to the future authoring envelope. |
| §6.7 `tenant_id` | Placeholder substrate-internal slug; no concrete tenant binding. Literal slug deferred to the future authoring envelope. |
| §6.8 Batch 2D evidence schema | Ratify the statement as written — Batch 2D remains downstream; Batch 2C does not mutate evidence schemas. |

## 1. Purpose

This document originated as a **Source decision-request artifact** and is
now **Source-ratified** (PR #29 / merge commit `66a8074`). It exists to
let Source explicitly decide how the
Source-ratified Batch 2A Codex Option C semantics (per-batch
architect/implementer authoring role assignment) and the Batch 2B
architecture actor/tool matrix wording (envelope-bound authority, not
personality-bound) are to be encoded inside the existing
`docs/contracts/identity-record.md` substrate **before** any
downstream CFC follow-on batch authors a Codex identity record file,
mutates the identity-record contract or schema, mutates the
authority-matrix contract, mutates a validator, template, example, or
tenant overlay, binds a provider/tool/model/host/account, or expands
Codex authority.

The original Batch 2C commit (PR #29 / `66a8074`) produced only this
decision document and minimal coherence updates to the four existing
delivery/governance files in the §10 historical five-path manifest.
This follow-on reconciliation gate addresses residual coherence gaps
across the expanded seven-path boundary listed in §10. Source
ratification of the eight §6 decisions is now recorded in the
ratification block above and in each §6 subsection's **Source-ratified
selection** line; these encoding claims are in effect. The future Codex
identity record authoring envelope is the next separately Source-ratified
privileged gate.

## 2. Source-ratified basis carried forward

Batch 2A ratified Codex Option C
([`./CODEX_ROLE_AND_AUTHORITY_DECISION.md`](./CODEX_ROLE_AND_AUTHORITY_DECISION.md)
§3.3 and §6.1): Codex's Phase 1 authoring posture is **per-batch
role assignment between `architect` and `implementer`**, selected by
the Source-ratified envelope for that batch. The Source-ratified
Phase-1 allowed mutation classes are `governance`, `docs`, and `code`,
with `code` gated to implementer-class envelopes and privileged
classes still Source-ratified per Feature 001 FR-008. Codex has
**authoring parity only**: no ratification authority, no merge
authority, no deploy authority. The provider/tool/model/host/account
identity remains **placeholder/unbound** upstream
([`./CODEX_ROLE_AND_AUTHORITY_DECISION.md`](./CODEX_ROLE_AND_AUTHORITY_DECISION.md)
§6.4). Review evidence remains a separate artifact class
([`./CODEX_ROLE_AND_AUTHORITY_DECISION.md`](./CODEX_ROLE_AND_AUTHORITY_DECISION.md)
§6.5). `codex-architect` is a tenant/public overlay alias where
needed, not a new baseline `role_category` row
([`./CODEX_ROLE_AND_AUTHORITY_DECISION.md`](./CODEX_ROLE_AND_AUTHORITY_DECISION.md)
§6.6).

Batch 2B instantiated the Codex row of the architecture actor/tool
matrix in
[`../architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md)
§a and the per-batch governed authoring/review pattern in §b.4, in
language that explicitly anchors the authority in the **envelope**,
not in the actor: an architect-class envelope authorizes architect
authoring, an implementer-class envelope authorizes implementer
authoring, and the authority remains envelope-bound, not
personality-bound.

The Batch 2A and Batch 2B wording is the substrate input to this
document. Batch 2C does not re-litigate the Batch 2A role decision
and does not re-litigate the Batch 2B architecture matrix wording.
Batch 2C surfaces the **encoding** question: given that the existing
`docs/contracts/identity-record.md` baseline treats `role_category`
as a single enum value (one of `source`, `ratifier`, `reviewer`,
`architect`, `implementer`, `verifier`, `observer`), how should a
Codex identity record carrying Option C semantics be encoded?

## 3. Candidate encodings for the Codex identity record

The encoding decision is bounded by the existing identity-record
contract baseline:

- `role_category` is a **single** enum value drawn from the seven
  baseline values in `docs/contracts/identity-record.md` and
  `docs/contracts/authority-matrix.md`. Multi-valued `role_category`
  is not currently permitted by the baseline contract and would
  require a separately Source-ratified privileged amendment to the
  contract and to `schemas/identity-record.schema.yaml` outside this
  draft's authority.
- `mutation_classes`, `allowed_repositories`, `signing_policy`,
  `authority_context`, `human_ratifier_roles`,
  `attestation_storage_path`, `ratification_storage_path`,
  `redaction_storage_path`, and `tenant_id` are required fields per
  the contract. Batch 2C must surface a Source-ratifiable value or
  posture for each.

The candidate encodings below are exhaustive for Batch 2C purposes.
Each option is described under the same headings:

- **`role_category` encoding** — which baseline enum value (or how
  many records) the option uses.
- **Where Option C semantics live** — how an architect-class envelope
  and an implementer-class envelope each find authorization under the
  encoding, given that the baseline `role_category` is single-valued.
- **Preserved invariants** — the Batch 2A §4 and Batch 2B §a /
  §b.4 invariants under the option (non-negotiable; restated here
  only to make the option's acceptance posture explicit).
- **Downstream consequences** — what the option implies for the
  later identity-record authoring envelope and for Batch 2D.
- **Schema/contract amendment cost** — whether the option requires
  any privileged mutation of
  `docs/contracts/identity-record.md`,
  `docs/contracts/authority-matrix.md`,
  `schemas/identity-record.schema.yaml`, or
  `docs/contracts/authority-matrix.yml`. **Batch 2C does not perform
  any such mutation under any option.**

### 3.1 Option A — single record, baseline `role_category = architect`

Codex is encoded as **one** Codex identity record whose baseline
`role_category` is `architect`. Implementer-class authoring is
authorized solely by the Source-ratified envelope's
`allowed_mutation_classes` and `consuming_actor_id` fields, not by a
second `role_category` value on the identity.

- **`role_category` encoding**: single value, `architect`.
- **Where Option C semantics live**: in the envelope. An
  architect-class envelope names the Codex identity as
  `consuming_actor_id` and authorizes architect-class mutation
  classes (e.g., `governance` and `docs`). An implementer-class
  envelope names the same Codex identity as `consuming_actor_id` and
  authorizes implementer-class mutation classes (`code` plus the
  `governance` and `docs` subset that implementer envelopes already
  cover under the Batch 2A §6.2 ratified posture). The envelope is
  the source of mutation-class authorization, consistent with the
  Batch 2B agent-interaction-model wording that "authority remains
  envelope-bound, not personality-bound."
- **Preserved invariants**:
  1. Single-valued `role_category` — no schema amendment.
  2. Source-only ratification (FR-008) — Source remains the sole
     ratifier of every privileged class regardless of envelope role.
  3. No merge / no deploy authority for Codex.
  4. Verifies-not-ratifies (FR-013 / FR-013a).
  5. One-driver-per-worktree and Codex-only worktree isolation.
  6. Author/approver separation (FR-007).
  7. Architect parity is authoring parity only (Batch 2A §6.3).
- **Downstream consequences**:
  - The future Codex identity record authoring envelope (a separately
    Source-ratified privileged `identity`-class envelope, outside
    this Batch 2C draft's authority) authors one Codex identity
    record file with `role_category = architect`.
  - Batch 2D evidence schema (separately Source-ratified) governs the
    review/architect/implementer evidence artifact class consistent
    with the Batch 2A §6.5 ratified posture (review evidence retained
    as a separate artifact class).
- **Schema/contract amendment cost**: **none**. The baseline
  `role_category` enum already contains `architect`; the baseline
  contract already treats `role_category` as single-valued; the
  seven-row authority matrix is unchanged.

### 3.2 Option B — single record, baseline `role_category = implementer`

Codex is encoded as **one** Codex identity record whose baseline
`role_category` is `implementer`. Architect-class authoring is
authorized solely by the Source-ratified envelope's
`allowed_mutation_classes` and `consuming_actor_id` fields, not by a
second `role_category` value on the identity.

- **`role_category` encoding**: single value, `implementer`.
- **Where Option C semantics live**: in the envelope, symmetrically
  to Option A but with the baseline anchored at `implementer` rather
  than `architect`. An architect-class envelope names the Codex
  identity as `consuming_actor_id` and authorizes architect-class
  mutation classes; an implementer-class envelope does the same for
  implementer-class mutation classes. The envelope is the source of
  mutation-class authorization.
- **Preserved invariants**: all invariants in Option A apply.
- **Downstream consequences**:
  - The future Codex identity record authoring envelope authors one
    Codex identity record file with `role_category = implementer`.
  - Batch 2D evidence schema framing is unchanged from Option A.
- **Schema/contract amendment cost**: **none**. Same as Option A.
- **Note vs. Batch 2A ratified wording**: Option B mirrors Option A
  mechanically but anchors the baseline at `implementer` rather than
  `architect`. Both options use the envelope as the seat of
  mutation-class authorization; the only difference is which baseline
  row a reviewer with a fresh clone sees first on the Codex identity
  record. The Batch 2A §3.3 and §6.1 ratified posture of "per-batch
  role assignment between `architect` and `implementer`" does not
  itself pin which of the two is the baseline anchor; that is the
  question this option surfaces.

### 3.3 Option C — two separate Codex identity records

Codex is encoded as **two** Codex identity records: one
architect-anchored, one implementer-anchored. Each record has its own
`role_category` (single-valued, baseline-conformant), its own
`agent_actor_id`, its own `agent_app_slug` (or a shared slug with
distinct actor ids), its own `mutation_classes`, its own
`signing_policy`, and so on.

- **`role_category` encoding**: two records, each single-valued; one
  `architect`, one `implementer`.
- **Where Option C semantics live**: in the **selection** of which
  identity the envelope names as `consuming_actor_id`. An
  architect-class envelope names the architect-anchored Codex
  identity; an implementer-class envelope names the
  implementer-anchored Codex identity. Each identity's
  `mutation_classes` is scoped to its baseline.
- **Preserved invariants**: all invariants in Option A apply.
  Additionally, author/approver separation (FR-007) becomes slightly
  easier to enforce because architect-authored artifacts and
  implementer-authored artifacts carry distinct `consuming_actor_id`
  values per envelope.
- **Downstream consequences**:
  - The future Codex identity record authoring envelope authors **two**
    Codex identity record files (or one file with two records,
    subject to the substrate's storage convention for multiple
    identities under a single tenant). Each record carries its own
    `authority_context.description`,
    `authority_context.governing_spec_refs`, and
    `authority_context.ratifier_authority_refs`.
  - Batch 2D evidence schema framing is unchanged from Option A.
- **Schema/contract amendment cost**: **none** to the identity-record
  contract or schema. Two single-valued records are already a
  permitted shape under the baseline. The cost is a doubled identity
  surface (two records, two `agent_actor_id` values, two
  `signing_policy` objects, etc.) and a doubled set of decisions in
  §6.

### 3.4 Option D — amend the identity-record schema to permit multi-valued `role_category`

Codex is encoded as **one** Codex identity record whose
`role_category` is **multi-valued** (e.g., the array
`["architect", "implementer"]`). This option requires a privileged
amendment to `docs/contracts/identity-record.md` and to
`schemas/identity-record.schema.yaml` to permit array-valued
`role_category`, and a corresponding amendment to the validator's
`identity` check.

- **`role_category` encoding**: array-valued; subset of the baseline
  seven enum values.
- **Where Option C semantics live**: on the identity itself. Both
  baseline role rows from the authority-matrix apply to the same
  Codex identity, and the envelope's `allowed_mutation_classes`
  narrows the per-batch authoring scope.
- **Preserved invariants**: the operational invariants (Source-only
  ratification, no merge/deploy, verifies-not-ratifies,
  one-driver-per-worktree, author/approver separation, architect
  parity as authoring parity only) hold. The **schema invariant** of
  single-valued `role_category` is **amended**.
- **Downstream consequences**:
  - A separately Source-ratified `schema`-class privileged envelope
    must precede the future Codex identity record authoring envelope.
    That schema-class envelope amends
    `docs/contracts/identity-record.md` and
    `schemas/identity-record.schema.yaml`. It also potentially
    requires re-running the validator against existing identity
    records and against the dogfood tenant fixture.
  - The future Codex identity record authoring envelope (also
    privileged `identity`-class, separately Source-ratified) then
    authors one Codex identity record file with array-valued
    `role_category`.
  - Batch 2D evidence schema framing is unchanged from Option A.
- **Schema/contract amendment cost**: **heavy**. Privileged
  `schema`-class mutation of
  `docs/contracts/identity-record.md` and
  `schemas/identity-record.schema.yaml`, validator amendment, and
  re-validation against existing identity records and the dogfood
  tenant. **Batch 2C does not perform any such mutation.** This
  option is explicitly recorded as **outside this draft's
  authority** and is listed for completeness so Source can decide
  whether to ratify the heavier amendment path separately.

## 4. Invariants preserved under every option

The following invariants apply regardless of which option Source
ratifies under §6.1. They are restated here to make this document
self-contained and to make the §3 option blocks compact.

1. **Source-only ratification** (Feature 001 FR-008). Source is the
   sole ratifier for every privileged mutation class. No option in
   §3 makes Codex a ratifier.
2. **No merge authority for Codex.** Per Feature 001 FR-008 and the
   Slice F policy in
   [`../delivery/MERGE_APPROVAL_CHECKLIST.md`](../delivery/MERGE_APPROVAL_CHECKLIST.md).
3. **No deploy authority for Codex.** The `deploy` class remains
   Source-only per Feature 001 FR-008 and the Slice F policy in
   [`../delivery/DEPLOYMENT_APPROVAL_POLICY.md`](../delivery/DEPLOYMENT_APPROVAL_POLICY.md).
4. **Verifies-not-ratifies** (Feature 001 FR-013 / Feature 002
   FR-013). Codex-authored evidence — review, architect, or
   implementer — never substitutes for Source ratification.
5. **One-driver-per-worktree.** A worktree occupied by Codex is not
   simultaneously occupied by Claude Code or by Nefarious for
   tracked-file authoring
   ([`../delivery/WORKTREE_RUNTIME_PROTOCOL.md`](../delivery/WORKTREE_RUNTIME_PROTOCOL.md)).
6. **Codex-only worktree isolation.** Codex acts only inside a
   Codex-owned isolated worktree separately authorized for that
   batch
   ([`./CODEX_FIRST_CLASS_SCOPE.md`](./CODEX_FIRST_CLASS_SCOPE.md) §4.4;
   [`../operations/CODEX_FIRST_CLASS_PROTOCOL.md`](../operations/CODEX_FIRST_CLASS_PROTOCOL.md) §2).
7. **No writes to an active Claude Code worktree.**
8. **Author/approver separation** (Feature 001 FR-007). The actor
   who authors a mutation is not its ratifier.
9. **Architect parity is authoring parity only.** Batch 2A §6.3
   ratified that architect parity is authoring parity, not
   ratification, merge, or deploy authority. This boundary is
   inherited by Batch 2C unmodified.
10. **Authority is envelope-bound, not personality-bound.** Batch 2B
    agent-interaction-model wording is inherited by Batch 2C
    unmodified. Whichever encoding Source ratifies under §6.1, the
    seat of mutation-class authorization remains the
    Source-ratified envelope.
11. **The seven-row baseline authority matrix is not amended.** Batch
    2C does not mutate `docs/contracts/authority-matrix.md` or
    `docs/contracts/authority-matrix.yml`. The seven-row FR-015 rule
    remains in effect.

## 5. Recommended option and rationale

Anchored in the Batch 2A and Batch 2B ratified wording carried
forward in §2, the **recommended option is Option A: single Codex
identity record with baseline `role_category = architect` and
implementer authoring authorized solely by implementer-class
envelopes** (§3.1), with **Option C: two separate Codex identity
records** (§3.3) as the conservative fallback if Source wants
physical identity separation between architect-acting Codex and
implementer-acting Codex.

Rationale:

1. **Preserves the Batch 2B envelope-bound wording.** Option A keeps
   the seat of mutation-class authorization in the
   Source-ratified envelope, which is exactly the wording Batch 2B
   landed: "authority remains envelope-bound, not
   personality-bound." Encoding a single baseline `role_category`
   and letting the envelope select implementer-class scope is the
   minimal encoding of that wording. Option B is mechanically
   equivalent but anchors the baseline at the narrower role and is
   slightly worse-aligned with the Batch 2A Source priority that
   Codex "should become a first-class architect like Claude Code,
   not merely a passive reviewer."
2. **Preserves the seven-row baseline.** Options A, B, and C all
   reuse existing baseline rows; the seven-row FR-015 rule is not
   amended. Option D would require a separately Source-ratified
   `schema`-class amendment to the baseline `identity-record.md`
   contract and `identity-record.schema.yaml`, which is heavier than
   the encoded posture requires.
3. **Minimal identity surface.** Option A authors one Codex identity
   record under the future privileged `identity`-class envelope.
   Option C authors two records, doubling the surface area for
   `agent_actor_id`, `signing_policy`, `authority_context`, and
   `mutation_classes` decisions. Option D adds a privileged
   `schema`-class envelope ahead of the `identity`-class envelope.
   Option A is the simplest implementation surface consistent with
   the Batch 2A / Batch 2B ratified wording.
4. **Author/approver separation remains enforceable.** FR-007 is
   enforceable under Option A because the envelope identifies the
   per-batch authoring scope; the ratifier is Source regardless of
   which envelope class is in effect. Option C makes FR-007 slightly
   more visible (two `consuming_actor_id` values, one per envelope
   class) but does not strengthen the underlying invariant; Option A
   is sufficient.
5. **Conservative fallback.** If Source prefers a physical identity
   separation between architect-acting Codex and implementer-acting
   Codex — for example, to make the architect/implementer split
   visible in attestation records and ratification records without
   needing to inspect the envelope — Option C is the recommended
   fallback. It preserves every invariant in §4 at the cost of a
   doubled identity surface.
6. **Option D is recorded for completeness only.** It is heavier than
   the encoded posture requires and is **outside this draft's
   authority**. Source may separately ratify Option D under a
   `schema`-class privileged envelope, but Batch 2C does not
   author it.

This recommendation is **non-binding**. Source's ratification of one
of the §6.1 options is what selects the encoding.

## 6. Required Source decisions

Each item below is a discrete decision Source is asked to ratify
under Batch 2C. The decisions are independent; Source MAY ratify
them individually or as a single bundle. Each item lists the
candidate values and the recommended value.

### 6.1 Codex identity record encoding

- **Candidate values**:
  - Option A — single record, baseline `role_category = architect`
    (§3.1).
  - Option B — single record, baseline `role_category = implementer`
    (§3.2).
  - Option C — two separate Codex identity records (§3.3).
  - Option D — amend identity-record schema to permit multi-valued
    `role_category` (§3.4); **outside this draft's authority** and
    requires a separately Source-ratified `schema`-class privileged
    amendment.
- **Recommended value**: Option A, with Option C as conservative
  fallback (see §5).
- **Source-ratified selection**: Option A — single record, baseline
  `role_category = architect`. Option C (two separate records) retained
  as conservative fallback only if a future authoring envelope proves
  Option A incompatible with checked-in schema truth. Option B and
  Option D are not selected.
- **Effect of ratification**: selects which encoding the future
  Codex identity record authoring envelope (separately Source-
  ratified, `identity`-class privileged) consumes. No identity
  record is authored under Batch 2C.

### 6.2 `authority_context`

The Codex identity record's `authority_context` object (per
[`../contracts/identity-record.md`](../contracts/identity-record.md)
§Authority context) must contain `description`,
`governing_spec_refs`, and `ratifier_authority_refs`. Batch 2C asks
Source to ratify the field values the future identity record
authoring envelope will adopt.

- **Candidate values for `description`**:
  - "Codex acts under per-batch Source-ratified architect/implementer
    authoring assignment per
    [`./CODEX_ROLE_AND_AUTHORITY_DECISION.md`](./CODEX_ROLE_AND_AUTHORITY_DECISION.md)
    §3.3 / §6.1 (Option C ratified) and the envelope-bound authority
    wording in
    [`../architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md)
    §a / §b.4. Authority remains envelope-bound, not
    personality-bound. Codex has authoring parity only: no
    ratification authority, no merge authority, no deploy authority."
  - A Source-amended description.
- **Recommended value**: ratify the description as written above.
- **Candidate values for `governing_spec_refs`** (non-empty array of
  repo-relative paths):
  - `docs/governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md`
  - `docs/architecture/agent-interaction-model.md`
  - `docs/governance/CODEX_FIRST_CLASS_SCOPE.md`
  - `docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md`
  - Any Source-added paths.
- **Recommended value**: the four paths above, plus this Batch 2C
  decision document
  (`docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`) once
  it reaches `Done`.
- **Candidate values for `ratifier_authority_refs`** (non-empty array
  of repo-relative paths):
  - `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`
  - `docs/contracts/authority-matrix.md`
  - Any Source-added paths.
- **Recommended value**: the two paths above.
- **Source-ratified selection**: description text as written above;
  `governing_spec_refs` = the four cited paths plus
  `docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`;
  `ratifier_authority_refs` =
  `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md` and
  `docs/contracts/authority-matrix.md`.
- **Effect of ratification**: pins the `authority_context` field
  values the future identity record authoring envelope will adopt.

### 6.3 `human_ratifier_roles`

- **Candidate values**:
  - `["source"]` — the sole ratifier role is Source.
  - A Source-amended list (e.g., adding a Source-delegated ratifier
    role for non-privileged classes once delegation is separately
    ratified).
- **Recommended value**: `["source"]`. Source-only ratification per
  Feature 001 FR-008 is the Phase 1 invariant; any delegation is a
  separately Source-ratified governance amendment outside Batch 2C.
- **Source-ratified selection**: `["source"]`.
- **Effect of ratification**: pins the `human_ratifier_roles` field
  the future identity record authoring envelope will adopt.

### 6.4 `allowed_repositories`

- **Candidate values**:
  - **Placeholder/unbound posture** — a substrate-internal placeholder
    value (or a non-empty placeholder array conforming to the
    contract's "non-empty fully qualified repo identifiers" rule)
    that explicitly signals deployment-time overlay binding. The
    contract requires the field to be non-empty; the placeholder
    value must satisfy that rule while making the unbound posture
    visible to a fresh-clone reviewer.
  - **Concrete repo identifier** — bind to a specific repository
    identifier under the source host now (treated as a separately
    Source-ratified `identity`-class binding decision; **forbidden
    under Batch 2C itself**).
  - **Defer the field decision** — defer the `allowed_repositories`
    value selection to the future identity record authoring envelope.
- **Recommended value**: **placeholder/unbound posture**, consistent
  with the Batch 2A §6.4 ratified posture (provider/tool/model/host/
  account binding remains placeholder/unbound upstream) and with
  [`./CODEX_FIRST_CLASS_SCOPE.md`](./CODEX_FIRST_CLASS_SCOPE.md) §3.7.
  The Source-ratified placeholder value will be chosen by the future
  identity record authoring envelope; Batch 2C does not pick the
  literal placeholder string.
- **Source-ratified selection**: placeholder/unbound posture; no
  concrete repository binding. Literal placeholder wording deferred
  to the future authoring envelope.
- **Effect of ratification**: pins the `allowed_repositories` posture
  the future identity record authoring envelope will adopt. **Batch
  2C does not bind any concrete repository identifier.**

### 6.5 `signing_policy`

- **Candidate values for `commit_signing_required`** (boolean):
  - `false` — commit signing not required at the substrate Phase 1
    layer; deferred to deployment-time overlay.
  - `true` — commit signing required; `commit_signing_method` must
    not be `none` per the contract.
- **Candidate values for `commit_signing_method`** (enum
  `gpg` / `ssh` / `none`):
  - `none` — appropriate when `commit_signing_required` is `false`
    and signing posture is deferred to deployment-time overlay.
  - `gpg` or `ssh` — appropriate when `commit_signing_required` is
    `true`.
- **Candidate values for `attestation_signing_required`** (boolean):
  - `false` — attestation signing not required at the substrate
    Phase 1 layer.
  - `true` — attestation signing required.
- **Recommended value**: **placeholder/unbound signing posture** —
  `commit_signing_required = false`, `commit_signing_method = none`,
  `attestation_signing_required = false`. This is consistent with the
  Batch 2A §6.4 ratified posture that concrete cryptographic
  identity binding is a deployment-time overlay decision. The
  contract's rule that `commit_signing_required = false` together
  with `commit_signing_method = none` is permitted (the "if `true`,
  must not be `none`" rule binds only the `true` branch) makes this
  posture contract-conformant.
- **Source-ratified selection**: `commit_signing_required = false`,
  `commit_signing_method = none`,
  `attestation_signing_required = false`. Placeholder/unbound signing
  posture; no signing enforcement authorized by this decision.
- **Effect of ratification**: pins the `signing_policy` posture the
  future identity record authoring envelope will adopt. Deployment-
  time overlay binding remains a separately Source-ratified
  decision.

### 6.6 Storage paths (`attestation_storage_path`, `ratification_storage_path`, `redaction_storage_path`)

Each path must be a non-empty repo-relative directory path; the
directory must exist at validation time (per
[`../contracts/identity-record.md`](../contracts/identity-record.md)
§Storage path rule). Existing tenant identity records under
`tenants/` use directories such as `tenants/<tenant-id>/attestations/`,
`tenants/<tenant-id>/ratifications/`, and
`tenants/<tenant-id>/redactions/`. Batch 2C asks Source to ratify the
storage-path posture the future identity record authoring envelope
will adopt.

- **Candidate values**:
  - **Substrate-internal storage** under a Codex-specific path that
    the future identity record authoring envelope creates (e.g.,
    `tenants/<placeholder-tenant>/codex/attestations/` and parallels
    for `ratifications` and `redactions`). The literal substrate-
    internal slug is pinned by §6.7.
  - **Tenant-overlay storage** — defer the storage-path selection
    to a later tenant-overlay decision, with the future identity
    record authoring envelope picking an interim
    substrate-internal placeholder path.
  - **Reuse of existing tenant paths** — bind to an existing tenant
    record's storage paths (treated as a tenant-overlay binding
    decision; **forbidden under Batch 2C itself**).
- **Recommended value**: **substrate-internal storage** under a
  Codex-specific path beneath the §6.7 placeholder tenant slug, with
  the literal path strings chosen by the future identity record
  authoring envelope. Batch 2C does not author the directories and
  does not bind tenant overlays.
- **Source-ratified selection**: substrate-internal storage under a
  Codex-specific path beneath the §6.7 placeholder tenant slug.
  Literal path strings deferred to the future authoring envelope.
- **Effect of ratification**: pins the storage-path posture the
  future identity record authoring envelope will adopt. The actual
  directory creation is part of the future privileged
  `identity`-class envelope, not Batch 2C.

### 6.7 `tenant_id`

The contract requires `tenant_id` to be a kebab-case slug matching
`^[a-z][a-z0-9-]*$`.

- **Candidate values**:
  - **Placeholder substrate-internal slug** (e.g., a name like
    `creator-engine-substrate` or another Source-chosen slug) that
    explicitly signals the substrate-internal placeholder posture
    and is not a real customer tenant.
  - **Tenant-overlay deferral** — defer tenant-id selection to a
    later tenant-overlay decision, with the future identity record
    authoring envelope picking the interim placeholder slug.
  - **Concrete tenant binding** — bind to a real tenant (treated as
    a separately Source-ratified tenant-overlay decision;
    **forbidden under Batch 2C itself**).
- **Recommended value**: **placeholder substrate-internal slug**,
  consistent with the Batch 2A §6.4 ratified placeholder/unbound
  posture. The literal slug is chosen by the future identity record
  authoring envelope. Batch 2C does not author a tenant record under
  `tenants/`.
- **Source-ratified selection**: placeholder substrate-internal slug;
  no concrete tenant binding. Literal slug deferred to the future
  authoring envelope.
- **Effect of ratification**: pins the `tenant_id` posture the future
  identity record authoring envelope will adopt.

### 6.8 Reaffirmation: Batch 2D evidence schema remains downstream

- **Statement to ratify**: **Batch 2C does not mutate
  `schemas/`, does not author or amend any review/architect/
  implementer evidence schema, and does not change the Batch 2A
  §6.5 ratified posture that review evidence remains a separate
  artifact class. Batch 2D (review/architect/implementer evidence
  schema) is downstream of Batch 2C and requires its own
  Source-ratified privileged `schema`-class envelope.**
- **Candidate values**:
  - Ratify the statement as written.
  - Ratify a Source-amended statement.
- **Recommended value**: ratify the statement as written.
- **Source-ratified selection**: ratify the statement as written —
  Batch 2D evidence schema remains downstream; Batch 2C does not
  mutate evidence schemas; Batch 2D remains a separate downstream
  Source-ratified gate.
- **Effect of ratification**: makes the non-mutation of evidence
  schemas part of the Batch 2C acceptance posture and preserves the
  Batch 2D gate as a separate Source decision.

## 7. Does not authorize

Batch 2C explicitly does NOT authorize any of the following. Each
item below requires its own separately Source-ratified envelope:

1. **Codex identity record creation.** No Codex identity record file
   is created or modified under Batch 2C. Identity-record authoring
   is a privileged `identity`-class mutation per Feature 001 FR-008.
2. **`docs/contracts/identity-record.md` mutation.** The identity
   record contract is not modified by Batch 2C. Any amendment is a
   privileged `governance` / `schema`-class mutation requiring its
   own Source-ratified envelope.
3. **`schemas/identity-record.schema.yaml` mutation.** The identity
   record schema is not modified by Batch 2C. Any amendment is a
   privileged `schema`-class mutation requiring its own
   Source-ratified envelope. This explicitly forecloses Option D
   (§3.4) under the Batch 2C boundary.
4. **`docs/contracts/authority-matrix.md` mutation.** The authority
   matrix contract is not modified. The seven-row FR-015 baseline
   rule remains in effect unchanged.
5. **`docs/contracts/authority-matrix.yml` mutation.** Not modified.
6. **Validator, template, example, or tenant mutation.** No
   validator under `validators/`, template under `templates/`,
   example under `examples/`, or tenant record under `tenants/` is
   modified or created.
7. **`docs/architecture/` mutation.** The Batch 2B
   agent-interaction-model wording is referenced but not modified.
8. **`specs/` mutation.** No spec is modified.
9. **`.github/` mutation.** No `.github/` content, branch protection
   settings, rulesets, CODEOWNERS, environments, visibility, topics,
   homepage, projects, wiki, merge-method settings, workflows, or
   secrets are mutated.
10. **Provider/tool/model/host/account binding.** No provider, tool,
    model, host installation, or account is bound under Batch 2C.
    Concrete bindings remain placeholder/unbound per Batch 2A §6.4.
11. **Codex authority expansion beyond authoring.** Codex acquires
    no ratification authority, no merge authority, and no deploy
    authority under Batch 2C regardless of which §6.1 option Source
    ratifies. Architect parity remains authoring parity only per
    Batch 2A §6.3.
12. **Dispatch automation.** No dispatch automation, Hermes
    dispatcher implementation, or worktree lifecycle automation is
    implemented. Feature 005 remains deferred.
13. **Deploy.** Nothing is deployed.

## 8. Cross-references

The following documents are cited as the substrate context for this
decision request. **None of these documents is modified by Batch
2C.** The four delivery/governance files in the §10 historical
five-path manifest were modified by the original Batch 2C commit
(PR #29 / `66a8074`); the follow-on reconciliation gate modifies
the seven-path boundary listed in §10.

| Document | Relevance | Modified by Batch 2C? |
|---|---|---|
| [`./CODEX_ROLE_AND_AUTHORITY_DECISION.md`](./CODEX_ROLE_AND_AUTHORITY_DECISION.md) | Batch 2A ratified role/authority decision. Carried forward in §2 as the Source-ratified basis. | No — landed; not re-litigated. |
| [`../architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md) §a / §b.4 | Batch 2B architecture actor/tool matrix and per-batch governed authoring pattern. Carried forward in §2 as the envelope-bound wording. | No — `docs/architecture/**` is not modified by Batch 2C. |
| [`./CODEX_FIRST_CLASS_SCOPE.md`](./CODEX_FIRST_CLASS_SCOPE.md) | CFC-1 Batch 1 governance scope; §3.7 (placeholder/unbound binding) and §4.4 (Codex worktree isolation) are inherited. §5 forward-scope row is updated for Batch 2C in the coherence updates listed in §10. | Yes — coherence update only; no scope broadening. |
| [`../operations/CODEX_FIRST_CLASS_PROTOCOL.md`](../operations/CODEX_FIRST_CLASS_PROTOCOL.md) | Operational protocol companion; pointer-only handoff, Codex-only worktree isolation, evidence requirements, stop lines, verifies-not-ratifies, transcript archival. | No — explicitly not modified by Batch 2C. |
| [`../contracts/identity-record.md`](../contracts/identity-record.md) | Identity record contract. Field rules in §3 and §6 reference this contract. | No — `docs/contracts/**` is not modified by Batch 2C. |
| [`../contracts/authority-matrix.md`](../contracts/authority-matrix.md) | Authority matrix contract; seven baseline `role_category` enum values; FR-015 per-row coverage rule. | No — `docs/contracts/**` is not modified by Batch 2C. |
| `schemas/identity-record.schema.yaml` | Identity record schema. Option D (§3.4) would require amending this file under a separate `schema`-class envelope; Batch 2C does not perform that amendment. | No — `schemas/**` is not modified by Batch 2C. |
| [`./AUTHORITY_AND_RATIFICATION_MODEL.md`](./AUTHORITY_AND_RATIFICATION_MODEL.md) | Source-only ratification authority; verifies-not-ratifies invariant. | No — not modified. |
| [`./MUTATION_CLASS_MODEL.md`](./MUTATION_CLASS_MODEL.md) | Authoritative mutation class definitions; basis for the §3 / §6 mutation-class implications. | No — not modified. |
| [`../delivery/WORKTREE_RUNTIME_PROTOCOL.md`](../delivery/WORKTREE_RUNTIME_PROTOCOL.md) | One-driver-per-worktree rule. §4 invariant. | No — not modified. |
| [`../delivery/MERGE_APPROVAL_CHECKLIST.md`](../delivery/MERGE_APPROVAL_CHECKLIST.md) | Slice F merge approval policy. §4 invariant. | No — not modified. |
| [`../delivery/DEPLOYMENT_APPROVAL_POLICY.md`](../delivery/DEPLOYMENT_APPROVAL_POLICY.md) | Slice F deploy approval policy. §4 invariant. | No — not modified. |

## 9. Acceptance posture for Batch 2C

This document satisfies the Batch 2C decision-request boundary if:

1. It carries forward (without re-litigation) the Batch 2A ratified
   Option C role/authority decision and the Batch 2B
   agent-interaction-model envelope-bound wording (§2).
2. It enumerates the §3 candidate encodings (single record at
   `architect`; single record at `implementer`; two records; schema
   amendment to multi-valued `role_category`) and explicitly marks
   schema-amendment Option D as outside this draft's authority.
3. For each candidate it lists `role_category` encoding, where
   Option C semantics live, preserved invariants, downstream
   consequences for the future identity record authoring envelope
   and for Batch 2D, and the schema/contract amendment cost
   (zero for Options A / B / C; heavy and out-of-scope for Option D).
4. It recommends one option (§5) with rationale anchored in the
   Batch 2A and Batch 2B ratified wording.
5. It lists eight required Source decisions (§6) as discrete items
   covering the identity record encoding, `authority_context`,
   `human_ratifier_roles`, `allowed_repositories`, `signing_policy`,
   storage paths, `tenant_id`, and the Batch 2D-remains-downstream
   reaffirmation.
6. It cross-references the documents in §8 without modifying any of
   them (the original Batch 2C commit modified the four delivery/
   governance files in the §10 historical five-path manifest; the
   follow-on reconciliation gate modifies the seven-path boundary
   listed in §10).
7. It includes a "does not authorize" block (§7) that explicitly
   forecloses identity-record creation, identity-record contract
   mutation, identity-record schema mutation, authority-matrix
   mutation, validator/template/example/tenant mutation,
   architecture/spec/.github mutation, provider binding, Codex
   authority expansion, dispatch automation, and deploy.

## 10. Batch 2C allowed path manifest (informational)

The original Batch 2C commit (PR #29 / merge commit `66a8074`)
mutated these five tracked paths (historical boundary):

```text
docs/delivery/BACKLOG.md
docs/delivery/DEPENDENCIES.md
docs/delivery/KANBAN.md
docs/governance/CODEX_FIRST_CLASS_SCOPE.md
docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md
```

The follow-on reconciliation gate (local-commit gate, post-PR #29)
corrects residual coherence gaps across the following seven tracked
paths (current reconciliation boundary):

```text
docs/delivery/BACKLOG.md
docs/delivery/DEPENDENCIES.md
docs/delivery/KANBAN.md
docs/delivery/README.md
docs/delivery/RISK_REGISTER.md
docs/governance/CODEX_FIRST_CLASS_SCOPE.md
docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md
```

The five-path list is the historical PR #29 boundary. The seven-path
list is the current reconciliation boundary. Both lists include this
document; only the reconciliation boundary includes `README.md` and
`RISK_REGISTER.md`. This manifest is restated here for
self-containment; the historical five-path boundary is also recorded
in the Source-ratified prompt and engineer handoff that authorized
the original Batch 2C commit.
