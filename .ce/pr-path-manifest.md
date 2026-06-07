# PR path manifest — feat(v3): G-4 agent-interaction contract (per-run substrate)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **ADDITIVE** v3 G-4 per-run agent-interaction substrate. A typed
`AgentActionEvent` (op × mutation_class × fidelity) → a PURE `classify()` branch →
a deterministic, zero-token `decide()` control-point (built-in deny + Zed
precedence + gate-mode ladder; `auto` advisory-only) → a hash-chained
`runtime_agent_action` record (pure-constant vocabulary on the shared spine).
Additive runtime-policy fields (`action_class_allowlist` / `gate_mode_ladder`) +
the runtime-evidence schema's fourth `oneOf` branch (both back-compatible). A
**boundary-clean** Tier-B CC-hook derivation seam (`runner.cc_hook_adapter`,
classified `v3` in `_versions.py`) that reuses the **shared** `checks.mutation_class`
taxonomy and NEVER the v1 `hook_check` runtime. Tests + a runtime-evidence example
pair (well-formed + malformed) + docs reconciliation + the G-4 roadmap flip.

Operator amendment (mid-execution): (a) reconcile `docs/architecture/agent-interaction-model.md`
to current terminology — Operator (legacy `Source`) / Controller (legacy `Hermes`-the-role) —
and DISAMBIGUATE the Hermes harness (the tool) from the Controller role, building §i from the
current-terminology design source. Targeted approach (Operator-chosen): a terminology-canon note
+ prose conversion, KEEPING the §a Actor/Tool Ownership Matrix names verbatim-aligned to the
Feature-002 matrix (which is still legacy `Source`/`Hermes`), so the cross-reference + §h
actor-parity posture hold (a full `specs/001`/`002` corpus migration is a separate ratifiable
gate). (b) `.gitignore` the in-repo instance-local execution zones (`/ce-worktrees/`,
`/ce-review-venues/`). Note: `ce_terminology_v2` is scoped to `specs/v2/` only and never scans
`docs/`, so this is canon hygiene, not a check fix.

Invariants held: **v1 deleted = ∅** (no v1 runtime module modified); the
`version_boundary` check (#44) STAYS GREEN (0/0) with the new v3 module classified;
the `BASELINE_SHARED_TO_VERSION_ALLOWLIST` is UNCHANGED (no new `shared→version`
edge); `--list-checks` STAYS **44**; `check-examples` goes **77/0 → 78/0** (one new
malformed fixture). The live transport tap + credential hardening + Tier-A/Tier-C
adapters are deferred follow-ons.

- **base:** `c1041a005a9b386485bf1d66fc220ff2c3bb4728`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=23

AUTHORIZED_PATHS_SHA256=c9cd26b133f2882d318a435cd8e3518af8c9f15ace6a90c614c1c7615a514707

```text
.ce/pr-path-manifest.md
.gitignore
docs/architecture/agent-interaction-model.md
docs/architecture/pilot-roadmap.md
docs/contracts/runtime-policy.md
docs/v3-roadmap.md
examples/README.md
examples/malformed/runtime-evidence/agent-action-bad-op.yml
examples/well-formed/runtime-evidence/example-runtime-evidence-chain-agent-action.yml
schemas/runtime-evidence.schema.yaml
schemas/runtime-policy.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/checks/ce_runtime_evidence.py
validators/creator_engine_validator/checks/ce_runtime_policy.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/runner/audit_overlay.py
validators/creator_engine_validator/runner/cc_hook_adapter.py
validators/creator_engine_validator/runtime_evidence_spine.py
validators/tests/integration/test_ce_runtime_evidence_examples.py
validators/tests/unit/test_audit_overlay.py
validators/tests/unit/test_cc_hook_adapter.py
validators/tests/unit/test_ce_runtime_policy.py
validators/tests/unit/test_version_boundary.py
```
