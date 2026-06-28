# PR path manifest — ce-ops#344 · Controller bootstrap checklist hardening

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-344-slice2-checklist` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=94a6d207084854015eaf70e688e010615762cafd86ee9385c14e6656c926cc2a

```text
.ce/changelog/ce-344-slice2-checklist.md
.ce/pr-manifests/ce-344-slice2-checklist.md
docs/design/controller-bootstrap-ssot.json
scripts/gen-controller-bootstrap.py
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_gen_controller_bootstrap.py
```
