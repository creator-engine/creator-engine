# PR path manifest — `ce640-coupling-current-head-gate`

Declared work class: `M`.

This carrier adds the advisory-by-default current-head coupling gate. It binds
the decision snapshot to the exact live PR base/head/ref/path projection at
actuation time and refuses drift before the existing actuator can call its
mutation transport. It does not alter workflow files, source filters, rulesets,
or the default disarmed policy state.

The authorized workflow delta passes the already captured immutable subject
base SHA to the advisory decision CLI. It changes no trigger, permission,
checkout, token, or source-filter behavior.

Per-file purpose:

- `.ce/changelog/ce640-coupling-current-head-gate.md` — changelog and coupling discovery.
- `.ce/pr-manifests/ce640-coupling-current-head-gate.md` — self-inclusive carrier.
- `.github/workflows/automerge-decide.yml` — emit the validated base SHA rather than a mutable base ref.
- `validators/creator_engine_validator/forge/automerge_policy.py` — decision-time snapshot emission.
- `validators/creator_engine_validator/forge/automerge_actuator.py` — final pre-mutation live re-derivation.
- `validators/creator_engine_validator/forge/coupling_current_head.py` — versioned obligation compiler and verifier.
- `validators/tests/unit/test_automerge_actuator.py` — mutation-seam drift refusal coverage.
- `validators/tests/unit/test_automerge_policy.py` — exact-base decision/actuator fixture coverage.
- `validators/tests/unit/test_coupling_current_head.py` — seven-kind drift and clean re-derivation coverage.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=47eb5d10a1908fdb704405a542a2b502c015c243f468f329ecfc61ae12cf7a3d

```text
.ce/changelog/ce640-coupling-current-head-gate.md
.ce/pr-manifests/ce640-coupling-current-head-gate.md
.github/workflows/automerge-decide.yml
validators/creator_engine_validator/forge/automerge_actuator.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/creator_engine_validator/forge/coupling_current_head.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
validators/tests/unit/test_coupling_current_head.py
```
