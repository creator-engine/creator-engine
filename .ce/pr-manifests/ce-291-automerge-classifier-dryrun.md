# PR path manifest - ce-ops#291 PR-A automerge classifier dry-run

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
The authorized path set below reflects the current classify-only implementation.

- **Declared work class:** epic

Per-file purpose (closed path set - 10 paths):
- **`.ce/changelog/ce-291-automerge-classifier-dryrun.md`** *(A)* - changelog and local dry-run evidence.
- **`.ce/pr-manifests/ce-291-automerge-classifier-dryrun.md`** *(A)* - this carrier, self-inclusive.
- **`.ce/reference/schemas.generated.md`** *(M)* - generated schema reference refreshed for the new automerge schemas.
- **`validators/creator_engine_validator/forge/automerge_mutation_policy.yaml`** *(A)* - data-driven mutation policy, state path, decision directory, and path predicates.
- **`validators/creator_engine_validator/forge/automerge_policy.py`** *(M)* - secret-free policy state, decision composition, and dry-run decision emitter.
- **`validators/creator_engine_validator/forge/mutation_classifier.py`** *(M)* - config-driven highest-risk-wins path classifier.
- **`validators/creator_engine_validator/schemas/automerge-decision.schema.yaml`** *(M)* - packaged decision record schema.
- **`validators/creator_engine_validator/schemas/automerge-policy.schema.yaml`** *(M)* - packaged policy state/config schema.
- **`validators/tests/unit/test_automerge_policy.py`** *(M)* - automerge policy and dry-run unit tests.
- **`validators/tests/unit/test_mutation_classifier.py`** *(M)* - classifier path table and fail-closed unit tests.

Dry-run evidence:

| PR | Commit | Expected | Actual | Mutation | Size |
| --- | --- | --- | --- | --- | --- |
| #545 | `26968a9f8e947365d9c8a82a8476e753d82b22d0` | AUTO | AUTO | docs | target_advisory/tiny |
| #584 | `2b34e39486b7d075913579861ae222e564b4c3a2` | GESTURE | GESTURE | security | warn/story |
| #546 | `33887a6ff4b87448b6fe978b20cebd8757c47fd1` | GESTURE | GESTURE | schema | warn/story |

Dry-run JSON records were written locally under `.ce/state/automerge/decisions/`;
that directory is ignored by `.gitignore` through `.ce/state/`, so the summary
above is the tracked evidence carrier.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=38e68be3d2ea5b4195a46950f0b3cb4a982b96c679a04b67a35402987e069e68

```text
.ce/changelog/ce-291-automerge-classifier-dryrun.md
.ce/pr-manifests/ce-291-automerge-classifier-dryrun.md
.ce/reference/schemas.generated.md
validators/creator_engine_validator/forge/automerge_mutation_policy.yaml
validators/creator_engine_validator/forge/automerge_policy.py
validators/creator_engine_validator/forge/mutation_classifier.py
validators/creator_engine_validator/schemas/automerge-decision.schema.yaml
validators/creator_engine_validator/schemas/automerge-policy.schema.yaml
validators/tests/unit/test_automerge_policy.py
validators/tests/unit/test_mutation_classifier.py
```
