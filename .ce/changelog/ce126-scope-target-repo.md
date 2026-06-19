---
slug: ce126-scope-target-repo
date: 2026-06-19
kind: fixed
scope: forge app onboarding
issue: ce-ops#126
---

Scoped live GitHub App installation coverage checks to the configured target
repository before minting an installation token, while preserving the actionable
zero-accessible-repositories error when the configured installation cannot cover
that repo.
