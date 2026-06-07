# PR path manifest — feat(v3): G-5 tokenomics gate (spend envelope: admission + circuit-breaker)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **ADDITIVE** CI-pure tokenomics gate (G-5) — `spend` as a deny-by-default
blast-radius axis. Additive runtime-policy spend fields (`spend_envelopes` nested
`global→fleet→run`, most-restrictive-wins + mandatory global `$` ceiling;
`max_concurrent_runs`; `model_rates` read-live-never-hardcode;
`spend_cap_enforcement`/`spend_cap_optout`) → the PURE `runner.spend_gate`
(two-regime cost [`$` fleet / `%` seat]; ledger-as-projection over the evidence
spine — no mutable ledger file; admission gate + synchronous soft/hard
circuit-breaker; two-signal `budget_exhausted`-vs-`throttle`) → a spend-ledger +
breach record axis on the hash-chained `runtime_evidence_spine` (validated by the
existing `ce_runtime_evidence` via two additive schema `oneOf` branches; reuses
`verify_chain`). The cost-enforcement opt-out is a ratified-HUMAN-only choice
(`spend_cap_enforcement: off` REQUIRES a `spend_cap_optout` binding) that splits
the opt-out-able CAP from the always-on runaway-DETECTION net (the mandatory global
ceiling stays). A new registered check `ce_spend_envelope` (#46; sibling pattern to
`ce_runtime_policy`) enforces the cross-envelope predicates. Contract:
`docs/contracts/spend-envelope.md`. Folds the deferred G-4.1 roadmap-SHA fill
(`#156` → `e916df2`).

Standing requirements honored (G-4.1; `docs/contracts/v3-naming-hygiene.md`): the v3
surface stays residue-clean (`v3_naming_hygiene` 0/0 — `runner.spend_gate` + the
spend schemas are clean) and any v3 local state goes under `.ce/state` (here the
ledger is state-as-projection — no new state file).

Invariants held: **v1 deleted = ∅** (no v1 runtime module modified); `version_boundary`
(#44) STAYS GREEN (0/0); `BASELINE_SHARED_TO_VERSION_ALLOWLIST` unchanged; the new
`runner.spend_gate` is v3 (imports only v3 `runner.audit_overlay` + shared
`runtime_evidence_spine`) and the new `ce_spend_envelope` check is `shared` (imports
`_versions` + the sibling `ce_runtime_policy` iterator — no `shared→v3` edge);
`--list-checks` 45 → **46**; `check-examples` STAYS **78/0** (the optional spend
fields keep the existing well-formed example valid; the spend-predicate teeth are
carried by the unit tests per the G-4.1 self-check latitude). The count-pin bumps
(45→46) across the `*_registers_no_check*` / `*_purity_unchanged` test family +
`test_version_boundary.py` (and its `V3_RUNTIME` 19→20) are the assertions that
legitimately shift when the new #46 check registers / the new v3 module is declared.
Explicitly deferred (named follow-ons): live `usage`/`/usage` taps; live cockpit
escalation channel; cross-process concurrency semaphore; live vendor-rate fetch; the
CE-harness overhead micro-benchmark; an incremental derived global/fleet ledger cache.

- **base:** `e916df22d163c8c532caea73f158f9007bf99fb0`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=23

AUTHORIZED_PATHS_SHA256=2a16dbaa736d3756b84909e3c18f26f27e008079281322b28334d29a972b98d1

```text
.ce/pr-path-manifest.md
docs/contracts/runtime-evidence.md
docs/contracts/runtime-policy.md
docs/contracts/spend-envelope.md
docs/v3-roadmap.md
schemas/runtime-evidence.schema.yaml
schemas/runtime-policy.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/ce_runtime_evidence.py
validators/creator_engine_validator/checks/ce_spend_envelope.py
validators/creator_engine_validator/runner/spend_gate.py
validators/creator_engine_validator/runtime_evidence_spine.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_ce_spend_envelope.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_spend_gate.py
validators/tests/unit/test_version_boundary.py
```
