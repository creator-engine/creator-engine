# State Boundary Protocol

**Requirements**: RV1-021 (State Boundary Check) and RV1-022 (State Version /
Migration Record Shape) — PCO v1 Gate 2.
**Type**: SVC (schema + validator + CLI). Strict TDD.
**Status**: Substrate/validator authored. Runtime state writes, migrations, and
lane launch remain later gates.

---

## 1. Purpose

The Creator Engine v1.0 local governed kernel keeps all instance-local runtime
state under the **ignored `.hermes/` state root**. The State Boundary Contract
(RV1-021) makes that invariant machine-checkable, and the State Version /
Migration record (RV1-022) defines the shape of future `.hermes/` state
migrations. Both records are **declarative and validated only**: the checks are
read-only, never create `.hermes/` files, never modify `.gitignore`, and never
perform a migration.

## 2. State Boundary Contract (RV1-021)

Schema: [`../../schemas/state-boundary-contract.schema.yaml`](../../schemas/state-boundary-contract.schema.yaml).
Canonical example:
[`../../examples/well-formed/state-boundary-contract/minimal.yaml`](../../examples/well-formed/state-boundary-contract/minimal.yaml).

Required fields: `kind`, `schema_version`, `state_root`, `allowed_write_roots`,
`forbidden_write_roots`, `tracked_artifact_policy`, `secret_policy`,
`record_timestamp`. (`state_root_gitignored` is an optional attestation; see §2.3.)

### 2.1 Write-root invariant

- The **only** governed runtime write root is `.hermes/`. `allowed_write_roots`
  must contain nothing else; any other entry — including a tracked governance/
  doc/spec/schema/template/validator/source/package surface — is refused with
  **`RV1-021-WRITE`**.
- `forbidden_write_roots` must enumerate the protected tracked surfaces at
  minimum: `docs/`, `specs/`, `schemas/`, `templates/`, `validators/`. A missing
  protected surface is refused with `RV1-021-WRITE`.
- `tracked_artifact_policy` must be `refuse` (schema-enforced): governed runtime
  writes must refuse any tracked governance artifact target.

### 2.2 Secret safety

`secret_policy` records secret **names / references only** (`mode:
names-and-references-only`). Any secret VALUE — a secret-bearing key name or a
secret-shaped string anywhere in the record — is refused with
**`RV1-021-SECRET`**.

### 2.3 `.hermes/` ignored verification

The check verifies that the governed state root is ignored by Git **from the
worktree context it discovers from the record path** (a read-only
`git check-ignore` query). Two failure modes both raise **`RV1-021-IGNORE`**:

- a record that declares `state_root_gitignored: false` (governed runtime state
  would be tracked), and
- a live `git check-ignore` that reports the `state_root` is not ignored.

If no Git worktree is discoverable, the live check is skipped rather than
inventing a failure.

## 3. State Version / Migration record (RV1-022)

Schema: [`../../schemas/state-version-record.schema.yaml`](../../schemas/state-version-record.schema.yaml).
Canonical example:
[`../../examples/well-formed/state-version-record/current.yaml`](../../examples/well-formed/state-version-record/current.yaml).

Required fields: `kind`, `schema_version`, `state_namespace`, `state_version`,
`migration_id`, `migration_status`, `record_timestamp`.

- `migration_status` is constrained to `not-required | pending | applied |
  blocked`. Any other value is refused with **`RV1-022`** (schema enum).
- v1.0 ships a single supported `.hermes/` governed state layout: **version 1**.
  A `state_version` below the minimum supported version (e.g. `0`, the
  pre-bootstrap layout) is **stale**; a version above the current supported
  version is an **unknown future** version. Both are refused with
  **`RV1-022-STALE`**.
- The record documents version/migration state; it must not perform migrations.

## 4. Validation

```bash
PYTHONPATH=validators python3.14 -m creator_engine_validator.cli \
  scan-state-boundary-contract examples/well-formed/state-boundary-contract
PYTHONPATH=validators python3.14 -m creator_engine_validator.cli \
  scan-state-version-record examples/well-formed/state-version-record
```

| Code | Meaning |
|---|---|
| `RV1-021` | State Boundary schema violation. |
| `RV1-021-WRITE` | Non-`.hermes/`/tracked write root, or missing protected surface. |
| `RV1-021-SECRET` | Secret value in config (only names/references allowed). |
| `RV1-021-IGNORE` | Governed state root not ignored by Git / declared tracked. |
| `RV1-022` | State Version schema violation (incl. invalid `migration_status`). |
| `RV1-022-STALE` | Stale or future/unknown `state_version`. |

## 5. Scope boundary

Substrate/validator work only. The Controller seat / harness classification is
defined in
[`CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md`](CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md).
This protocol does not implement `ce`, lane launch, worker runtime, the
Side-Effect Ledger runtime, packaging, or fan-in.
