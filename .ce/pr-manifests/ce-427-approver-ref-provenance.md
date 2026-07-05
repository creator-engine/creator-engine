# PR path manifest — ce-ops#427 · Approver ref provenance for installer ratification bindings

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-427-approver-ref-provenance` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=6a1c850f2334c9aaef14af31ec55c4f95c68c98c117313b64cf19d5be7a9fbeb

```text
.ce/changelog/ce-427-approver-ref-provenance.md
.ce/pr-manifests/ce-427-approver-ref-provenance.md
docs/contracts/installer.md
validators/creator_engine_validator/checks/install_answers.py
validators/creator_engine_validator/schemas/install-answers.schema.yaml
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_install_answers.py
validators/tests/unit/test_v3_installer.py
```
