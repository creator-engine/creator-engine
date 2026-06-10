# PR path manifest — feat(v3.5-C/A): team-mode coordination wave (A-C1 → A-C2 → A-C3 → α-precursor → A-C4, one combined branch)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: the **v3.5-C A-cluster wave** (team-mode/coordination) — the four
Operator-ratified gates of
`.hermes/research/v3-5-C-gates-20260609T155331Z/GATES_A_CLUSTER_coordination.md`
(sha256 c16f1749…) plus the ratified **α-precursor** (A-C4 = option α), executed
in the ratified order **A-C1 → A-C2 → A-C3 → α-precursor → A-C4** on ONE
combined branch (the #185 lesson), each gate committed at its own full green.
This carrier is the UNION of the five gates' closed manifests.

- **A-C1 — Decision Record + `decision_record` check + `binding_decisions`.**
  `schemas/decision-record.schema.yaml` + `checks/decision_record.py` *(NEW,
  shared)*: MADR-4.0.0 ADRs (`docs/decisions/`) + Rust-RFC/FCP records
  (`docs/rfcs/`) with CE governance front-matter — accepted-is-human-ratified,
  no privileged self-ratification, supersede-with-link, FCP open-concern
  blocking. Conventions + templates + contract; `scope.schema.yaml` gains the
  optional `binding_decisions` field (the A↔B seam consumed by B-C2 — field
  only). Registry 47→48.
- **A-C2 — advisory storage-tier finding + the public/private policy ADR.**
  `schemas/storage-tier-finding.schema.yaml` + `checks/storage_tier_finding.py`
  *(NEW, shared)*: advisory-by-construction relevance+tier finding with the
  no-auto-promotion HARD invariant (`promoted: true` requires the spine
  `ratification_ref`; the only constructor emits unpromoted; no `promote()`),
  split form, noise-stays-local; the 5-stage triage loop re-implemented as pure
  helpers (CODE_UNALLOWED ratchet). The tier rule ships as
  `docs/decisions/ADR-0001-public-private-storage-policy.md`, a ratified
  governance Decision Record validated by A-C1's check. Registry 48→49.
- **A-C3 — peer authority (per-area ownership × risk-tiered quorum).**
  `.ce/coordination.yml` *(NEW; self-classified `governance` via schema const)*
  + `schemas/coordination-policy.schema.yaml` + `checks/peer_authority.py`
  *(NEW, shared; reuses `mutation_class.PRIVILEGED_NAMES` verbatim)*: quorum of
  DISTINCT resolved humans per tier (privileged ≥ 2), cross-area-needs-owner,
  no self-approval at the human level, identity resolver with FAIL-CLOSED
  unresolved actors (§11.5 shipped honestly — the repo map declares today's
  N=1 reality). `forge/plan_approval.py` *(EDIT — the wave's only v3 edit
  beside the precursor)* generalizes `plan_approved` to consult the area+tier
  map (lazy shared import; `authority=None` byte-compatible;
  approver ≠ author ≠ seat preserved). Registry 49→50.
- **α-precursor — `forge/backlog.py`** *(NEW v3 forge module; ratified
  precursor that A-C4-option-α consumes)*: Projects-v2 reader/writer + the
  §A.4 forge-projected advisory claim (assignee + `Status=Running`),
  drift-check-immediately-before-claim, randomized back-off + re-read,
  earlier-`claimed_at`-wins reconciliation surfaced as an Escalation — no
  force/overwrite path; explicitly NOT a hard lock. `_versions.py` V3_RUNTIME
  31→32 (`forge.backlog`, module + entry in the same commit).
- **A-C4 — `forge_claim_dedup` check (option α).**
  `schemas/forge-claim.schema.yaml` + `checks/forge_claim_dedup.py` *(NEW,
  shared)*: the auditable claim record — idempotency-key integrity (canonical
  SHA256 over the claim tuple, re-implemented under the ratchet,
  drift-guarded against the v3 twin in tests), escalation-never-silent-
  overwrite, and the deterministic dedup bar (pinned embedding similarity
  sufficient; token-overlap + cross-ref additive). Registry 50→51.

Version-boundary outcome on base `a7f3ebb`: check registry **47→51** (+4
`shared` checks, `--list-checks`=51), **V3_RUNTIME 31→32** (+`forge.backlog`),
V1_RUNTIME stays 22; zero v1↔v3 crossings (suite green). All four new schemas
classified `shared` (omitted from `V3_SCHEMAS`). The seven purity tests that
carry twin registry-count assertions (`test_open_change`, `test_merge`,
`test_redact`, `test_credential_runner`, `test_evidence_sink`,
`test_change_status`, `test_app_jwt_runner`) are re-derived 47→51
(assertion-only edits, declared in the wave report). The wheelhouse validator
wheel is rebuilt from the merged source + `SHA256SUMS` re-pinned per the launch
addendum (oracle: `test_wheelhouse_validator_wheel_matches_current_source`).

- **base:** `a7f3ebb` (current `main`; Cockpit-MVP #189 squash).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=53

AUTHORIZED_PATHS_SHA256=8ec98af748bf0ba2cea859b4e0f94dd7d04c7161a521f2b332e69c895b1325c1

```text
.ce/coordination.yml
.ce/pr-path-manifest.md
docs/contracts/decision-record.md
docs/contracts/forge-claim.md
docs/contracts/peer-authority.md
docs/contracts/storage-tier-finding.md
docs/decisions/ADR-0000-template.md
docs/decisions/ADR-0001-public-private-storage-policy.md
docs/decisions/README.md
docs/rfcs/README.md
docs/rfcs/RFC-0000-template.md
schemas/coordination-policy.schema.yaml
schemas/decision-record.schema.yaml
schemas/forge-claim.schema.yaml
schemas/scope.schema.yaml
schemas/storage-tier-finding.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/decision_record.py
validators/creator_engine_validator/checks/forge_claim_dedup.py
validators/creator_engine_validator/checks/peer_authority.py
validators/creator_engine_validator/checks/storage_tier_finding.py
validators/creator_engine_validator/forge/backlog.py
validators/creator_engine_validator/forge/plan_approval.py
validators/examples/decision-record/invalid-self-ratified-privileged.md
validators/examples/decision-record/invalid-superseded-no-target.md
validators/examples/decision-record/valid-adr.md
validators/examples/decision-record/valid-rfc.md
validators/examples/forge-claim/invalid-nondeterministic-dedup.ce.yml
validators/examples/forge-claim/invalid-silent-overwrite.ce.yml
validators/examples/forge-claim/valid-claim.ce.yml
validators/examples/peer-authority/invalid-crossarea-missing-owner.yml
validators/examples/peer-authority/invalid-privileged-single-ratifier.yml
validators/examples/peer-authority/valid-coordination.yml
validators/examples/storage-tier-finding/invalid-auto-promoted.ce.yml
validators/examples/storage-tier-finding/valid-advisory.ce.yml
validators/examples/storage-tier-finding/valid-split.ce.yml
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_backlog.py
validators/tests/unit/test_ce_scope.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_decision_record.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_forge_claim_dedup.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_peer_authority.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_storage_tier_finding.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
