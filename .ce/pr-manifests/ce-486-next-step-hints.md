# PR path manifest — ce-ops#486 · next-step hints for journey verbs

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-486-next-step-hints` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=a54b729539a129c8bdf12820d2cec614a58fb79904784e97fe8f2566b47044eb

```text
.ce/changelog/ce-486-next-step-hints.md
.ce/pr-manifests/ce-486-next-step-hints.md
docs/architecture/shaping-ux.md
docs/architecture/stage-vocabulary.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/journey_guidance.py
validators/creator_engine_validator/project_init.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_ce_cli_v3_shim.py
validators/tests/unit/test_project_init.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_report.py
```
