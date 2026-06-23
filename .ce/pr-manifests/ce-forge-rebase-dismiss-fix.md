# PR path manifest - ce-forge-rebase-dismiss-fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-forge-rebase-dismiss-fix
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`a83d384d` (`origin/main` at branch handoff).

- **Declared work class:** bug

Scope:
creator-engine#368 / ce-ops#151. The CE-emitted `ce-reference-protection-floor`
ruleset carried GitHub's blunt `dismiss_stale_reviews_on_push: true`, dismissing
standing approvals on EVERY push including pure rebases and silently overriding
branch-protection `dismiss_stale_reviews=false`. This PR makes the emitted
ruleset diff-aware-safe: CE no longer emits the blunt flag by default
(re-review-on-content-change is the CE-owned `forge.re_review` lane / ce-ops#151),
and the two installer emit sites stop propagating the branch-protection floor
into the blunt ruleset flag. The already-live ruleset must be remediated out of
band (see PR body for the exact `gh api`). No wheel rebuild: the validator is
built from source (no committed `creator_engine_validator-*.whl` in
`validators/wheelhouse/`).

Per-file purpose:
- **`.ce/changelog/ce-forge-rebase-dismiss-fix.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-forge-rebase-dismiss-fix.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/forge/github_repo_config.py`** *(M)* - `_ruleset_policy_from_branch_protection` no longer propagates the branch-protection `dismiss_stale_reviews` floor into the blunt ruleset flag.
- **`validators/creator_engine_validator/forge/ruleset.py`** *(M)* - `RulesetPolicy.dismiss_stale_reviews_on_push` default flipped `True -> False` (diff-aware-safe); explanatory docstring.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* - `_ruleset_policy_for_branch` no longer propagates the floor flag into the blunt ruleset flag.
- **`validators/tests/unit/test_ruleset.py`** *(M)* - regression tests: default emits no blanket dismissal; rebase-safe live ruleset satisfies policy; explicit opt-in still emits the blunt flag.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=2914b6e526f77680a077e90f0376fb44ce3069d1d91d52448a956232df2d90c2

```text
.ce/changelog/ce-forge-rebase-dismiss-fix.md
.ce/pr-manifests/ce-forge-rebase-dismiss-fix.md
validators/creator_engine_validator/forge/github_repo_config.py
validators/creator_engine_validator/forge/ruleset.py
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_ruleset.py
```
