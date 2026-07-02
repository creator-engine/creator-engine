# PR path manifest — ce-ops#337 · Self-push broker stable socket mount and canary

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-337-selfpush-canary` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=2eb531e46c844440dafab5473de007c4e715e296001f141210f3fc7a519d52d8

```text
.ce/changelog/ce-337-selfpush-canary.md
.ce/pr-manifests/ce-337-selfpush-canary.md
deploy/vps-runsc/run-vps-runsc.sh
tools/egress-broker/README.md
tools/egress-broker/ce_self_push_canary.py
validators/tests/unit/test_egress_self_push_canary.py
validators/tests/unit/test_vps_runsc_launcher.py
```
