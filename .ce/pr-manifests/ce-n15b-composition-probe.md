# PR path manifest — N-15b · Add a detection-only composition probe for representative changes against the current main tip

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-n15b-composition-probe` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=534b89d3fbf4d2f9511857d2abacc94bb9986b1e19fdd253e20abadb93535a0b

```text
.ce/changelog/ce-n15b-composition-probe.md
.ce/pr-manifests/ce-n15b-composition-probe.md
validators/creator_engine_validator/composition_probe.py
validators/tests/unit/test_composition_probe.py
```
