---
slug: ce207-w2prime-pty-session
ticket: ce-ops#207
type: feature
scope: governed lane launch / headless PTY visibility backend
---

Adds the **CE-owned PTY attachable-session backend** (W2′) on top of the W1
`VisibilityBackend` registry seam. A visibility-required worker lane can now
launch with **no tmux**: CE owns the seat process under its own PTY (not tmux,
not a log redirect) and the lane reaches LAUNCHED with the same evidence spine a
tmux lane produces — a schema-valid Pane Registry record + an `events.jsonl`
lifecycle — plus a live PTY master the substrate holds.

- Adds `seat_pty_session.py`: `spawn_pty_session` forks the sentinel-wrapped argv
  under a PTY (`pty.fork`) with the seat's cwd/env applied; the parent keeps the
  master fd (the single byte tap). The master tap EXISTS and is CE-owned, but raw
  bytes are NOT streamed to any new surface here — interactive attach and its
  redaction gate are the separate W2-sec / T1 lanes. A control-socket `surface_ref`
  is reserved (recorded, not bound) for the future attach RPC.
- Adds `HeadlessVisibilityBackend` (`terminal_kind=headless`,
  `visibility_class=operator_inspectable`) that spawns through the PTY substrate
  and returns a `{kind: headless, surface_ref, pid}` terminal record. It is always
  available — the correct no-tmux fallback for a host/container.
- **C1**: generalizes the `lane_runtime` visibility gate from "tmux only" to the
  attachable-and-emitting predicate — it now refuses an *unknown / non-satisfying*
  surface, while both `operator_visible` (tmux) and `operator_inspectable`
  (headless) satisfy the contract. The refusal stays load-bearing.
- **C3**: generalizes the Pane Registry schema + validator — adds the `headless`
  terminal kind, the `operator_inspectable` visibility class, `surface_ref`/`pid`
  terminal fields, and a conditional requiring `surface_ref` for headless. The
  validator now requires session/window/pane for tmux, `surface_ref` for headless,
  and refuses an unknown class or a class/kind mismatch. The seat-lifecycle schema
  learns the `headless` terminal kind so `register_spawn` accepts the record.
- CLI: `--no-tmux` flips from "always refused" to the headless backend; the launch
  success message describes a headless lane by kind + surface_ref + pid.
- Classifies the new `seat_pty_session` module as `v1` (`_versions.py`): the v1
  launcher's PTY-owning surface seam, stdlib-only, consumed via
  `visibility_backend` → `lane_runtime` — both edges stay `v1->v1`.

Out of scope (later lanes): raw-byte streaming + the redaction/secret-leak gate
(W2-sec), the control-socket NDJSON attach RPC (T1), the cockpit attach UI (T2),
the controller C4 token + `ce launch` headless path (T3), and container attach
with its E-att-1..4 escalations (T4 / #208). The tmux path is regression-green.
