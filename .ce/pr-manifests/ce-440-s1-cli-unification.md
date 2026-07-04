# PR path manifest — creator-engine/ce-ops#440 · ce-ops#440 slice 1: one `ce` command (install rename, dispatch journey verb, v3 shim)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-440-s1-cli-unification` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=cb38a3da8df3cbc24aa425ca85e18a4375f533102e6b619c06c44081262d6b49

```text
.ce/changelog/ce-440-s1-cli-unification.md
.ce/pr-manifests/ce-440-s1-cli-unification.md
.ce/reference/cli.generated.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_ce_cli_v3_shim.py
validators/tests/unit/test_dispatch_plan.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_cli_cleanroom.py
```
