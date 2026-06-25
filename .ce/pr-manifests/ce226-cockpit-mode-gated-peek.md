# PR path manifest — ce-ops#226 · mode-gated cockpit peek

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce226-cockpit-mode-gated-peek` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=cece7669c18b0c11ab49157a097416dc11d18bf49983ac94eed6abf85988f146

```text
.ce/changelog/ce226-cockpit-mode-gated-peek.md
.ce/pr-manifests/ce226-cockpit-mode-gated-peek.md
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cockpit.py
validators/tests/unit/test_cockpit_peek.py
```
