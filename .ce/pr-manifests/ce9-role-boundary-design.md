# PR path manifest - ce9-role-boundary-design

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce9-role-boundary-design
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
`creator-engine/creator-engine#9` Stage 1 architect design / policy amendment
output only. This PR adds the design document, changelog fragment, and this
path-manifest carrier. It explicitly does not implement enforcement, hooks,
validators, runtime code, CI wiring, schema changes, live settings, or any
binding Operator decision.

Per-file purpose (closed path-set - 3 paths):

- **`.ce/changelog/ce9-role-boundary-design.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce9-role-boundary-design.md`** *(A)* - this PR's closed path-set carrier.
- **`docs/operations/ROLE_BOUNDARY_FAILSAFE_STAGE_1_DESIGN.md`** *(A)* - Stage 1 design / policy amendment output for `creator-engine/creator-engine#9`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=21e9b2078b595f6633ec3279e8b8a3876c933ceb1c6536896951c7ac975c279c

```text
.ce/changelog/ce9-role-boundary-design.md
.ce/pr-manifests/ce9-role-boundary-design.md
docs/operations/ROLE_BOUNDARY_FAILSAFE_STAGE_1_DESIGN.md
```
