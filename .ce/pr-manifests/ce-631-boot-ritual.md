# PR path manifest — ce-ops#631 · Boot-time pin re-derivation as mandatory resume ritual

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-631-boot-ritual` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=3f79f7f4aacf5e89962ea6b145ac85b0de253d889fa237a095cb5e1f05430578

```text
.ce/changelog/ce-631-boot-ritual.md
.ce/pr-manifests/ce-631-boot-ritual.md
.claude/skills/ce-checkpoint/SKILL.md
docs/operations/BOOT_TIME_PIN_REDERIVATION_PROTOCOL.md
validators/creator_engine_validator/public_docs_confidentiality.py
```
