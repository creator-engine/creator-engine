---
slug: ce-366-mainhead-resolver-adr
date: 2026-07-02
kind: governance
scope: docs adr
issue: ce-366-mainhead-resolver-adr
---

**Ratify the main-HEAD artifact resolver/builder/verifier trust contract.**

- ADR-0003 is Accepted — ratified by the Operator on 2026-07-02: Option A (commit-SHA pinning plus local
  reproducible build) is the accepted trust model for the already-live `ce clean-main-install` and
  `ce update --track main` main-HEAD install surface, retroactively as-is, with no code-level
  ratification gate added to those existing commands.
- Document how `ce update --track main` composes with, but stays separate from, the signed-release chain.
- A general ratification-gate pattern for future trust surfaces is tracked separately as a follow-up in
  the internal issue tracker; it does not gate the surface ratified here.
