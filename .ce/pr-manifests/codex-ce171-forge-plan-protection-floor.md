# PR path manifest - codex-ce171-forge-plan-protection-floor

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref codex/ce171-forge-plan-protection-floor
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#171 onboard protection-floor diagnostics for GitHub repositories whose
plan/capability cannot enforce branch protection or Rulesets.

Base:
`297be9f08f71f5f454594b6519dc20d6ab61ed84` (`origin/main` after #314).

Per-file purpose (closed path-set - 12 paths):

- **`.ce/changelog/ce171-protection-floor-unenforceable.md`** *(A)* - per-change changelog fragment.
- **`.ce/pr-manifests/codex-ce171-forge-plan-protection-floor.md`** *(A)* - this PR's closed path-set carrier.
- **`validators/creator_engine_validator/forge/github_repo_config.py`** *(M)* - reuses the shared protection-floor capability classifier.
- **`validators/creator_engine_validator/forge/protection_diagnostics.py`** *(A)* - shared GitHub plan/capability 403 classifier and remediation payload.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* - carries structured already-CE probe diagnostics and refuses unenforceable protection floors.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* - returns structured classic/rulesets unenforceable diagnostics while preserving Ruleset fallback success.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - surfaces protection enforcement state and refuses plan/apply preflight on unenforceable floors.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - adds branch-protection enforcement state to the pure GitHub plan.
- **`validators/tests/unit/test_onboard_apply.py`** *(M)* - covers apply-leg refusal and remediation.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* - covers live-driver Ruleset fallback and plan-tier 403 diagnostics.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - covers plan/apply preflight refusal payloads.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - covers planner enforcement state.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=4da7ecf60081a1da02489ab4f2266a8c7ce83d71a6798602332d767b941c3de2

```text
.ce/changelog/ce171-protection-floor-unenforceable.md
.ce/pr-manifests/codex-ce171-forge-plan-protection-floor.md
validators/creator_engine_validator/forge/github_repo_config.py
validators/creator_engine_validator/forge/protection_diagnostics.py
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
```
