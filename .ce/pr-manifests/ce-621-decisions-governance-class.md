# PR path manifest — ce-ops#621 · decisions/ governance predicate escalation

This per-PR carrier lists the closed authorized path set for the `S` slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=dab3a95cb00d17bfa4536adf1001d1748ed3659f20cfb06b6d994446670ef2fb

```text
.ce/changelog/ce-621-decisions-governance-class.md
.ce/pr-manifests/ce-621-decisions-governance-class.md
validators/creator_engine_validator/forge/automerge_mutation_policy.yaml
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
validators/tests/unit/test_mutation_classifier.py
```
