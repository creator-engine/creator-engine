# PR path manifest - ce-885-882-followups - #885/#882 follow-up batch

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-885-882-followups` and requires
this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this
carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=1c29b82e470df2c74c1635cff4c5a151ed9e55caa3a0603468844655be96df15

```text
.ce/changelog/ce-885-882-followups.md
.ce/pr-manifests/ce-885-882-followups.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_pr_preflight.py
```

## Evidence Summary

- Focused unit: `PYTHONPATH=validators PYTEST_ADDOPTS="-n 2" /tmp/ce-885-882-followups-venv/bin/python -m pytest validators/tests/unit/test_onboard_apply.py -q` - 74 passed.
- Focused unit: `PYTHONPATH=validators PYTEST_ADDOPTS="-n 2" /tmp/ce-885-882-followups-venv/bin/python -m pytest validators/tests/unit/test_pr_preflight.py -q` - 41 passed.
- Local preflight: pending clean committed-tree run.
