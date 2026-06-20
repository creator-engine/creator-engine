---
slug: ce45-journey-cockpit-elevation-slice2
date: 2026-06-20
kind: added
scope: cockpit / CEO-mode journey
issue: ce-ops#45
---

**Resolve a decision from the cockpit inbox — the one governed write-seam (Slice 2).**

The decision-inbox can now RESOLVE a decision, but ONLY by actuating the existing
canonical escalation-resolve gate with a form-echo confirmation
([[ce-authority-attaches-to-form]]). The cockpit becomes another *rendering* of
ratification — it never writes governance state itself and never bypasses any gate.

- **The gate as a reusable seam.** `v3_cli.resolve_escalation(root, id, resolution=…)`
  exposes the canonical resolve gate as one callable that BOTH the
  `cev3 escalation resolve` CLI and the cockpit inbox actuate. It loads the record,
  stamps `resolved_at` (+ a value-free provenance note), **re-validates against the
  escalation-record schema** (the modality-independent FORM gate — a garbled click
  fails closed exactly like a typo'd CLI arg), then writes through the same
  `_write_escalation` edge. Fail-closed: a bad id / missing record / schema failure
  yields no partial write.
- **The view writes nothing.** The composition root (`v3_cli._cmd_cockpit`) injects
  an `on_resolve` callback into the cockpit **in live mode only**; the seeded demo
  stays read-only (the affordance is hidden when no seam is wired). On confirm, the
  L3 view calls the injected callback — the write happens inside the canonical gate,
  never in `v3_cockpit.py` (a source guard asserts the view never calls
  `resolve_escalation(`, never imports `v3_cli`, and never touches the escalation
  store).
- **Form-echo before binding.** Selecting an inbox item opens the read-only plain
  detail; `r` opens a `ResolveConfirmScreen` that echoes the plain form of what will
  be recorded and requires a deliberate `y` (a fidelity affordance, not the authority
  gate). After the gate runs, the snapshot re-folds and the resolved item drops out
  of the inbox.

Holds the hard laws: L1/L2/L3 separation (the write goes through the canonical
gate, not the view); `ce cockpit --json` parity (no new datum — `need_id` is the
same `escalation_id` the read-model already carries, so a future GUI actuates the
identical gate with the identical key); plain-language guard (the form-echo carries
zero blocked jargon). Ships as a SEPARATE slice for a distinct governance review.
