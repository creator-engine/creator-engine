# PR path manifest - ce216-deterministic-resolvers

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce216-deterministic-resolvers
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`origin/main` at branch handoff.

- **Declared work class:** story

Scope:
ce-ops#216 Unit 2. Add a pure deterministic resolver library for the Integrator
MVP's currently hand-resolved conflict families. No executor, push, merge, or
credential authority is introduced.

Per-file purpose:
- **`.ce/changelog/ce216-deterministic-resolvers.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce216-deterministic-resolvers.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify the resolver module as v3 forge code.
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* - expose resolver result and helper APIs through the forge package surface.
- **`validators/creator_engine_validator/forge/deterministic_resolvers.py`** *(A)* - deterministic resolver implementation.
- **`validators/tests/unit/test_deterministic_resolvers.py`** *(A)* - TDD coverage for the required mechanical conflict families and fail-closed cases.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - update the v3 module count and classification assertion.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=1d7c4e59a4b417270d6ae22e28dc4cfebcdf7c50d57c79663f7252fa783a414f

```text
.ce/changelog/ce216-deterministic-resolvers.md
.ce/pr-manifests/ce216-deterministic-resolvers.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/deterministic_resolvers.py
validators/tests/unit/test_deterministic_resolvers.py
validators/tests/unit/test_version_boundary.py
```
