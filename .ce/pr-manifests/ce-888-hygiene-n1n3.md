# PR path manifest - ce-888-hygiene-n1n3 - CE-888 hygiene N1-N3

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-888-hygiene-n1n3` and requires
this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this
carrier lists itself.

- **Declared work class:** tiny

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=bbbdea3be3d50657d8df9ecdb6216857e10ab7b62d7fd6ddb5463488c532d0b9

```text
.ce/changelog/ce-888-hygiene-n1n3.md
.ce/pr-manifests/ce-888-hygiene-n1n3.md
validators/creator_engine_validator/brain_runtime.py
validators/tests/unit/test_brain_runtime.py
```

## Evidence Summary

- Focused unit: `PYTEST_ADDOPTS="-n 2" uv run --directory validators --with pytest==9.0.2 --with pytest-xdist==3.8.0 python -m pytest tests/unit/test_brain_runtime.py -q` - 21 passed.
- Mutation check: with `_resume_state_pointer` temporarily reverted to the old hash-first tuple order, `test_resume_state_pointer_selects_newest_resume_path_before_hash` failed by selecting the older `20260707...` file; restored path-first order passes.
- Local preflight: `CE_VALIDATOR_PYTHON=/var/tmp/ce-888-hygiene-n1n3-venv/bin/python PYTHONPATH=validators PYTEST_ADDOPTS="-n 2" PYTEST_XDIST_AUTO_NUM_WORKERS=2 /var/tmp/ce-888-hygiene-n1n3-venv/bin/python -m creator_engine_validator.ce_cli validate-pr --repo-root .` - ENV-SKIP: clean worktree, comparison base, brain-ledger gate, and declared work class passed; baseline-diff validation is environment-blocked on this host (`Landlock filesystem mediation is required`, shell dry-run checks cannot import `PyYAML`, and installer tests report missing `ssh-keygen`). Baseline attempt reported 6880 passed, 31 skipped, 9 environment failures before the run was interrupted to avoid continuing into head tests with the same host blockers.
