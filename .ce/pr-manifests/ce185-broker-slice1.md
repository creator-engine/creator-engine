# PR Path Manifest - ce185-broker-slice1

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce185-broker-slice1
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#185 Slice-1 broker skeleton and envelope validator only. This adds a
fail-closed local runtime skeleton, deterministic schema/policy/semantic
validation, stub-only dispatch for the two allowed execution modes, and a
value-free hash-chained decision/action ledger. Live OpenBao, SSH, network,
shell, subprocess, provider mutation, and privileged execution remain out of
scope.

Per-file purpose (closed path-set - 14 paths):
- **`.ce/changelog/ce185-broker-slice1.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce185-broker-slice1.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - register the broker envelope check.
- **`validators/creator_engine_validator/checks/devops_privileged_action_broker.py`** *(A)* - YAML discovery and registered validator check for broker envelopes.
- **`validators/creator_engine_validator/devops_privileged_action_broker.py`** *(A)* - Slice-1 fail-closed broker skeleton, validation policy, stub executors, and ledger.
- **`validators/tests/unit/test_app_jwt_runner.py`** *(M)* - update registered check count for ce-ops#185 broker registration.
- **`validators/tests/unit/test_change_status.py`** *(M)* - update registered check count for ce-ops#185 broker registration.
- **`validators/tests/unit/test_credential_runner.py`** *(M)* - update registered check count for ce-ops#185 broker registration.
- **`validators/tests/unit/test_devops_privileged_action_broker.py`** *(A)* - focused unit coverage for validation, dispatch, ledger, and check discovery.
- **`validators/tests/unit/test_evidence_sink.py`** *(M)* - update registered check count for ce-ops#185 broker registration.
- **`validators/tests/unit/test_merge.py`** *(M)* - update registered check count for ce-ops#185 broker registration.
- **`validators/tests/unit/test_open_change.py`** *(M)* - update registered check count for ce-ops#185 broker registration.
- **`validators/tests/unit/test_redact.py`** *(M)* - update registered check count for ce-ops#185 broker registration.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - update registered check count for ce-ops#185 broker registration.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=4b9fdc95380faa6cf86d64d74db6525a229b2435768b7a0bfdc090297555613f

```text
.ce/changelog/ce185-broker-slice1.md
.ce/pr-manifests/ce185-broker-slice1.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/devops_privileged_action_broker.py
validators/creator_engine_validator/devops_privileged_action_broker.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_devops_privileged_action_broker.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
```
