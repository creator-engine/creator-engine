# PR path manifest — public-docs-internal-reference-guard · public docs internal-reference guard

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref public-docs-no-internal-refs-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=f6812d57a08831a05f264fdf3226a169a5a5cebd4a99d8d6651b4084493c70e8

```text
.ce/changelog/public-docs-no-internal-refs-guard.md
.ce/pr-manifests/public-docs-no-internal-refs-guard.md
deploy/systemd/README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/harness_matrix.py
validators/tests/unit/test_harness_matrix.py
validators/tests/unit/test_public_docs_confidentiality.py
```
