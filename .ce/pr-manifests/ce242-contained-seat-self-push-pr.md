# PR path manifest — ce-ops#242 · contained-seat self-push via injected credential (transport-deputy)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce242-contained-seat-self-push-pr` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=4c479ece3a1f8c99f21f1512eeb2546d248ddcce514f9b3cc72be4537621450d

```text
.ce/changelog/ce242-contained-seat-self-push-pr.md
.ce/pr-manifests/ce242-contained-seat-self-push-pr.md
docs/architecture/egress-broker.md
tools/egress-broker/README.md
tools/egress-broker/egress_broker/__init__.py
tools/egress-broker/egress_broker/orchestrator.py
validators/tests/unit/test_egress_orchestrator.py
```
