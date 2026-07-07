# PR path manifest — ce-491-optiona-merge-intent

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-491-optiona-merge-intent` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=de04bebbb2ddd046788115bc8bba55a89840c4d1cfac82eebdb9f3541b9477cc

```text
.ce/changelog/ce-491-optiona-merge-intent.md
.ce/pr-manifests/ce-491-optiona-merge-intent.md
docs/design/ce-491-optiona-merge-intent.md
```

## Evidence / Preflight Summary

Brief verification:

- `sha256sum /var/tmp/BRIEF_dev4_491_optionA_design_20260707.md`
  returned `b19584043eb71df8953bb2150145650af95ceb55840010530e03d486cc5d13bc`.

Working-tree checks before commit:

- `PYTHONPATH=validators python -m creator_engine_validator scan-public-docs-confidentiality docs/design/ce-491-optiona-merge-intent.md`
  returned `PASS public_docs_confidentiality`.
- `PYTHONPATH=validators python -m creator_engine_validator scan-path-manifest .ce/pr-manifests/ce-491-optiona-merge-intent.md`
  returned `PASS path_manifest_fidelity`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-work-sizing-floor --base origin/main --declared-work-class S`
  returned `PASS work_sizing_floor`.

Committed-state preflight after initial commit `914abaca`:

- `PYTHONPATH=validators python -m creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref ce-491-optiona-merge-intent`
  returned `PASS path_manifest_fidelity`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-test-coupling --base origin/main --pr-body-file .ce/pr-manifests/ce-491-optiona-merge-intent.md`
  returned `PASS test_coupling`.
- `./scripts/ce-preflight.sh --base origin/main --head-ref ce-491-optiona-merge-intent`
  exited `1`. Its final report showed the PR-diff gates passing, including
  `path-manifest`, `test-coupling`, `work-sizing floor`, declared work class
  `S`, brain ledger current-tail gate not applicable, and baseline-diff pytest
  with zero new failures (`baseline=63`, `head=63`). The failing repo-wide
  gates were `Control-plane portability guard`, `check-examples aggregate gate`,
  and `well-formed examples`.
- `PYTHONPATH=validators python -m creator_engine_validator scan-portability-plane`
  exited `1` with `CE-PORTABILITY:
  validators/creator_engine_validator/container_launcher.py:86: literal /run
  path is only allowed in declared runtime-plane modules or exact dated baseline
  exemptions`.
- `PYTHONPATH=validators python -m creator_engine_validator check examples/well-formed/`
  exited `1` with `FAIL worktree_lease_schema` because the signed lease example
  could not be verified: `libsodium unavailable`.
- `PYTHONPATH=validators python -m creator_engine_validator check-examples`
  exited `1` because `examples/well-formed` did not meet its expected-pass
  expectation (`FR-028`), consistent with the `libsodium unavailable` failure
  above.
