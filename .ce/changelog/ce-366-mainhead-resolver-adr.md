---
slug: ce-366-mainhead-resolver-adr
date: 2026-07-02
kind: governance
scope: docs adr
issue: ce-366-mainhead-resolver-adr
---

**Propose the main-HEAD artifact resolver/builder/verifier trust contract.**

- Add an ADR proposing retroactive ratification of the unsigned `origin/main` artifact resolution, build,
  verification, and atomic promotion trust surface — disclosing that `ce clean-main-install` and
  `ce update --track main` already ship live today with no code-level ratification gate.
- Document how `ce update --track main` composes with, but stays separate from, the signed-release chain.
- Record commit-SHA pinning plus local reproducible build as the recommended interim trust anchor, and
  give the Operator an explicit choice between retroactive ratification as-is or adding a follow-up
  ratification gate.
