# PR path manifest — ce-496-controller-bootstrap-doc-s1 · Controller bootstrap runbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-496-controller-bootstrap-doc-s1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=58bfc3fba9972b942e03ca679a1367a3109e91918224bdede49667d0ef664e08

```text
.ce/changelog/ce-496-controller-bootstrap-doc-s1.md
.ce/pr-manifests/ce-496-controller-bootstrap-doc-s1.md
docs/operations/CONTROLLER_BOOTSTRAP.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_controller_bootstrap_paths.py
```
