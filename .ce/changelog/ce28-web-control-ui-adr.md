---
slug: ce28-web-control-ui-adr
date: 2026-06-20
kind: added
scope: web control UI (web L3) — ADR design
issue: ce-ops#28
---

Added ADR-0008, a design-only decision record for CE's web control UI — the
**web L3** the front-end-agnostic core was designed for. It renders the existing
L2 read-model (`fold_snapshot()`, the `cev3 cockpit --json` parity surface) and
actuates existing gates; it computes nothing and writes no governance state
directly.

The ADR adjudicates seven decisions against the real OpenClaw reference (Vite +
Lit + TypeScript, single-port WebSocket-RPC, hand-rolled service worker,
Tailscale Serve identity) and CE's existing assets: mirror the Vite + Lit + TS
stack; **evolve `cockpit-serve`** (reuse its loopback / token-then-cookie /
Host-header security spine, swap the `textual_serve` payload for static SPA +
WebSocket on one port); Tailscale Serve identity with token fallback (no new
public perimeter); the **L3 hard law** (read only via the L2 JSON parity surface,
write only via a closed, form-echoed, server-validated RPC allowlist) and how
CI/review enforce it over the wire; the journey-cockpit (#45) five requirements
as web views in a CEO / Dev face split; and PWA/mobile (#28) with Web Push on
`⏸️ AWAITING-OPERATOR`. The visual direction (frontend-design plugin) reuses the
live-site "Control-Room Violet" token system; low-fi mockups are staged in
`tmp/webui-shots/` for the Operator's visual checkpoint.

It records the honest gap that **no programmatic ratification seam exists yet**
(only escalation open/resolve write seams + a CLI ratify path), so the sliced
plan's Web-B slice includes building that canonical seam — reused by both CLI and
gateway — and never a web-only bypass. The plan slices the build into **Web-A**
(read-only live mirror, incl. gateway evolution) and **Web-B** (discharge the
binding act, governance-reviewed separately).

This fragment records no code, gateway, SPA, trust-root, or release-artifact
change; the build is a separate later ratified dispatch. ADR-0008 is `accepted`
(Operator-ratified 2026-06-20); the Web-A/Web-B build is the separate dispatch.
