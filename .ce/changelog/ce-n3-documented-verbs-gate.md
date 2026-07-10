---
slug: ce-n3-documented-verbs-gate
date: 2026-07-10
kind: feature
scope: validator
issue: round-3-unit-a
---

**Add a documented `ce` verb registry gate.**

- Added a validator check that imports the in-process `ce` argparse registry and scans tracked markdown docs for taught `ce <verb>` invocations in code fences and inline code spans.
- Added explicit forward-teaching and baseline-debt seams so current docs debt is visible while new unshipped verb teachings fail.
- Wired the check into the generic registry, a focused CLI scan command, and `ce validate-pr`.
