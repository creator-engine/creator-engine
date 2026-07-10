# Research Brief — herdr (agent-native terminal multiplexer)

- **Seat:** CE-DEV-2 research worker (cedev2 @ DGX Spark)
- **Date:** 2026-06-23
- **Task:** Research herdr; assess relevance to CE's headless-controller + read-model + multi-renderer (TUI/WebUI/App) direction.
- **Method:** WebFetch of herdr.dev/docs sub-pages + GitHub README + herdr.dev/compare + one independent analysis (maxtokens.ai); WebSearch for design rationale. All specifics below are cited; inference is flagged `[INFERRED]`.

## Sources fetched
- https://herdr.dev/docs/ (docs index; last updated **June 22, 2026**)
- https://herdr.dev/docs/agents/ (agent detection + state model)
- https://herdr.dev/docs/socket-api/ (transport + method/event catalog)
- https://herdr.dev/docs/session-state/ (persistence/restore/handoff)
- https://github.com/ogulcancelik/herdr (README; **v0.7.0**, June 15 2026; ~90% Rust)
- https://herdr.dev/compare/ (positioning matrix)
- https://maxtokens.ai/posts/herdr-agent-multiplexer/ (independent analysis)

---

## 1. What herdr is

**One-liner (from repo):** "agent multiplexer that lives in your terminal." Positioned as "to coding agents what tmux is to terminals." Single **Rust** binary (~90% of codebase), **no Electron, no hosted control plane**, runs anywhere a terminal + SSH reach.

- **Version / date / license (verified):** v0.7.0 (2026-06-15); docs last updated 2026-06-22. **Dual-licensed AGPL-3.0-or-later OR commercial** for orgs that can't comply with AGPL. Windows support experimental.
- **Author:** ogulcancelik (single-maintainer young project; "releases come fast, many preview versions" — independent reviewer).

### Architecture (verified)
- **Server-client model.** A background **server** owns the real pane processes; the thing you look at is a **thin client** that connects over a **Unix domain socket** (named pipe on Windows). "The work lives in the server" (independent analysis). This is the same persistence model as tmux but the differentiator is what the server *knows* about its panes.
- **Object hierarchy:** Workspace → Tab → Pane. A workspace is a per-project container; panes are real terminal processes. An **Agent** is a first-class runtime object layered on a pane — herdr "treats agents as first-class runtime objects" and tracks semantic state per agent.

### Agent awareness — the core abstraction (verified)
herdr's central claim over tmux is **semantic agent state**. Each agent pane is classified into one of: `working`, `blocked`, `done`, `idle` (plus `unknown`). Detection is layered:
1. **Process detection + TOML manifests:** herdr "detects the foreground process in each pane" and evaluates TOML manifests against a **live bottom-buffer screen snapshot** (not the scrolled viewport) to classify idle/working/blocked.
2. **`blocked` heuristic:** marked **only** when the bottom-buffer snapshot matches known visible approval/question/permission UI.
3. **Lifecycle hooks / official integrations:** for agents shipping integrations (Pi, OMP have *full lifecycle authority*; Claude Code, Copilot CLI are *screen-only* = session identity but not full lifecycle), herdr uses authoritative hook reports for state + session identity.
4. **Self-reporting:** agents can push state via socket method `pane.report_agent` (`state` ∈ working/blocked/idle/done + message). `state` drives waits/notifications/rollups; `custom-status` is display-only text. Detects **14+ agents** (Claude Code, Copilot CLI, Cursor, Devin, …).

The `done` vs `idle` split is load-bearing: `done` = finished-but-unseen, `idle` = finished-and-reviewed (operator triage signal).

