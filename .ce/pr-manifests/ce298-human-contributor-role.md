# PR path manifest -- ce-ops#298 human-contributor identity role

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce298-human-contributor-role` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Closes creator-engine/ce-ops#298

- **Declared work class:** story

Adds `human-contributor` role to the identity-registry schema.
Human contributors (running Claude Code, not host-bound bots) can now
be represented in the identity model without requiring `owning_seat` or `host`.
Uses JSON Schema if/then discrimination; backward-compatible for existing bot accounts.
Placeholder values only (real values: ce-ops#269).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=4d6ec371c5d388f69d28b8275d9a5a9221ff54bfc014f34b114c0ae2bc9b29d0

```text
.ce/changelog/ce298-human-contributor-role.md
.ce/pr-manifests/ce298-human-contributor-role.md
docs/governance/identity-registry.example.yaml
schemas/identity-registry.schema.yaml
validators/tests/unit/test_identity_registry_schema.py
```
