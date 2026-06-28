# PR path manifest — ce-ops#344 · Controller bootstrap checklist hardening

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-344-slice2-checklist` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=180bab6547f7c0e659d31d0105f91a81f3d7692fce89d9207fb2b06dd685830a

```text
.ce/changelog/ce-344-slice2-checklist.md
.ce/pr-manifests/ce-344-slice2-checklist.md
docs/design/controller-bootstrap-ssot.json
scripts/gen-controller-bootstrap.py
validators/tests/unit/test_gen_controller_bootstrap.py
```
