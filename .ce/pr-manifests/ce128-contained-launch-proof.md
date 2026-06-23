# PR path manifest - ce128-contained-launch-proof

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce128-contained-launch-proof
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`ce128-launch-runner-integration` after rebasing #391 onto `origin/main`.

- **Declared work class:** story

Scope:
ce-ops#128/#221 contained-launch verification. Adds proof tests and operator
documentation only; runtime/probe behavior comes from the composed dependency
base.

Per-file purpose:
- **`.ce/changelog/ce128-contained-launch-proof.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce128-contained-launch-proof.md`** *(A)* - this closed path-set carrier.
- **`docs/operations/CONTAINED_LAUNCH_PROOF.md`** *(A)* - CI mock legs and live DGX dogfood command.
- **`validators/tests/unit/test_contained_launch_proof.py`** *(A)* - end-to-end mocked launch/probe proof tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e60cc3b8281fa6c1414c13b5f5b76d0f4cfcfd05f4a04cdbb10d38489d2e7d0b

```text
.ce/changelog/ce128-contained-launch-proof.md
.ce/pr-manifests/ce128-contained-launch-proof.md
docs/operations/CONTAINED_LAUNCH_PROOF.md
validators/tests/unit/test_contained_launch_proof.py
```