### Socket API — the headless/automation surface (verified)
- **Transport:** newline-delimited JSON over local socket. Default `~/.config/herdr/herdr.sock`; named sessions at `~/.config/herdr/sessions/<name>/herdr.sock`.
- **RPC shape:** `{"id":"req_1","method":"ns.method","params":{...}}` → `{"id":..,"result":{"type":..,..}}` or `{"error":{"code","message"}}`.
- **Method namespaces:** `workspace.*`, `tab.*`, `pane.*` (split/swap/move/zoom/layout/resize/send_text/send_keys/send_input/**read**/**wait_for_output**/report_agent/…), `agent.*` (list/get/read/explain/send/start/focus), `events.*` (subscribe/wait), `plugin.*`.
- **Reading output:** `pane.read` with `source` ∈ `visible | recent | recent-unwrapped | detection`.
- **Event stream:** `events.subscribe` holds the connection open and pushes typed events: `pane.created|closed|focused|moved|exited|agent_status_changed`, `workspace.created|closed`. This is herdr's push read-model.
- **Agents drive it too:** the README's pitch is an "agent-shaped API" so agents themselves can read/send/wait/split/attach.

### Persistence / replay (verified)
- **Live persistence (detach/reattach):** processes keep running on detach (`ctrl+b q`); reattach with `herdr`. Same as tmux.
- **Snapshot restore (server restart):** restores workspaces/tabs/panes/cwd/layout/focus but **does not resurrect processes** — panes become fresh shells in saved dirs. Stored in `session.json`.
- **Pane history replay:** restores recent terminal contents after restart — **OFF by default** because "pane output can include secrets, tokens, prompts." Opt-in `[experimental] pane_history = true`; data in `session-history.json`.
- **Native agent session resume:** for agent CLIs with native resume (Claude Code, Devin, Copilot), herdr resumes eligible restored agent panes across workspaces without per-pane focus.
- **Live handoff:** experimental `herdr update --handoff` migrates live panes to a new server during upgrade.

### Operator attach model (verified)
- Full herdr TUI (mouse-first: click panes, drag borders, right-click split/switch; `ctrl+b` prefix like tmux; 18 themes). Sidebar shows agent states for triage ("scan state, jump to blocked work").
- **`herdr agent attach`:** attach your current terminal to a *single agent terminal* instead of the full UI — direct 1:1 control with multiplexer-style detach.

---

## 2. tmux vs herdr vs CE

| Dimension | tmux / zellij | herdr | CE (target model) |
|---|---|---|---|
| Unit of work | Pane = opaque text stream | Pane + **Agent** as first-class object w/ semantic state | Seat/lane/run w/ lifecycle + sentinel events + transcript |
| Server knows… | "It's all just text streams" — no diff between Claude Code, `npm test`, `tail -f` | pane *contains an agent* that is working/blocked/done/idle | Full governance state: pco-allocate, refusal-spine, posture, ratification |
| Read-model | none (screen scrape only) | **push event stream over socket** (`agent_status_changed`, pane lifecycle) | canonical JSON read-model, front-end-agnostic core (L1 spine → L2 JSON → L3 view) |
| Automation API | scriptable via `tmux` CLI (text) | structured **NDJSON socket RPC** (read/send/wait/split/report) | CE drives/observes; transport-agnostic (subprocess + CC-hooks first-class) |
| Persistence | live panes survive detach; no restart survival | live detach + restart snapshot + opt-in history replay + agent native-resume | transcript archive + evidence as first-class durable record |
| State capture for evidence | scrollback only | bottom-buffer snapshot + opt-in history (secret-aware OFF default) | sentinel events + seat-lifecycle + transcript archive |
| Governance | none | none — observation only, "doesn't make any process survive anything" | refusal-spine, §7 push-block, ratification gates, containment |
| Runtime | single Rust binary, no daemon control plane | single Rust binary, local server, no hosted plane | Python (through v4.0); containerized (OpenShell/gVisor) |
| License | ISC/permissive | **AGPL-3.0-or-later / commercial dual** | mixed (public creator-engine / private ce-ops) |

