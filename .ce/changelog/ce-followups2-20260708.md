---
slug: ce-followups2-20260708
date: 2026-07-08
kind: fixed
scope: review follow-ups / validator preflight / deploy smoke
---

Batch two follow-up fixes from merged review findings.

- DGX runsc image rendering now defaults surface build args to the host architecture
  and accepts `--arch` when cross-building.
- Singleton redeploy smoke coverage accepts both install and unchanged dry-run paths,
  while redeploy rendering escapes backslashes and cleans temp files on early function
  exits.
- Seat-ready preflight now normalizes registered autogen surface paths consistently
  and has companion coverage for schema-reference autogen repair commits.
- The seat-ready pytest worker cap is pinned directly in unit coverage.
