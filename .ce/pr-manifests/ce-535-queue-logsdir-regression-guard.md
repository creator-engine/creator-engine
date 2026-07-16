# PR path manifest — ce-ops#535 · Add queue-daemon log directory regression guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-535-queue-logsdir-regression-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=b80dbc01c5e23c1332390967544e9994ac852aba20eca50bb59fc05a040d0bc3

```text
.ce/changelog/ce-535-queue-logsdir-regression-guard.md
.ce/pr-manifests/ce-535-queue-logsdir-regression-guard.md
validators/tests/unit/test_gate_daemons_systemd.py
```
