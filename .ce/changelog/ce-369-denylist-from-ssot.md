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
- Superseded the d1b-39 brain assertion again to re-pin `validators/pyproject.toml` after the rework removed generated artifact package data.
