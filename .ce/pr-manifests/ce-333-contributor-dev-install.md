# PR path manifest - ce-333-contributor-dev-install - ce-ops#333 contributor editable install docs

- **Declared work class:** tiny

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-333-contributor-dev-install

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#333 documents the public contributor path for installing the validator
package from source in editable mode.

The change:
- Add a public `Developer install (from source, editable)` section to
  `CONTRIBUTING.md`.
- Cross-link the editable contributor install from `validators/README.md`.
- Record the offline editable-install build-backend gap and the dev wheelhouse
  workaround without changing source code.

Per-file purpose (the closed path-set - 4 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce-333-contributor-dev-install.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-333-contributor-dev-install.md`** *(A)* - this carrier.
- **`CONTRIBUTING.md`** *(M)* - public editable contributor install instructions.
- **`validators/README.md`** *(M)* - short public pointer to the contributing guide.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=077fb07c03ea7e4380bf1478993924de534e47245c6f2c23706b5ea9a7df46a2

```text
.ce/changelog/ce-333-contributor-dev-install.md
.ce/pr-manifests/ce-333-contributor-dev-install.md
CONTRIBUTING.md
validators/README.md
```
