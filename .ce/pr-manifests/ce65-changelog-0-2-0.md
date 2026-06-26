# PR path manifest - ce65-changelog-0-2-0 - bring CHANGELOG.md current to v0.2.0

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce65-changelog-0-2-0 --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Change:
Bring the root changelog current to the 0.2.0 self-hosting milestone, preserving
the existing release-surface preamble and adding an [Unreleased] section for
future work.

Per-file purpose (the closed path-set - 3 paths):
- **`.ce/changelog/ce65-changelog-0-2-0.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce65-changelog-0-2-0.md`** *(A)* - this carrier (self-inclusive).
- **`CHANGELOG.md`** *(M)* - release notes for v0.2.0 plus [Unreleased].

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=50a62d1efa92e8216e3620a8d8855c14e1a14ba241a7546fb83c20b923b79746

```text
.ce/changelog/ce65-changelog-0-2-0.md
.ce/pr-manifests/ce65-changelog-0-2-0.md
CHANGELOG.md
```
