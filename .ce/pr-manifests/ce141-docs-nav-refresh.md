# PR path manifest - ce141-docs-nav-refresh

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce141-docs-nav-refresh
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`b344549800dbadf1b550262c2b35b82c599172be` (`origin/main` at branch creation).

Work class: `story`.

Scope:
ce-ops#141 refreshes the live v8 site docs navigation by adding a real `#docs`
section to `docs/index.html`, linking current user-facing docs, and proving
offline that same-page anchors resolve. No site archive mutation is authorized.

Per-file purpose:
- **`.ce/changelog/ce141-docs-nav-refresh.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce141-docs-nav-refresh.md`** *(A)* - this closed path-set carrier.
- **`docs/index.html`** *(M)* - live v8 site docs section and current doc links.
- **`validators/tests/unit/test_site_index_docs_nav.py`** *(A)* - focused offline anchor and docs-link coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=de8135b94f668091842781278807085d55353e491f2918e5b88ccd5b709d075a

```text
.ce/changelog/ce141-docs-nav-refresh.md
.ce/pr-manifests/ce141-docs-nav-refresh.md
docs/index.html
validators/tests/unit/test_site_index_docs_nav.py
```
