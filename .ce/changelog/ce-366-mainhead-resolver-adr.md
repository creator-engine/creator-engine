---
slug: ce-366-mainhead-resolver-adr
date: 2026-07-02
kind: governance
scope: docs adr
issue: ce-366-mainhead-resolver-adr
---

**Propose the main-HEAD artifact resolver/builder/verifier trust contract.**

- Add a ratification-gated ADR for unsigned `origin/main` artifact resolution, build, verification, and atomic promotion.
- Document how `ce update --track main` composes with, but stays separate from, the signed-release chain.
- Record commit-SHA pinning plus local reproducible build as the recommended interim trust anchor.
