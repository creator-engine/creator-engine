# PR path manifest — ce-ops#244 · controller bootstrap injection preview scaffold

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce244-bootstrap-injection-pr` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=5bb79313ebbc568050fb935e36e7c80e8939e454a1a98be3814770c76b0ee83e

```text
.ce/changelog/ce244-bootstrap-injection-pr.md
.ce/pr-manifests/ce244-bootstrap-injection-pr.md
docs/design/controller-bootstrap-injection.md
docs/design/controller-bootstrap-ssot.json
scripts/gen-controller-bootstrap.py
```
