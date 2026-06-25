# PR path manifest — NIGHT-ARC · Document CE work-sizing tiers

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref dev1-night-work-sizing-tiers` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=bf3cc6ce4abcf4ceb3f0217d09f98f454c20ab48bbc776475b1e9598b16e5b3a

```text
.ce/changelog/dev1-night-work-sizing-tiers.md
.ce/pr-manifests/dev1-night-work-sizing-tiers.md
docs/contracts/work-sizing-tiers.md
schemas/work-sizing-floor.schema.yaml
validators/creator_engine_validator/work_sizing.py
```
