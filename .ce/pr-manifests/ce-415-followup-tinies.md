# PR path manifest - ce-415-followup-tinies

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, governed path-manifest convention).
This is the closed path set for the CE-415 follow-up tinies branch.

- **Declared work class:** S

The change:
Clarifies that `brownfield.enabled` in the install answers schema is not a live
default-true switch, and adds a focused boundary test for git-history-only
brownfield detection. The schema reference generator was run and produced no
content diff for `.ce/reference/schemas.generated.md`.

Per-file purpose:
- **`.ce/changelog/ce-415-followup-tinies.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-415-followup-tinies.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/schemas/install-answers.schema.yaml`** *(M)* - schema source reached through the top-level `schemas/` symlink; `brownfield.enabled` now defaults false and describes probe-derived live enablement.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - regression coverage for git history present with zero CI workflows and zero test commands.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=76365315c45bf1fd5e5d80ffb6050c52c7a968eabf30439397c8a2f5942babb1

```text
.ce/changelog/ce-415-followup-tinies.md
.ce/pr-manifests/ce-415-followup-tinies.md
validators/creator_engine_validator/schemas/install-answers.schema.yaml
validators/tests/unit/test_v3_cli.py
```
