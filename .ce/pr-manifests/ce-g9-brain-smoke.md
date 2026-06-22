# PR path manifest - ce-g9-brain-smoke - ce-ops#186 G9 brain recall/hydrate smoke

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-g9-brain-smoke
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`73bff5a9561c8f141b1f79cda9a54030a02f0230` (`origin/main` at branch creation).

Work class: `story`.

Scope:
ce-ops#186 G9 adds a bounded, repeatable smoke for the company-brain recall and
session hydration path. It is test-only: no production code, existing tests, or
wheelhouse files are authorized.

Per-file purpose:
- **`.ce/changelog/ce-g9-brain-smoke.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-g9-brain-smoke.md`** *(A)* - this carrier.
- **`validators/tests/integration/test_ce_brain_recall_smoke.py`** *(A)* -
  end-to-end G9 recall/hydrate smoke over a temporary Markdown corpus.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=2bfb3edba32d72d8e37471ebb987de3666d5a68feb7b179348b62830fcf72ad7

```text
.ce/changelog/ce-g9-brain-smoke.md
.ce/pr-manifests/ce-g9-brain-smoke.md
validators/tests/integration/test_ce_brain_recall_smoke.py
```
