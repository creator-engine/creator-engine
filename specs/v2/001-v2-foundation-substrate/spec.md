# Feature Specification: Creator Engine v2.0 Foundation Substrate

**Feature Branch**: `v2/001-v2-foundation-substrate`
**Created**: 2026-05-29
**Status**: Draft
**Input**: User description: Establish the Creator Engine v2.0 foundation
substrate — a canonical `.ce/` active-state and governance namespace with an
enforceable tracked-vs-instance boundary, a hard `.hermes/` write-freeze for v2
flows, a read-only v1→v2 importer contract, canonical v2 terminology and role
surfaces, the v2 sidecar shape with risk-inventory placement, and the
authoritative v1→v2 crosswalk — so that every later v2 feature gate can be
authored and implemented on a clean v2 foundation without accruing legacy
state, terminology, or authority debt. This specification authors the
foundation gate `G2.001.0` (`.ce` namespace + state-boundary contract) and
frames the remaining foundation slices; it does not implement runtime code.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Canonical `.ce/` state root with an enforceable tracked-vs-instance boundary (Priority: P1)

The Operator and Controller need one canonical place for Creator Engine v2
active state and governance. The checkout today carries only `.hermes/`, which
is wholesale gitignored. v2 introduces `.ce/` as the canonical active-state
root and splits it into two zones: repo-authored governance/configuration that
is tracked and validator-visible, and runtime/session-local/credential-adjacent
state that is gitignored. A reader must be able to determine, from a tracked
contract alone, which `.ce/` subtree is tracked governance and which is ignored
instance state, and the boundary must refuse secret-bearing or runtime-only
files from entering tracked governance paths.

**Why this priority**: Every later v2 ledger, event, PCL, connector, and
directive-pack record writes into `.ce/`. Until the namespace exists and its
tracked-vs-instance boundary is defined and enforceable, any downstream feature
risks committing runtime or secret state, or losing tracked governance. This is
the prerequisite the whole v2 line depends on.

**Independent Test**: A reviewer with a fresh clone and the state-boundary
contract document can list every `.ce/` subtree, state whether it is tracked
governance or ignored instance state, and explain why a secret-bearing file in
a tracked governance path must be refused — without consulting any external
system or running runtime code.

**Acceptance Scenarios**:

1. **Given** the v2 foundation substrate spec, **When** a reviewer reads the
   state-boundary description, **Then** they can enumerate the tracked
   governance subtrees and the ignored instance/runtime subtrees of `.ce/` and
   name the rule that governs each.
2. **Given** a proposed file carrying secret material targeted at a tracked
   `.ce/` governance path, **When** the boundary is evaluated, **Then** the
   substrate contract states unambiguously that the write must be refused
   (fail-closed).
3. **Given** CE-event and PCL storage, **When** a reviewer inspects the
   boundary, **Then** canonical published records are distinguished from local
   spool/cache, and only the canonical records are eligible to be tracked or
   transport-synced.

---

### User Story 2 - `.hermes/` is frozen for active v2 state (Priority: P1)

New v2 flows must never write active Creator Engine product or governance state
to `.hermes/`. `.hermes/` remains valid only as archived v1 material, an
import/parser compatibility source, a historical/research location, a migration
source input, or Hermes-controller infrastructure outside CE product
governance.

**Why this priority**: `.ce/` and `.hermes/` coexist during the migration
window. Without a hard, stated write-freeze, the path of least resistance is
for new v2 code to keep writing the root it already knows, producing
dual-namespace drift that silently fragments authority and evidence.

**Independent Test**: A reviewer can read the write-freeze rule and classify any
proposed v2 write as compliant (targets `.ce/`) or non-compliant (treats
`.hermes/` as active v2 state), and confirm that legacy/import/archive reads of
`.hermes/` remain permitted.

**Acceptance Scenarios**:

1. **Given** a new v2 artifact, spec, sidecar, schema, policy, ledger, runtime
   record, validator, or CLI flow, **When** it writes active CE state, **Then**
   it targets a canonical `.ce/` path and not `.hermes/`.
2. **Given** a v1→v2 importer, **When** it reads legacy `.hermes/` material,
   **Then** it may read but must never write `.hermes/`, and it emits canonical
   `.ce/` outputs.
3. **Given** an explicit legacy/import/crosswalk/historical context, **When**
   `.hermes/` is referenced read-only, **Then** the reference is permitted.

---

