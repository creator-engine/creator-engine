# PR path manifest - ce157-context-observability-design

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce157-context-observability-design

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#157 install-acceptance slice: add a repo-visible documentation/design note
capturing Controller context-window observability requirements for future G-6/G-7
UX design. Keep the change docs-only and small. Do not implement runtime hooks,
status-line scripts, product code, or v1 behavior.

Base:
`85c9330480a4e80f045f1211a3934d2b01b744f8` (`origin/main` at branch creation).

Per-file purpose (closed path-set - 3 paths; `(A)` add):
- **`.ce/changelog/ce157-context-observability-design.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce157-context-observability-design.md`** *(A)* - this carrier.
- **`docs/architecture/controller-context-observability.md`** *(A)* - design note for future G-6/G-7 context-window observability UX.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=cb4dd9c08559b2f0a73a2c04edd49c4f6d0b5f27e67edca87836419e45d5446b

```text
.ce/changelog/ce157-context-observability-design.md
.ce/pr-manifests/ce157-context-observability-design.md
docs/architecture/controller-context-observability.md
```
