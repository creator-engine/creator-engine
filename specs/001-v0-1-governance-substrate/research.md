# Research: Creator Engine v0.1 Governance Substrate

**Phase**: 0 (Outline & Research) | **Date**: 2026-05-09

This document records the research-time decisions that informed the
implementation plan. The five user-facing clarifications already landed in
spec.md (Clarifications, Session 2026-05-09); this document records
*technology* and *layout* decisions made by the planner and not yet recorded
in spec.md.

The spec contains no open `NEEDS CLARIFICATION` markers. Every decision
below maps to one or more functional requirements or success criteria from
spec.md.

---

## Decision 1: Validator implementation language — Python 3.11

**Decision**: Implement the validator (`validators/`) as a Python 3.11
package with a CLI entrypoint (`python -m creator_engine_validator`).

**Rationale**:
- Python is already the substrate language of Spec Kit and Claude Code, so
  contributors and tenants can be assumed to have a recent Python on their
  workstation; this matches FR-026's "fresh `git clone` without external
  service calls" while not requiring a compiled binary release pipeline.
- Python's standard library plus two pure-Python dependencies (`PyYAML`,
  `jsonschema`) is enough to express every check the spec demands, without
  introducing a daemon, a hosted policy engine, or a non-repo state store
  (constitution principle II).
