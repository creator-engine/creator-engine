# PR path manifest - ce99-p1-devops

Design/task: `creator-engine/ce-ops#99` P1 repo-scope devops automation,
ratified by the Controller mandate.

Base:
`bcf84649ab6343784bd1aa45690f32ded21ba339`

This is the closed path set for P1 only. It includes repo-scope ruleset,
review-submit, auto-merge, repo-config, PoLP token bindings, unit tests,
the validator wheel rebuild, and this carrier/changelog. It intentionally
excludes org-level rulesets, org membership/PAT/secrets work, and live
`apply=True` integration execution.

Per-file purpose:

- **`.ce/changelog/ce99-p1-devops.md`** *(A)* - per-change changelog fragment.
- **`.ce/pr-manifests/ce99-p1-devops.md`** *(A)* - this PR's closed path-set carrier.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classifies the three new forge op modules as v3 runtime modules.
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* - exports ruleset, review-submit, auto-merge, CODEOWNERS, and repo auto-merge surfaces.
- **`validators/creator_engine_validator/forge/auto_merge.py`** *(A)* - GraphQL per-PR auto-merge op, plan-by-default with injected `GhRunner`.
- **`validators/creator_engine_validator/forge/github_repo_config.py`** *(M)* - repo-level `allow_auto_merge` toggle and Contents API `set_codeowners` op.
- **`validators/creator_engine_validator/forge/merge.py`** *(M)* - documents the corrected `contents:write` merge identity.
- **`validators/creator_engine_validator/forge/review_submit.py`** *(A)* - independent App `APPROVE` submission op with 422 fail-closed behavior.
- **`validators/creator_engine_validator/forge/ruleset.py`** *(A)* - repo ruleset upsert/delete op with `pull_request` bypass actor enforcement.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - adds `cev3`-only `configure-repo`, `ruleset`, `review-submit`, and `auto-merge` verbs.
- **`validators/creator_engine_validator/v3_forge_join.py`** *(M)* - adds P1 token permission bindings and reviewer/auto-merge run wrappers.
- **`validators/tests/unit/test_auto_merge.py`** *(A)* - unit coverage for GraphQL auto-merge plan/apply/refusal/redaction/zero-live behavior.
- **`validators/tests/unit/test_github_repo_config.py`** *(M)* - adds repo auto-merge and CODEOWNERS Contents API coverage.
- **`validators/tests/unit/test_review_submit.py`** *(A)* - unit coverage for reviewer approval, 422 fail-closed, redaction, and reviewer token scope.
- **`validators/tests/unit/test_ruleset.py`** *(A)* - unit coverage for repo ruleset plan/apply/delete, bypass payload, and `always` refusal.
- **`validators/tests/unit/test_scoped_token.py`** *(M)* - asserts P1 token bindings are minimal and mintable under the existing ceiling.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - updates the v3 runtime taxonomy count for the new forge modules.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed digest for the rebuilt validator app wheel.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel for source parity.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=19

AUTHORIZED_PATHS_SHA256=4eeeefa491b00ac97d6e1c6b8c7ffcc8848dca4c4ffca95c8fd87142e3d49d47

```text
.ce/changelog/ce99-p1-devops.md
.ce/pr-manifests/ce99-p1-devops.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/auto_merge.py
validators/creator_engine_validator/forge/github_repo_config.py
validators/creator_engine_validator/forge/merge.py
validators/creator_engine_validator/forge/review_submit.py
validators/creator_engine_validator/forge/ruleset.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_forge_join.py
validators/tests/unit/test_auto_merge.py
validators/tests/unit/test_github_repo_config.py
validators/tests/unit/test_review_submit.py
validators/tests/unit/test_ruleset.py
validators/tests/unit/test_scoped_token.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
