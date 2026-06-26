# PR path manifest - ce252-validate-pr-preflight

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce252-validate-pr-preflight --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
ce-ops#252 completes the additive safety slice for local PR preflight by
preserving the existing `ce validate-pr` gate surface, adding hard-fail coverage
for carrier, manifest, declared-work-class, and new-test-failure regressions, and
documenting the author flow for a CE-valid PR.

Per-file purpose:
- **`.ce/changelog/ce252-validate-pr-preflight.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce252-validate-pr-preflight.md`** *(A)* - this closed path-set carrier.
- **`docs/operations/AUTHOR_A_CE_VALID_PR.md`** *(A)* - concise author playbook.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - CLI wiring for declared-work-class discovery and test command selection.
- **`validators/creator_engine_validator/pr_preflight.py`** *(M)* - additive preflight hardening and per-check summary behavior.
- **`validators/tests/unit/test_ce_validate_pr_cli.py`** *(M)* - CLI dispatch coverage.
- **`validators/tests/unit/test_pr_preflight.py`** *(M)* - focused safety regression coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=fbcf96b190cca093b98dddabb86f486330a0e27563e8911257ed188c42130658

```text
.ce/changelog/ce252-validate-pr-preflight.md
.ce/pr-manifests/ce252-validate-pr-preflight.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_validate_pr_cli.py
validators/tests/unit/test_pr_preflight.py
```
