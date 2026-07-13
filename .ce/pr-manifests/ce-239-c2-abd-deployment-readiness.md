# PR path manifest — ce-ops#239 · C2-A/B/D deployment readiness

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-239-c2-abd-deployment-readiness` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=71530f7fe809bd0d7c5e90b6d6f176f40aa3632e437863bff68637c9a453ebf9

```text
.ce/changelog/ce-239-c2-abd-deployment-readiness.md
.ce/pr-manifests/ce-239-c2-abd-deployment-readiness.md
deploy/systemd/README.md
deploy/systemd/ce-integrator-daemon.service
deploy/systemd/install-gate-daemons-systemd.sh
validators/tests/unit/test_gate_daemons_systemd.py
```
