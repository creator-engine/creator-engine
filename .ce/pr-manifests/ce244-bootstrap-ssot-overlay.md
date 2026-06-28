# PR path manifest — ce-ops#344/#244 · Controller bootstrap SSOT overlay

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce244-bootstrap-ssot-overlay` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=3e5129a495ee52d50747fdc8ab1891de3ea774a048fc49b857d9782590e0c3a6

```text
.ce/changelog/ce244-bootstrap-ssot-overlay.md
.ce/pr-manifests/ce244-bootstrap-ssot-overlay.md
docs/design/controller-bootstrap-ssot.json
scripts/gen-controller-bootstrap.py
validators/tests/unit/test_gen_controller_bootstrap.py
```
