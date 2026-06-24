---
slug: ce213-carrier-presence-gate
date: 2026-06-24
kind: fixed
scope: validate workflow carrier enforcement
issue: ce-ops#213
---

Makes the Validate governance-artifacts job fail closed when a pull request is
missing its added per-PR path-manifest carrier or matching `.ce/changelog/`
fragment.

- Adds CI-only required-carrier mode to the path-manifest verifier.
- Keeps default verifier behavior transition-neutral unless the CI flag is
  passed.
- Covers missing carrier and missing changelog cases with focused unit tests.
