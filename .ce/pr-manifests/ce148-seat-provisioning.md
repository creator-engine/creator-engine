# PR path manifest - ce148-seat-provisioning

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce148-seat-provisioning
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#148 - controller/seat provisioning-by-construction for source clones:
offline bootstrap into a target venv plus a named doctor failure when the target
app or console scripts are absent.

Base:
`0d4ed0e2c6958a2ce80a36fac5e48e2a5bf28388` (`origin/main` at branch creation).

Per-file purpose (closed path-set - 11 paths):
- **`.ce/changelog/ce148-seat-provisioning.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce148-seat-provisioning.md`** *(A)* - this carrier.
- **`README.md`** *(M)* - document the top-level `ce bootstrap` command group.
- **`docs/operations/AGENT_NATIVE_BOOTSTRAP.md`** *(M)* - source-clone bootstrap prose now provisions an installed target venv before doctor/launch.
- **`templates/hermes/agent-native-bootstrap.yaml`** *(M)* - machine-readable construction path now creates a venv, invokes the stdlib bootstrap module, and runs installed `ce`.
- **`validators/creator_engine_validator/bootstrap_runtime.py`** *(A)* - offline bootstrap and target-seat inspection helper.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - add `ce bootstrap` and doctor target-env CLI flags.
- **`validators/creator_engine_validator/doctor_runtime.py`** *(M)* - append the `CE-SEAT-ENV` target controller/seat check to doctor reports.
- **`validators/tests/integration/test_ce_bootstrap_cli.py`** *(A)* - bootstrap idempotence and doctor absent/present target-env coverage.
- **`validators/tests/integration/test_ce_doctor_cli.py`** *(M)* - update agent-native bootstrap template/doc assertions.
- **`validators/tests/unit/test_v1_docs_reconciliation.py`** *(M)* - include `ce bootstrap` in the expected as-built docs inventory.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=74178b11d75694cb8cc97ccfe27e910ca42989cff73a4551bdf4896c1d84734d

```text
.ce/changelog/ce148-seat-provisioning.md
.ce/pr-manifests/ce148-seat-provisioning.md
README.md
docs/operations/AGENT_NATIVE_BOOTSTRAP.md
templates/hermes/agent-native-bootstrap.yaml
validators/creator_engine_validator/bootstrap_runtime.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/doctor_runtime.py
validators/tests/integration/test_ce_bootstrap_cli.py
validators/tests/integration/test_ce_doctor_cli.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
