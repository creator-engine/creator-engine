# PR path manifest — ce-ops#629 · Require RED-at-base evidence before harvest

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce629-red-at-base-briefs` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=13

AUTHORIZED_PATHS_SHA256=2b93497415d84f6826a821f6f649506b75846b1a868d4c1cf7e60dd896155ad1

```text
.ce/brain/assertions.yaml
.ce/changelog/ce629-red-at-base-briefs.md
.ce/pr-manifests/ce629-red-at-base-briefs.md
.claude/skills/ce-dispatch/SKILL.md
.claude/skills/ce-harvest/SKILL.md
docs/design/controller-bootstrap-ssot.json
playbooks/controller/briefs/dispatch.md
playbooks/controller/briefs/harvest.md
validators/creator_engine_validator/conveyor.py
validators/creator_engine_validator/conveyor_daemon.py
validators/creator_engine_validator/harvest_evidence.py
validators/tests/unit/test_conveyor.py
validators/tests/unit/test_gen_controller_bootstrap.py
```
