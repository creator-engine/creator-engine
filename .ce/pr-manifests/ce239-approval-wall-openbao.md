# PR path manifest - ce-ops#239 - Approval wall OpenBao wiring

This per-PR carrier lists the closed authorized path-set for ce-ops#239. The
daemon approval wall is wired to prefer `SecretIdentityBackend`/OpenBao as the
primary verifier-secret supplier, with the documented env var retained as
bootstrap fallback.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=03c3567a6591a55bb6c4633e7fcc4fc1210689caf34418ea55fd6d63d5e8ac7d

```text
.ce/changelog/ce239-approval-wall-openbao.md
.ce/pr-manifests/ce239-approval-wall-openbao.md
docs/security/ce234-approval-capability-wall.md
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_integrator_belt.py
```
