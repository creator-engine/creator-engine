---
slug: ce-p5-seatwatch-s1
date: 2026-07-09
kind: added
scope: seat-watch daemon observe-only slice 1
issue: ce-p5-seatwatch-s1
work_class: feature
---

**Add seat-watch daemon slice 1 (observe-only).**

Add seat-watch daemon slice 1 (observe-only) at `deploy/seat-watch/`: polls configured seat panes on a configurable interval, emits structured JSONL events (`ready_signal`, `blocked_signal`, `idle_without_signal`, `pane_error`, `dispatch_delivery_ack`), ships with a systemd unit, launcher script, 20 targeted unit tests, and a design doc. Reuses existing seat-probe argv machinery from `conveyor_discovery`; singleton lease; no dispatch authority in slice 1.