### User Story 3 - Read-only v1→v2 importer contract (Priority: P1)

A tenant migrating from v1 needs a bounded, read-only way to bring archived
`.hermes/` and v1 artifacts into the v2 `.ce/` shape. The importer reads legacy
material, maps it through the v1→v2 crosswalk, and either emits canonical `.ce/`
outputs or produces a dry-run migration report with provenance. It never
mutates `.hermes/`. If no importable v1 artifacts exist, it exits cleanly with
an explicit no-op result. Real tenant migration activation remains a separate
Operator-ratified decision.

**Why this priority**: The v2 reset must not strand v1 history. A read-only,
provenance-bearing importer is what lets v2 stay a clean foundation while
preserving the ability to migrate prior work safely and reversibly.

**Independent Test**: A reviewer can trace one example legacy record through the
importer contract to a canonical `.ce/` output (or a dry-run report entry) and
confirm the output carries provenance and crosswalk metadata, that `.hermes/`
is unmodified, and that an empty input yields a clean no-op.

**Acceptance Scenarios**:

1. **Given** importable legacy `.hermes/`/v1 artifacts, **When** the importer
   runs in dry-run, **Then** it produces a migration report mapping each source
   to its canonical `.ce/` target with provenance, mutating nothing.
2. **Given** importable artifacts and an emit run, **When** the importer emits,
   **Then** every imported record carries provenance and crosswalk metadata and
   no record reintroduces `.hermes/` as active v2 state.
3. **Given** no importable v1 artifacts, **When** the importer runs, **Then** it
   exits cleanly with an explicit no-op result rather than an error.

---

### User Story 4 - v2 terminology and role surfaces are canonical from inception (Priority: P2)

New v2 artifacts emit canonical v2 terminology and role surfaces. The
human-authority machine role is `operator`; `source` is accepted only as an
import/parser alias and is never emitted by new v2 artifacts. The agent role
surface adds `agent_reviewer` as an active advisory role and `agent_ratifier`
as a reserved-inactive placeholder that must be rejected for any active
authority binding in v2. Privileged-class ratification and emergency governed
override remain Operator-only in every mode.

**Why this priority**: If new artifacts can emit legacy terms or bind authority
to the reserved agent role, the foundation accrues exactly the debt the v2 reset
exists to prevent, and the Operator-only privileged floor is at risk.

**Independent Test**: A reviewer can read the terminology/role canon and
classify a sample artifact as compliant or non-compliant (emits `operator`, not
`source`; treats `agent_reviewer` as advisory-only; treats `agent_ratifier` as
reserved-inactive), and confirm that privileged ratification and emergency
override route only to the Operator.

**Acceptance Scenarios**:

1. **Given** a new v2 artifact, **When** it names the human-authority machine
   role, **Then** it emits `operator` and never emits `source`.
2. **Given** a tenant policy, envelope, runtime record, or ledger entry, **When**
   it attempts to bind active authority to `agent_ratifier`, **Then** the
   substrate contract states the binding must be rejected.
3. **Given** any operating mode (`strict`, `auto`, `transcendence`), **When** a
   privileged-class mutation or an emergency override is proposed, **Then** the
   ratifying authority is the Operator and not any agent role.

---

### User Story 5 - v2 sidecar shape and risk-inventory placement (Priority: P2)

Standard Spec Kit `spec.md`, `plan.md`, and `tasks.md` stay free of
Creator-Engine-specific metadata. CE metadata lives in adjacent `*.ce.yml`
sidecars (`spec.ce.yml`, `plan.ce.yml`, `tasks.ce.yml`). The authoritative
`risk_inventory` for a spec lives in its `spec.ce.yml`, and required validation
is mapped against each declared risk. Legacy `*.creator-engine.yml` sidecars are
accepted only as import/parser aliases.

**Why this priority**: OD-24 forbids inline CE metadata while CE needs rich
governance metadata. A defined sidecar shape and risk-inventory placement is
what lets every later v2 spec carry its governance without polluting the
standard Markdown.

**Independent Test**: A reviewer can confirm that this feature's CE metadata
lives entirely in `spec.ce.yml` (and the crosswalk/ADR), that `spec.md` carries
no CE-specific blocks, and that the risk inventory and its required validation
mapping are present in the sidecar.

**Acceptance Scenarios**:

1. **Given** a v2 spec, **When** a reviewer inspects `spec.md`, **Then** it
   contains no CE-specific governance/authority/ledger/risk/autonomy/connector
   metadata blocks.
