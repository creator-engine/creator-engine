# PR path manifest — ce-ops#343 · version-agnostic install-spec tests

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-343-installspec-version-agnostic` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=aca481d23d0bb4da7569e62b66745a0c3ca535ab3c17da9ad9f1543af57468b3

```text
.ce/changelog/ce-343-installspec-version-agnostic.md
.ce/pr-manifests/ce-343-installspec-version-agnostic.md
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_v3_installer.py
```
