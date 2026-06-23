# PR path manifest - ce216-executor-race-guard

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce216-executor-race-guard
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`origin/ce216-deterministic-resolvers` at branch handoff.

- **Declared work class:** story

Scope:
ce-ops#216 Unit 3. Add the deterministic executor that applies already-resolved
Unit 2 content for Unit 1 repair-needed events, with PR head/base race guards
and adapter-owned write/push authority.

Per-file purpose:
- **`.ce/changelog/ce216-executor-race-guard.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce216-executor-race-guard.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify the executor module as v3 forge code.
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* - expose executor result and helper APIs through the forge package surface.
- **`validators/creator_engine_validator/forge/integrator_executor.py`** *(A)* - deterministic executor implementation with write-authority adapter and race guards.
- **`validators/tests/unit/test_integrator_executor.py`** *(A)* - TDD coverage for resolved-only writes, race refusals, push/requeue abstraction, and evidence redaction.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - update the v3 module count and classification assertion.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=3d7355f117f22e5919f5d135dd41d7042e6d81a1b5760bdbf739ae0fcf1892a2

```text
.ce/changelog/ce216-executor-race-guard.md
.ce/pr-manifests/ce216-executor-race-guard.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/integrator_executor.py
validators/tests/unit/test_integrator_executor.py
validators/tests/unit/test_version_boundary.py
```
