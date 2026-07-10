# PR path manifest - ce-materializer-deploy-unit

This per-PR carrier lists the closed authorized path set for this branch. The
diff must match exactly the files below; this carrier lists itself.

- **Declared work class:** S

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=fba4df04c1b393ee34cee712ddae78d565bac8052eace857de2bda8e421caf9f

```text
.ce/changelog/ce-materializer-deploy-unit.md
.ce/pr-manifests/ce-materializer-deploy-unit.md
deploy/materializer/ce-materializer.env.example
deploy/materializer/ce-materializer.service
deploy/materializer/launch-materializer.sh
deploy/singleton-redeploy/redeploy-singleton.sh
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_singleton_redeploy.py
```
