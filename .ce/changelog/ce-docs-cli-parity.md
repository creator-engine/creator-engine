---
slug: ce-docs-cli-parity
date: 2026-07-08
kind: changed
scope: public guide tree (docs/guide)
issue: docs-cli-parity
---

**Align guide CLI references and keep Welcome orientation-only.**

- Moves the day-one install and handoff material out of `welcome.md` and into
  `quickstart.md`, leaving Welcome as orientation plus navigation.
- Removes the retired local-state gitignore prerequisite from the governed-seat
  quickstart.
- Records a full `docs/guide` CLI reference sweep against the shipped `ce`
  parser surfaces; no missing verbs were found.
