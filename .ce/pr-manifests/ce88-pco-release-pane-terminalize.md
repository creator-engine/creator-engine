# PR path manifest - ce88-pco-release-pane-terminalize

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce88-pco-release-pane-terminalize
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#88 fix: terminalize matching Pane Registry records during `pco-release`
for lapsed claim releases, preserving claim release behavior while keeping the
Pane Registry record closed with `close_reason: lapsed`.

Base:
`79bbaee97f885c5bdf26d91958377af121a7a86b` (`origin/main` after PR #357).

Per-file purpose (closed path-set - 4 paths):
- **`.ce/changelog/ce88-pco-release-pane-terminalize.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce88-pco-release-pane-terminalize.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/pco_allocator.py`** *(M)* - terminalize matching pane records for lapsed releases.
- **`validators/tests/integration/test_pco_allocator_cli.py`** *(M)* - CLI regression coverage for lapsed release terminalization.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=5f155517cb69c29eb884f3ed5d49974510f1db85de276fb15ee10b01fda99a7a

```text
.ce/changelog/ce88-pco-release-pane-terminalize.md
.ce/pr-manifests/ce88-pco-release-pane-terminalize.md
validators/creator_engine_validator/pco_allocator.py
validators/tests/integration/test_pco_allocator_cli.py
```
