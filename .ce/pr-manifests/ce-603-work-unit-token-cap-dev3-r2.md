# PR path manifest - ce-603-work-unit-token-cap-dev3-r2 - CE603 raw-token work-unit cap

Per-PR carrier for `ce-ops#603`. The base-to-head diff must equal exactly this closed path-set.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

Declared work class: feature

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=d6f09c1e9fd251370fab1278725f0ca83c2a5121adac434d0736d2babaa9636b

```text
.ce/changelog/ce603-work-unit-token-cap-dev3.md
.ce/pr-manifests/ce-603-work-unit-token-cap-dev3-r2.md
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
