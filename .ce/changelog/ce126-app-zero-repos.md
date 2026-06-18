---
slug: ce126-app-zero-repos
date: 2026-06-18
kind: fixed
scope: forge app onboarding
issue: ce-ops#126
---

Made live forge App installation probes fail closed with an explicit actionable
error when the configured GitHub App installation reports zero accessible
repositories, and documented that the installation must cover the target repo.
