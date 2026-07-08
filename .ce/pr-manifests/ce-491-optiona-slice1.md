# PR path manifest - ce-491-optiona-slice1

Per-PR carrier for CE-491 Option A merge-time brain append intent materializer, Slice 1. This carrier is self-inclusive and the slug equals the branch name exactly: `ce-491-optiona-slice1`.

- **Declared work class:** feature

## Evidence Summary

Focused tests were run with `PYTEST_ADDOPTS="-n 2"`:

- `test_brain_intent_materializer_key.py`: 4 tests.
- `test_brain_intent_materializer_validation.py`: 11 tests.
- `test_brain_intent_materializer_core.py`: 5 tests.
- `test_brain_intent_materializer_hold.py`: 6 tests.
- `test_brain_intent_materializer_lease.py`: 4 tests.
- `test_brain_intent_materializer_dryrun.py`: 6 tests.
- `test_brain_intent_xor_gate.py`: 5 tests.
- Total focused count: 44 passed.

Contained-seat preflight: `ce validate-pr --profile contained-seat` was attempted first and the `ce` console script was not present on `PATH`; the equivalent `PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --profile contained-seat` was then run. The broad CI-parity suite is ENV-SKIP in this container: the validator reported Python `3.11.2` out of contract for the doctor gate and missing local runtime tools such as `tmux`, rootless `podman`, and `uv`; broad baseline/branch suites printed environment/pre-existing failures unrelated to this slice before the wrapper was interrupted after more than 10 minutes to avoid leaving a stuck process.

ARMING coverage: `ARMING_ENABLED = False` is hard-coded and covered by a dedicated assertion that the commit-construction placeholder raises `RuntimeError("materializer arming is disabled: slice 1 ships dry-run only")`.

Quarantine guarantee: malformed materialization-time intent validation writes out-of-band quarantine artifacts under `.ce/state/brain-intent-quarantine/<materialization-key>.json`, writes HELD state under `.ce/state/brain-intent-materializer/held/`, emits a HELD event, and does not write under `.ce/brain/`.

Deterministic record bytes: same-inputs-same-output assertions cover all four intent kinds: `active_assertion_append`, `ce411_supersede_pair`, `decision_append`, and `lesson_append`. The tests also verify mediated chain linkage and `content_hash` recomputation.

Design gaps / conservative decisions:

- The current runtime ledger schema does not yet allow `mediation`; the dry-run builder uses runtime normalization and hash helpers, then serializes dry-run ledger bytes with `sort_keys=False` to preserve the CE-491 field order. This is dry-run only; schema updates remain deferred before arming, as the design states.
- The event `event_sha256` is computed over the canonical JSON event payload before adding `event_sha256`, avoiding a self-referential digest while keeping deterministic verification.
- Tail-proof parser failures, chain validation failures, missing ledger text, and missing tail hash all map to HELD `brain_ledger_tail_unprovable`.

Open Operator Questions:

- Q4 singleton topology is represented by the module docstring caveat and local lease tests; a future multi-instance deployment still requires an external linearizable `brain-append` lock.
- Arming and credential use remain out of scope. `private_key_env` is configured as an env-var name only and is not dereferenced in this slice.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=5274a1631ab5fb2857af134a733f6f867d85eb047a44287d0b5a96c6a09983f3

```text
.ce/changelog/ce-491-optiona-slice1.md
.ce/pr-manifests/ce-491-optiona-slice1.md
validators/creator_engine_validator/brain_intent_materializer.py
validators/creator_engine_validator/brain_intent_xor_gate.py
validators/tests/unit/test_brain_intent_materializer_core.py
validators/tests/unit/test_brain_intent_materializer_dryrun.py
validators/tests/unit/test_brain_intent_materializer_hold.py
validators/tests/unit/test_brain_intent_materializer_key.py
validators/tests/unit/test_brain_intent_materializer_lease.py
validators/tests/unit/test_brain_intent_materializer_validation.py
validators/tests/unit/test_brain_intent_xor_gate.py
```
