# PR path manifest - ce176-brain-probe

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce176-brain-probe
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#176 Knowledge-SSOT capability probes (`ce brain probe`) on top of the
ce-ops#167 brain assertion ledger. This adds fresh capability interrogation
only: no datastore, MCP, recall/vector surface, or MEMORY migration.

The changes:
- Adds a pure, injectable `brain_probe` registry with deterministic
  `present` / `absent` / `unknown` verdicts for the seeded probes.
- Wires `ce brain probe <name>` and `ce brain probe --all`.
- Extends the existing `ce_brain_assertions` check so active `probe:<name>`
  capability assertions are re-probed and fail closed on stored/live mismatch.
- Adds focused unit and CLI coverage, including unknown probe and probe-error
  handling.
- Regenerates the baked validator build identity after the rebase so
  `BUILD_GIT_SHA` names a real branch ancestor.
- Rebuilds the tracked validator wheel and refreshes `SHA256SUMS`.

Per-file purpose (closed path-set - 11 paths):
- **`.ce/changelog/ce176-brain-probe.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce176-brain-probe.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/_version.py`** *(M)* - regenerated
  build identity after the rebase onto current main.
- **`validators/creator_engine_validator/brain_probe.py`** *(A)* - capability
  probe registry and assertion-probe helpers.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - wires
  `ce brain probe`.
- **`validators/creator_engine_validator/checks/ce_brain_assertions.py`** *(M)* -
  re-probes active probe-backed assertions.
- **`validators/tests/integration/test_ce_brain_cli.py`** *(M)* - CLI probe
  coverage.
- **`validators/tests/unit/test_brain_probe.py`** *(A)* - probe registry unit
  coverage.
- **`validators/tests/unit/test_ce_brain_assertions.py`** *(M)* - probe-backed
  assertion drift coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app wheel digest re-pinned
  after rebuild.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`**
  *(M)* - rebuilt app wheel containing the probe surface.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=8e8d03df073f1338817efe2378240bcdeeefa865d2110f08b2b184d84d84836b

```text
.ce/changelog/ce176-brain-probe.md
.ce/pr-manifests/ce176-brain-probe.md
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/brain_probe.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/ce_brain_assertions.py
validators/tests/integration/test_ce_brain_cli.py
validators/tests/unit/test_brain_probe.py
validators/tests/unit/test_ce_brain_assertions.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
