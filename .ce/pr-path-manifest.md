# PR path manifest — feat(v3): G-6 coordination layer (the Scope dispatch spine)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **ADDITIVE** CI-pure coordination gate (G-6) — the OUTER-loop **Scope
dispatch spine** (Scope-only). `schemas/scope.schema.yaml` (the ephemeral atom)
→ a PURE v3 `coordination` module (`scope_is_ready` DoR predicate · `is_ratified`
· `appetite_to_spend_envelope` [the G-5 appetite→spend-cap join] · `project_scope_state`
[state-as-projection over the CONSERVED spec-lifecycle, surfacing the canon
Frame→Shape→Build→Review→Ship skin] · `assemble_dispatch` refusing-unless-ready+ratified,
producing the inputs for ONE G-4/G-5-governed run) → a new registered `ce_scope`
check (#47; the `ce_runtime_policy`/`ce_spend_envelope` pattern). Contract:
`docs/contracts/scope.md`. Folds the deferred G-5 roadmap-SHA fill (`#158` → `1ed368b`).

Stage-vocabulary canon honored (#161, `docs/architecture/stage-vocabulary.md`): the
Scope `state` is the conserved spec-lifecycle (`draft→ready→in_progress→verified→
ratified→done`, zero new enums); the cognitive phase is a derived presentation skin
(`ce_scope` forces a stored `phase` to equal the derivation) — no third vocabulary.
G-4.1 honored: `v3_naming_hygiene` stays 0/0 (`coordination` + `schemas/scope.schema.yaml`
are residue-clean) and any v3 local state is `.ce/state` (the backlog is committed
Scope artifacts + state-as-projection — no new state file). G-5 honored: the
appetite→cap join feeds `runner.spend_gate` unchanged.

Invariants held: **v1 deleted = ∅** (no v1 runtime module modified); `version_boundary`
(#44) STAYS GREEN (0/0); `BASELINE_SHARED_TO_VERSION_ALLOWLIST` unchanged; the new
`coordination` module is v3 (imports only stdlib) and the new `ce_scope` check is
`shared` (no `shared→v3` edge — the canon constants are a drift-guarded duplicate);
`--list-checks` 46 → **47**; `V3_RUNTIME` 20 → **21**; `V3_SCHEMAS` 2 → **3**;
`check-examples` STAYS **78/0** (the new check fires only on `scope-record` artifacts,
of which the examples tree has none — green-on-day-one; teeth via unit fixtures). The
count-pin bumps (46→47 across the `*_registers_no_check*`/`*_purity_unchanged` family +
`test_version_boundary.py` `len(reg)`; `V3_RUNTIME` 20→21) are the assertions that
legitimately shift. Explicitly deferred (named follow-ons): the live Scope dispatch
(spawn a run); the durable Skill axis; the finding-schema + discard-on-drift gate; the
crosswalk-register `scope_mappings` axis; a backlog index register; a spine-level
scope-dispatch attestation record.

- **base:** `02caa5165b568602d5458e5bb4b7c6a548ee7fb6`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=18

AUTHORIZED_PATHS_SHA256=e4473bd7892d2c5abfda4138b55438e9c79beb0d6aa96fd6d45c4cee93b436e9

```text
.ce/pr-path-manifest.md
docs/contracts/scope.md
docs/v3-roadmap.md
schemas/scope.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/ce_scope.py
validators/creator_engine_validator/coordination.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_ce_scope.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_coordination.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
```
