# PR path manifest — ce-ops#356 · Surface-B broker run-mode deployment wiring

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-armb-broker-runmode` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=d8b04d3937a47bed72816316b673e6ffa5e3b703b28192fe05ff1e6c5c99e79c

```text
.ce/changelog/ce-armb-broker-runmode.md
.ce/pr-manifests/ce-armb-broker-runmode.md
deploy/systemd/README.md
deploy/systemd/ce-egress-self-review.service
deploy/systemd/install-gate-daemons-systemd.sh
validators/tests/unit/test_gate_daemons_systemd.py
```
