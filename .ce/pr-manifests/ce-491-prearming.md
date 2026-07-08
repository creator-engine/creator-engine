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
- **`validators/creator_engine_validator/pr_preflight.py`** *(M)* - accepts the task carrier class required by this unit and normalizes it for existing work-sizing gates.
- **`validators/tests/unit/test_brain_intent_materializer_hold.py`** *(M)* - actor-version fixture update and dot-dot traversal regression coverage.
- **`validators/tests/unit/test_pr_preflight.py`** *(M)* - `run_preflight` integration coverage for the XOR gate, intent-only pass direction, and task carrier parsing.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=b44198c9d148138bdae8ebaac7b10cb393d9e35f6d357f2171e413de3adecf57

```text
.ce/changelog/ce-491-prearming.md
.ce/pr-manifests/ce-491-prearming.md
.ce/wt-491-prearming/READY
validators/creator_engine_validator/brain_intent_materializer.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_brain_intent_materializer_hold.py
validators/tests/unit/test_pr_preflight.py
```
