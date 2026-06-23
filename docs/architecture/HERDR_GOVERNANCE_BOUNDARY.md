# herdr-ce governance boundary — the AGPL firewall (the HARD line)

**Status:** LOAD-BEARING boundary doc. ce-ops#217 (Cockpit-on-herdr, Posture A),
U1. **Design-of-record:** `.ce/state/research/DESIGN_COCKPIT_ON_HERDR_20260623.md`
(§1 license gate, §2 integration seam, §4 governed-interaction model).

This document records the **hard process boundary** between the AGPL-licensed
`creator-engine/herdr-ce` multiplexer fork and CE's proprietary Python
governance/validator stack. The boundary is both a **license firewall** and the
right engineering seam; it must be explicit so future work does not accidentally
cross it.

## The two programs

1. **`creator-engine/herdr-ce`** — a public AGPL-3.0-or-later **fork of
   `ogulcancelik/herdr`** (a single Rust terminal multiplexer binary; vendored
   `vendor/libghostty-vt` is MIT). It exposes workspaces / tabs / panes / output
   reads / status waits over a **local JSON Unix socket** (`herdr workspace`,
   `herdr tab`, `herdr pane split`, `herdr pane run`, `herdr pane read`,
   `herdr wait agent-status`). CE's modifications to this fork are AGPL source
   and published (§13).

2. **CE's governance/validator stack** — the proprietary Python
   `creator_engine_validator` package: the evidence spine, the read-model fold,
   the Ring-1 hook + §7 deny surface, the refusal chain, the resource meters, the
   visibility-backend registry. **Not** AGPL.

## The HARD boundary (never cross this)

> CE's Python governance stack runs as a **SEPARATE PROCESS** communicating with
> the herdr-ce fork over herdr's **JSON Unix socket**. It is **NEVER linked,
> compiled, embedded, statically bound, or otherwise combined into the AGPL Rust
> binary**, and the Rust binary never imports or embeds the Python stack.

Because the two are separate programs communicating at arm's length over a
socket (the classic FSF "mere aggregation / separate process = separate work"
line), the **AGPL §13 copyleft blast radius covers ONLY the herdr-ce fork** (its
Rust + CE's patches to its panes/socket). CE's governance differentiator — the
spine, the refusal moat, the read-model, the deny surface — **stays out of the
copyleft reach and remains proprietary.**

This is enforced in code by the seam: `runner/herdr_session.py`
(`HerdrSession`) is a socket *client*. herdr never imports Python; Python never
links Rust. The seam is the only contact surface.

> ⚠️ One-line counsel/Operator confirmation of the "separate process = separate
> work" position is the standing condition (design §1 Fork-AGPL-firewall) before
> relying on this to keep any CE surface proprietary. Standard, low-risk, but
> recorded here as a gate.

## What MUST NOT happen (the crossings that would infect CE)

- ❌ Statically linking / FFI-binding the herdr Rust crate into a CE process, or
  vice versa (compiling CE Rust/Python *into* the herdr binary).
- ❌ Embedding the Python governance stack inside the AGPL binary (e.g. an
  in-process interpreter) or shipping them as a single combined work.
- ❌ Forking herdr, modifying it, and shipping it **closed-source** (binary-only
  or as a network service) without source availability — that violates AGPL §13.
  (If CE ever wants a closed multiplexer: buy the commercial license from
  `hey@herdr.dev` — Posture B. Not needed for the pilot.)

## What MUST happen (the compliant shape)

- ✅ Keep the AGPL `LICENSE`, the dual-license preamble, and the MIT
  `vendor/libghostty-vt/LICENSE` intact in the fork; add a `NOTICE` recording the
  `ogulcancelik/herdr` origin + CE's modifications + the §13 source-availability
  commitment. Do **not** relicense or strip headers.
- ✅ Drive herdr only over its socket from `HerdrSession` (subprocess / socket),
  never via linkage.
- ✅ Publish the complete corresponding source of the modified herdr to any user
  who reaches it over a network (§13) — satisfied by the public
  `creator-engine/herdr-ce` fork.

## The §7 corollary (the socket is a NEW attach surface — wrap it, don't trust it)

herdr's socket can spawn panes and `pane run` arbitrary commands — a new
authority path that bypasses the Ring-1 hook if a governed seat could reach it.
The boundary therefore also requires:

- The herdr control socket is **owned by the CE substrate/controller process,
  NOT exposed to the governed seat.** The seat runs *inside* a herdr pane as a
  confined child; it never gets a handle to the control socket (same posture as
  today's tmux: the seat does not control its own tmux server). — implemented by
  the U2 containment wrapper.
- Every control-path steer / `pane run` from outside is funneled through the CE
  **attribution shim** (`HerdrSession.send`, U4), which appends a
  `runtime_operator_steer` record to the evidence spine **before** the bytes
  reach the PTY, and fails **closed** if the append fails. `HerdrSession` is the
  **sole control-path writer** to the socket.
- The seat's own tool-calls still pass its Claude-Code/Codex Ring-1 hook, so the
  §7 hard-denies (`git push` → deploy, secret-path read) still fire. herdr
  changes the *terminal substrate*, not the seat's hook chain.

## Unit map (where this boundary is enforced)

| Unit | Enforces |
|---|---|
| **U1** (this) | Fork + AGPL/NOTICE/§13 compliance + this boundary doc + CE-side `HerdrSession` scaffold. |
| **U2** | Containment wrapper: socket owned by substrate, not the seat; assert no new egress. |
| **U3** | `terminal_kind=herdr` `VisibilityBackend` over the socket; retire the `pty.fork` backend (registry seam kept). |
| **U4** | Attribution shim: `HerdrSession.send` as the sole control-path writer; `runtime_operator_steer` spine-append-before-effect, fail-closed. |