2. **Given** a risk-bearing v2 spec, **When** a reviewer inspects `spec.ce.yml`,
   **Then** a non-empty `risk_inventory` is present and each declared risk maps
   to required validation.
3. **Given** a legacy `*.creator-engine.yml` sidecar, **When** v2 tooling
   encounters it, **Then** it is treated as an import alias only and new v2
   artifacts emit `*.ce.yml`.

---

### User Story 6 - Authoritative v1→v2 crosswalk register (Priority: P2)

A single tracked crosswalk at `specs/v2/_crosswalk.yml` records the
machine-readable v1→v2 mappings: `source`→`operator`, `.hermes/`→`.ce/`, the old
Feature 008–021 working labels→`specs/v2/NNN`, and `*.creator-engine.yml`→
`*.ce.yml`. Importers, validators, and roadmap tooling treat it as
authoritative; `.ce/crosswalks/` may hold derived/runtime/tenant-expanded
material but must not silently supersede it.

**Why this priority**: A living crosswalk is what keeps importers and validators
routing correctly as features land. If the mapping rots or forks, imports
misroute and the clean-foundation guarantee erodes.

**Independent Test**: A reviewer can resolve each of the four canonical mappings
from `specs/v2/_crosswalk.yml` alone and confirm the file declares itself
authoritative over any derived `.ce/crosswalks/` material.

**Acceptance Scenarios**:

1. **Given** the crosswalk register, **When** a reviewer looks up a v1 term or
   path, **Then** its v2 canonical mapping and its disposition (e.g. import
   alias, retarget, rejected→v2) are stated.
2. **Given** a v2 spec that supersedes or imports v1 material, **When** it is
   reviewed, **Then** it can reference a live crosswalk entry.
3. **Given** derived material under `.ce/crosswalks/`, **When** it diverges from
   the register, **Then** the register remains authoritative.

---

### User Story 7 - Migrated v1 tenants default to strict (Priority: P3)

A tenant migrated from v1 defaults to `strict` operating mode. Import or
migration must not infer or grant `auto` or `transcendence` authority. Elevated
autonomy is opt-in per tenant and requires explicit Operator-ratified policy. If
prior autonomy posture cannot be determined, the importer chooses `strict`,
records the uncertainty in provenance, and requires Operator ratification before
any delegated autonomy.

**Why this priority**: The safest default protects the Operator-only privileged
floor during migration. It is P3 because it governs migration behavior rather
than the foundational namespace itself, but it must be stated at the foundation
so no later gate infers autonomy from import.

**Independent Test**: A reviewer can confirm that a migrated tenant with unknown
prior posture lands in `strict`, that the uncertainty is recorded in provenance,
and that enabling `auto`/`transcendence` requires explicit Operator-ratified
policy.

**Acceptance Scenarios**:

1. **Given** a migrated v1 tenant, **When** no autonomy policy is explicitly
   ratified, **Then** the tenant operates in `strict`.
2. **Given** an import that cannot determine prior autonomy posture, **When** it
   completes, **Then** it selects `strict`, records the uncertainty, and
   requires Operator ratification before any delegated autonomy.
3. **Given** a request to enable `auto` or `transcendence`, **When** it is
   processed, **Then** it requires explicit Operator-ratified policy and never
   delegates privileged-class authority.

---

### Edge Cases

- What happens when both `.hermes/` and `.ce/` contain a record of the same
  logical kind during migration? The boundary and write-freeze rules make `.ce/`
  the only active v2 state; `.hermes/` is read-only legacy/import context.
- How does the system handle a tracked governance file that later acquires
  secret material? The fail-closed secret policy refuses it from tracked `.ce/`
  governance paths.
- What happens when the importer finds partially-readable or ambiguous v1
  artifacts? It records the uncertainty in provenance and defaults to the safest
  posture (`strict`, no inferred autonomy), surfacing the gap for Operator
  review rather than guessing.
- How does the system handle a new v2 artifact that emits a legacy `source`
  value or treats `.hermes/` as active state? It is non-compliant with the
  terminology canon and write-freeze; later foundation slices add validators
  that fail closed on such emissions.
- What happens if `.ce/crosswalks/` derived material contradicts
  `specs/v2/_crosswalk.yml`? The tracked register is authoritative and the
  derived material must not silently supersede it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The substrate MUST define a canonical v2 active-state and
  governance root, `.ce/`, distinct from the legacy `.hermes/` root.
