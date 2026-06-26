# PR path manifest — ce241-contained-controller-parity · ce-ops#241 contained controller parity acceptance

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
This feature adds the C3 checklist and offline acceptance harness that prove a
contained controller matches the host controller capability surface before
cutover.

Declared work class:
- **Declared work class:** feature

Per-file purpose (the closed path-set — 6 paths):
- **`.ce/changelog/ce241-contained-controller-parity.md`** *(A)* — feature changelog entry.
- **`.ce/pr-manifests/ce241-contained-controller-parity.md`** *(A)* — this carrier.
- **`docs/architecture/contained-controller-parity.md`** *(A)* — architecture note for the C3 parity contract.
- **`docs/operations/CONTAINED_CONTROLLER_PARITY_ACCEPTANCE.md`** *(A)* — operator checklist/spec for contained-controller parity.
- **`validators/creator_engine_validator/contained_controller_parity.py`** *(A)* — reusable offline parity validator harness.
- **`validators/tests/unit/test_contained_controller_parity.py`** *(A)* — checklist and harness conformance tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=982704c96a543f1c1e893fb05f2c426eeea0dd4321486dca306b9bcb3d3ce1e6

```text
.ce/changelog/ce241-contained-controller-parity.md
.ce/pr-manifests/ce241-contained-controller-parity.md
docs/architecture/contained-controller-parity.md
docs/operations/CONTAINED_CONTROLLER_PARITY_ACCEPTANCE.md
validators/creator_engine_validator/contained_controller_parity.py
validators/tests/unit/test_contained_controller_parity.py
```
