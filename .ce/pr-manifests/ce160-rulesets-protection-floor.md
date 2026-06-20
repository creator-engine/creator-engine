# PR path manifest - ce160-rulesets-protection-floor

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce160-rulesets-protection-floor
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#160 protection floor via repository Rulesets for Free-plan private repos,
classic-to-Ruleset fallback, and independent squash-only merge settings.

Base:
`b25e57b3bf1239c83a34837d90312f15f1d82e6f` (`origin/main` after #290).

Per-file purpose (closed path-set - 14 paths):

- **`.ce/changelog/ce160-rulesets-protection-floor.md`** *(A)* - per-change changelog fragment.
- **`.ce/pr-manifests/ce160-rulesets-protection-floor.md`** *(A)* - this PR's closed path-set carrier.
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* - exports the CE protection Ruleset name and squash-only repo setting operation.
- **`validators/creator_engine_validator/forge/github_repo_config.py`** *(M)* - classic branch-protection plan fallback to Rulesets plus squash-only repo merge settings.
- **`validators/creator_engine_validator/forge/ruleset.py`** *(M)* - maps the CE floor to repository Ruleset status-check and pull-request rules.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* - carries the schema `squash_only` floor through apply and already-CE detection.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* - verifies the floor through classic protection or the named Ruleset and checks squash-only settings.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - exposes the squash-only repo setting operation through `cev3 configure-repo`.
- **`validators/tests/unit/test_github_repo_config.py`** *(M)* - covers classic-to-Ruleset fallback and squash-only repo settings.
- **`validators/tests/unit/test_onboard_apply.py`** *(M)* - asserts onboard apply carries the squash-only floor.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* - covers live Ruleset floor detection when classic protection is unavailable.
- **`validators/tests/unit/test_ruleset.py`** *(M)* - covers the CE floor Ruleset payload.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed digest for the rebuilt validator app wheel.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel for source parity.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=382014f326153d7ac68bcee9f99a09b6fe742e8d40c8bfbfdb6fd0f11838be5b

```text
.ce/changelog/ce160-rulesets-protection-floor.md
.ce/pr-manifests/ce160-rulesets-protection-floor.md
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/github_repo_config.py
validators/creator_engine_validator/forge/ruleset.py
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_github_repo_config.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_ruleset.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
