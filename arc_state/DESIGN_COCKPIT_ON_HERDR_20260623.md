# DESIGN — Cockpit on herdr (fork eval + build sketch)

**Status:** DESIGN-ONLY / decision-ready eval. No product code, no PR, no self-ratification. Operator ratifies before any fork lands.
**Author:** CE-DEV-2 research worker (Opus 4.8, design-only), 2026-06-23.
**Base pin:** `creator-engine/creator-engine @ origin/main` (DGX).
**Eval ticket:** ce-ops#217. **Supersedes:** the forward Textual L3 path *and* the "extend creator-engine#368" attach path (Operator direction 2026-06-23).
**Companion design-of-record (governance reqs carried over):** `/home/cedev2/ce-ops/designs/ce-cockpit-b-design-20260609.md`.
**Method:** facts read directly on 2026-06-23 are `[OBSERVED]` with source; reasoning is `[INFERRED]`.

---

## 0 — Verdicts up front (TL;DR)

| Gate | Verdict |
|---|---|
| **1. LICENSE** | **CONDITIONAL — proceed only as an AGPL-3.0 fork (source-available CE-fork) OR buy the commercial license.** A *closed/internal-proprietary* customization that is redistributed (or offered as a network service) is **NOT permitted** under the OSS terms. See §1. |
| **2. Containment fit** | **GO.** herdr is a single Rust binary, local-first, daemonless-by-shape, no network egress required — runs cleanly under bwrap/gVisor→OpenShell. Its socket API is a *new attach surface* that must be brought under the §7 boundary by wrapping it, not trusting it. See §2. |
| **3. Reuse map (one-liner)** | The entire **L1/L2 governance stack ports unchanged as an OVERLAY** — `cockpit_readmodel.py` (L2, pure fold), the Fork-2 refusal seam in `hook_check.py`, `cockpit_demo_seed.py`, the spine + schemas. **Only L3 (`v3_cockpit.py` Textual view) is replaced** by a herdr-fork surface that consumes the SAME `fold_snapshot()` JSON. See §3. |
| **4. Governed-interaction model** | A keystroke-to-agent through herdr becomes a governed event by routing every steer through a CE attribution shim that appends a `runtime_operator_steer` record (new) to the evidence spine before the bytes reach the PTY; grader-outside + no-new-authority hold WITH interactivity. See §4. |
| **5. Build units** | **9 ordered units**, this-week-sized. Critical path: **U1 (fork+license) → U2 (containment wrapper) → U4 (attribution shim) → U7 (CE_DEMO parity)**. See §5. |
| **6. Open forks** | 6 forks need Operator ratification (license posture is the blocker). See §6. |

---

## 1 — LICENSE GATE (the hard blocker)

### What it is `[OBSERVED]`

- **herdr is dual-licensed.** `LICENSE` (read via GitHub API, repo `ogulcancelik/herdr@main`, 2026-06-23) opens verbatim:
  > "Herdr is dual-licensed: 1. Open source: GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). … 2. Commercial: commercial licenses are available for organizations that cannot comply with AGPL. Contact hey@herdr.dev for details."
- **`Cargo.toml`** confirms: `license = "AGPL-3.0-or-later"`.
- GitHub repo metadata reports `spdx_id: NOASSERTION` / "Other" — this is only because GitHub's classifier does not recognize the dual-license preamble prepended to the GPL text; **the actual license is AGPL-3.0-or-later** (the file body is the full AGPLv3).
- **Vendored `vendor/libghostty-vt/`** is **MIT** (`Copyright (c) 2024 Mitchell Hashimoto, Ghostty contributors`) — vendored from ghostty commit `0f7cd84b`, libghostty-vt `1.3.2`. MIT is permissive and **compatible with redistribution inside an AGPL work**; its only obligation is to preserve the MIT copyright/permission notice. No blocker from the vendored tree.
- **CONTRIBUTING.md** has **no CLA / no DCO / no copyright-assignment** clause observed (it is a short "clank'd from pi" note). `[OBSERVED]` — meaning contributions back are not gated by a CLA, but **also** means the upstream author retains sole copyright and is the only party who can grant the commercial relicense.
- Repo health `[OBSERVED]`: ~6,873 stars, 421 forks, pushed `2026-06-22` (active). Single-maintainer copyright holder ("can" / hey@herdr.dev).

