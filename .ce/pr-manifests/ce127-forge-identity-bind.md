# PR path manifest - ce127-forge-identity-bind - bind forge identity at install time

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce127-forge-identity-bind
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Ratified:
Controller relay for ce-ops#127 on 2026-06-18: bind forge identity at install
time to the per-dev identity from onboard/App/PAT configuration, not ambient git;
surface and validate the resolved identity; fail closed on ambient fallback.

Base:
`4b62822` (`origin/main` at branch creation).

Per-file purpose (closed path-set - 8 paths):
- **`.ce/changelog/ce127-forge-identity-bind.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce127-forge-identity-bind.md`** *(A)* - this carrier.
- **`docs/contracts/installer.md`** *(M)* - documents install-time forge author binding and ambient fallback refusal.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* - surfaces resolved forge identity in scaffold leg evidence.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* - binds local git author config to install-time forge identity and validates the commit author.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* - TDD coverage for per-dev identity binding and unresolved identity refusal.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel from this branch source.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app-wheel digest re-pinned.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=815aa415cf917a134bc929d1e5c66c3a84c610972555afeef51d9bce6a80f943

```text
.ce/changelog/ce127-forge-identity-bind.md
.ce/pr-manifests/ce127-forge-identity-bind.md
docs/contracts/installer.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply_live.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
