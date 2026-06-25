# PR path manifest - ce-ops#239 - Approval wall OpenBao wiring

This per-PR carrier lists the closed authorized path-set for ce-ops#239. The
daemon approval wall is wired to prefer `SecretIdentityBackend`/OpenBao as the
primary verifier-secret supplier, with the documented env var retained as
bootstrap fallback.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=16ed7ec62955410e67b3c3f400899d146dfb75c73046abc8077be9c76bf7f127

```text
.ce/changelog/ce239-approval-wall-openbao.md
.ce/pr-manifests/ce239-approval-wall-openbao.md
docs/security/ce234-approval-capability-wall.md
validators/creator_engine_validator/runner/herdr_session.py
validators/creator_engine_validator/secret_identity.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_herdr_session.py
validators/tests/unit/test_integrator_belt.py
validators/tests/unit/test_secret_identity.py
```
