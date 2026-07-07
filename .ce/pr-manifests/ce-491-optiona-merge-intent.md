# PR path manifest — ce-491-optiona-merge-intent

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-491-optiona-merge-intent` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

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
- `sha256sum /var/tmp/BRIEF_dev4_889_revision_20260708.md`
  returned `855943b2c32baaeb1895f34d81a0539dce1a8f41d55afc7e7c704a9967892e62`.

Revision evidence summary:

- B1 and n1: resolved in `Tracked Schema Reconciliation`, which names
  `validators/creator_engine_validator/brain_append_intent.schema.yaml` and
  `validators/creator_engine_validator/brain_append_worker.py`, classifies
  Option A as extending the tracked ce-488 envelope, and reconciles
  discriminator, string schema version, `intent_kind`, payload shape, and
  PR-binding fields.
- M1: resolved in `Materialized Ledger Record Schema`, which lists full field
  sets, canonical YAML ordering, and the prohibition on execution-time-variable
  fields in record bodies.
- M2: resolved in `Failure And Crash Model` and `Materialized Ledger Record
  Schema`, which persist `materialization_key` in both the appended ledger
  record and the `CE-Materialization-Key` commit trailer.
- M3 and m3: resolved in `HELD State Cascade` and `Failure And Crash Model`,
  including per-component hold scope, a 30-minute closeout window, restart
  re-entry, follow-up-PR repair semantics, and pre-arming manual authorization.
- M4: resolved in `Tracked Schema Reconciliation` and `Interaction With The
  #882 Stale-Tail Gate`, naming `brain_append_intent_xor_direct_ledger` and
  refusing hybrid intent plus direct-ledger PRs as a hard gate.
- M5: resolved in `Lease Contract`, naming runtime lease storage, 15-minute
  expiry, heartbeat cadence, and `brain-append` exclusion scope.
- M6 and n3: resolved in `Constraints`, `Lease Contract`, and `Open Operator
  Questions`, explicitly assuming a singleton gate daemon unless Operators
  choose multi-instance-under-external-lock as Blocking Question 4.
- m1: resolved in `State Machine`, changing validator enforcement from "can"
  to "must".
- m2: resolved in `State Machine` and `Materialization Algorithm`, specifying
  merge-order discovery from the gate stream rechecked by `main` first-parent
  history.
- n2: resolved in `Evidence Contract`, specifying dry-run/advisory JSON output
  and PR advisory comment format.

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

Revision working-tree checks before final commit:

- `PYTHONPATH=validators python -m creator_engine_validator scan-public-docs-confidentiality docs/design/ce-491-optiona-merge-intent.md`
  returned `PASS public_docs_confidentiality`.
- `PYTHONPATH=validators python -m creator_engine_validator scan-path-manifest .ce/pr-manifests/ce-491-optiona-merge-intent.md`
  returned `PASS path_manifest_fidelity`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref ce-491-optiona-merge-intent`
  returned `PASS path_manifest_fidelity`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-test-coupling --base origin/main --pr-body-file .ce/pr-manifests/ce-491-optiona-merge-intent.md`
  returned `PASS test_coupling`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-work-sizing-floor --base origin/main --declared-work-class S`
  returned `PASS work_sizing_floor`.
- `PYTEST_ADDOPTS="-n 2" ./scripts/ce-preflight.sh --base origin/main --head-ref ce-491-optiona-merge-intent`
  exited `1` before validation because the worktree was dirty.
- `PYTEST_ADDOPTS="-n 2" ./scripts/ce-preflight.sh --base origin/main --head-ref ce-491-optiona-merge-intent --allow-dirty`
  exited `1`. The script internally invoked pytest with `-n auto`; its final
  report showed zero new pytest failures (`baseline=63`, `head=63`), PR-diff
  gates passing (`brain ledger current-tail`, `work-sizing floor`,
  `test-coupling`, `path-manifest`), and repo-wide failures in
  `Control-plane portability guard`, `check-examples aggregate gate`, and
  `well-formed examples`.
- The portability failure was the existing `/run` literal in
  `validators/creator_engine_validator/container_launcher.py:86`.
- The well-formed/check-examples failure included `PCO-024` for
  `examples/well-formed/worktree-leases/signed-lease/lease.yaml` because
  `libsodium` was unavailable.
