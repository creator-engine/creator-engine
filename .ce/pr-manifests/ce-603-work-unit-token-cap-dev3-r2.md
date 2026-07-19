# PR path manifest - raw-token work-unit cap

The base-to-head diff must equal exactly this closed path-set.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

Declared work class: feature

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=461b162fc6f567e29c725b16fc06049af7a50b0a2b3e43cc12dddd4d73710c6c

```text
.ce/changelog/ce603-work-unit-token-cap-dev3.md
.ce/pr-manifests/ce-603-work-unit-token-cap-dev3-r2.md
.ce/reference/schemas.generated.md
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/runner/spend_gate.py
validators/creator_engine_validator/runner/usage_tap.py
validators/creator_engine_validator/runner/work_unit_cap.py
validators/creator_engine_validator/schemas/runtime-evidence.schema.yaml
validators/creator_engine_validator/schemas/work-unit-cap.schema.yaml
validators/creator_engine_validator/side_effect_ledger_runtime.py
validators/creator_engine_validator/work_unit_ledger.py
validators/tests/unit/test_cockpit_readmodel.py
validators/tests/unit/test_side_effect_ledger_runtime.py
validators/tests/unit/test_spend_gate.py
validators/tests/unit/test_usage_tap.py
validators/tests/unit/test_work_unit_cap.py
validators/tests/unit/test_work_unit_ledger.py
```
