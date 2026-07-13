# PR path manifest — ce-ops#556 · Resolve ARG-indirected local Docker image bases

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-556-arg-indirect-base-exemption` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=09c4ee44353f0e1c91bcd22f6bdd8a6c0993d29a8cca2e3721102f842cf3863a

```text
.ce/changelog/ce-556-arg-indirect-base-exemption.md
.ce/pr-manifests/ce-556-arg-indirect-base-exemption.md
validators/creator_engine_validator/image_build_smoke.py
validators/tests/unit/test_image_build_smoke.py
```
