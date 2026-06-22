# PR path manifest - ci192-shallow-fetch-fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ci192-shallow-fetch-fix

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

The change (ce-ops#192): the `Validate` workflow intermittently failed with
`fatal: shallow file has changed since we read it` in the "Resolve live
comparison base" step, ejecting APPROVED + green PRs from the merge queue. The
`Checkout` step ran with the default shallow clone (fetch-depth 1), forcing
runtime `--depth`/`--unshallow` deepening that races on `.git/shallow`. Setting
`fetch-depth: 0` gives full history so the comparison-base `git merge-base`
resolves directly — no shallow state, no race.

Per-file purpose (the closed path-set - 3 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ci192-shallow-fetch-fix.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ci192-shallow-fetch-fix.md`** *(A)* - this carrier.
- **`.github/workflows/validate.yml`** *(M)* - set `fetch-depth: 0` on the
  `Checkout` step (removes the shallow-clone race).

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=e4f23bf7d4585e2c42690102e8f814d559184465931c48265e718af04db312e8

```text
.ce/changelog/ci192-shallow-fetch-fix.md
.ce/pr-manifests/ci192-shallow-fetch-fix.md
.github/workflows/validate.yml
```
