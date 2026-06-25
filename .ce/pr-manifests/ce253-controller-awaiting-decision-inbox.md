# PR path manifest — ce-ops#253 · Controller awaiting-decision inbox

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce253-controller-awaiting-decision-inbox` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=68ccd6e68fc71d39ceeaa0b817c873a54002a3ab7c7515593efa8580633c1896

```text
.ce/changelog/ce253-controller-awaiting-decision-inbox.md
.ce/pr-manifests/ce253-controller-awaiting-decision-inbox.md
deploy/systemd/ce-review-pickup-daemon.service
validators/creator_engine_validator/forge/review_pickup.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_review_pickup.py
```
