# PR path manifest — ce-ops#467 · Add current-version drift gate

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-467-version-drift-gate` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=20

AUTHORIZED_PATHS_SHA256=93943d0ab7dacc49db88f6ff1303064bb0fe92abca257b29233bc2c27418c38f

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-467-version-drift-gate.md
.ce/pr-manifests/ce-467-version-drift-gate.md
.github/workflows/validate.yml
deploy/daemons/Dockerfile
deploy/daemons/README.md
deploy/daemons/run-daemon-container.sh
deploy/oci/README.md
deploy/oci/build-image.sh
deploy/runtime-image/Dockerfile
deploy/seat-image/Dockerfile
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/version_drift.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_cli.py
validators/tests/unit/test_daemon_lease.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_version_drift.py
validators/tests/unit/test_work_sizing_floor_ci_wiring.py
```
