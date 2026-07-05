---
slug: ce-415-followup-tinies
date: 2026-07-05
kind: fix
scope: brownfield install answers schema + boundary coverage
issue: CE-415
---

**Clarify brownfield enablement defaults and pin the git-history-only boundary.**

- `brownfield.enabled` no longer advertises default-true behavior in the install
  answers schema; live enablement is derived from read-only project probe
  signals.
- Added focused CLI coverage proving a project with git history, no CI
  workflows, and no detected test commands still enables brownfield adoption.
- Regenerated the schema reference with `python3 scripts/gen_schema_reference.py
  --write`; it was already content-current for this nested description change.
