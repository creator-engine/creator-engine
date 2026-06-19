# PR path manifest - ce140-readme-refresh

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce140-readme-refresh

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Controller relay for ce-ops#140 on 2026-06-19: refresh the repository README to
the current v3.5 state, accurate to in-repo contracts and operations docs.
Do not touch website files, served install docs, trust-root paths, checksum
manifests, or wheelhouses.

Base:
`d2d22b0787be883a149f6702e11dfb2e62358b8e` (`origin/main` at branch creation).

The changes:
- `README.md` is rewritten as the repository orientation for CE's current
  governed-SDLC automation layer posture.
- The README now summarizes the active v3.5 direction, the every-agent-contained
  containment arc, the installer/offline wheelhouse story, per-developer forge
  identity binding, controller/reviewer identity records, and current canonical
  repo links.
- Changelog and PR carrier metadata record the README-only scope.

Per-file purpose (the closed path-set - 3 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce140-readme-refresh.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce140-readme-refresh.md`** *(A)* - this carrier.
- **`README.md`** *(M)* - current v3.5 repository orientation.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=4fadff542b684f65100b5db629ad49443a715800df5fb8dcdeb06d534c150b64

```text
.ce/changelog/ce140-readme-refresh.md
.ce/pr-manifests/ce140-readme-refresh.md
README.md
```
