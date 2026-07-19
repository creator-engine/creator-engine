# PR path manifest — DF-4-MC1-arming · MC1 docs_envelope arming materialization surface

This per-PR carrier lists the closed authorized path set for the `S` slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=907f5f48d7d1c37c5771aff0a3ff399ce433179c3b250fc6007528e54bbeff87

```text
.ce/changelog/ce-df4-mc1-arming.md
.ce/pr-manifests/ce-df4-mc1-arming.md
deploy/automerge/materialize-automerge-policy.py
deploy/automerge/policy-declaration.yaml
docs/decisions/ADR-0016-pre-delegated-merge-classes.md
docs/decisions/DEC-0017-mc1-docs-envelope-arming.md
validators/creator_engine_validator/forge/automerge_actuator.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
validators/tests/unit/test_automerge_policy_materializer.py
```