- **FR-002**: The substrate MUST define a state-boundary contract that
  enumerates, for the `.ce/` tree, which subtrees are tracked
  governance/configuration and which are ignored runtime/instance state.
- **FR-003**: The substrate MUST classify repo-authored governance/configuration
  subtrees (including policy, contracts, directive-packs, extensions, hooks,
  connector-contracts, authority, schemas, templates, and crosswalks) as tracked
  and validator-visible.
- **FR-004**: The substrate MUST classify runtime, session-local, generated,
  cache, credential-adjacent, and machine-local subtrees (including runtime,
  session-state, pane-registry, worktree-leases, active-work-ledger,
  side-effect-ledger spool, cache, tmp, secrets, credentials, and local) as
  ignored instance state.
- **FR-005**: The substrate MUST distinguish canonical CE-event and PCL records
  (eligible to be tracked or transport-synced when intentionally published as
  governance/evidence) from local spool/cache (ignored operational state).
- **FR-006**: The state boundary MUST fail closed on secret-bearing or
  runtime-only files entering tracked `.ce/` governance paths.
- **FR-007**: New v2 flows MUST NOT write active CE product or governance state
  to `.hermes/`; `.hermes/` remains valid only as archived v1 material,
  import/parser compatibility source, historical/research location, migration
  source input, or Hermes-controller infrastructure outside CE product
  governance.
- **FR-008**: The substrate MUST define a read-only v1→v2 importer contract that
  reads legacy `.hermes/` and v1 artifacts, maps them through the v1→v2
  crosswalk, and emits either canonical `.ce/` outputs or a dry-run migration
  report with provenance; the importer MUST NOT mutate `.hermes/`.
- **FR-009**: The importer MUST exit cleanly with an explicit no-op result when
  no importable v1 artifacts exist.
- **FR-010**: Imported records MUST carry provenance and crosswalk metadata and
  MUST NOT reintroduce `.hermes/` as active v2 state.
- **FR-011**: New v2 artifacts MUST emit `operator` as the human-authority
  machine role; `source` MUST be accepted only as an import/parser alias and
  MUST NOT be emitted by new v2 artifacts.
- **FR-012**: New v2 artifacts MUST emit the canonical ratification line
  `Operator ratifies prompt:` and MUST accept the legacy `Source ratifies
  prompt:` form only on import.
- **FR-013**: The role surface MUST define `agent_reviewer` as an active
  advisory/evidence-bearing role that may review, test, critique, and recommend,
  and MUST NOT permit it to ratify privileged-class mutations, authorize
  emergency governed override, or satisfy Operator-only requirements.
- **FR-014**: The role surface MUST define `agent_ratifier` as reserved-inactive
  — schema-present only — and MUST require rejection of any active authority
  binding, policy, envelope, runtime record, connector action, ledger entry, or
  ratification act that uses it in v2; activation is reserved to the named
  post-v2 `AOS-RATIFIER-MILESTONE`.
- **FR-015**: Privileged mutation classes (`deploy`, `governance`, `identity`,
  `security`, `attestation`, `redaction`) and emergency governed override MUST
  remain Operator-only in every operating mode.
- **FR-016**: CE-specific metadata MUST live in adjacent `*.ce.yml` sidecars
  (`spec.ce.yml`, `plan.ce.yml`, `tasks.ce.yml`) and MUST NOT be embedded in the
  standard Spec Kit Markdown; legacy `*.creator-engine.yml` sidecars MUST be
  accepted only as import/parser aliases.
- **FR-017**: The authoritative `risk_inventory` for a v2 spec MUST live in its
  `spec.ce.yml`; it MUST be non-empty for security-, identity-, deploy-,
  governance-, privileged-class-, connector-, migration-, state-boundary-, or
  external-side-effect-relevant specs, and required validation MUST be mapped
  against each declared risk.
- **FR-018**: The substrate MUST define `specs/v2/_crosswalk.yml` as the single
  authoritative spec-level v1→v2 crosswalk; `.ce/crosswalks/` may contain
  derived/runtime/tenant-expanded material but MUST NOT silently supersede the
  tracked register.
- **FR-019**: Canonical requirement identifiers MUST use the scoped form
  `RV2-<specNNN>-<reqNNN>` (e.g. `RV2-001-001`).
- **FR-020**: Gate identifiers MUST use `G2.<feature>.<slice>` where `<feature>`
  binds to the canonical `specs/v2/NNN` number (e.g. `specs/v2/001` →
  `G2.001.0`).
