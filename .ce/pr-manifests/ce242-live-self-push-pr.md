# PR path manifest — ce-ops#242 · live contained-seat self-push broker

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce242-live-self-push-pr` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=81359549ac708867ef64809e9a51c87d2ee4260a712ba1fff6ce1d6bb91dceaf

```text
.ce/changelog/ce242-live-self-push-pr.md
.ce/pr-manifests/ce242-live-self-push-pr.md
deploy/dgx-runsc/README.md
deploy/dgx-runsc/herdr-harness-entrypoint.sh
deploy/dgx-runsc/run-codex-runsc.sh
tools/egress-broker/README.md
tools/egress-broker/ce_egress_self_push_broker.py
tools/egress-broker/egress_broker/__init__.py
tools/egress-broker/egress_broker/host_broker.py
tools/egress-broker/egress_broker/orchestrator.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_egress_cli.py
validators/tests/unit/test_egress_host_broker.py
validators/tests/unit/test_egress_orchestrator.py
```
