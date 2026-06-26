# PR path manifest - ce163-foreman-canon-enforced

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce163-foreman-canon-enforced --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
ce-ops#163 makes the foreman/swarm operating model deterministic governance
canon. Governed seats must carry a launch-pinned foreman dispatch contract and
must expose researcher, implementer, and reviewer worker surfaces before launch
or worker spawn can proceed.

Per-file purpose:
- **`.ce/changelog/ce163-foreman-canon-enforced.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce163-foreman-canon-enforced.md`** *(A)* - this closed
  path-set carrier.
- **`docs/contracts/harness-seat-contract.md`** *(A)* - documents the
  harness-seat foreman dispatch contract.
- **`docs/contracts/seat-class-policy.md`** *(M)* - documents foreman as the
  governed default seat class and required dispatch model.
- **`examples/**` / `validators/examples/**`** *(A/M)* - add valid and malformed
  examples for seat-class and harness-seat foreman dispatch enforcement.
- **`schemas/*seat*.schema.yaml`** *(M)* - require launch-pinned foreman dispatch
  role surfaces in structured records.
- **`validators/creator_engine_validator/checks/*seat*.py`** *(M)* - validates
  launch-pinned foreman dispatch and role surfaces.
- **`validators/creator_engine_validator/brain_bootstrap.py`** *(M)* - carries
  the deterministic foreman dispatch contract in launch bootstrap context.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* - refuses
  governed seat launch before tmux spawn when the foreman contract is absent or
  malformed.
- **`validators/creator_engine_validator/worker_spawn.py`** *(M)* - refuses
  worker spawn before record/launcher side effects when the foreman contract is
  absent or malformed.
- **`validators/tests/**`** *(M)* - covers schema, check, launch, and worker
  spawn enforcement.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=36

AUTHORIZED_PATHS_SHA256=30beec5e639571083e9825df6c5ad60afe905b45e1e749ba3928201fabeb8ee2

```text
.ce/changelog/ce163-foreman-canon-enforced.md
.ce/pr-manifests/ce163-foreman-canon-enforced.md
docs/contracts/harness-seat-contract.md
docs/contracts/seat-class-policy.md
examples/malformed/harness-seat-contract/incomplete-foreman-dispatch.yaml
examples/malformed/harness-seat-contract/missing-foreman-dispatch.yaml
examples/malformed/harness-seat-contract/unpinned-foreman-dispatch.yaml
examples/malformed/seat-class-policy/bad-depth.yaml
examples/malformed/seat-class-policy/bad-mutation-class.yaml
examples/malformed/seat-class-policy/default-not-foreman.yaml
examples/malformed/seat-class-policy/incomplete-foreman-dispatch.yaml
examples/malformed/seat-class-policy/missing-foreman-dispatch.yaml
examples/malformed/seat-class-policy/secret-value.yaml
examples/malformed/seat-class-policy/worker-seat-class.yaml
examples/well-formed/harness-seat-contract/complete-foreman-dispatch.yaml
examples/well-formed/seat-class-policy/foreman.yaml
examples/well-formed/seat-class-policy/minimal.yaml
examples/well-formed/seat-class-policy/worker.yaml
schemas/harness-seat-contract.schema.yaml
schemas/seat-class-policy.schema.yaml
validators/creator_engine_validator/brain_bootstrap.py
validators/creator_engine_validator/checks/harness_seat_contract.py
validators/creator_engine_validator/checks/seat_class_policy.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/worker_spawn.py
validators/examples/harness-seat-contract/valid-claude-code-seat.ce.yml
validators/examples/harness-seat-contract/valid-codex-seat.ce.yml
validators/examples/harness-seat-contract/valid-hermes-seat.ce.yml
validators/examples/harness-seat-contract/valid-openclaw-seat.ce.yml
validators/tests/integration/test_harness_seat_contract_examples.py
validators/tests/integration/test_seat_class_policy_examples.py
validators/tests/unit/test_brain_bootstrap.py
validators/tests/unit/test_harness_seat_contract.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_seat_class_policy.py
validators/tests/unit/test_worker_spawn.py
```
