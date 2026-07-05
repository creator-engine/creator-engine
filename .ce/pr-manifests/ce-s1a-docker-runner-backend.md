# PR path manifest — ce-s1a-docker-runner-backend · Plain Docker runner backend

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-s1a-docker-runner-backend` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story
- **Governance-contract note:** this carrier includes the controller-authorized
  additive runtime-policy `role` enum change adding `controller`, plus the
  `docker` isolation backend enum addition.
- **Schema path note:** the dispatch named `schemas/runtime-policy.schema.yaml`;
  in this repository `schemas/` is a symlink to
  `validators/creator_engine_validator/schemas/`, so the tracked diff path below
  is the package schema path Git records.

AUTHORIZED_PATHS_COUNT=20

AUTHORIZED_PATHS_SHA256=73f3b2e78024713cd4569a2d7a83ed797f9972cf332241833ed7077ad4eb4a1e

```text
.ce/changelog/ce-s1a-docker-runner-backend.md
.ce/pr-manifests/ce-s1a-docker-runner-backend.md
docs/contracts/runtime-policy.md
validators/creator_engine_validator/checks/ce_runtime_policy.py
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/docker_backend.py
validators/creator_engine_validator/runtime_backend_bridge.py
validators/creator_engine_validator/schemas/runtime-policy.schema.yaml
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_audit_overlay.py
validators/tests/unit/test_ce_runtime_policy.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_docker_backend.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_openshell_backend.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_redact.py
```
