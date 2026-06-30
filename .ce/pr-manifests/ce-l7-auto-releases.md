# PR path manifest — L7/day-arc · Automate release staging and post-sign finalization seam

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l7-auto-releases` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** feature

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=911b2744d0218aa3422f7d5940d3dafd403a3b4115834256e08360f5fb70fe70

```text
.ce/changelog/ce-l7-auto-releases.md
.ce/pr-manifests/ce-l7-auto-releases.md
.github/workflows/release.yml
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/release_orchestrator.py
validators/creator_engine_validator/release_publish.py
validators/tests/unit/test_release_phase_a.py
validators/tests/unit/test_release_publish.py
validators/tests/unit/test_release_workflow.py
```
