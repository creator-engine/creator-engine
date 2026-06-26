# PR path manifest - ce166-knowledge-ssot-slice1

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce166-knowledge-ssot-slice1 --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
ce-ops#166 adds the first deterministic Knowledge-SSOT assertion slice:
versioned checkable assertion fields, bootstrap projection, drift verification
dispatch, and a real probed `harness_fan_out` capability assertion path.

Per-file purpose:
- **`.ce/changelog/ce166-knowledge-ssot-slice1.md`** *(A)* - changelog
  fragment.
- **`.ce/pr-manifests/ce166-knowledge-ssot-slice1.md`** *(A)* - this closed
  path-set carrier.
- **`schemas/brain-assertion.schema.yaml`** *(M)* - requires canonical
  statement, type, and verification method fields.
- **`validators/creator_engine_validator/brain_runtime.py`** *(M)* - derives and
  validates canonical assertion fields for existing structured claim callers.
- **`validators/creator_engine_validator/brain_bootstrap.py`** *(M)* - projects
  canonical assertion fields into the launch-injected Knowledge-SSOT payload.
- **`validators/creator_engine_validator/brain_probe.py`** *(M)* - resolves probe
  names from explicit verification metadata without overriding static/manual
  methods.
- **`validators/creator_engine_validator/checks/ce_brain_drift.py`** *(M)* -
  routes probe, static, and manual-attested verification methods deterministically.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - exposes explicit
  assertion fields through `ce brain assert` and correction flows.
- **`validators/tests/unit/test_brain_runtime.py`** *(M)* - covers required
  assertion fields and probe-method derivation.
- **`validators/tests/unit/test_ce_brain_drift.py`** *(M)* - covers method
  dispatch plus real `harness_fan_out` pass and planted-stale drift.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=86df15b8ba51d6a0a008fd73629a0c29ff292aacd4d2ef01507af0fe4818b351

```text
.ce/changelog/ce166-knowledge-ssot-slice1.md
.ce/pr-manifests/ce166-knowledge-ssot-slice1.md
schemas/brain-assertion.schema.yaml
validators/creator_engine_validator/brain_bootstrap.py
validators/creator_engine_validator/brain_probe.py
validators/creator_engine_validator/brain_runtime.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/ce_brain_drift.py
validators/tests/unit/test_brain_runtime.py
validators/tests/unit/test_ce_brain_drift.py
```
