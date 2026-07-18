# PR path manifest - ce603-work-unit-token-cap-dev3 - CE603 raw-token work-unit cap

Per-PR carrier for `ce-ops#603`. The base-to-head diff must equal exactly this closed path-set.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=fee12d512b917a5e447a9aefb9438e88f09d5213956e30b6e61e25cff83445a8

```text
.ce/changelog/ce603-work-unit-token-cap-dev3.md
.ce/pr-manifests/ce603-work-unit-token-cap-dev3.md
validators/creator_engine_validator/forge/automerge_policy.py
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/runner/spend_gate.py
validators/creator_engine_validator/runner/usage_tap.py
validators/creator_engine_validator/runner/work_unit_cap.py
validators/creator_engine_validator/schemas/runtime-evidence.schema.yaml
validators/creator_engine_validator/schemas/work-unit-cap.schema.yaml
validators/creator_engine_validator/side_effect_ledger_runtime.py
validators/tests/unit/test_automerge_policy.py
validators/tests/unit/test_cockpit_readmodel.py
validators/tests/unit/test_side_effect_ledger_runtime.py
validators/tests/unit/test_spend_gate.py
validators/tests/unit/test_usage_tap.py
validators/tests/unit/test_work_unit_cap.py
```