### What AGPL-3.0 means for a CE fork

AGPLv3 is **strong copyleft with the network clause (§13)**. The obligations that bite CE:

1. **Source-availability of the modified work.** If CE distributes the fork binary **OR** makes the modified herdr available to users **over a network** (the cockpit-attach-to-a-seat affordance, a hosted pilot, a "watch your fleet" web view served from a CE box), CE **must offer the complete corresponding source of its modified herdr** to those users. `[OBSERVED — AGPLv3 §13]`
2. **Copyleft reach.** Code that is a *derivative work of herdr* (the fork's own Rust, our overlay compiled/linked into the herdr binary, our patches to its panes/socket) inherits AGPL. **The Python governance stack is NOT automatically infected** if it stays a *separate program* that communicates at arm's length (separate process, talking over the socket/CLI / a pipe) — the classic "mere aggregation / separate process = separate work" line. `[INFERRED, standard FSF position — confirm with counsel before relying on it]`. This is **architecturally decisive**: it is the reason the CE governance layer must overlay herdr **as a separate process across the socket**, never be statically linked into the fork.
3. **No proprietary/closed redistribution.** A "closed/internal customization + redistribution" (the prompt's middle option) is **incompatible** with AGPL unless CE either (a) ships its modifications as AGPL source too, or (b) holds the commercial license.

### Verdict: **CONDITIONAL — GO under one of two postures, NO-GO for closed-proprietary redistribution.**

- **Posture A (recommended for THIS WEEK): treat the fork as AGPL-3.0 source-available.** CE forks herdr publicly (or makes the modified-herdr source available to any user who reaches it over a network), keeps the **Python governance/validator stack as a separate process** (already the case — it's a different language and repo), and complies with §13 by publishing the herdr-fork source. This costs nothing, lands this week, and matches CE's existing PUBLIC `creator-engine` posture for code. The **governance differentiator stays out of the AGPL blast radius** because it is a separate program speaking over the socket — *do not statically link or compile CE Python/Rust governance into the herdr binary.*
- **Posture B (if CE ever wants the multiplexer closed): buy the commercial license** from hey@herdr.dev. Required only if CE wants to redistribute a *proprietary, source-withheld* multiplexer. Not needed for the pilot or the fork build; flag as a future option, not a this-week dependency.
- **NO-GO:** forking herdr, modifying it, and shipping it closed-source (binary-only or as a network service) **without** the commercial license. That violates AGPL §13.

**Conditions to satisfy before U1 lands (license-compliance unit):**
1. Operator picks Posture A or B (Fork-L, §6). Default recommendation = **A**.
2. Keep the AGPL `LICENSE`, the dual-license preamble, and the MIT `vendor/libghostty-vt/LICENSE` intact in the fork; add a `NOTICE` recording the herdr origin + commit.
3. **Architectural firewall:** the CE governance overlay is a *separate process over the socket*, never linked into the herdr binary (this is also the right engineering boundary — §3/§4).
4. Get a one-line counsel/Operator confirmation on the "separate process = separate work" line before relying on it to keep the Python stack non-AGPL (low risk, standard, but it gates how much we can keep proprietary).

---

## 2 — Architecture + containment fit `[OBSERVED repo structure; INFERRED fit]`

### herdr shape (read 2026-06-23)
- **Single Rust binary**, no external runtime deps (Cargo.toml `include` ships `src/**`, sound assets, README, LICENSE). Stack: ratatui + crossterm + portable-pty + tokio + vendored libghostty-vt (the Ghostty VT parser, MIT). Repo dirs: `src/`, `vendor/`, `tests/`, `nix/` (flake-built), `workers/`, `website/`.
- **Daemon-by-shape:** sessions/agents survive the terminal closing; detach/reattach (tmux-model), SSH-native, local-first. `[OBSERVED — herdr.dev, README]`
- **CLI + JSON Unix-socket API** `[OBSERVED — herdr.dev]`: `herdr workspace create --cwd … --label …`, `herdr tab create`, `herdr pane split <id> --direction …`, `herdr pane run <id> "<cmd>"`, `herdr pane read <id> --source recent-unwrapped`, `herdr wait agent-status <id> --status done`. "A CLI and JSON socket API expose workspaces, panes, output, and waits." Agent-status detection = process-name + output heuristics → blocked/working/done/idle in a sidebar; built-in hooks for Claude Code, Codex, OpenCode, Copilot CLI, Hermes.

### Containment fit — **GO**
- A single static-ish Rust binary with **no required network egress** (local Unix socket, local PTYs) is an **ideal containment payload**. It runs under bwrap/gVisor→OpenShell (ce-ops#115/#128) the same way any CE seat process does: file-system + socket confined, no new egress. `[INFERRED — high confidence]`
- It is **strictly better than tmux** for the post-tmux direction (#207/#208): one process tree CE owns, a documented socket to drive/observe, no global tmux server, container-friendly (nix flake build → reproducible image layer).
- **Build:** the nix flake (`flake.nix`) + Cargo gives a reproducible build for the container image; aarch64 (GB10/DGX) builds need verifying (Rust + Zig-built libghostty-vt cross-compile) — flag as a build-unit check, not a blocker.

### The §7-boundary risk — **the socket is a NEW attach surface; wrap it, don't trust it**
This is the one real governance hazard. herdr's socket lets *anything with socket access* (a) spawn panes and (b) **run arbitrary commands** (`herdr pane run`). That is a **new authority path that bypasses the Ring-1 hook** if a governed seat can reach the socket directly. The §7 boundary (`governed-seat-cannot-push`, `hook_check.py:288`) lives in the Claude-Code/Codex hook chain — herdr's `pane run` does not pass through it.

**Mitigation (load-bearing design rule):**
- The herdr socket is **owned by the CE substrate/controller process, NOT exposed to the governed seat.** The seat runs *inside* a herdr pane as a confined child; it does not get a handle to the herdr control socket. (Same posture as today: the seat doesn't control its own tmux server.)
- **Steering/`pane run` from outside** (the Operator driving the agent) is funneled through the CE attribution shim (§4), which is the only writer to the socket on the control path — so every command is attributed and spine-logged before it executes.
- The existing §7 deny (`git push`→deploy, secret-path read) still fires because the **seat's own tool-calls still go through its Claude-Code/Codex Ring-1 hook** — herdr changes the *terminal substrate*, not the seat's hook chain. The boundary is preserved as long as we don't hand the seat the socket.

### Integration seam: Rust multiplexer ↔ Python governance
- **Seam = the herdr JSON Unix socket + CLI, driven from CE Python via subprocess/socket** — exactly the "drive/observe transport-agnostic; subprocess + hooks first-class" decision (ce-substrate-acp-decision). The Python `runner.*` layer issues `herdr` socket calls to create panes / read output / wait, and reads herdr's status events; herdr never imports Python and Python never links Rust → **also the AGPL firewall** (§1).
- **What this replaces:** today CE-DEV-2 controllers drive tmux panes via `tmux send-keys`/`capture-pane` and #368's `seat_pty_session.py` (`pty.fork`, master-fd byte tap, reserved control-socket `surface_ref`). **herdr replaces both the tmux pane-drive AND the hand-rolled PTY backend** — its socket is the productized version of #368's "reserved control-socket for the future attach RPC." #368's `HeadlessVisibilityBackend` / `terminal_kind` / `visibility_class` schema seam is **kept** as the registry contract; a new `terminal_kind=herdr` backend implements it against the socket (see §3 reuse map).

---

## 3 — Reuse map (the distillation) — what ports as OVERLAY vs is replaced

The Cockpit-B design's **principle 6** ("a future GUI replaces L3 only, consuming the same L2") was built for exactly this moment. The three-layer law makes the fork a clean L3 swap.

| Asset | File | Disposition |
|---|---|---|
| **L1 — evidence spine + schemas** | `runtime_evidence_spine.py`, `schemas/runtime-evidence.schema.yaml`, `schemas/pane-registry.schema.yaml`, `schemas/reviewer-authority-envelope.schema.yaml`, `schemas/scope.schema.yaml` | **REUSED AS-IS.** Source of truth, untouched. |
| **L2 — pure read-model fold** | `validators/creator_engine_validator/runner/cockpit_readmodel.py` (`fold_snapshot()` L1491, `snapshot_from_roots()` L1970) | **REUSED AS-IS.** A pure, JSON-serializable fold; imports neither textual nor a terminal. The herdr-fork L3 consumes the **same snapshot dict** via `ce cockpit --json` (the seam already exists, design §3.0.6 / readmodel:30). |
| **Fork-2 refusal-spine seam** | `hook_check.py` `_record_refusal` (L819-857) + `_refusal_record_body` (L800-816) → readmodel `_refusal_entry` (L813), `REFUSAL_CHAIN_FILENAME` | **REUSED AS-IS.** Refusals already hash-chain to `refusal-chain.yaml`; the fold projects the REFUSED feed. **The moat surfaces in the new L3 unchanged** — it is read off the snapshot. |
| **Envelope access-matrix + can-i** | readmodel `_seat_governance` (L737), `can_i` (L761), `RESTRICTED_MECHANICS` (L108) | **REUSED AS-IS.** The governance panel is snapshot data; overlay renders it beside the live panes. |
| **Resource/health meters** | readmodel `_fold_meters` (L1021), `fold_cost_meter` (L1163); `spend_gate.py`, `usage_tap.py`, `v3_session` | **REUSED AS-IS.** MEASURED/ESTIMATED honesty tiers travel in the snapshot. |
| **CEO-mode journey projection** | readmodel `_fold_journey` (L426) + jargon scrub | **REUSED AS-IS.** Plain-language CEO surface is snapshot data. |
| **CE_DEMO seed** | `validators/creator_engine_validator/runner/cockpit_demo_seed.py` (`seed()` returns `fold_snapshot` kwargs); `DEMO_ENV="CE_DEMO"`, `DEMO_WATERMARK` | **REUSED AS-IS** for parity. The seed → fold → snapshot path is unchanged; the new L3 renders the same seeded story (the blocked `git push` refusal on camera) with the persistent DEMO watermark. |
| **#368 visibility-backend registry** | `seat_pty_session.py`, `HeadlessVisibilityBackend`, `terminal_kind`/`visibility_class`/`surface_ref` schema (C1/C3) | **REGISTRY CONTRACT REUSED; PTY impl RETIRED.** New `terminal_kind=herdr` backend implements the same `VisibilityBackend` seam against the herdr socket. The reserved `surface_ref` control-socket concept becomes the herdr socket ref. The `pty.fork` byte-tap is superseded by herdr's panes. |
| **L3 — Textual view** | `validators/creator_engine_validator/v3_cockpit.py` (binds-only) | **RE-SURFACED / REPLACED.** Per Operator: a *fresh redesign distilling the cockpit learnings* onto the herdr fork — NOT the Textual app bolted in. The Textual L3 remains the **01-Jul pitch artifact** (frozen, no further polish investment); the herdr-fork surface is the forward/post-pitch L3. |

**One-liner:** *Everything from L1 up to the snapshot ports unchanged as an overlay; only the L3 viewer is rebuilt on the herdr fork, consuming the identical `fold_snapshot()` JSON over the existing `--json` seam.*

**Governance reqs to carry into the new L3** (from `ce-cockpit-b-design-20260609.md` §3.1, §3.3, §6): the four-section governance/authority panel (envelope matrix · REFUSED live feed · ratified-by attribution · posture); the unified resource/health meter with MEASURED/ESTIMATED badges; the CE_DEMO watermark (Fork 4); the request-not-authorize execution model (Fork 3); Control-Room Violet tokens; the AWAITING-OPERATOR approvals inbox. These are **snapshot-driven**, so the new L3 renders them by binding, exactly as the Textual L3 did.

---

## 4 — Governed-interaction model (the CE moat with interactivity)

herdr gives live interactive attach + steer (`pane run`, keystrokes to the live agent). CE must keep that GOVERNED. The keystone insight: **a steer is an Operator action; an Operator action is an attributed write on the evidence spine; therefore every steer must be appended to the spine *before* its bytes reach the agent's PTY.**

### The attribution shim (the seam)
```
Operator keystroke / steer command
        │
        ▼
 CE attribution shim  ──(1)──►  append runtime_operator_steer{actor, target_lane, bytes_digest, ts}
   (sole control-path             to the evidence spine (via runtime_evidence_spine.append)
    writer to the herdr socket)
        │
        └──(2, only after the spine append succeeds)──►  herdr socket: pane run / write keys
                                                          │
                                                          ▼
                                                   the live agent PTY
```

**Design rules (the moat invariants, preserved WITH interactivity):**
1. **No-new-authority holds.** Steering does **not** widen the seat's envelope. The seat's own tool-calls still pass its Ring-1 hook; the §7 hard-denies (`git push`→deploy, secret-path) still fire. Steering injects *input*, it cannot grant the agent a capability it lacks. An Operator who steers "push it" still hits the hook deny — visible on the REFUSED feed.
2. **Attributed, distinct from agent action.** A new spine record `runtime_operator_steer` (additive to `runtime-evidence.schema.yaml`) carries `actor` (the human/controller ref), `target_lane`, a content digest of the injected bytes (value-free; not the raw secret-bearing keystrokes), and timestamp. It is **visually and structurally distinct** from `runtime_agent_action` — preserving design principle 2 ("an Operator action and an agent action are separately attributed on the spine").
3. **Grader-outside holds.** The grade/refusal still comes from the external spine, not the agent's self-report; steering is just another attributed input event on that same tamper-evident chain. `verify_chain()` covers steer records too.
4. **The shim is the only control-path writer to the socket** (§2 mitigation). The governed seat never holds the socket; the Operator's steer is mediated. This is what stops the socket from becoming a §7 bypass.
5. **Spine-append-before-effect ordering** is load-bearing: if the append fails, the steer does not execute (fail-closed on attribution) — the opposite of `_record_refusal`'s best-effort posture, because here the record gates a *mutation*, not an observation.

**New L2/L3 surface:** the read-model gains a `steer` projection (operator-attributed events interleaved on the seat-detail Stream, color-distinct from agent actions); the governance panel shows "last steered by <actor> at <ts>." This is the *visible* form of governed interactivity — no competitor (FABRO/Devin "steer mid-run") attributes the steer to a ratifier on a tamper-evident spine.

---

## 5 — Build decomposition for THIS WEEK (ordered, bounded)

Repos: **herdr fork** = a new `creator-engine/herdr` (AGPL, public, Posture A). **CE glue** = `creator-engine/creator-engine` `validators/creator_engine_validator/runner/` (the new `terminal_kind=herdr` backend, the attribution shim) + the new L3 surface. Each unit is one batch-strict, manifest-carrying gate.

| # | Unit | Repo / location | Depends on | Boundary class |
|---|---|---|---|---|
| **U1** | **Fork + license compliance.** Fork herdr → `creator-engine/herdr`; keep AGPL `LICENSE` + dual preamble + MIT `vendor/.../LICENSE`; add `NOTICE` (origin + commit `0f7cd84b` for libghostty-vt); record the Posture-A decision. Verify aarch64/DGX build via the nix flake. | new `creator-engine/herdr` | Operator picks Fork-L (§6) | infra/license |
| **U2** | **Containment wrapper.** Run the herdr binary under bwrap/gVisor→OpenShell; socket owned by the CE substrate, **not** exposed to the governed seat; assert no new egress. | OpenShell config + `runner/` launch path | U1 | substrate / governance |
| **U3** | **`terminal_kind=herdr` VisibilityBackend.** Implement the #368 `VisibilityBackend` seam against the herdr socket: create pane → schema-valid pane-registry record (`surface_ref`=herdr socket ref) + `events.jsonl`. Retire the `pty.fork` path behind the registry. | `runner/` (new backend) + schema add `herdr` kind (C3-style) | U2 | validator (schema) + product |
| **U4** | **★ Governed-interaction attribution shim.** The sole control-path socket writer; `runtime_operator_steer` schema record (additive); spine-append-before-effect; fail-closed. The §7-boundary keystone. | `runner/` + `schemas/runtime-evidence.schema.yaml` | U2, U3 | **validator (schema)** + product |
| **U5** | **Governance overlay binding L2.** New L3 surface on the fork renders the snapshot from `ce cockpit --json` (`fold_snapshot()`): ops board + governance/authority panel (envelope matrix · ratified-by · posture) + meters. Binds-only, computes nothing. | `creator-engine/herdr` (overlay) consuming CE `--json` | U3 | product |
| **U6** | **REFUSED live feed overlay.** Surface the existing refusal-chain projection (`_refusal_entry`) + the new steer events on the live seat-detail Stream, color-distinct (gate-red refusals, violet steer). Reuses Fork-2 seam unchanged. | overlay (binds L2) | U4, U5 | product |
| **U7** | **CE_DEMO parity.** `CE_DEMO=1` → `cockpit_demo_seed.seed()` → `fold_snapshot()` → new L3 renders the seeded story (blocked `git push` on camera) + persistent DEMO watermark. Proves the fork hits feature-parity with the Textual pitch artifact. | overlay + existing seed (unchanged) | U5, U6 | product |
| **U8** | **Multi-session / resizable / interactive (A/B/C).** Wire herdr's native multiplexer: (C) multiple concurrent seats as panes/workspaces; (A) resizable live stream; (B) interactive steer via U4's shim. The three drivers the Textual read-only L3 cannot meet. | overlay + U4 shim + herdr fork | U4, U5 | product |
| **U9** | **Migration sketch + #368 retirement note.** Document fleet cut-over (tmux panes → herdr backend), container-rebuild implications (#208), and mark `seat_pty_session.py` superseded (registry seam retained). | docs (`docs/architecture/`) | U3 | docs |

**Critical path:** **U1 → U2 → U3 → U4 → (U5 ∥ U6) → U7**, with **U4 (attribution shim)** the highest-risk/highest-leverage unit (the §7 boundary + the moat) and **U7 (CE_DEMO parity)** the demoable milestone. U8 (A/B/C) is the *reason to fork* but rides on U4's shim and U5's binding. U9 is parallelizable docs.

**This-week realism `[INFERRED, agent-paced]`:** U1–U3 (fork, containment, backend) + U4 (shim) + U7 (CE_DEMO parity) is an achievable bounded week if Posture-A is ratified up front; U8's full A/B/C polish and U9 spill to early next week. Front-load the license decision (Fork-L) — it gates U1 and therefore everything.

---

## 6 — Open forks / risks needing Operator ratification

- **Fork-L (THE BLOCKER): License posture.** Posture **A** (AGPL source-available fork — *recommended*, free, this-week) vs **B** (buy commercial license — only if CE wants a closed multiplexer later). NO-GO = closed proprietary redistribution without B. **Default: A.** Must be decided before U1.
- **Fork-AGPL-firewall: confirm "separate process = separate work."** The Python governance stack stays non-AGPL only if it talks to herdr at arm's length (socket/subprocess, never linked). Standard FSF position, low risk, but get a one-line Operator/counsel confirmation before relying on it to keep any CE surface proprietary. (Architecturally we want this boundary anyway.)
- **Fork-socket-boundary: ratify "the governed seat never holds the herdr socket."** The shim (U4) is the sole control-path writer. Confirms herdr's `pane run` cannot become a §7 bypass. Load-bearing.
- **Fork-steer-record: ratify the additive `runtime_operator_steer` spine record + fail-closed ordering** (validator/schema change; spine-append-before-effect). This is a version-boundary-sensitive change like Fork-2 was.
- **Fork-supersede-#368: confirm fork SUPERSEDES the #368 PTY backend** (registry seam kept, `pty.fork` retired). Eval ticket asks for this confirmation; recommendation = **supersede** (herdr's socket is the productized version of #368's reserved control-socket).
- **Fork-aarch64: DGX build verification.** Rust + Zig-built libghostty-vt cross/native build on GB10 aarch64 (the #134 wheelhouse-is-x86 footgun rhymes here) — verify in U1, not a blocker but a risk.
- **Risk — single-maintainer upstream.** herdr is one copyright holder; active (pushed 2026-06-22) but bus-factor 1. AGPL fork means CE can carry its own fork indefinitely (mitigates), but upstream commercial-license terms could change — Posture A insulates CE from that.

---

## Sources

- herdr repo (read via GitHub API 2026-06-23, `ogulcancelik/herdr@main`): `LICENSE` (AGPL-3.0-or-later dual preamble, verbatim), `Cargo.toml` (`license = "AGPL-3.0-or-later"`), `vendor/libghostty-vt/LICENSE` (MIT, Mitchell Hashimoto / Ghostty), `vendor/libghostty-vt.vendor.json` (ghostty commit `0f7cd84b`, libghostty-vt 1.3.2), `CONTRIBUTING.md` (no CLA/DCO), repo metadata (6873★/421 forks/pushed 2026-06-22).
- herdr.dev (WebFetch 2026-06-23): CLI/socket API (`workspace/tab/pane split/pane run/pane read/wait agent-status`), daemon/detach/reattach model, agent-status detection, harness hooks.
- CE repo (read 2026-06-23, `creator-engine/creator-engine@origin/main`): `validators/creator_engine_validator/runner/cockpit_readmodel.py` (`fold_snapshot` L1491, `snapshot_from_roots` L1970, `_seat_governance` L737, `can_i` L761, `_fold_meters` L1021, `_fold_journey` L426, `_refusal_entry` L813, `--json` seam L30); `hook_check.py` (`_record_refusal` L819-857, `_refusal_record_body` L800-816); `runner/cockpit_demo_seed.py` (`seed()`, `DEMO_WATERMARK`); `v3_cockpit.py` (L3 binds-only); creator-engine#368 (PTY backend, MERGED — `seat_pty_session.py`, `HeadlessVisibilityBackend`, C1/C3 schema).
- ce-ops#217 (eval ticket + scope-expansion comment); `/home/cedev2/ce-ops/designs/ce-cockpit-b-design-20260609.md` (principle 6, §3.1/§3.3, Fork-2/3/4, Control-Room Violet).
- AGPL-3.0 §13 (network clause) — standard text bundled in herdr's `LICENSE`.

*Design-only. No code, no PR, no self-ratification. Fork-L (license posture) is the blocker; the Operator ratifies before U1.*
