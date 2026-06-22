# PR path manifest - ce196-triage-queue-hygiene

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce196-triage-queue-hygiene
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`e963eaf` (`origin/main` at branch handoff).

- **Declared work class:** story

Scope:
ce-ops#196 forge triage planner queue hygiene follow-up to ce-ops#194 / PR
#338. The slice extends `ce pickup triage` candidate exclusion so completed
linked PRs, explicit hold markers, and tracking/meta queue entries are not
labeled as pickup-ready.

Per-file purpose:
- **`.ce/changelog/ce196-triage-queue-hygiene.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce196-triage-queue-hygiene.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/forge_triage.py`** *(M)* - linked-PR completion, hold marker, tracking/meta exclusion, and fail-closed lookup handling.
- **`validators/tests/unit/test_forge_triage.py`** *(M)* - offline regression tests for the new exclusion paths.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=088e336478251decd0104a7cc441db106496b7aac7634c949b102db6b004a3e1

```text
.ce/changelog/ce196-triage-queue-hygiene.md
.ce/pr-manifests/ce196-triage-queue-hygiene.md
validators/creator_engine_validator/forge_triage.py
validators/tests/unit/test_forge_triage.py
```
