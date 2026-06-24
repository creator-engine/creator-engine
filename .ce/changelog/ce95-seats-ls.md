---
slug: ce95-seats-ls
date: 2026-06-24
kind: added
scope: validator engine (forge.seats_status) / v3 CLI
issue: ce-ops#95
---

Added `ce seats ls` fleet-liveness on the v3 user-facing CLI surface.

The new `forge.seats_status` reader discovers governed seats from CE lifecycle
records and sentinel event files, classifies them as up, idle, working, down, or
unknown, and renders table or JSON output without scraping terminal panes.
