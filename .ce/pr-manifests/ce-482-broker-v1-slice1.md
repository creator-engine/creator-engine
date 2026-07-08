# PR path manifest - ce-482-broker-v1-slice1

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, path-manifest convention).
This is the closed path set for host-ops broker v1 Slice 1.

- **Declared work class:** L

## Summary

Adds the Slice 1 host-ops broker v1 library as a pure-stdlib package under
`tools/host-ops-broker/host_ops_broker/`. The broker accepts raw request dicts,
validates the shared envelope and fixed verb params, checks broker-wide and
per-verb disable flags before rate accounting, resolves targets against a
CE-owned config allow-list, enforces per-caller/per-target rate limits, writes
secret-free JSONL audit, and dispatches only the in-scope `status` and
`restart-daemon` handlers through injectable adapters.

Deferred verbs are intentionally validation-only in this slice:
`prepare-owned-state-root`, `rotate-attempt-log`, `repair-systemd-unit`,
`run-ephemeral-container`, `prune-stopped-owned-containers`, `snapshot-openbao`,
and `restore-drill-openbao`.

## Evidence Summary

Focused tests with requested xdist setting:

```bash
PYTEST_ADDOPTS="-n 2" pytest validators/tests/unit/test_host_ops_broker_envelope.py validators/tests/unit/test_host_ops_broker_verb_schema.py validators/tests/unit/test_host_ops_broker_audit.py validators/tests/unit/test_host_ops_broker_kill_switch.py validators/tests/unit/test_host_ops_broker_rate_limit.py validators/tests/unit/test_host_ops_broker_verb_status.py validators/tests/unit/test_host_ops_broker_verb_restart_daemon.py
```

Result: `153 passed in 1.81s`.

Per-module test counts:
- `validators/tests/unit/test_host_ops_broker_envelope.py`: 15
- `validators/tests/unit/test_host_ops_broker_verb_schema.py`: 109
- `validators/tests/unit/test_host_ops_broker_audit.py`: 9
- `validators/tests/unit/test_host_ops_broker_kill_switch.py`: 4
- `validators/tests/unit/test_host_ops_broker_rate_limit.py`: 4
- `validators/tests/unit/test_host_ops_broker_verb_status.py`: 5
- `validators/tests/unit/test_host_ops_broker_verb_restart_daemon.py`: 7

Schema-validation matrix covers all nine v1 verbs by name:
`status`, `restart-daemon`, `prepare-owned-state-root`, `rotate-attempt-log`,
`repair-systemd-unit`, `run-ephemeral-container`,
`prune-stopped-owned-containers`, `snapshot-openbao`, and
`restore-drill-openbao`.

Hard-invariant evidence:
- Kill-switch ordering pass: broker-wide and per-verb disables return
  `disabled` before rate-limit accounting; the focused kill-switch ordering test
  asserts the rate-limit store remains empty.
- Pre-mutation audit fail-closed pass: `restart-daemon` returns `failed` and the
  systemd adapter is not called when the pre-mutation audit append cannot write.
- Audit secret-free pass: audit rejects credential-by-name keys using the copied
  egress-broker forbidden substring list and rejects gh/github_pat/JWT-shaped
  values before creating a JSONL file. `params_redacted` tests cover only
  schema-safe non-secret fields.
- No command-like params: every verb schema rejects `command`, `argv`, `script`,
  `shell`, `environment`, `mount`, `socket`, `exec`, and `pipe`.
- Pure stdlib package: `host_ops_broker` imports only Python stdlib and package
  modules; tests use pytest as existing validator infrastructure.

Additional local check:

```bash
python -m py_compile $(find tools/host-ops-broker -name '*.py' | sort)
```

Result: passed; generated `__pycache__` files were removed before commit.

Contained-seat preflight / CI-parity attempt:

```bash
PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --profile contained-seat
```

Result: ENV-SKIP / environment-blocked after full run. The validator executed the
full profile but exited 1 because this container is not the validator contract
environment: Python is 3.11.2 while the validator contract requires >=3.14,
rootless worker/runtime prerequisites are unavailable, signed worktree-lease
verification reports libsodium unavailable, and the repository's well-formed
example aggregate is red in both baseline and head. Importantly, the
baseline-diff lane reported zero new pytest failures after the confidentiality
wording fix: `baseline=63, head=63`; path-manifest, test-coupling, public-docs
confidentiality, workflow-permissions, version-drift, brain-drift, and harness
promotion gates passed. The work-sizing floor initially required a larger class;
the carrier now declares `L` and the targeted gate passes:

```bash
PYTHONPATH=validators python -m creator_engine_validator.cli verify-work-sizing-floor --base 010ef3deac86e297d01ac188cab2bf99454dbe92 --declared-work-class L
```

Result: `PASS work_sizing_floor`.

## Design Gaps / Conservative Decisions

- Config format is JSON and fail-closed. The design requires fail-closed config
  but leaves the concrete file format open.
- Kill-switch file format is JSON with `disabled`, `reason_ref`, and
  `disabled_verbs`. Missing flag file means enabled; unreadable or malformed
  flag file fails closed as broker-wide disabled.
- Local transport and caller auth are not implemented; the dispatcher accepts
  raw dicts as Slice 1 specifies.
- Production CE-owned allow-list values are not invented. Tests construct
  minimal `BrokerConfig` stubs with explicit allowed daemons, units, namespaces,
  roots, and profiles.
- Repeated-failure auto-disable enforcement is not implemented in Slice 1; the
  config data shape is present as `repeated_failure_policy` for later slices.
