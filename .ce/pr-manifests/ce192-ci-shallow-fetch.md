# PR path manifest - ce192-ci-shallow-fetch

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce192-ci-shallow-fetch
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Declared work class: tiny

Scope:
ce-ops#192 fixes the Validate workflow shallow-fetch race in the live
comparison base resolver. The change is limited to retrying the existing
live-base fetch/deepen commands when Git reports that `.git/shallow` changed
mid-read. It does not make checkout full-history and does not change the
packaging contract.

Per-file purpose:
- **`.ce/changelog/ce192-ci-shallow-fetch.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce192-ci-shallow-fetch.md`** *(A)* - this closed
  path-set carrier.
- **`.github/workflows/validate.yml`** *(M)* - bounded retry around the
  live-base fetch/deepen commands.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=e036defa713228d0fea9fbfc0b9361942995c1fa2d5e572ad64bd4ee34f62f69

```text
.ce/changelog/ce192-ci-shallow-fetch.md
.ce/pr-manifests/ce192-ci-shallow-fetch.md
.github/workflows/validate.yml
```
