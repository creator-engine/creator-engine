---
slug: ce322-doc-autogen-schema-reference
date: 2026-06-27
kind: added
scope: internal schema reference doc-autogen
issue: ce-ops#322
work_class: story
---

Adds the Tier-1 generated schema reference for `schemas/*.yaml`.

- Adds `scripts/gen_schema_reference.py` with deterministic `--write` and
  `--check` modes.
- Commits `.ce/reference/schemas.generated.md` as the checked generated artifact.
- Registers `schema_reference_autogen_sync`
  (`VAL-AUTOGEN-STALE-SCHEMA`) so stale or missing schema reference output fails
  closed.
- Adds focused unit coverage for registration, current committed freshness,
  stale/missing docs, write/check roundtrip, source-schema drift, and unreadable
  generator failure.