- A scripting language keeps the validator small enough to remain auditable
  by the same reviewers who approve the contracts it enforces, which is
  what FR-027 ("contract-referenced error citing the specific field or
  rule violated") requires of the implementation.

**Alternatives considered**:
- *Bash + `yq` + `jq`*: Rejected. Cross-artifact checks (FR-027a:
  duplicate-spec-id detection, mutation class/action mismatch, lifecycle
  ordering, no-LIMITLESS string scan with auditable mapping back to the
  identifier list) would each require ad-hoc shell pipelines; error
  messages tying back to specific FRs (FR-027) become brittle string
  concatenation; tenant onboarding would inherit `yq`/`jq` version
  sensitivity that we cannot pin without a lockfile.
- *Go binary*: Rejected for v0.1. Distributing a compiled validator means
  either a release pipeline (out of scope for v0.1 per FR-026's "fresh
  `git clone`") or asking tenants to have Go installed, which is a higher
  bar than Python on most engineering workstations.
- *Node.js / TypeScript*: Rejected. Adds a `node_modules`/lockfile
  dependency surface for a substrate that explicitly ships no JS code.
- *Java/Rust*: Rejected as overkill for a YAML-and-Markdown linter.

---

## Decision 2: YAML parser — PyYAML; schema engine — `jsonschema` (Draft 2020-12)

**Decision**: Use `PyYAML` (safe loader only) for parsing all YAML files,
and `jsonschema` (Draft 2020-12) for schema validation. Pin both in
`validators/requirements.txt`. Schemas under `schemas/` are authored in
YAML for human readability but conform to JSON Schema Draft 2020-12.

**Rationale**:
- Both libraries are pure Python and are distributed for v0.1 through a
  checked-in offline wheelhouse (`validators/wheelhouse/`) pinned by
  `validators/requirements.txt`. This preserves "no external service
  calls" and "runs from a fresh `git clone`" (FR-026) while keeping the
  validator implementation small.
- JSON Schema is a widely understood contract format; expressing every
  identity/sidecar/attestation/ratification/redaction record schema as
  JSON Schema makes the contracts auditable independent of the validator
  implementation, which matters for SC-001 ("answer all five governance
  questions without consulting any external system").
- PyYAML's `safe_load` rejects arbitrary tag execution, which is the
  posture FR-020a's "validator parses by configured directory glob + YAML
  parse only" assumes.

**Alternatives considered**:
- *`ruamel.yaml`*: Rejected; round-trip preservation is unnecessary for a
  read-only validator.
- *`pydantic`*: Rejected for v0.1; introduces an additional schema
  representation that contracts would have to be authored against, when
  JSON Schema authored in YAML is already enough.
- *Hand-rolled validation*: Rejected; we would lose the ability to point
  reviewers at standalone schema files for audit, and FR-027's
  "contract-referenced error" property becomes a free-form-string problem.

---

## Decision 3: Schemas authored in YAML, conforming to JSON Schema Draft 2020-12

**Decision**: Every schema under `schemas/` is a YAML file whose content
is a valid JSON Schema (Draft 2020-12) document. Filenames follow
`<artifact>.schema.yaml` (e.g. `identity-record.schema.yaml`).

**Rationale**:
- YAML is the same encoding as the records the schemas govern (sidecars,
  identity records, attestation/ratification/redaction records per
  FR-020a). Authoring schemas in YAML keeps the substrate's own contracts
  in one shape.
- JSON Schema Draft 2020-12 supports `$id`, `$ref`, `oneOf`, `pattern`,
  and `unevaluatedProperties`, which we need to express "exactly one of
  pre-merge/post-merge attestation state" (FR-004) and "no fields beyond
  the declared schema" rules.
- Authoring schemas in YAML rather than JSON keeps line-level diffs
  readable in PRs, which matters when the schema itself is a
  Creator-Engine-governed artifact.

**Alternatives considered**:
- *JSON-encoded schemas*: Rejected; harder to comment in PR diffs, no
  benefit since we already have a YAML parser in dependencies.
- *OpenAPI*: Rejected; we have no HTTP API in v0.1 (constitution
  principle II).
- *CUE / Dhall*: Rejected; introduces a substrate-internal DSL contributors
  must learn, fighting the YAGNI principle (XI).

---

## Decision 4: Sidecar filename convention and adjacency rule

**Decision**: Creator Engine wrapper sidecars use the canonical filenames
`spec.creator-engine.yml`, `plan.creator-engine.yml`,
`tasks.creator-engine.yml` and MUST live in the same directory as the
Spec Kit file they wrap. The validator pairs sidecars to Spec Kit files
by directory + canonical name; no other discovery rule is in scope.

**Rationale**:
- The clarification at spec.md §Clarifications/Session 2026-05-09 locks
  "pure sidecar" and the canonical filenames; this decision records the
  lookup rule the validator implements.
- A directory-adjacent rule keeps the substrate file-tree-only and avoids
  introducing any global registry, which would violate principle II
  (Repo-Native) and add discovery state outside the repo.

**Alternatives considered**:
- *Front-matter merge*: Rejected by the locked clarification (and by
  principle X — vanilla Spec Kit files MUST remain byte-identical).
- *Content-addressed sidecars indexed by `id`*: Rejected as YAGNI for
  v0.1 — directory adjacency is unambiguous because Spec Kit already
  one-feature-per-folder.

---

## Decision 5: Validator CLI surface

**Decision**: A single CLI entrypoint, invokable as `python -m
creator_engine_validator <subcommand> [paths…]`. Subcommands for v0.1:

- `check` — run all enabled checks against a target path (a single
  feature folder, a tenant directory, or the whole repo). Default for
  CI-style invocation.
- `check-examples` — convenience wrapper that runs `check` against
  `examples/well-formed/` and `examples/malformed/`, asserting the
  documented success/failure shape per FR-028/FR-029. The wrapper exits
  `0` when the well-formed fixtures pass and every malformed fixture
  fails with its expected FR citation; it exits `1` only when those
  expectations are not met.
- `scan-no-limitless` — runs only the FR-024 / FR-024a no-LIMITLESS
  exact-string scan against the four generic-contract paths.
- `--list-checks` — prints the enabled checks and the FRs each one
  enforces, supporting reviewer audits per FR-027.

Exit codes: `0` success, `1` validation failure, `2` invocation error.
Output format: human-readable by default, `--json` for machine-readable
runs.

**Rationale**:
- A single entrypoint keeps the surface auditable; subcommands map to
  user stories (US7 acceptance scenarios 1–3).
- `--json` is needed so the substrate's own `tasks.creator-engine.yml`
  can record validator output as Verification Evidence (FR-014) without
  forcing reviewers to grep human-readable text.
- `--list-checks` is the mechanism by which FR-027's "contract-
  referenced error citing the specific field or rule violated" is made
  reviewable: a reviewer can ask "which check enforces FR-024a?" and get
  a concrete answer from the binary.

**Alternatives considered**:
- *Multiple CLIs* (one per check): Rejected; multiplies invocation
  complexity without benefit.
- *Pytest as the user-facing surface*: Rejected; pytest is the test
  framework for the validator's own tests, not the substrate's
  validation surface for tenants.

---

## Decision 6: No-LIMITLESS string scan — exact-substring, list-driven

**Decision**: `tenants/limitless/limitless-identifiers.yml` contains the
canonical non-secret identifier list (host names, channel names, bot
slugs, bot actor ids, repository names) referenced by FR-024a. The
validator's `scan-no-limitless` check loads this list and performs an
exact-substring search across every file under the four generic-contract
paths (`docs/contracts/`, `schemas/`, `validators/`, `templates/`).

**Rationale**:
- An exact-substring check is reproducible, auditable, and answers the
  exact wording of SC-004 ("0 LIMITLESS-specific identifiers from the
  canonical list appear under the generic-contract paths, as confirmed
  by a reproducible exact-string search").
- Sourcing the list from the LIMITLESS fixture (rather than hard-coding
  it in `validators/`) keeps generic-contract paths LIMITLESS-free
  recursively: even the validator does not contain LIMITLESS strings.
- Substring matching avoids false negatives from regex escaping bugs;
  the list is small enough that linear scan per file is well under the
  60-second SC-007 budget.

**Alternatives considered**:
- *Regex with word boundaries*: Rejected; risks false negatives on
  hyphenated or dotted identifiers, and risks reviewer disagreement
  about what counts as a "boundary." Substring is unambiguous.
- *Hard-coded list in `validators/`*: Rejected; would put LIMITLESS
  strings inside `validators/`, which is itself a generic-contract path
  per FR-024.
- *AST-aware scanner*: Rejected as YAGNI; substring is sufficient and
  auditable.

---

## Decision 7: Lifecycle state machine encoded as schema + check

**Decision**: The six-state lifecycle (`draft → ready → in_progress →
verified → ratified → done`, FR-013a) is encoded twice: (a) the
`status` enum in `spec-wrapper-sidecar.schema.yaml` enumerates exactly
those six values; (b) a dedicated `lifecycle.py` check verifies, across
the spec sidecar plus its associated attestation/ratification records,
that transitions are gated as the spec describes.

**Rationale**:
- A pure-enum schema is not enough to enforce ordering rules (FR-013a
  forbids skipping or backfilling states); cross-artifact lookup is
  needed to verify that `verified → ratified` had a ratifier distinct
  from the author (FR-007), and that `ratified → done` is backed by a
  pre-merge attestation that has been finalized with a merge reference
  (FR-004).
- Separating the two concerns (vocabulary vs. ordering) keeps the
  schema file small enough to be read as a contract and keeps the
  ordering logic in one auditable function.

**Alternatives considered**:
- *Implicit lifecycle*: Rejected — FR-013a's "skipping or backfilling
  states out of order is a contract violation" requires an explicit
  transition check.
- *State machine library*: Rejected as YAGNI for six states; a flat
  `allowed_next` mapping suffices.

---

## Decision 8: Mutation-class taxonomy storage — generic baseline + tenant overlay

**Decision**: The baseline mutation classes (FR-006: `docs`, `code`,
`schema`, `deploy`, `governance`, `identity`, `security`, `attestation`,
`redaction`) and the reserved-action vocabulary (FR-008) are defined in
`docs/contracts/mutation-class-taxonomy.md` and machine-encoded in
`schemas/mutation-class.schema.yaml`. Tenant extension classes are
declared in the tenant's own `mutation-classes.yml` (e.g.
`tenants/limitless/mutation-classes.yml`), which validates against the
same schema with `extends_baseline: true`.

**Rationale**:
- Splitting baseline (substrate-shipped) from extensions (tenant-shipped)
  matches the locked clarification ("Baseline substrate class list plus
  the reserved-action vocabulary; tenants MAY extend") and keeps
  generic-contract paths LIMITLESS-free.
- Encoding both the baseline and any tenant extension against the same
  `mutation-class.schema.yaml` makes FR-006's "tenant-extension classes
  MUST also declare an action vocabulary against the substrate's
  reserved-action vocabulary and MUST NOT redefine baseline class
  semantics" machine-checkable.

**Alternatives considered**:
- *Single substrate-wide list*: Rejected — locked clarification
  permits tenant extensions.
- *Free-form per-tenant taxonomies*: Rejected — would let a tenant
  redefine `governance` or `deploy` permissions, weakening FR-008.

---

## Decision 9: Authority matrix layout — generic rows + tenant overlay

**Decision**: `docs/contracts/authority-matrix.md` and
`schemas/authority-matrix.schema.yaml` define the authority matrix shape
and ship the concrete baseline rows for each baseline mutation class
(FR-015's "concrete rows for every baseline mutation class declared in
FR-006"). Tenants overlay tenant-specific rows in
`tenants/<name>/authority-matrix-overlay.yml` (LIMITLESS-specific role
names live only there per FR-015's tenant-fixture rule).

**Rationale**:
- Mirrors the mutation-class baseline+overlay split (Decision 8), so
  reviewers see one consistent overlay pattern across the substrate.
- Concretizing baseline rows in the generic substrate is what makes US3
  acceptance scenario 1 satisfiable from repo artifacts alone.

**Alternatives considered**:
- *Empty baseline matrix, all rows tenant-supplied*: Rejected by FR-015
  (matrix MUST contain concrete rows for baseline classes).
- *Frozen matrix with no overlay path*: Rejected; tenants legitimately
  need to name their own roles (e.g. tenant titles, named
  ratifier roles), and a frozen matrix would force LIMITLESS-specific
  role names into the generic substrate, violating principle IX.

---

## Decision 10: Attestation/ratification/redaction record location and naming

**Decision**: Records live under tenant-declared roots
(`attestation_storage_path`, `ratification_storage_path`,
`redaction_storage_path`) with filename `<date>-<record-subject-id>.yml`,
where date is `YYYY-MM-DD` (UTC date the record was authored) and
subject id is the mutation id (attestation, ratification) or
redaction/artifact id (redaction). One record per file. The validator
discovers records by globbing the configured directory and parsing each
file as YAML.

**Rationale**:
- Locked by clarification.
- `YYYY-MM-DD` prefix sorts records chronologically on disk, which is
  enough audit ordering for v0.1; finer-grained ordering (timestamps,
  monotonic counters) is YAGNI.

**Alternatives considered**:
- *Append-only log files*: Rejected by clarification.
- *Markdown-bodied records*: Rejected by clarification.
- *Per-tenant single file*: Rejected by clarification ("one record per
  file").
- *UUID-prefixed filenames*: Rejected; loses the chronological-sort
  property without adding value over the date+subject-id pair, and
  makes filenames harder to read in `git log`-style audits.

---

## Decision 11: Identity record file location

**Decision**: A tenant's identity record lives at
`tenants/<name>/identity-record.yml`. The substrate does not impose a
location for tenants outside this repository; the location convention
applies to in-repo dogfood fixtures only. The identity-record schema
defines its own fields and is location-agnostic.

**Rationale**:
- Matches FR-022 / FR-023 ("Tenant fixtures live under
  `tenants/<name>/`") for in-repo tenant material.
- Out-of-repo tenants supply their identity record through whatever
  governance file layout they choose; this is consistent with the
  schema being a portable contract rather than a directory mandate
  (principle IX, LIMITLESS as Dogfood).

**Alternatives considered**:
- *Substrate-mandated fixed path for all tenants*: Rejected; tenants
  not in this repo are out of scope of the substrate's directory
  layout, and locking a path adds no value when the schema already
  defines the record's identity.

---

## Decision 12: `tasks.creator-engine.yml` task-level granularity

**Decision**: `tasks.creator-engine.yml` carries a per-task array where
each task entry includes `id`, `title`, `mutation_class` (one of the
declared baseline or tenant-extension classes), `permitted_actions`
(subset of the class's action vocabulary), `verification_evidence_ref`
(path or anchor to the artifact that proves the task was completed),
and `ratification_or_approval_ref` (for ratification-relevant tasks
only, points at the ratification record per FR-007/FR-016/FR-017).

**Rationale**:
- Satisfies FR-012b's "task-level mutation class/action/evidence
  declarations, and ratification or approval references sufficient to
  preserve author/approver separation."
- Mirroring per-task structure to a single sidecar file (one per
  feature) keeps the file size manageable and aligns with Spec Kit's
  one-`tasks.md`-per-feature convention.

**Alternatives considered**:
- *One sidecar per task*: Rejected as proliferation of files for no
  benefit; tasks within a feature cohere as a unit and are reviewed
  together.
- *Task-level metadata in `tasks.md` body*: Rejected by the locked
  "pure sidecar" clarification and by principle X (Spec Kit
  byte-identical compatibility).

---

## Decision 13: Pre-merge / post-merge attestation states

**Decision**: An attestation record carries a top-level `state` field
with values `pre_merge` or `finalized`. A `pre_merge` record proves
that the mutation is mergeable (spec linked, identity declared,
mutation class declared, permitted actions checked, verification
evidence collected, ratifier identified). A `finalized` record adds the
`merge_reference` field (e.g. commit sha or PR merge reference) and is
the post-merge state that satisfies `ratified → done` per FR-013a. The
validator's `attestation_linkage` check requires `pre_merge` for any
merge-eligible mutation and `finalized` for any spec at status `done`.

**Rationale**:
- Encodes FR-004 ("MUST support a pre-merge attestation state used to
  prove the mutation is mergeable and a post-merge finalization state
  that adds the merge reference after merge") as a single record with
  a state discriminator rather than two separate record types, keeping
  audit lookup simple ("one record per mutation").
- Separating discovery (path glob) from state (record field) preserves
  FR-020a's "validator parses by configured directory glob + YAML
  parse only" rule.

**Alternatives considered**:
- *Two record types in two directories*: Rejected; would either
  duplicate fields or force a "finalize" link between two files,
  expanding the audit surface unnecessarily.
- *Separate post-merge sidecar to `tasks.creator-engine.yml`*:
  Rejected; the merge reference belongs on the attestation, not on the
  task list.

---

## Decision 14: Verification spec is itself a Creator-Engine-governed spec

**Decision**: The verification specification is authored as a canonical
Spec Kit pair under `docs/contracts/verification-spec/`: vanilla
`spec.md` plus adjacent canonical `spec.creator-engine.yml`. The
rendered human-readable contract is `docs/contracts/verification-spec.md`
and is generated/copied from that governed source during implementation.
No sidecar named after `verification-spec.md` exists; Decision 4's
canonical sidecar discovery remains the only sidecar lookup rule.

**Rationale**:
- FR-031 requires the verification specification to be reconstructable
  from the repo and itself Creator-Engine-governed.
- Using `spec.md` + `spec.creator-engine.yml` preserves the locked
  canonical sidecar names and keeps the validator's directory + canonical
  name discovery rule unchanged.
- Keeping a rendered `docs/contracts/verification-spec.md` gives tenants
  the same contract-document surface as the rest of `docs/contracts/`
  without inventing a second sidecar convention.

**Alternatives considered**:
- *Skip wrapper for substrate-self-governance docs*: Rejected by
  FR-031.
- *Use a sidecar named after `verification-spec.md` beside that
  rendered contract*: Rejected because it creates a non-canonical
  sidecar filename and contradicts Decision 4.

---

## Open follow-ups (post-v0.1, not in scope here)

These are recorded for traceability but are NOT v0.1 scope; v0.1 is the
minimum substrate per the YAGNI principle (XI):

- Live source-host enforcement (e.g. GitHub App PR check that runs the
  validator). v0.1 is repo-runnable only (FR-026, FR-027a's "v0.1 MUST
  NOT require live source-host API calls").
- Hosted policy engine or SaaS runtime enforcement. Out of scope per
  principle XI.
- Public/NDA export pipeline. v0.1 defines the redaction gate but
  executes no export workflow (US5, FR-019, principle XII).
- Drift detection between the constitution and validator behavior. The
  constitution review cadence (governance section of constitution.md)
  is the v0.1 mechanism.
