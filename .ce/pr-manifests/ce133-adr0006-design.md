# PR path manifest - ce133-adr0006-design

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce133-adr0006-design
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Ratified controller relay:
ce-ops#133 ADR-0006 design only. Produce
`docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md` covering the
derived-artifact trust-path split, reproducible vendored dependencies,
merge-queue wheel/source verification, ce-ops#91 doc-currency touchpoints,
ce-ops#65 changelog-gate touchpoints, and a phased plan that ends the per-PR
app-wheel rebuild tax. No implementation, no binding changes, no push.

Base:
`3314ec4d` (`origin/main` at rebase, post PR #272).

Per-file purpose (closed path-set - 3 paths):
- **`.ce/changelog/ce133-adr0006-design.md`** *(A)* - changelog fragment for the design artifact.
- **`.ce/pr-manifests/ce133-adr0006-design.md`** *(A)* - this carrier.
- **`docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md`** *(A)* - proposed design-only ADR.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=fc909ddecb32c762a7ae80728843b403698fd980445b4c08d063200eab1bf6d8

```text
.ce/changelog/ce133-adr0006-design.md
.ce/pr-manifests/ce133-adr0006-design.md
docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md
```
