# PR path manifest — ce-ops#279 · rented surface render CLI

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-279-surfaces-render
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below.
This carrier lists itself.

- **Declared work class:** story

Scope: ce-ops#279 — add the rented-surface manifest renderer and focused unit
tests. No registered validator checks or existing runtime/Docker integration
files are modified.

Per-file purpose:
- **`.ce/changelog/ce-279-surfaces-render.md`** *(A)* - changelog fragment with `work_class: story`.
- **`.ce/pr-manifests/ce-279-surfaces-render.md`** *(A)* - this carrier (self-inclusive).
- **`surfaces/render.py`** *(A)* - deterministic manifest renderer CLI.
- **`validators/tests/unit/test_surfaces_render.py`** *(A)* - focused renderer unit tests.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=ba81bf8034b290731be4019507ec89b218d5d9402cb2f9a9f3f8d57c2d6f5215

```text
.ce/changelog/ce-279-surfaces-render.md
.ce/pr-manifests/ce-279-surfaces-render.md
surfaces/render.py
validators/tests/unit/test_surfaces_render.py
```
