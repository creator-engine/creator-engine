# PR path manifest — ce-gate-daemon-systemd · systemd gate daemons

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs `verify-path-manifest --base <PR base sha> --manifest-dir
.ce/pr-manifests --head-ref ce-gate-daemon-systemd` and requires this PR's
`origin/main..HEAD` diff to equal exactly the authorized path-set below (the
carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=ab6310588a0250db3c766ad5c042029b3ae70dea221a82ccebd18b547f1e7909

```text
.ce/changelog/ce-gate-daemon-systemd.md
.ce/pr-manifests/ce-gate-daemon-systemd.md
deploy/systemd/README.md
deploy/systemd/ce-integrator-daemon.service
deploy/systemd/ce-review-pickup-daemon.service
deploy/systemd/install-gate-daemons-systemd.sh
validators/tests/unit/test_gate_daemons_systemd.py
```
