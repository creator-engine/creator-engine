# PR path manifest - ce178-brain-bootstrap

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce178-brain-bootstrap
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#178 Knowledge-SSOT born-knowing bootstrap on top of the ce-ops#167
brain assertion ledger and the ce-ops#163 seat-class spine. This adds the
deterministic bootstrap mechanism only: no datastore, MCP, recall/vector
surface, or MEMORY migration.

The changes:
- Adds a pure, read-only `brain_bootstrap` projection that validates the
  assertion ledger, fails closed on invalid/missing state, and returns a
  deterministic JSON payload for controller bootstrap injection.
- Wires `ce brain bootstrap` so the injection payload can be reproduced
  directly.
- Resolves seat class through the existing #163 `seat_class` spine, so absent
  or unknown values fail closed to `foreman`.
- Adds offline unit and CLI coverage for deterministic load, tamper refusal,
  scope filtering, corrected-assertion reflection, and seat-class defaulting.
- Rebuilds the tracked validator wheel and refreshes `SHA256SUMS`.

Per-file purpose (closed path-set - 9 paths):
- **`.ce/changelog/ce178-brain-bootstrap.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce178-brain-bootstrap.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/_version.py`** *(M)* - regenerated
  build identity before the wheel rebuild.
- **`validators/creator_engine_validator/brain_bootstrap.py`** *(A)* -
  deterministic born-knowing bootstrap projection.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - wires
  `ce brain bootstrap`.
- **`validators/tests/integration/test_ce_brain_cli.py`** *(M)* - CLI
  bootstrap coverage.
- **`validators/tests/unit/test_brain_bootstrap.py`** *(A)* - runtime unit
  coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app wheel digest re-pinned
  after rebuild.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`**
  *(M)* - rebuilt app wheel containing the bootstrap surface.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=3b35447f094a34dd815cc031e39b5d0bc8647713baaeb6fcb81939023d10b364

```text
.ce/changelog/ce178-brain-bootstrap.md
.ce/pr-manifests/ce178-brain-bootstrap.md
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/brain_bootstrap.py
validators/creator_engine_validator/ce_cli.py
validators/tests/integration/test_ce_brain_cli.py
validators/tests/unit/test_brain_bootstrap.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
