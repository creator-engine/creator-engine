---
slug: ce217-u2-herdr-containment
date: 2026-06-23
kind: added
scope: v3 runner (herdr containment wrapper)
issue: ce-ops#217
---

**Cockpit-on-herdr U2 — the CE-substrate containment-launch spec + a thin
wrapper stub for running the `creator-engine/herdr-ce` AGPL multiplexer fork
under CE's mandatory containment.**

- Adds `runner/herdr_containment.py`: `plan_herdr_containment()` — a PURE
  translation (no I/O) of a runtime-policy record into a
  `HerdrContainmentPlan`, and `HerdrContainmentLaunch` — a thin wrapper stub
  whose live `launch` / `control_socket_path` fail **closed**
  (`HerdrContainmentNotWired`) until U3 wires the live contained launch.
- Pins the §7 keystone for U4 as a fail-closed invariant: the herdr control
  socket is **owned by the CE substrate/controller and never handed to the
  governed seat**. The planner REFUSES
  (`HerdrContainmentInvariantViolation`) any policy whose seat-writable mount
  overlaps the substrate-owned socket directory — so `herdr pane run` cannot
  become a `governed-seat-cannot-push` (§7) bypass.
- Asserts **no new egress**: herdr is local-first (local PTYs + a local Unix
  socket); the plan carries exactly the policy's egress allowlist and adds none.
- Side-effect-free on import (registers no validator check; `--list-checks`
  stays byte-identical). No live agent session, no socket, no subprocess — that
  is U3. Design-of-record `.ce/state/research/DESIGN_COCKPIT_ON_HERDR_20260623.md`
  (§2, §5 unit U2); boundary `docs/architecture/HERDR_GOVERNANCE_BOUNDARY.md`.
