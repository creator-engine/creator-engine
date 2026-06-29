# PR path manifest — ce-ops#313 · Harden automerge actuator arming guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-harden-actuator-arming-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=1eaf73ff1ad1f827a4c64fefed989c45c568df295b7e297f55f67329f6c5501f

```text
.ce/changelog/ce-harden-actuator-arming-guard.md
.ce/pr-manifests/ce-harden-actuator-arming-guard.md
validators/creator_engine_validator/forge/automerge_actuator.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
```
