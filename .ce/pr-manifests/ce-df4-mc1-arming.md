# PR path manifest — DF-4-MC1-arming · MC1 docs_envelope arming materialization surface

This per-PR carrier lists the closed authorized path set for the `S` slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=d19ab86c96542ba3a71f6b5d6088a5182d9cf35e36461a43509573ba0680aecb

```text
.ce/changelog/ce-df4-mc1-arming.md
.ce/pr-manifests/ce-df4-mc1-arming.md
deploy/automerge/materialize-automerge-policy.py
deploy/automerge/policy-declaration.yaml
docs/decisions/DEC-0017-mc1-docs-envelope-arming.md
validators/tests/unit/test_automerge_policy_materializer.py
```
