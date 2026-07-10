# BUILD MANDATE N2 — M2 visibility gateway + governed onboarding (for Operator sign-off)
**Drafted by CE-DEV-2 controller, 2026-06-23.** Continues N1 (ce-ops#210, fleet conversion COMPLETE). Build autonomously, worker-driven, fleet on clean installs, controller holds the merge gate; stage the M2-unknown-heavy endpoints so they're hit with the Operator reachable.

## RATIFIED DESIGN BASIS (decisions resolved 2026-06-23)
- **Visibility** [[ce-visibility-channel-emission-model]]: contract = **read-model emission from authoritative governance/lifecycle events** (NOT screen-scrape — herdr guardrail). Headless OK **incl. controllers** (= read-model/channel-visible, not dark; C4 refuses *dark* only). Default **inverts**: headless+read-model baseline, per-lane tmux/attach = opt-in. **No auto-degrade knob.** Transition: keep tmux as default renderer until the cockpit renders live state.
- **Install** [[ce-agent-pointed-install-model]]: **agent-driven install is first-class + GOVERNED** (auto verify-trust + confirm-on-consequence + emit-audit). 3 modes (agent-pointed / guided one-liner / one-liner-hands-to-agent); `--install-mode=print` = manual fallback. Escalation sharpened to "no **ungoverned** install."

## WORK TRACKS (prioritized by 80/15/5 value × risk)

### Track A — Visibility / M2 gateway (#207 → #208)
- **A1 · #207 baseline = ATTACHABLE-SESSION SUBSTRATE (READY, foundational):** CE owns a **PTY-backed attachable session per agent (herdr-shaped, replaces tmux)** that supports BOTH (a) read-model emission from authoritative events AND (b) interactive **attach** (read+write) on demand; headless **worker lanes** proven attachable+emitting. C1 = "running in a CE-owned attachable+emitting session?". (DESIGN_207 revised 2026-06-23 — attach-capable, NOT log-capture-only; worker ad81fe43-sibling revision in flight.) **Design must accommodate attach from day 1** even if the polished UI trails.
- **A2 · Channel-emission / contact-on-need — THE 95% SURFACE (READY, high-value):** first-class `kind: webhook` sink + fold run-outcomes/spend into notify events for periodic reports/status; contact-on-need → Discord/Slack/NanoClaw. Built on existing `runner/notify_feed.py` (spine already there). Additive, low risk, biggest near-term win.
- **A3 · Interactive-attach UI + Dev-Mode default (TRAILS A1, but substrate is foundational):** cockpit/TUI shows ALL controllers + lets the user **attach + drive any** (read+write, as if launched standalone) = Dev-Mode default + always-available option; input routing + C4 (controller `operator_inspectable`/attachable) + **redaction gate + secret-leak test on the raw stream** (mandatory, coverage R3). Builds on A1's attachable substrate.
- **A4 · #208 container image — M2 gateway ENDPOINT (GATED):** needs its own design pass FIRST (substrate/runtime = gVisor/OpenShell specifics = M2-arch ESCALATION). Then: consume signed wheel, brain-init first-run, prove ≥1 seat running **containerized + headless (read-model-visible)**.

### Track B — Onboarding (#197 / W5) — READY on revised design (in flight, worker ad81fe43)
3-mode governed install. Ordered PR-units (~200–400 ln, strict-TDD): `ce verify-install` (provenance) · install.sh low-TMPDIR fallback + install-lock UX · profile-PATH writer (default-on managed block, #212-adjacent) · brain/init entry + doctor probes · `ce onboard` orchestrator (3 modes + governed rail) · launcher refuse-before-spawn (#212 fix) · agent-installable spec polish (`llms-install.md`).

### Track C — W6 hygiene (parallel, opportunistic)
#209 merge-queue flake · land #362 (rebase) / #351 (resolve already-merged-vs-divergent drain Q first) / #337 · gap tickets #212/#213/#214 · **ce-ops#215 seat-side read-only ce-ops checkout** (design-artifact access so future briefs point-not-embed; design docs now durable in private ce-ops/designs via fixed sync-ops.sh) · #349 (live-site — GATED on Operator visual-check).

## GRANTS REQUESTED (for autonomous build execution)
- **G-A** — worker fan-out across A/B/C in isolated worktrees; route hardest (#208) to dev-4 (DGX).
- **G-B** — auto-merge any build PR on **independent dev-seat APPROVED + green CI** (R1); controller holds gate.
- **G-C** — governed-install authority per [[ce-agent-pointed-install-model]] (install agent runs under verify + confirm-on-consequence + audit).

## DESIGN STATUS (both done 2026-06-23)
- **#207 attachable-session substrate** = DESIGN_207_VISIBILITY_BACKEND.md (REVISION 2026-06-23): CE owns a PTY-master session per agent (herdr-shaped, replaces tmux) → read-model emission (gov events) + interactive attach (raw PTY over NDJSON RPC) from ONE session; C1="attachable+emitting session?"; **C4 now permits controller `operator_inspectable`/attachable, refuse *dark* only** (supersedes orig §5.G). Baseline PR-units: W1 registry → W2′ PTY-session backend+C1/C3 → W2-sec redaction/leak gate → W4 teardown. Trailing: T1 socket+NDJSON · T2 cockpit attach-UI · T3 controller-C4+`ce launch` · T4 container-attach.
- **#197 3-mode governed install** = DESIGN_197_CE_ONBOARD.md (REVISION 2026-06-23): 7 PR-units; governed rail w/ consequence×novelty×irreversibility table.

## ESCALATION LINES (updated)
- **M2 arch beyond #207/#208** → halt + surface. Specifically the attach-substrate container decisions: **E-att-1** PTY-into-sandbox mechanism (host-PTY vs in-sandbox bridge × gVisor) · **E-att-2** socket reachability across container boundary + its secret surface (bind-mount/forward/vsock) · **E-att-3** write-lock arbitration for multi-attach "drive-any" · **E-att-4** replay/scrollback buffer size + persistence default (secret-aware — default OFF/opt-in). E-att-1/2 = #208 (A4); E-att-3/4 = conservative defaults in A3, flag if non-trivial.
- **Every new live-work surface (log/transcript/stream) ships ONLY with a redaction gate + secret-leak test** — non-negotiable; halt if a unit can't meet it.
- **Ungoverned install** (install agent skipping verify/confirm/audit) → not allowed.
- Version bump / new external publish → escalate.
- **#349 live-site / web-design visual-checkpoint** → Operator's call.
- Arad/chmod735 (postponed 27 Jun) → out of scope.

## SEQUENCING
**Wave 1 (now, parallel, low-risk high-value):** A1 + A2 + B.  **Wave 2 (staged, Operator reachable):** A3 (+redaction gates) then A4 (#208, after its design pass).  **Track C** opportunistic throughout. Checkpoint + resume-write at each unit boundary.
