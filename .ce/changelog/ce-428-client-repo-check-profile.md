---
slug: ce-428-client-repo-check-profile
date: 2026-07-05
kind: feature
scope: validator
issue: creator-engine/ce-ops#428
---

**ce check client-repo profile.**

- Add explicit `ce check --profile client-repo` handling for adopted client repositories.
- Omit only the CE-resident mutation taxonomy, surfaces manifest, and v3 schema hygiene checks under that profile while keeping the default check path unchanged.
- Pin reusable client-shaped fixture coverage, NOTICE output, unknown-profile refusal, and default wrapper equivalence.
- Document why the v3 naming hygiene test uses a monkeypatch for the CE-self check instead of cwd fixture setup.
