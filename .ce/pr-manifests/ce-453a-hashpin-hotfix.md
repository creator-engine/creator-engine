# PR path manifest — ce-ops#453 · signed-artifact-pins + path-manifest-fidelity hotfix

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-453a-hashpin-hotfix` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=4e652de89e8ab289459f12d9a00fffa02102bc9a5126d60f9d666337ced1b4a9

```text
.ce/changelog/ce-453a-hashpin-hotfix.md
.ce/pr-manifests/ce-453a-hashpin-hotfix.md
validators/creator_engine_validator/checks/path_manifest_fidelity.py
validators/creator_engine_validator/checks/signed_artifact_pins.py
validators/tests/unit/test_path_manifest_fidelity.py
validators/tests/unit/test_signed_artifact_pins.py
```
