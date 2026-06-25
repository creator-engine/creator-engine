# PR path manifest — ce234-credential-wall-approval · ce-ops#234 credential-wall approval gate

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
This feature makes raw GitHub approval necessary but insufficient for integrator
daemon enqueue: a valid controller-minted approval capability must also be
present on the PR body.

Declared work class:
- **Declared work class:** feature

Per-file purpose (the closed path-set — 12 paths):
- **`.ce/changelog/ce234-credential-wall-approval.md`** *(A)* — feature changelog entry.
- **`.ce/pr-manifests/ce234-credential-wall-approval.md`** *(A)* — this carrier.
- **`docs/security/ce234-approval-capability-wall.md`** *(A)* — approval-wall design note.
- **`validators/creator_engine_validator/_versions.py`** *(M)* — classify the new forge module as v3.
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* — export capability helpers.
- **`validators/creator_engine_validator/forge/approval_capability.py`** *(A)* — pure HMAC capability marker signer/verifier.
- **`validators/creator_engine_validator/forge/integrator_belt.py`** *(M)* — parse PR body markers and enforce capability verification before enqueue.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — wire queue-daemon approval wall state and add marker mint command.
- **`validators/tests/unit/test_fleet_status.py`** *(M)* — update daemon candidate fixture for the value-free capability fields.
- **`validators/tests/unit/test_integrator_belt.py`** *(M)* — daemon wall behavior and parsing tests.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — approval capability mint CLI coverage.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — v3 taxonomy count ratchet.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=10d106711402259f4d53dfc1057977d0c18aa8103e26c65dba3d3485fa1f8f4d

```text
.ce/changelog/ce234-credential-wall-approval.md
.ce/pr-manifests/ce234-credential-wall-approval.md
docs/security/ce234-approval-capability-wall.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/approval_capability.py
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_fleet_status.py
validators/tests/unit/test_integrator_belt.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_version_boundary.py
```