- Deferred verb handlers return/refuse as not implemented after schema and
  conservative target checks; their full host mutations are out of scope.

## Open Operator Questions Affecting Slice 1

- Local transport and caller-auth mechanism remain unresolved, so Slice 1 exposes
  dict dispatch only.
- Durable audit storage location remains unresolved, so tests use injected temp
  JSONL paths and config requires an explicit `audit_log_path`.
- Ratified CE-owned production allow-lists remain unresolved, so no production
  unit, daemon, state-root, container-label, or backup-profile values are added.
- Repeated-failure thresholds remain unresolved, so auto-disable enforcement is
  deferred while preserving a config field for the future policy.
- Dependency ceiling is treated as pure stdlib for the package per brief.

## Per-file Purpose

- **`.ce/changelog/ce-482-broker-v1-slice1.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-482-broker-v1-slice1.md`** *(A)* - this self-inclusive carrier and evidence summary.
- **`tools/host-ops-broker/host_ops_broker/__init__.py`** *(A)* - package metadata for the Slice 1 library.
- **`tools/host-ops-broker/host_ops_broker/envelope.py`** *(A)* - shared request envelope validation, RFC3339 UTC `Z` timestamp handling, and response envelope construction.
- **`tools/host-ops-broker/host_ops_broker/verb_schema.py`** *(A)* - strict typed schemas for all nine v1 verbs and command-like field rejection.
- **`tools/host-ops-broker/host_ops_broker/audit.py`** *(A)* - append-only secret-free JSONL audit sink with copied egress-broker secret pattern.
- **`tools/host-ops-broker/host_ops_broker/kill_switch.py`** *(A)* - broker-wide and per-verb disable flag reader with fail-closed unreadable/malformed handling.
- **`tools/host-ops-broker/host_ops_broker/rate_limit.py`** *(A)* - per-caller/per-target in-memory rate limiter with design-table defaults.
- **`tools/host-ops-broker/host_ops_broker/config.py`** *(A)* - fail-closed `BrokerConfig` dataclass and JSON loader covering allow-lists, maps, rate overrides, and repeated-failure policy shape.
- **`tools/host-ops-broker/host_ops_broker/broker.py`** *(A)* - main dispatch path enforcing schema, kill switch, allow-list, rate limit, pre-mutation audit, handler dispatch, and final audit ordering.
- **`tools/host-ops-broker/host_ops_broker/verbs/__init__.py`** *(A)* - verb package marker.
- **`tools/host-ops-broker/host_ops_broker/verbs/status.py`** *(A)* - read-only `status` verb with injectable subsystem adapter and degraded-check reporting.
- **`tools/host-ops-broker/host_ops_broker/verbs/restart_daemon.py`** *(A)* - `restart-daemon` verb with injectable systemd adapter, daemon-to-unit resolution input, try-restart convergence, and wait bound consumption.
- **`validators/tests/unit/test_host_ops_broker_envelope.py`** *(A)* - envelope and response result-class unit coverage.
- **`validators/tests/unit/test_host_ops_broker_verb_schema.py`** *(A)* - all-nine-verb schema matrix, invalid, extra, and command-like field coverage.
- **`validators/tests/unit/test_host_ops_broker_audit.py`** *(A)* - append-only audit, secret refusal, timestamp, redaction, and parent-dir coverage.
- **`validators/tests/unit/test_host_ops_broker_kill_switch.py`** *(A)* - broker-wide/per-verb disable, unreadable flag fail-closed, audit, and rate-order coverage.
- **`validators/tests/unit/test_host_ops_broker_rate_limit.py`** *(A)* - accepted/refused/rate-limited behavior, mutation ordering, bucket isolation, clock injection, and defaults coverage.
- **`validators/tests/unit/test_host_ops_broker_verb_status.py`** *(A)* - status include/target/detail/degraded/read-only/audit/rate-limit coverage.
- **`validators/tests/unit/test_host_ops_broker_verb_restart_daemon.py`** *(A)* - restart-daemon boundary, adapter, wait bound, try-restart, audit, rate-limit, and pre-mutation audit fail-closed coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=20

AUTHORIZED_PATHS_SHA256=7e8bcd76b9c337c501a2e0b541fa463c1583e0f6e85570629145503d94320234

```text
.ce/changelog/ce-482-broker-v1-slice1.md
.ce/pr-manifests/ce-482-broker-v1-slice1.md
tools/host-ops-broker/host_ops_broker/__init__.py
tools/host-ops-broker/host_ops_broker/audit.py
tools/host-ops-broker/host_ops_broker/broker.py
tools/host-ops-broker/host_ops_broker/config.py
tools/host-ops-broker/host_ops_broker/envelope.py
tools/host-ops-broker/host_ops_broker/kill_switch.py
tools/host-ops-broker/host_ops_broker/rate_limit.py
tools/host-ops-broker/host_ops_broker/verb_schema.py
tools/host-ops-broker/host_ops_broker/verbs/__init__.py
tools/host-ops-broker/host_ops_broker/verbs/restart_daemon.py
tools/host-ops-broker/host_ops_broker/verbs/status.py
validators/tests/unit/test_host_ops_broker_audit.py
validators/tests/unit/test_host_ops_broker_envelope.py
validators/tests/unit/test_host_ops_broker_kill_switch.py
validators/tests/unit/test_host_ops_broker_rate_limit.py
validators/tests/unit/test_host_ops_broker_verb_restart_daemon.py
validators/tests/unit/test_host_ops_broker_verb_schema.py
validators/tests/unit/test_host_ops_broker_verb_status.py
```
