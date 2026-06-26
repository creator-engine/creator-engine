# PR path manifest - ce252-validate-pr-ci-parity

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce252-validate-pr-ci-parity --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** tiny

Scope:
ce-ops#252 follow-up. `ce validate-pr`'s default baseline-diff test command
ran unit-only (`validators/tests/unit`), which is narrower than CI's offline
pytest step and produced false-greens (it let integration-test failure #507
through). This change aligns `DEFAULT_TEST_COMMAND` to CI's offline invocation
exactly (full `validators/tests/` tree, `-m "not wheel_bake_gate"`, `-q`,
`-n auto --dist loadgroup`), restoring true CI parity for the local preflight.

Per-file purpose:
- **`.ce/changelog/ce252-validate-pr-ci-parity.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce252-validate-pr-ci-parity.md`** *(A)* - this closed path-set carrier.
- **`docs/operations/AUTHOR_A_CE_VALID_PR.md`** *(M)* - document the CI-parity (full-tree) preflight scope.
- **`validators/creator_engine_validator/pr_preflight.py`** *(M)* - `DEFAULT_TEST_COMMAND` now mirrors CI's offline pytest invocation.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=c71c753033d20a2d018cb173f8b5c8c1d5670f5a3c54e4d8b6a9bbde7d83dcbc

```text
.ce/changelog/ce252-validate-pr-ci-parity.md
.ce/pr-manifests/ce252-validate-pr-ci-parity.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
validators/creator_engine_validator/pr_preflight.py
```