**Key takeaways from the table:**
- herdr is **tmux + a semantic agent-state layer + a structured socket read-model**. The genuinely novel part vs tmux is (a) per-pane agent state classification and (b) the typed event stream / agent-shaped RPC. Everything else (server/client, detach persistence) is tmux-equivalent.
- herdr is **observation-only**. It explicitly does NOT govern, ratify, contain, or guarantee survival. That is precisely the layer CE adds and herdr disclaims.

---

## 3. Relevance to CE

CE's direction: headless controller/lanes emit a **canonical read-model** consumed by TUI + WebUI + desktop App + comms (Discord/Slack/NanoClaw); witnessability/evidence (sentinel events, seat-lifecycle, transcript archive) is first-class. Against that:

**Strong alignment (validates CE's design):**
- herdr's **server-owns-processes / thin-client-renders** split is exactly CE's headless-core + multi-renderer thesis ([[ce-cockpit-frontend-agnostic-core]]: L1 spine / L2 pure JSON read-model / L3 view). herdr independently arrived at the same shape — a market signal that the front-end-agnostic core is the right bet.
- The **typed event stream** (`agent_status_changed`, pane lifecycle over NDJSON socket) is a concrete, shipped instance of a push read-model. Its event taxonomy (created/closed/focused/exited/status_changed) is a useful reference for CE's read-model event schema.
- The **`done` vs `idle` distinction** (finished-unseen vs finished-reviewed) is a sharp triage primitive that maps directly onto CE's decision-inbox / journey-cockpit "what needs the operator now" surface ([[ce-journey-cockpit-vision]], [[ce-context-observability-issue-157]]).
- The **`blocked`-on-approval-UI** detection is the same need CE meets with AWAITING-OPERATOR markers — herdr surfaces "this agent is waiting on a human" as a first-class scannable state. CE's equivalent is governance-native (refusal-spine / ratification) rather than screen-scraped, which is **stronger**.

**Conflict / where CE diverges (deliberately):**
- **State source-of-truth.** herdr's default state detection is **screen-scraping** (bottom-buffer snapshot + TOML manifests + output heuristics). This is brittle and exactly the "pretty polling" anti-pattern the independent reviewer warns against. CE must NOT take state from screen heuristics — CE has authoritative governance/lifecycle events (sentinel events, seat-lifecycle, pco ledger). herdr's *self-report path* (`pane.report_agent` + lifecycle hooks) is the right model; its screen-scrape fallback is the anti-pattern.
- **Governance is absent.** herdr is observation/orchestration with zero governance, containment, or evidence-durability guarantees. CE's whole value-add (refusal-spine, §7 push-block, ratification, containment, transcript archive) sits above where herdr stops. herdr is therefore **not a competitor to CE** — it's a competitor to tmux/zellij/Conductor.
- **Secret-leak surface.** herdr ships history-replay OFF by default *because pane output contains secrets/tokens*. CE's transcript archive is a first-class evidence store — CE already treats this as load-bearing, but herdr's explicit secret-awareness is a reminder to keep the evidence/replay path secret-scrubbed and opt-in-audited.
- **License.** AGPL-3.0-or-later. Any *code* reuse (vs. learning) would impose AGPL/commercial obligations — a hard blocker for adoption as a dependency in CE's public substrate. Treat herdr as **reference, not dependency**. [INFERRED: CE would not want AGPL viral terms in creator-engine.]
- **Language.** Rust vs CE's Python-through-v4.0 ([[ce-v4-runtime-language-research]]); no in-process reuse path anyway.

**Classification:** herdr is **orthogonal-to-CE + a strong reference**, *not* a dependency and *not* a competitor. It occupies the tmux-replacement / agent-observation niche; CE consumes that niche's *function* but needs governance on top. CE is explicitly moving **off tmux** ([[ce-post-tmux-direction]] / M2 #207) — herdr is the closest existing thing to "what replaces tmux for agents," so it's the best single reference for the CE TUI + observation layer even though CE won't adopt its code.

---

## 4. Concrete takeaways

### Adopt / learn (patterns)
1. **Server-owns-processes, thin-client-renders.** Confirms CE's headless-core. The TUI/WebUI/App should all be thin clients over the same read-model socket — herdr proves a single Rust server + NDJSON socket serves both human TUI and agent RPC from one surface. Consider one canonical local socket (NDJSON or equivalent) that the TUI, comms emitters, and agent automation all consume.
2. **Typed lifecycle event stream as the read-model wire format.** Borrow herdr's event taxonomy as a starting checklist for CE's read-model events: seat/pane created, focused, exited, **status_changed**, workspace created/closed. Make `subscribe`-style long-lived push first-class (not just polling).
3. **Semantic seat-state with a `done`/`idle` distinction.** Add an explicit "finished-but-unseen vs finished-and-reviewed" axis to CE's seat state so the decision-inbox can highlight unreviewed completions, not just blocked ones.
4. **`blocked`-as-scannable-state for AWAITING-OPERATOR.** CE already has the marker; herdr shows the value of surfacing it as a first-class *scannable, jump-to* state in the TUI sidebar. The CE TUI should let an operator scan all lanes and jump straight to the blocked/awaiting ones.
5. **Single-agent direct attach (`agent attach`).** A 1:1 "attach to just this lane's terminal, detach back to the cockpit" mode is a strong operator ergonomic for the CE TUI — drive one seat directly without losing the multiplexed cockpit.
6. **State self-reporting > screen-scraping.** Adopt herdr's `report_agent`/lifecycle-hook *path* as CE's only state source (CE already has governance events for this); treat any screen-heuristic as a last-resort display hint, never authoritative.
7. **Secret-aware replay default-OFF.** Keep transcript/history replay secret-scrubbed and conservatively defaulted; herdr's explicit rationale ("output includes secrets, tokens, prompts") reinforces CE's evidence-archive hygiene.

### Avoid (anti-patterns)
1. **Screen-scrape state detection as primary signal** — brittle, heuristic, the "pretty polling" trap. CE has authoritative events; do not regress to scraping.
2. **`wait_for_output`/blind `wait-for-done` as the coordination primitive** — the independent reviewer explicitly warns multi-agent workflows degrade into polling; CE should coordinate on structured governance events + explicit markers, not "wait until the screen says done."
3. **AGPL code reuse** — reference only; no dependency. Don't pull herdr (or AGPL-licensed pieces) into the public substrate.
4. **No-governance/no-survival posture** — herdr disclaims durability and governance; CE must not model its observation layer on a tool that treats panes as ephemeral text. CE's evidence/transcript must be durable and governed where herdr's is best-effort.

---

## 5. Open questions / not verified
- **Exact read-model schema for `agent_status_changed`** (full payload fields) — saw the method/event names, not the complete JSON body. Would need the source or a live socket dump.
- **How herdr renders WebUI/non-TUI** — appears TUI-only (single Rust binary, mouse-in-terminal). No evidence of a WebUI or comms-emission surface; CE's multi-renderer + comms (Discord/Slack/NanoClaw) goes beyond herdr. [INFERRED no WebUI: not mentioned anywhere fetched.]
- **Plugin system depth** (`SKILL.md` framework, manifest actions/event hooks) — saw it exists; did not deep-read `/docs/plugins/` or `/docs/marketplace/`.
- **Performance / scale** — how many concurrent agent panes herdr handles; not stated.
- **Maturity risk** — v0.7.0, single maintainer, "many preview versions," Windows experimental. Not production-proven; reinforces reference-not-dependency.
- **Whether official Claude Code integration uses CC hooks** (vs screen-only) — docs say Claude Code is "screen-only" (session identity, not full lifecycle authority); the deeper Pi/OMP-style hook path was not fully inspected.

*All version/license/architecture/method/event/state facts above are quoted from fetched docs/README (2026-06-22/06-15). Comparison-table CE columns and the relevance assessment are this worker's synthesis against CE memory/standing direction.*
