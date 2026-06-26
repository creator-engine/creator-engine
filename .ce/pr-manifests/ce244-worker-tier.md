# PR path manifest - ce244-worker-tier

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce244-worker-tier --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
ce-ops#244 makes the in-process Worker tier a first-class governed contract:
spawned researcher, implementer, and reviewer workers carry deterministic
inherited-governance and capability-bound metadata, and worker records are
validated before they can satisfy foreman delegation.

Per-file purpose:
- **`.ce/changelog/ce244-worker-tier.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce244-worker-tier.md`** *(A)* - this closed path-set
  carrier.
- **`schemas/worker-tier-contract.schema.yaml`** *(A)* - machine-readable
  governed worker-tier contract schema.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* -
  registers the worker-tier contract check.
- **`validators/creator_engine_validator/checks/worker_tier_contract.py`** *(A)*
  - validates worker spawn records for contract presence, inherited governance,
  prohibited capabilities, bounds, role surface, and result protocol.
- **`validators/creator_engine_validator/worker_spawn.py`** *(M)* - stamps
  governed worker contracts onto researcher, implementer, and reviewer spawn
  records.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* - refuses
  foreman-routed implementation records that do not pass the worker-tier
  contract check.
- **`validators/tests/unit/test_worker_tier_contract.py`** *(A)* - covers
  conforming, missing, over-broad, depth-bound, and role-surface cases.
- **`validators/tests/unit/test_hook_check.py`** *(M)* - covers missing worker
  contract fail-closed behavior in delegated implementation.
- **`validators/tests/integration/test_hook_check_cli.py`** *(M)* - conforms
  foreman-delegation CLI fixture to worker-tier contract (adds
  governed_worker_contract field and role-surface file to worker record).
- **`validators/tests/unit/test_*` count guards** *(M)* - update registered
  check count from 63 to 64 for the new worker-tier check.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=18

AUTHORIZED_PATHS_SHA256=4bfcac8ddbc116b9b906a35ebfc23efa173d42e3417843a58fbbee5b352b79e8

```text
.ce/changelog/ce244-worker-tier.md
.ce/pr-manifests/ce244-worker-tier.md
schemas/worker-tier-contract.schema.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/worker_tier_contract.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/worker_spawn.py
validators/tests/integration/test_hook_check_cli.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
validators/tests/unit/test_worker_tier_contract.py
```
