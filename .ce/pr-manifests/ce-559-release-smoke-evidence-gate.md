# PR path manifest — ce-ops#559 · Fail-closed release smoke-evidence gate

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-559-release-smoke-evidence-gate` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=3f4c83a402169ad17d762fd9742b453360378539b0200a9046d88cee70afb557

```text
.ce/changelog/ce-559-release-smoke-evidence-gate.md
.ce/pr-manifests/ce-559-release-smoke-evidence-gate.md
.github/workflows/validate.yml
validators/creator_engine_validator/checks/release_smoke_evidence.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/pr_preflight.py
validators/creator_engine_validator/schemas/release-smoke-evidence.schema.yaml
validators/tests/unit/test_release_smoke_evidence.py
validators/tests/unit/test_release_smoke_evidence_ci_wiring.py
```
