---
slug: ce-545-commit-first-contract
date: 2026-07-16
kind: changed
scope: governed PR authoring and dispatch contract
issue: ce-ops#545
---

**Commit-first candidate validation contract.**

- Governed authors create a named exact-path candidate commit before contained-seat validation.
- Corrections append a new commit and rerun validation; candidate history is never amended, rewritten, or discarded.
- The controller generates and commits the contained-seat carrier before its unprofiled validation and merge-gate handling.
