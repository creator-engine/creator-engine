# PR path manifest - ce154-autoclose

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce154-autoclose

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Controller relay for ce-ops#154 on 2026-06-20: add a cross-repo GitHub Action
that closes creator-engine/ce-ops issues only from explicit merged-PR closing
refs, using a dedicated least-privilege `CE_OPS_TOKEN` and fail-soft runtime
behavior. Fold the explicit `Closes ce-ops#N` authoring requirement toward
ce-ops#65.

Base:
`03d3796dd16429358884658a29bdcda8e3f986b4` (`origin/main` at branch creation).

The changes:
- `.github/workflows/ce-ops-autoclose.yml` runs on `pull_request` close events
  merged to `main`, checks out this repo's script, and invokes it with
  `CE_OPS_TOKEN`.
- `.github/scripts/ceops_autoclose.py` parses PR title/body closing refs,
  guards non-`main` base refs, skips already-closed issues, posts provenance,
  closes open ce-ops issues via the GitHub API, and logs instead of failing the
  workflow on API errors.
- `validators/tests/unit/test_ceops_autoclose.py` covers parser behavior for
  required separators, rejected adjacent keywords, bare mentions, negated prose,
  multiple refs, Fixes/Resolves/Closed variants, case-insensitivity, duplicate
  refs, and non-`main` base no-op behavior.
- Changelog and PR carrier metadata record the branch scope.

Per-file purpose (the closed path-set - 5 paths; `(A)` add):
- **`.ce/changelog/ce154-autoclose.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce154-autoclose.md`** *(A)* - this carrier.
- **`.github/scripts/ceops_autoclose.py`** *(A)* - tested parse and close logic.
- **`.github/workflows/ce-ops-autoclose.yml`** *(A)* - merged-PR autoclose workflow.
- **`validators/tests/unit/test_ceops_autoclose.py`** *(A)* - parser unit tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=49ef0050406cb829fad55a9033d8724dd8cb69f92e5037f9a6bf8fd319db709f

```text
.ce/changelog/ce154-autoclose.md
.ce/pr-manifests/ce154-autoclose.md
.github/scripts/ceops_autoclose.py
.github/workflows/ce-ops-autoclose.yml
validators/tests/unit/test_ceops_autoclose.py
```
