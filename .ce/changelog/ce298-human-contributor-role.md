# Changelog: ce298-human-contributor-role

## ce-ops#298 - human-contributor identity role

**Date:** 2026-06-27
**Branch:** ce298-human-contributor-role
**Parents:** ce-ops#137, ce-ops#147, ce-ops#269

### What changed
Extended `schemas/identity-registry.schema.yaml` to support a `human-contributor`
role in the `account` definition. Previously, all accounts required `owning_seat`
and `host`, which only apply to bot/seat accounts. Human contributors running
Claude Code can now be represented without host-bound bot ownership fields.

The change uses JSON Schema `if/then` discrimination: when
`role != "human-contributor"`, `owning_seat` and `host` remain required
(backward-compatible for existing bot accounts). For `human-contributor`, these
fields are optional. Two new optional fields were added: `trust_tier`
(constrained enum) and `onboarding_date`.

### Placeholders
All example values use `EXAMPLE_` or `TODO_VERIFY` prefixes. Real fleet
identities remain internal (ce-ops#269).

### Tests added
Five new unit tests in `validators/tests/unit/test_identity_registry_schema.py`
cover valid human-contributor accounts without `owning_seat`/`host`, existing
bot requirements for those fields, `trust_tier` constraints, and optional
`owning_seat`/`host` values for human-contributor accounts.
