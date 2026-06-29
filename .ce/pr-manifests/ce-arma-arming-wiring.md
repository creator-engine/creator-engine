# PR path manifest - ce-arma-arming-wiring

This per-PR carrier (`.ce/pr-manifests/ce-arma-arming-wiring.md`) lists the
closed authorized path-set for this PR. CI runs `verify-path-manifest --base
<sha> --manifest-dir .ce/pr-manifests --head-ref ce-armA-arming-wiring` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=d0170ee2ae39e0e5840bd21ef2975bacf9d27f84e5172d838750be97cf2a8297

```text
.ce/changelog/ce-arma-arming-wiring.md
.ce/pr-manifests/ce-arma-arming-wiring.md
.github/workflows/automerge-actuate.yml
.github/workflows/automerge-decide.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
```
