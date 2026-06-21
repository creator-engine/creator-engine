# PR path manifest - ce167-brain-assertion-ledger

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce167-brain-assertion-ledger

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Controller relay for ce-ops#167 Knowledge-SSOT assertion ledger. Implement the
first slice only: schema-gated, deterministic assertion ledger with
`ce brain assert/check/correct/verify` under `.ce/state`; reuse existing
evidence-spine/PCL/CE-event idioms; do not add datastore, MCP, recall/vector, or
MEMORY migration surfaces. Rebuild the validator wheel and update checksums
because packaged source changes.

The changes:
- Adds a structured brain assertion schema and runtime that writes a local
  hash-chained ledger under `.ce/state/brain/assertions.yaml`.
- Adds deterministic check semantics: active verified assertion or `unknown`,
  never a guess.
- Adds correction semantics by appending a supersession marker plus a corrected
  active assertion.
- Adds a static validator check and focused runtime/CLI/check tests.
- Updates the README and existing inventory/count guards for the new `ce brain`
  command group and registered check.
- Rebuilds the tracked validator wheel and refreshes `SHA256SUMS`.

Per-file purpose (the closed path-set - 22 paths; `(A)` add):
- **`.ce/changelog/ce167-brain-assertion-ledger.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce167-brain-assertion-ledger.md`** *(A)* - this carrier.
- **`README.md`** - documents the new `ce brain` command group in the as-built
  `ce` inventory.
- **`schemas/brain-assertion.schema.yaml`** *(A)* - brain assertion ledger schema.
- **`validators/creator_engine_validator/brain_runtime.py`** *(A)* - deterministic
  local assertion ledger runtime.
- **`validators/creator_engine_validator/ce_cli.py`** - wires `ce brain`.
- **`validators/creator_engine_validator/checks/__init__.py`** - registers the
  new validator check.
- **`validators/creator_engine_validator/checks/ce_brain_assertions.py`** *(A)* -
  schema/hash-chain/supersession validator check.
- **`validators/tests/integration/test_ce_brain_cli.py`** *(A)* - CLI roundtrip
  and tamper coverage.
- **`validators/tests/unit/test_app_jwt_runner.py`** - registered-check inventory
  reconciliation.
- **`validators/tests/unit/test_brain_runtime.py`** *(A)* - runtime behavior and
  fail-closed coverage.
- **`validators/tests/unit/test_ce_brain_assertions.py`** *(A)* - static check
  coverage.
- **`validators/tests/unit/test_change_status.py`** - registered-check inventory
  reconciliation.
- **`validators/tests/unit/test_credential_runner.py`** - registered-check
  inventory reconciliation.
- **`validators/tests/unit/test_evidence_sink.py`** - registered-check inventory
  reconciliation.
- **`validators/tests/unit/test_merge.py`** - registered-check inventory
  reconciliation.
- **`validators/tests/unit/test_open_change.py`** - registered-check inventory
  reconciliation.
- **`validators/tests/unit/test_redact.py`** - registered-check inventory
  reconciliation.
- **`validators/tests/unit/test_v1_docs_reconciliation.py`** - `ce` command
  inventory reconciliation.
- **`validators/tests/unit/test_version_boundary.py`** - registered-check
  inventory reconciliation.
- **`validators/wheelhouse/SHA256SUMS`** - refreshed wheelhouse checksums.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** -
  rebuilt validator wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=22

AUTHORIZED_PATHS_SHA256=f13cc4ca111e1439608697cfdc4d513df1d27cf939e953c71eb4994e617641af

```text
.ce/changelog/ce167-brain-assertion-ledger.md
.ce/pr-manifests/ce167-brain-assertion-ledger.md
README.md
schemas/brain-assertion.schema.yaml
validators/creator_engine_validator/brain_runtime.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/ce_brain_assertions.py
validators/tests/integration/test_ce_brain_cli.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_brain_runtime.py
validators/tests/unit/test_ce_brain_assertions.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
