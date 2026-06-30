# PR path manifest — ce-ops#364 · Share install signature guard pinned keys

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-364-guard-single-source` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=8cdeeaa08834ae48bd443d8310a20dfb5cdcebc5bf0ac58c5f6b6c155f64922e

```text
.ce/changelog/ce-364-guard-single-source.md
.ce/pr-manifests/ce-364-guard-single-source.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/checks/install_spec_signature_guard.py
validators/tests/unit/test_install_spec_signature_guard.py
validators/tests/unit/test_version_boundary.py
```
