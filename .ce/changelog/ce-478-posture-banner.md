---
slug: ce-478-posture-banner
date: 2026-07-06
kind: feature
scope: ce-cli
issue: ce-ops#478
---

**Controller posture banner.**

- Added a deterministic read-only `ce posture` banner with text and JSON output for controller posture evidence.
- Documented the banner fields and deterministic status markers, and covered the CLI/docs/version-boundary coupling with focused unit tests.
- Refreshed the authoritative brain assertion evidence hashes for the touched documentation/test evidence required by the drift gate.
