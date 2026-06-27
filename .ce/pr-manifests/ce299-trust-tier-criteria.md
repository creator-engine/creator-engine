# PR path manifest - ce299-trust-tier-criteria - ce-ops#299 trust-tier graduation criteria

- **Declared work class:** tiny

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce299-trust-tier-criteria

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#299 defines concrete, observable trust-tier graduation criteria for
the contributor growth path without changing schema, validators, CODEOWNERS,
branch protection, governance contracts, or the constitution.

Per-file purpose:
- **`.ce/changelog/ce299-trust-tier-criteria.md`** *(A)* - changelog fragment for the docs-only trust-tier criteria update.
- **`.ce/pr-manifests/ce299-trust-tier-criteria.md`** *(A)* - this carrier.
- **`docs/guide/contributing-to-ce.md`** *(M)* - add trust-tier graduation criteria under Section 9.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=2253ec10cd51b9f943cd06d98917ed8636ad1fe829c8c5f4d339dfdc5e9e63c5

```text
.ce/changelog/ce299-trust-tier-criteria.md
.ce/pr-manifests/ce299-trust-tier-criteria.md
docs/guide/contributing-to-ce.md
```
