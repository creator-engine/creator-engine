# PR path manifest - ce189-supersession-guard

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce189-supersession-guard
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`2afc480` (`origin/main` at branch handoff).

- **Declared work class:** story

Scope:
ce-ops#189 deterministic supersession guard for the courier/belt push path.
This slice refuses stale duplicate or regressive branch pushes before any
remote read or mutation.

Per-file purpose:
- **`.ce/changelog/ce189-supersession-guard.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce189-supersession-guard.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/_version.py`** *(M)* - regenerated build identity for the branch parent to satisfy packaging-contract ancestry after squash merges.
- **`validators/creator_engine_validator/forge/change_push.py`** *(M)* - pure supersession policy core, local git fact extraction, and pre-remote enforcement in the push primitive.
- **`validators/tests/unit/test_change_push.py`** *(M)* - unit coverage for each fail-closed supersession refusal and endpoint ordering.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* - adoption push fake support for the new read-only guard probes.
- **`validators/tests/unit/test_v3_forge_join.py`** *(M)* - forge-join fake support for the new read-only guard probes.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=5c5f0bcfc4f18e182f57a34856740e6cfe2ad94c12637b4af96db0699b542343

```text
.ce/changelog/ce189-supersession-guard.md
.ce/pr-manifests/ce189-supersession-guard.md
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/forge/change_push.py
validators/tests/unit/test_change_push.py
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_v3_forge_join.py
```
