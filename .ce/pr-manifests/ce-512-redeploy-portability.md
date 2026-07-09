# PR path manifest — ce-512 · singleton redeploy host portability

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-512-redeploy-portability` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

The portability manifest keeps `container_launcher.py` in the runtime plane so
future daemon launcher path changes remain under the same guard as this redeploy
portability work.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=2736338088d3b7757d462f113793b02b2e409d9f2c64062af7c75657860a07bb

```text
.ce/changelog/ce-512-redeploy-portability.md
.ce/pr-manifests/ce-512-redeploy-portability.md
deploy/queue-daemon/RELOCATION.md
deploy/queue-daemon/ce-queue-daemon.service
deploy/singleton-redeploy/redeploy-singleton.sh
deploy/singleton-redeploy/smoke-singleton-redeploy.sh
surfaces/portability-plane-manifest.yaml
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_singleton_redeploy.py
```
