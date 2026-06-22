# PR path manifest - ce83-issue-intake-role-contract

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce83-issue-intake-role-contract

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified scope:
`creator-engine/creator-engine#83` docs-only slice: define the CE GitHub Issue
intake/opening role/sub-agent contract. This pass does not implement runtime
code, GitHub mutation tooling, workflow wiring, or validator behavior.

Base:
`10dc92261073945cfc3088255de9360fdb8d83b6` (`origin/main` at authoring time).

The changes:
- Add `docs/contracts/github-issue-intake.md` documenting the issue intake role
  boundary, required Operator authority, duplicate search, existing-label
  selection, mutation evidence, returned URL/number/body hash, and the
  non-authorizing nature of GitHub issues.
- Add a changelog fragment and this path-manifest carrier.

Per-file purpose (the closed path-set - 3 paths; `(A)` add):
- **`.ce/changelog/ce83-issue-intake-role-contract.md`** *(A)* - changelog
  fragment.
- **`.ce/pr-manifests/ce83-issue-intake-role-contract.md`** *(A)* - this
  carrier.
- **`docs/contracts/github-issue-intake.md`** *(A)* - issue intake role
  contract.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=f7129214acf06d3c1af7a0e9f69038ebc3244852e077dde67e91ac05e35bbc60

```text
.ce/changelog/ce83-issue-intake-role-contract.md
.ce/pr-manifests/ce83-issue-intake-role-contract.md
docs/contracts/github-issue-intake.md
```
