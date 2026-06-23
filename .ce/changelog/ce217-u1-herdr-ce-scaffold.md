---
slug: ce217-u1-herdr-ce-scaffold
date: 2026-06-23
kind: added
scope: v3 runner (herdr integration seam) / architecture docs
issue: ce-ops#217
---

**U1 foundation for Cockpit-on-herdr (Posture A): the CE-side integration-seam
scaffold + the AGPL governance-boundary doc.**

- **`runner/herdr_session.py` — the CE-side adapter scaffold.** A `HerdrSession`
  client stub that will drive the `creator-engine/herdr-ce` AGPL fork over its
  JSON Unix socket, replacing today's `tmux send-keys` pane-drive and the
  creator-engine#368 `pty.fork` backend. U1 ships the interface only
  (connect / spawn-pane / send / attach / observe); every method fails **closed**
  with `HerdrNotWired` until U3 (live socket drive) and U4 (the attribution shim)
  wire it. Nothing is registered against the visibility-backend registry yet.
- **`docs/architecture/HERDR_GOVERNANCE_BOUNDARY.md` — the AGPL firewall (HARD
  boundary).** Records that CE's Python governance stack runs as a SEPARATE
  PROCESS over herdr's socket and is NEVER linked/compiled into the AGPL Rust
  binary, so the §13 copyleft blast radius covers only the multiplexer fork and
  CE's governance differentiator stays proprietary. Also records the §7 corollary
  (the socket is a new attach surface owned by the substrate, not the seat).
- **creator-engine#368 PTY backend marked SUPERSEDED-IN-PRINCIPLE.** A doc note +
  `TODO(ce-ops#217 U3)` on `seat_pty_session.py` points at the herdr seam; the
  `pty.fork` path is kept live and is retired by U3 (registry seam retained), not
  deleted here.
