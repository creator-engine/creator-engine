# PR path manifest - ce-n3-dualformat-sync-gate

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs
`verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-n3-dualformat-sync-gate`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

- **Declared work class:** S

Per-file purpose:
- **`.ce/changelog/ce-n3-dualformat-sync-gate.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-n3-dualformat-sync-gate.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - registers the new check module.
- **`validators/creator_engine_validator/checks/dual_format_sync.py`** *(A)* - PR-diff dual-format sibling gate.
- **`validators/creator_engine_validator/pr_preflight.py`** *(M)* - runs the new gate during validate-pr.
- **`validators/tests/unit/test_dual_format_sync.py`** *(A)* - focused gate coverage.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=af509083fd8295128d7575dd31f45fdb7c27065066d888adde088aef0fab9e69

```text
.ce/changelog/ce-n3-dualformat-sync-gate.md
.ce/pr-manifests/ce-n3-dualformat-sync-gate.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/dual_format_sync.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_dual_format_sync.py
```
