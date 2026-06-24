---
slug: ce207-visibility-backend
date: 2026-06-24
kind: added
scope: validator lane-launch visibility (headless backend)
issue: ce-ops#207
---

**Headless/non-tmux visibility backend for lane launch (fleet-retirement M2).**

Registers a `headless` visibility backend alongside `tmux`/`herdr` so a lane can be
hosted without a tmux pane — the substrate for witnessable headless contained
controllers (ce-ops#226/#227). `HeadlessVisibilityBackend` launches via
`subprocess.Popen`, streams combined stdout/stderr to `seat_dir/headless/.../stream.log`,
and records a `surface.json` (kind/visibility/surface_ref/pid/stream_ref/started_at) plus a
Pane Registry record (`kind=headless`, `visibility=operator_inspectable`). `ce lane launch`
gains `--no-tmux` / `--terminal-kind headless`. Satisfies the visibility contract
(operator-inspectable evidence) without tmux.
