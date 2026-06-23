# PR path manifest - ce216-eviction-detection

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce216-eviction-detection
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#216 Unit 1 adds read-only integrator eviction detection for approved,
green PRs that flip to dirty, behind, or conflicting merge state. This PR does
not add a daemon, executor behavior, merge behavior, or repair mutation.

Per-file purpose:
- **`.ce/changelog/ce216-eviction-detection.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce216-eviction-detection.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classifies the new detector as v3 forge runtime.
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* - exports the detector event and poll helpers.
- **`validators/creator_engine_validator/forge/eviction_detection.py`** *(A)* - read-only Search API plus PR-state detector.
- **`validators/tests/unit/test_eviction_detection.py`** *(A)* - TDD coverage for event shape, gates, and polling.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - updates the v3 taxonomy count.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=21943a66a2f2e3135a7c4a25bbb6983d83f21e22ca8e4b6a6a1096648559f787

```text
.ce/changelog/ce216-eviction-detection.md
.ce/pr-manifests/ce216-eviction-detection.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/eviction_detection.py
validators/tests/unit/test_eviction_detection.py
validators/tests/unit/test_version_boundary.py
```
