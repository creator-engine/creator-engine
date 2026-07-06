---
slug: ce-release-0-3-3
date: 2026-07-06
kind: chore
scope: release
issue: creator-engine/ce-ops#469
---

**bump 0.3.2 -> 0.3.3 + CHANGELOG + release staging.**

Minimal point release to unblock canary C and the Arad live tenant. Bumps version 0.3.2 -> 0.3.3, rolls up six changelog fragments merged since 0.3.2 (ce-468 verify_cli fix, ce-462 auto-tag dispatch chain, ce-467 docs version currency, ce-405 mediated brain-ledger append ADR, ce-463 dependency-unlock arming preconditions, ce-423 tenant denylist matrix), assembles the 0.3.3 CHANGELOG section, publishes the placeholder-signed 0.3.3 install spec to docs/llms-install.md, refreshes the drifted brain-assertion evidence pin for validators/pyproject.toml, and stages placeholder-signed 0.3.3 release artifacts under .ce/release-staging/0.3.3/. Emits bytes-to-sign for the controller at .ce/release-staging/0.3.3/INSTALL_SPEC_TO_SIGN.
