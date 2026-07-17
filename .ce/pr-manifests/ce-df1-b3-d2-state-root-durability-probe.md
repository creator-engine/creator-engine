# PR path manifest - ce-df1-b3-d2-state-root-durability-probe

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
This is the exact closed path set for DF-1 B3/D2 state-root durability.

- **Declared work class:** feature
- **Authority posture:** filesystem evidence only; no lease, fence, controller
  identity, approval, merge, signing, credential, or promotion authority.

Per-file purpose:
- **`.ce/changelog/ce-df1-b3-d2-state-root-durability-probe.md`** *(A)* - bounded changelog fragment.
- **`.ce/pr-manifests/ce-df1-b3-d2-state-root-durability-probe.md`** *(A)* - this exact path-set carrier.
- **`CHANGELOG.md`** *(M)* - aggregate Unreleased entry.
- **`playbooks/controller/runbooks/controller-standup.md`** *(M)* - Step 0 pre-provisioning, offline migration, residue, and rollback procedure.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - package/version-line inventory registration.
- **`validators/creator_engine_validator/brain_bootstrap.py`** *(M)* - writable probe-before-ledger-sync composition and private sync writer.
- **`validators/creator_engine_validator/continuity_drill_runtime.py`** *(M)* - read-only diagnostic composition and RED refusal posture.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* - writable probe before live seat mutation/spawn.
- **`validators/creator_engine_validator/state_root_probe.py`** *(A)* - descriptor-pinned structural and nonce durability implementation.
- **`validators/creator_engine_validator/takeover_runtime.py`** *(M)* - serialize read-only diagnostic evidence as not-proven.
- **`validators/tests/unit/test_brain_bootstrap.py`** *(M)* - bootstrap ordering/refusal coverage and private fixtures.
- **`validators/tests/unit/test_ce_launch_cli.py`** *(M)* - live ordering and dry-run-purity coverage.
- **`validators/tests/unit/test_ce_takeover_cli.py`** *(M)* - read-only takeover evidence coverage.
- **`validators/tests/unit/test_continuity_drill_cli.py`** *(M)* - unsafe-root RED/no-mutation coverage.
- **`validators/tests/unit/test_state_root_probe.py`** *(A)* - hermetic structural, policy, syscall-fault, residue, repeatability, and confidentiality coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=8c2868b4cedbf73fb9376fcb48c7b34345d0338d49e8291fc09e59ded6adc394

```text
.ce/changelog/ce-df1-b3-d2-state-root-durability-probe.md
.ce/pr-manifests/ce-df1-b3-d2-state-root-durability-probe.md
CHANGELOG.md
playbooks/controller/runbooks/controller-standup.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/brain_bootstrap.py
validators/creator_engine_validator/continuity_drill_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/state_root_probe.py
validators/creator_engine_validator/takeover_runtime.py
validators/tests/unit/test_brain_bootstrap.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_ce_takeover_cli.py
validators/tests/unit/test_continuity_drill_cli.py
validators/tests/unit/test_state_root_probe.py
```
