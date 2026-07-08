# PR path manifest - ce-491-prearming

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
This is the closed path set for the CE-491 materializer pre-arming checklist batch.

- **Declared work class:** T

The change:
Close four pre-arming findings from the Option A materializer review: add real
`run_preflight` integration coverage for the brain append intent/direct ledger XOR gate,
bump the materializer audit actor version, normalize evidence paths before `.ce/state`
subtree validation, and document the HeldError artifact asymmetry beside the handler.
`ARMING_ENABLED` remains `False`; this branch does not arm the materializer.

Per-file purpose:
- **`.ce/changelog/ce-491-prearming.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-491-prearming.md`** *(A)* - this closed path-set carrier.
- **`.ce/wt-491-prearming/READY`** *(A)* - contained-seat completion signal, committed last.
- **`validators/creator_engine_validator/brain_intent_materializer.py`** *(M)* - actor version bump, resolved evidence-path guard, and HeldError asymmetry comment.
- **`validators/tests/unit/test_brain_intent_materializer_hold.py`** *(M)* - actor-version fixture update and dot-dot traversal regression coverage.
- **`validators/tests/unit/test_pr_preflight.py`** *(M)* - `run_preflight` integration coverage for the XOR gate and intent-only pass direction.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=d4badae4ca7df13dd7e59e6d50ffb04acb92b2b8aa30fc964123794f239cc3d1

```text
.ce/changelog/ce-491-prearming.md
.ce/pr-manifests/ce-491-prearming.md
.ce/wt-491-prearming/READY
validators/creator_engine_validator/brain_intent_materializer.py
validators/tests/unit/test_brain_intent_materializer_hold.py
validators/tests/unit/test_pr_preflight.py
```
