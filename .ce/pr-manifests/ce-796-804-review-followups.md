# PR path manifest — ce-796-804-review-followups · stale-wheel and contained-seat review follow-ups

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-796-804-review-followups` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** tiny

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=5714c68c53db657fcb5fe647600e6d1101cd58426341a02199975e9c96f8478a

```text
.ce/changelog/ce-796-804-review-followups.md
.ce/pr-manifests/ce-796-804-review-followups.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/path_manifest_fidelity.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_cli_skew_guard.py
```
