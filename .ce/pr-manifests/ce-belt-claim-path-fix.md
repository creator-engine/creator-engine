# PR path manifest - ce-belt-claim-path-fix - pickup belt claim-path crash fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-belt-claim-path-fix
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path set below
(including this carrier).

Base:
`ae8a4c9` (`origin/main` at branch creation).

Change:
Fix the `ce pickup poll --claim` belt canary crash diagnosed on current main.
The pickup claim/launch paths now use the already imported `V3_LOCAL_STATE_ROOT`
instead of stale `_versions.V3_LOCAL_STATE_ROOT` references. Offline CLI coverage
exercises `pickup poll --claim` with launch disabled, fake Search transport, one
work item, default pickup ledger root, and no lane spawn.

Per-file purpose:
- **`.ce/changelog/ce-belt-claim-path-fix.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-belt-claim-path-fix.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - replace stale pickup `_versions` references with `V3_LOCAL_STATE_ROOT`.
- **`validators/tests/unit/test_pickup.py`** *(M)* - offline regression for claim-path ledger write with launch disabled.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=61c3bcd9978b3335f727dfd9b31dfb09cae4cfa593414f1212262f5410cf187f

```text
.ce/changelog/ce-belt-claim-path-fix.md
.ce/pr-manifests/ce-belt-claim-path-fix.md
validators/creator_engine_validator/ce_cli.py
validators/tests/unit/test_pickup.py
```
