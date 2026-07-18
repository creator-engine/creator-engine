# PR path manifest — ce-ops#605 · Add standing-rider validation (current-main-r2)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-605-standing-rider-current-main-r2` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=bd1309d833c05101cc3d3ee3e5c51dea832dec27a8a69138fdf8e97dfd39ca60

```text
.ce/changelog/ce-605-standing-rider-dev3.md
.ce/pr-manifests/ce-605-standing-rider-current-main-r2.md
.ce/reference/schemas.generated.md
docs/decisions/ADR-0605-standing-rider-cadence.md
docs/decisions/ce605-standing-rider-notes.ndjson
validators/creator_engine_validator/checks/decision_record.py
validators/creator_engine_validator/checks/standing_rider.py
validators/creator_engine_validator/schemas/standing-rider-note.schema.yaml
validators/tests/unit/test_standing_rider.py
```
