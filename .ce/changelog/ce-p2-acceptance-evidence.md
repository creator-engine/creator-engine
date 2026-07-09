---
slug: ce-p2-acceptance-evidence
date: 2026-07-09
kind: changed
scope: P2 acceptance autoclose
---

**P2 Acceptance-Evidence autoclose hardening.**

- Parse the PR body `Acceptance-Evidence:` field for issue validation evidence.
- Enforce warn-mode handling for tracked issues labeled exactly `directive`.
- Fail closed with exit 1 when the required cross-repo token is absent.
- Add focused unit coverage for the parser, directive-label behavior, and token absence path.