- **FR-021**: v2 architecture decision records MUST use the `ADR-V2-NNN`
  namespace under `specs/v2/adrs/`, MUST reference the relevant Operator decision
  ledger entries, and MUST NOT ratify authority.
- **FR-022**: Migrated v1 tenants MUST default to `strict`; `auto` and
  `transcendence` MUST be opt-in per tenant under explicit Operator-ratified
  policy; when prior autonomy posture is indeterminate the importer MUST select
  `strict`, record the uncertainty, and require Operator ratification before any
  delegated autonomy.
- **FR-023**: v2.0 MUST NOT perform destructive removal of v1 artifacts or
  aliases; legacy `source` and `.hermes/` remain readable for
  import/parser/crosswalk/archive/history, and any destructive removal requires a
  separately Operator-ratified deprecation/removal gate.
- **FR-024**: This specification MUST NOT authorize or contain runtime
  implementation; the foundation substrate is defined by tracked
  spec/schema/governance documentation artifacts, with runtime behavior landing
  in later, separately-ratified gates.

### Key Entities *(include if feature involves data)*

- **`.ce/` state root**: the canonical v2 active-state and governance namespace;
  composed of a tracked governance zone and an ignored instance/runtime zone.
- **State-boundary contract**: the artifact that enumerates each `.ce/` subtree's
  zone and the fail-closed secret/runtime policy; the v2 extension of the
  existing v1 state-boundary contract.
- **v1→v2 importer contract**: the read-only migration surface that maps legacy
  `.hermes/`/v1 material to `.ce/` outputs or a dry-run report with provenance.
- **v2 sidecar (`*.ce.yml`)**: the adjacent CE-metadata carrier for a Spec Kit
  artifact; holds authority, risk inventory, operating-mode relevance, and
  crosswalk pointers.
- **v1→v2 crosswalk register**: the authoritative tracked mapping at
  `specs/v2/_crosswalk.yml`.
- **Role surface**: the human-authority and agent role set — `operator`
  (canonical), `source` (import alias), `agent_reviewer` (active advisory),
  `agent_ratifier` (reserved-inactive).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can enumerate 100% of the `.ce/` subtrees named in the
  state-boundary description and correctly classify each as tracked governance or
  ignored instance state from the tracked artifacts alone.
- **SC-002**: Zero CE-specific metadata blocks appear in `spec.md`; 100% of this
  feature's CE metadata is carried in `spec.ce.yml`, `specs/v2/_crosswalk.yml`,
  and the ADR.
- **SC-003**: Every declared risk in the spec's `risk_inventory` maps to at least
  one required-validation entry (100% risk-to-validation coverage).
- **SC-004**: The four canonical crosswalk mappings (`source`→`operator`,
  `.hermes/`→`.ce/`, Feature 008–021→`specs/v2/NNN`, `*.creator-engine.yml`→
  `*.ce.yml`) are each resolvable from `specs/v2/_crosswalk.yml` alone.
- **SC-005**: A reviewer can classify any sample v2 write as compliant or
  non-compliant against the `.hermes/` write-freeze with no ambiguity.
- **SC-006**: A migrated tenant with indeterminate prior posture deterministically
  lands in `strict` with the uncertainty recorded in provenance.

## Assumptions

- The Operator remains the apex authority; this spec preserves the Operator-only
  privileged floor and does not design or activate agent ratification authority.
- The v1 substrate (existing schemas, validators, `ce` runtime, and `.hermes/`
  archive) remains in place and readable; v2 is a clean foundation layered
  beside it, not a destructive replacement.
- Later foundation slices (`G2.001.1`–`G2.001.4`) author the terminology
  validator, role-enum schema, v2 sidecar schema, and crosswalk validator that
  make the rules in this spec machine-enforceable; this gate (`G2.001.0`)
  establishes the namespace, state-boundary contract, write-freeze, and importer
  contract that those slices build on.
- The formal `spec.ce.yml` schema is authored in a later foundation slice
  (`G2.001.3`); this spec's own `spec.ce.yml` is a forward-declared bootstrap
  sidecar that the later schema will validate.
- Real tenant migration activation is a separate Operator-ratified decision; the
  importer defined here is read-only and dry-run-capable only.
- This is a documentation/spec-authoring gate; no runtime code, commit, push,
  PR, merge, or external side effect is in scope.
