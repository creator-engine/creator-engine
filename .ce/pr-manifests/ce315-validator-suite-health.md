# PR path manifest - ce315-validator-suite-health - #315 W4-G10 validator test-suite health

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce315-validator-suite-health
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path set below
(including this carrier).

Base:
`8421ca64ad8b2c779ad476c581b721710ccc9ec8` (`origin/codex/ce133-remove-committed-app-wheel`).

Change:
#315 repairs the W4-G10 validator test-suite health path. It restores full
`validators/tests` suite health by fixing the adoption apply live test's
temporary-path isolation and updating the Ring-1 tool guard to honor `TMPDIR`.
This PR is stacked on #312 so ADR-0010's first-party app wheel removal remains
owned by `codex/ce133-remove-committed-app-wheel`; this diff does not modify the
committed validator wheel or re-pin its checksum.

Per-file purpose:
- **`.ce/changelog/ce315-validator-suite-health.md`** *(A)* - changelog fragment for #315.
- **`.ce/pr-manifests/ce315-validator-suite-health.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/runner/ring1_tool_guard.py`** *(M)* - honor `TMPDIR` when choosing the Ring-1 guard shim parent.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* - fix the adoption apply live test to use `tmp_path` isolation.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=d01e4bbcd13dc2088ae350f2e461820779e01a74b4527cccade314ae4f86cd09

```text
.ce/changelog/ce315-validator-suite-health.md
.ce/pr-manifests/ce315-validator-suite-health.md
validators/creator_engine_validator/runner/ring1_tool_guard.py
validators/tests/unit/test_onboard_apply_live.py
```
