# PR Manifest: ce298-human-contributor-role

## Issue
ce-ops#298

## Summary
Adds `human-contributor` role to the identity-registry schema.
Human contributors (running Claude Code, not host-bound bots) can now
be represented in the identity model without requiring `owning_seat` or `host`.

## Files changed
- `schemas/identity-registry.schema.yaml` - extend account $def with if/then for human-contributor role
- `docs/governance/identity-registry.example.yaml` - add placeholder human-contributor account
- `validators/tests/unit/test_identity_registry_schema.py` - unit tests for new role

## Territory
schemas/identity-registry.schema.yaml
docs/governance/identity-registry.example.yaml
validators/tests/unit/test_identity_registry_schema.py
.ce/pr-manifests/ce298-human-contributor-role.md
.ce/changelog/ce298-human-contributor-role.md

## Gate status
- [ ] preflight green
- [ ] tests pass
- [ ] no real identity values
