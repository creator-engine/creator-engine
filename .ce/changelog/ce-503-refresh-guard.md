---
slug: ce-503-refresh-guard
date: 2026-07-08
kind: fixed
scope: onboard refresh-workflow recognition guard
issue: ce-ops#503
---

**generation-aware refresh workflow recognition.**

- Accepts prior CE-shipped validate workflow generations during `ce onboard --refresh-workflow`.
- Keeps refresh fail-closed for workflows that only mention the validator without the CE workflow structure.
- Deliberately refuses G1-era workflows with renamed job headings; modified CE workflows are foreign.
