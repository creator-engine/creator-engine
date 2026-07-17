# PR path manifest — ce-ops#565 · Define deployable-capability closure evidence

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-565-dod-full-reseed` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=8d0dd6771e3bc377e6b68a9fba697f246ce48e6a7e633fd34b955d1db64a2bac

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-565-dod-full-reseed.md
.ce/pr-manifests/ce-565-dod-full-reseed.md
.claude/agents/README.md
.claude/agents/architect_research.md
.claude/agents/canary_qa.md
.claude/agents/implementer.md
.claude/agents/reviewer.md
.claude/agents/verification.md
playbooks/controller/briefs/dispatch.md
validators/tests/unit/test_ce_brain_drift.py
```
