# PR path manifest - ce119-tasks-handoff-contract

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce119-tasks-handoff-contract

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified scope:
Controller relay for ce-ops#119 on 2026-06-20: design the
ratified-tasks-to-worker handoff contract, including `tasks.ce.yml`,
`do_not_replan`, and SHA drift detection. This is a design pass, not
merge-bound runtime enforcement; no forge write, push, or merge.

Fold-in:
Operator resolutions supplied on 2026-06-20 ratify the contract shape and close
the five open decisions: emit only `tasks.ce.yml`; bind the full task set while
dispatch selects ids by reference; forbid worker edits to `tasks.md` and
`tasks.ce.yml`; use the proposed deterministic `cev3 tasks bind` materialization
step; and permit only breadth-capped allowed-path globs with exact-only
`prohibited_paths`.

Base:
`03d3796dd16429358884658a29bdcda8e3f986b4` (`origin/main` after ce-ops#149
launcher state relocation merge; ce119 rebased before Operator-resolution
fold-in).

The changes:
- Add `docs/architecture/tasks-handoff-contract.md` describing the contract,
  lifecycle, SHA binding, `do_not_replan` enforcement, harness contract, and
  mapping to existing Scope/Dispatch/brief machinery.
- Add `schemas/tasks.schema.yaml` as the reference schema for the proposed
  `tasks.ce.yml` handoff shape, including the design-pass scope breadth rule.
- Add schema unit coverage for the documented scope-empty and scope-breadth
  predicates.
- Add a changelog fragment and this path-manifest carrier.
- Do not add runtime/validator enforcement; that remains pending Operator
  ratification of the implementation pass for this keystone contract.

Per-file purpose (the closed path-set - 5 paths; `(A)` add):
- **`.ce/changelog/ce119-tasks-handoff-contract.md`** *(A)* - changelog
  fragment.
- **`.ce/pr-manifests/ce119-tasks-handoff-contract.md`** *(A)* - this carrier.
- **`docs/architecture/tasks-handoff-contract.md`** *(A)* - contract design.
- **`schemas/tasks.schema.yaml`** *(A)* - reference schema.
- **`validators/tests/unit/test_tasks_handoff_schema.py`** *(A)* - schema
  fidelity tests for the documented scope predicates.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=ad6c6e43e4a0e40b64e6a2ce60127d2a08ccc124ffb06e8d07de97cebb01df76

```text
.ce/changelog/ce119-tasks-handoff-contract.md
.ce/pr-manifests/ce119-tasks-handoff-contract.md
docs/architecture/tasks-handoff-contract.md
schemas/tasks.schema.yaml
validators/tests/unit/test_tasks_handoff_schema.py
```
