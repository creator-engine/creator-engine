---
slug: ce-369-denylist-from-ssot
date: 2026-07-02
kind: feature
scope: validators
issue: ce-369
---

**Generate the identity denylist from registry source at runtime.**

- Added a required-registry generator that writes the CE-internal identity denylist only as a gitignored runtime artifact where the private ce-ops registry is available.
- Updated the fleet manifest guard to fail open with an explicit advisory when that runtime artifact is absent, while preserving structural regex protections and using generated runtime data when present.
- Removed the committed generated artifact and package-data shipping for it; committed content no longer carries registry-derived identity summaries.
- Added a scheduled freshness workflow that checks out ce-ops with `secrets.CE_OPS_READ_TOKEN`, generates the runtime artifact, and verifies it against the private registry without auto-push or auto-PR behavior.
- Design: default gitignored-artifact approach (not keyed-HMAC) — the round-1 rework replaced a committed unsalted-sha256 denylist with a runtime-only, plaintext-token artifact that is generated on demand from the private registry and never packaged or committed; the artifact loader rejects any 64-hex-digest-shaped token to guard against reintroducing hashed identifiers.
- Superseded the d1b-39 brain assertion again to re-pin `validators/pyproject.toml` after the rework removed generated artifact package data (squashed on harvest merge: the round-1 v2->v3 intermediate state was corrected by the rework back to byte-identical pyproject.toml content, so the landed ledger carries a single v2(tombstone)->v4(active) supersede instead of two chained hops).
