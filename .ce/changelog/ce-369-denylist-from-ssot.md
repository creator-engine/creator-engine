---
slug: ce-369-denylist-from-ssot
date: 2026-07-02
kind: feature
scope: validators
issue: ce-369
---

**Hash identity denylist from registry source.**

- Added a generated, hashed identity denylist artifact and loader so fleet manifest checks no longer keep CE-internal identifiers in plaintext source.
- Added a required-registry generator plus offline autogen sync check; the PR gate verifies artifact structure, hashed-only contents, and guard wiring.
- Added a scheduled freshness workflow that checks the private identity registry with `secrets.CE_OPS_READ_TOKEN` and fails loudly on drift without auto-push or auto-PR behavior.
- Seeded this PR with a like-for-like migration of the prior hand-maintained literal list into hashes only. The workflow begins enforcing freshness once the controller provisions `CE_OPS_READ_TOKEN`; controller regeneration against the live registry remains the immediate follow-up because this worker cannot read the private registry.
