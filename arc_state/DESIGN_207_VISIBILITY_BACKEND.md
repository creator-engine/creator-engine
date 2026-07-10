# DESIGN — ce-ops#207: Headless / non-tmux visibility backend for lane launch

**Author:** CE-DEV-2 worker (design only) · **Date:** 2026-06-22
**Program:** fleet-retirement Milestone 2 (containerize + retire tmux). Parents: #115, #82.
**Status:** design/research artifact — NO production code in this PR. Feeds controller dispatch.
**Repo paths cited:** canonical tree `validators/creator_engine_validator/`, `schemas/`, `docs/`.

---

## REVISION 2026-06-23 — attachable-session substrate (supersedes log-capture model)

**Operator-ratified correction** (see memory `ce-visibility-channel-emission-model.md`,
the ATTACH requirement). The headless backend designed below as a *"detached subprocess
+ `headless.log` capture"* is **insufficient and is superseded by this section.** Log
capture only enables read-**only** watching. CE must ALWAYS be able to hand the user a
**full interactive session (read+write) with the live agent/controller — exactly as if
they'd launched Claude Code / Codex themselves** — surfaced through the CE TUI/WebUI/App.
**Dev-Mode makes this the DEFAULT** (see all controllers; drive any). It is an
always-available option for everyone, not a niche feature.

**Therefore the #207 backend is a CE-OWNED ATTACHABLE SESSION per agent** — a PTY-backed
multiplexer that **replaces tmux's role** (herdr-shaped: CE owns the process *and its
PTY*; clients attach on demand). One owned session yields BOTH surfaces:
- **(a) read-model emission** — the structured/multi-seat/contact-on-need surface for the
  ~95% who delegate. Derived from authoritative governance/lifecycle events, **NOT
  screen-scraping** (the herdr anti-pattern; see RESEARCH_HERDR §3).
- **(b) interactive attach** — stream the live session out + route interactive input back
  in (read+write), on demand, to a TUI/WebUI/App client (incl. multi-controller view +
  attach-any). This is what tmux-pane-attach gives today, owned by CE instead of tmux.

**What this supersedes below:** §3.2 `HeadlessVisibilityBackend` ("detached subprocess +
log capture"), the §3.2 capture-parity table's "log-only" framing, and the
companion DESIGN_207B G1 framing of "tail a `headless.log`" as the live-watch surface.
**What still holds:** the §3.1 `VisibilityBackend`-registry seam (the named seam the
ticket asks for), §3.3 wiring points (C1/C2/C2′), §3.4 schema/validator generalization
(C3), §3.6/§3.7 container fit, and the entire §2 evidence-spine inventory (sentinel
events, lifecycle record, sidecar, cockpit read-model are already tmux-free and survive
unchanged). The registry stays; **the headless *backend* it registers becomes the
attachable-session substrate, not a log-capture subprocess.**

---

### R.1 The attachable-session substrate (what CE owns per agent)

CE owns, per agent/lane, a **session object** that wraps the seat process in a
**PTY** (pty/pir master/slave pair) that CE — not tmux — holds. This is herdr's
"server owns the real pane processes; the thing you look at is a thin client over a
Unix domain socket" model (RESEARCH_HERDR §1: *"The work lives in the server"*), placed
on CE's governance spine.

**Owned per session** (proposed):
- **The seat process** — spawned by CE under a PTY (`pty.openpty()` / `os.forkpty`, or a
  small pir helper), so the child sees an interactive tty exactly as under tmux. The
  sentinel wrapper still wraps the OUTERMOST argv (verified `lane_runtime.py:917-930`:
  `sentinel.pane_command` is what the spawn backend receives), so lifecycle events
  (`events.jsonl`) are produced **identically** — the substrate change is *which surface
  owns the PTY*, not the wrapper contract.
- **The PTY master fd** — the single byte tap. CE reads it for BOTH (a) and (b). This is
  the structural fix for the DESIGN_207B gap: today the wrapper runs `{inner}` as a
  foreground child with **no redirection** (verified `seat_sentinel.py:184-185` /
  build_wrapper_script — the live work-stream exists only in the tmux pane buffer and
  dies with tmux). Owning the PTY master means CE holds the byte stream regardless of
  any renderer.
- **A session daemon / supervisor** that survives client detach (the seat keeps running
  with no client attached — herdr "processes keep running on detach," RESEARCH_HERDR §1)
  and accepts (re)attach on demand.
- **A control socket** — a per-session Unix domain socket (herdr default
  `~/.config/herdr/sessions/<name>/herdr.sock`, RESEARCH_HERDR §1). CE's analogue lives
  under the controller state root the cockpit already watches (so it composes with the
  existing read-model input seams, `cockpit_readmodel.py:1718-1888`).

**How a client attaches/detaches** (proposed transport, herdr-cited):
- **Transport = NDJSON RPC + event stream over the local socket** (herdr: newline-
  delimited JSON over a local socket; `{"id","method","params"}` → `{"result"}` /
  `{"error"}`, RESEARCH_HERDR §1). CE adopts the *shape*, not the code (herdr is AGPL+Rust
  — reference only, RESEARCH_HERDR §3).
- **1:1 attach** = herdr's `agent attach` ("attach your current terminal to a *single*
  agent terminal … direct 1:1 control with multiplexer-style detach", RESEARCH_HERDR §1).
  Client sends `attach`; CE streams PTY output bytes out as a typed stream and accepts
  `send_input`/`send_keys` back (herdr `pane.send_input`/`send_keys`/`read`, §1).
- **Multi-view** = many read-only clients subscribe to the same session's output stream
  (herdr `events.subscribe` holds the connection open and pushes typed events, §1);
  Dev-Mode's "see all controllers + drive any" = subscribe-all + a single writable attach
  at a time (write-lock arbitration is a substrate decision — flag as R.5 escalation).
- **Detach** leaves the seat running (live persistence, herdr §1). **Reconnect** re-opens
  the socket and re-attaches; the substrate must replay enough recent output for context.

**Survives detach + reconnect (persistence) — proposed, with the herdr secret caveat:**
- Live detach/reattach: seat process unaffected (PTY master held by the daemon, not the
  client).
- **Scrollback/replay on reconnect is the secret-hazard seam.** herdr ships pane-history
  replay **OFF by default** *"because pane output can include secrets, tokens, prompts"*
  (RESEARCH_HERDR §1, opt-in `pane_history`). CE inherits this directly: any replay
  buffer is value-bearing raw bytes → it MUST pass the same redaction gate as attach
  (R.2/R3) and default conservative. **Server-restart process-resurrection is NOT in
  scope** (herdr doesn't resurrect processes either — restored panes become fresh shells,
  §1); CE relies on harness-native resume (Claude Code/codex `--resume`) the same way
  herdr does (§1 "native agent session resume").

### R.2 Both surfaces from one owned session

The single PTY-master tap feeds two **independent projections**:

| Surface | Source from the owned session | Value-free invariant |
|---|---|---|
| **(a) read-model emission** | NOT the PTY bytes. Authoritative governance/lifecycle events: sentinel `events.jsonl`, Pane Registry record, refusal/runtime-evidence chains, escalations — the §2 spine, already tmux-free. The cockpit read-model is a **pure fold** of these (DESIGN_207B §1; `cockpit_readmodel.py:1-31`). herdr guardrail: state from authoritative self-report/hooks, **never screen-scrape** (RESEARCH_HERDR §3; memory). | Already value-free by law (digests not text, `seat_sentinel.py:101-104`). No new leak surface. |
| **(b) interactive attach** | The PTY-master **raw bytes** streamed out + interactive input routed in. | **Raw bytes = the first surface that can leak secrets/tokens/output.** Redaction + a secret-leak test are **mandatory** (coverage report **R3**: "every new live-work surface … must carry a redaction/screening gate + a test asserting injected env/secret values never reach the surface"). The §5.D env-value-leak test extends to the attach stream and any replay buffer. |

This corrects the original §3.2: read-model emission and live-watch are **not** the same
mechanism with a log file between them — they are two projections of one CE-owned session,
one structured-and-value-free, one raw-and-redaction-gated. Attach is the load-bearing
new capability; the read-model fold already exists.

### R.3 Governance preserved (attach is CE-mediated, not a bypass)

- The agent's **acts still go through Ring-1 hooks regardless of who drives input.**
  Whether bytes on the PTY came from the agent's own loop or from an operator's attach
  keystrokes, the resulting *tool calls* hit the in-band hook (the launch-pinned
  `CE_LEDGER_ROOT` / reviewer-authority env the substrate must still pin into the seat
  env — verified `lane_runtime.py:907-915` pane_env; the PTY substrate sets the same env
  on the child). Input routing changes *who types*, not *what gate the act passes*.
- **Attach is CE-mediated + audited.** The operator attaches **THROUGH** CE's owned,
  audited session (over CE's socket), never around it. An attach session is itself an
  auditable event (attach/detach/who/when → a read-model event, herdr
  `agent_status_changed`-style). This is the property herdr **lacks** (RESEARCH_HERDR §3:
  herdr is "observation-only … zero governance") and is exactly CE's value-add on top of
  herdr's function.
- **Dev-Mode confirmation-relaxation = a SEPARATE policy knob.** Dev-Mode making attach
  the default, and any relaxation of confirm-on-consequence while an operator is hands-on,
  is a **distinct policy seam — NOT designed here.** Flag the seam: it rides on the same
  attach substrate but is gated by a Dev-Mode policy binding (memory: "Dev-Mode
  confirmation-relaxation is a separate policy knob"). Substrate ships attach;
  policy decides relaxation later.

### R.4 C1 / C4 gate updates (revised)

- **C1** (`lane_runtime.py:741-746`) — restate the satisfaction predicate as *"is the lane
  running in a **CE-owned attachable + emitting session**?"* The §3.3 generalization to a
  `visibility_class` check still holds, but the satisfying class for the non-tmux backend
  is now **attachable-and-emitting** (the substrate owns a PTY + a socket + produces the
  evidence spine), not merely "produced a log file." The refusal stays load-bearing: it
  refuses an *unknown / non-attachable / non-emitting* surface.
- **C4** (`checks/harness_seat_contract.py:71, 220`) — the controller seat-contract gate.
  Per the memory directive, C4 should refuse **dark** headless only (Claude `--print`, no
  archivable surface, `claude_launch_spec.py:25,161`) and **ALLOW** a controller to
  declare `operator_inspectable`/**attachable** headless. This **supersedes the original
  §5.G recommendation to leave C4 untouched**: the Operator has now ruled that an
  attachable+emitting headless controller is a sanctioned visibility class. The C4 change
  = introduce the `operator_inspectable`/attachable `terminal_visibility` token and refuse
  only *dark*. (Still gated behind the trailing controller PR-unit, see R.6.)

### R.5 Containerization (#208) seam — attach reaches INTO the container

A containerized headless agent must **still be attachable**. The substrate decision: CE
**execs a PTY into the sandbox** (gVisor/OpenShell `RunnerBackend`) so the in-container
seat process is PTY-owned by CE through the sandbox boundary, and the control socket is
reachable from the host (bind-mounted / forwarded). This composes the orthogonal tiers
(§3.1): `RunnerBackend` = *where it runs* (sandbox), attachable-session substrate = *how
it's owned + observed*. `container_instance_id`/`_ref` (schema `:134-140`) bind the
session to the container.

**M2-arch ESCALATIONS (do NOT decide here — surface to the Operator/#208):**
- **E-att-1: PTY-into-sandbox mechanism.** Whether CE owns the PTY on the *host* and the
  sandbox runs the child, vs. a pir/agent inside the sandbox bridging to CE's socket
  (gVisor syscall-interception interplay with pty master/slave). Substrate-shaping.
- **E-att-2: socket reachability across the container boundary** (bind-mount vs forward
  vs vsock) and its **secret-surface** (the socket carries raw PTY bytes — R.2/R3 gate
  must hold across the boundary).
- **E-att-3: write-lock arbitration for multi-attach** (who may drive when N clients are
  attached; Dev-Mode "drive any"). Policy×substrate — escalate, don't decide.
- **E-att-4: replay/scrollback buffer size + persistence** across detach (the secret-aware
  default-OFF/opt-in decision, herdr-shaped) and across a daemon restart.

### R.6 Revised PR-unit breakdown (attachable substrate)

Strict-TDD, ~200-400 ln each. The §4 W1–W5 units **mostly survive** — W1 (registry
seam) and W5 (docs) are unchanged; **W2 is re-scoped** from "log-capture subprocess" to
"PTY-owned session + read-model emission," and **new trailing units** add interactive
attach, the C4 controller token, and container attach.

**Ships in #207 baseline (worker lanes attachable + emitting):**
- **W1 — `VisibilityBackend` registry + tmux backend** (unchanged from §4). ~250-350 ln.
  The seam; tmux stays one backend, regression-green.
- **W2′ (re-scoped) — PTY-owned attachable session backend + C1/C3.** ~350-400 ln (likely
  splits, see below). Replaces the §4-W2 detached-subprocess design: spawn the
  sentinel-wrapped argv under a **CE-owned PTY** (not a log redirect), expose the PTY
  master to the substrate, write the Pane Registry record (`terminal.kind` = the new
  attachable kind + `surface_ref`/socket ref + pid), generalize C1 to the
  attachable+emitting predicate, generalize the C3 schema/validator
  (`pane-registry.schema.yaml` enum + conditional; `checks/pane_registry.py:178-203`).
  *Acceptance:* a visibility-required **worker lane** launches to LAUNCHED on a host with
  **no tmux**, produces a schema-valid record + `events.jsonl` + a live PTY the substrate
  owns. **If >400 ln, split W2a (PTY substrate + spawn) / W2b (schema+validator+C1).**
- **W2-sec — redaction/secret-leak gate on the raw stream** (coverage R3). ~150-250 ln.
  The redaction screen over any raw-byte surface + the mandatory test asserting injected
  env/secret values never reach the attach stream or replay buffer. **Gating** for any
  attach surface — lands in baseline even though the *interactive UI* trails.
- **W4 — headless/attachable teardown executor** (reaper, §4-W4 unchanged in intent;
  now also closes the PTY/daemon + socket). ~150-250 ln.

**Trails #207 (separate PRs, each gated):**
- **T1 — control socket + NDJSON attach protocol** (server side). ~300-400 ln. The
  per-session socket, `attach`/`detach`/`send_input`/`subscribe`/output-stream methods
  (herdr-shaped). Rides on W2-sec (raw bytes screened). Splits if needed.
- **T2 — cockpit interactive-attach UI** (TUI first; WebUI/App later). The 1:1 attach
  pane + multi-view subscribe in the CE TUI (herdr `agent attach` ergonomic,
  RESEARCH_HERDR §4). Thin client over T1's socket.
- **T3 — controller C4 token + `ce launch` path.** ~150-250 ln. The §4-W3 `ce launch`
  registry wiring **plus** the R.4 C4 change (add `operator_inspectable`/attachable
  `terminal_visibility` token, refuse only *dark*). Lets a **controller** run
  attachable-headless. This is now sanctioned (R.4) — no longer the §5.G "leave untouched."
- **T4 — container attach** (#208 / M2-arch). PTY-into-sandbox + cross-boundary socket.
  **Carries the R.5 escalations** — do not start until E-att-1..4 are ruled.

**Coupling (unchanged, re-confirmed):** each PR needs `.ce/pr-manifests/<slug>.md`
(verify-path-manifest blocks otherwise) + `.ce/changelog/<slug>.md`. Schema + validator
ship in the wheel → **wheelhouse-wheel rebuild + SHA256SUMS re-pin** + `rm -rf` egg-info
before suite (W2′). No new top-level `ce` command **group** is added by W1/W2′/W4 →
`test_v1_docs_reconciliation.py` group inventory untouched; **T1/T2 may add a `ce lane
attach` subcommand** (a flag/subcommand under the existing `lane` group, not a new group)
— confirm the group inventory at `test_v1_docs_reconciliation.py:54` stays
`{lane, …, launch, hud}`. The prose docs (lane protocol, sentinel contract) are touched
in W5/T-docs; a new `ce` group would also trip the docs-reconciliation README coupling.
`_versions.py` bump only at a milestone boundary, not per-PR (semver milestone policy).

**Sequencing:** W1 → W2′ (+W2-sec) → W4 = the #207 baseline (workers attachable-capable +
emitting; the live-attach *UI* not yet shipped). Then T1 → T2 (attach UI), T3 (controller
C4), T4 (container attach, gated on R.5 rulings). Recommended wave: **[W1]** →
**[W2′, W2-sec]** → **[W4, W5]** → (post-baseline) **[T1]** → **[T2, T3]** → **[T4]**.

---

## 1. Problem framing (in CE's terms)

`ce lane launch` is the governed lane-launch primitive (RV1-030, `lane_runtime.py`).
For a **visibility-required role** (`architect`, `implementer`, `reviewer`,
`verification` — `lane_runtime.py:51`) it MUST spawn an **operator-visible tmux
pane** or fail closed with `VisibilityRefused` (`lane_runtime.py:741-746`). tmux is
hard-wired three ways:

- `TMUX_TERMINAL_KIND = "tmux"` is a module constant and the only legal terminal
  for a visible role (`lane_runtime.py:80`, gate at `:742`).
- `tmux_adapter.TmuxAdapter` is the only spawn backend (`lane_runtime.py:48,
  892-896, 932-941`); `launch_runtime.launch` (the `ce launch` controller-seat
  path) is identically hard-wired (`launch_runtime.py:497-505, 581-583`).
- The Pane Registry *validator* requires `terminal.kind == "tmux"` for any
  `operator_visible` record (`checks/pane_registry.py:182-203`).

This blocks two things #207 must unblock:

1. **Containerization (#208).** A CE seat/controller running inside an OCI image
   has no host tmux server; #208's acceptance ("a seat runs end-to-end inside the
   container with **no host tmux**") is literally `blocked-by` #207.
2. **Autonomous/headless belt.** A cron-driven seat (the #55 belt direction) has
   no operator watching a pane, so "operator-visible tmux" is incoherent for it —
   yet governance still requires the visibility *contract* (an inspectable
   evidence record).

**What #207 must deliver** (ticket Ask + Acceptance):
- Replace the hardcoded tmux gate with a **backend / terminal-kind registry**
  (tmux stays one backend, regression-green).
- Add a **headless visibility mode**: a logged/streamed lane surface that
  satisfies the visibility *contract* (operator-inspectable evidence) without an
  interactive tmux pane.
- Preserve all governance: visibility is still **required**, just satisfiable by
  a non-tmux inspectable surface.
- **Acceptance:** a visibility-required lane launches to LAUNCHED state on a host
  with **no tmux server**, producing an operator-inspectable record; tmux path
  unchanged/regression-green.

**Key framing insight:** "visibility" in CE is *not* "a human is staring at a
pane." It is "the lane's existence, identity, command, and lifecycle are bound to
a live claim and recorded in machine-watchable, operator-inspectable artifacts."
tmux is one *renderer* of that contract; #207 generalizes the contract away from
that one renderer. The witnessability artifacts (below) are already substrate-
neutral — the gap is the *spawn seam* and the *schema/validator* that still
assume the tmux renderer.

---

## 2. Current state — where tmux couples, what evidence must survive

### 2.1 The three coupling points (must change)

| # | Coupling | File:line | Nature |
|---|----------|-----------|--------|
| C1 | Visibility gate refuses non-tmux for visible roles | `lane_runtime.py:741-746` | the load-bearing refusal |
| C2 | `TMUX_TERMINAL_KIND` constant + tmux-availability precheck + `TmuxAdapter().ensure_pane()` spawn + tmux terminal record | `lane_runtime.py:80, 622, 891-896, 932-941, 980-992` | the spawn seam |
| C2′ | Same spawn seam on the `ce launch` controller path | `launch_runtime.py:497-505, 581-589` | parallel spawn seam |
| C3 | Pane Registry validator requires `terminal.kind == tmux` for `operator_visible` | `checks/pane_registry.py:182-203` | the evidence-schema gate |
| C4 | Harness seat-contract validator requires `launch_posture.terminal_visibility == operator_visible` and refuses `print_headless` | `checks/harness_seat_contract.py:71, 220` | **governance-doc gate — see §5.G; do NOT naively weaken** |

> **C4 is a trap, read carefully.** `harness_seat_contract.py` validates a *seat-contract
> posture document* (`CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md`), not the runtime Pane
> Registry record. Its `print_headless` refusal (`:71`) is specifically Claude's
> `--print` mode (CC-D-2, `claude_launch_spec.py:25,161`) — a *genuinely
> posture-defeating* mode that produces **no archivable surface at all**. That is
> categorically different from #207's headless **visibility backend**, which DOES
> produce an archivable, operator-inspectable surface (Pane Registry + events.jsonl +
> log). #207 must NOT relax C4 to permit `print_headless`; it must instead establish
> that "headless visibility backend" is a *distinct, witnessable* class — not the
> "hidden/headless seat" the contract refuses. This is the §5.A/§5.G policy decision
> to escalate. Recommendation: leave C4 untouched in #207 and introduce a *new* posture
> token for the inspectable-headless class only if/when the Operator rules headless is
> a sanctioned visibility class for governed seat-contracts.

CLI surface already half-anticipates this: `--no-tmux` exists on **both** `ce lane
launch` (`ce_cli.py:252-256`) and `ce launch` (`ce_cli.py:912-916`) but is a
**"refuse-only flag … always refused"** today — `ce_cli.py:1012` sets
`terminal_kind = "headless" if args.no_tmux else TMUX_TERMINAL_KIND`, and that
`"headless"` value currently lands on the C1 refusal. `ce launch` passes
`visible=not args.no_tmux` (`ce_cli.py:2378`). #207 turns these from "always
refused" into "satisfiable by a headless backend."

### 2.2 Witnessability / evidence artifacts that MUST be preserved

These are the operator-inspectable surfaces produced at launch. Note that **most
are already tmux-independent** — the design must keep producing all of them.

1. **Pane Registry record** (`lane_runtime.py:964-1012`, schema
   `schemas/pane-registry.schema.yaml`, validator `checks/pane_registry.py`).
   The durable claim-bound identity record. Today stamps `visibility:
   operator_visible` + `terminal.kind: tmux` + session/window/pane ids. This is
   the artifact whose *schema* must learn a headless terminal kind.

2. **Seat sentinel `events.jsonl` + `sentinel-wrapper.sh`**
   (`seat_sentinel.py`; written via `prepare_seat_sentinel`,
   `lane_runtime.py:924-930`, `launch_runtime.py:573-579`). **This is the crux of
   portable witnessability and it is ALREADY substrate-neutral.** The wrapper is
   a PURE POSIX-sh supervisor (`build_wrapper_script`, `seat_sentinel.py:139`)
   that runs the seat command as a foreground child and appends `launched`/`exited`
   lifecycle events to `events.jsonl` on ANY termination (silence≠success). Its
   docstring explicitly anticipates the container case: *"a future container seat
   sets `ENTRYPOINT ["/bin/sh", "sentinel-wrapper.sh"]` and emits identical
   events"* (`seat_sentinel.py:27-29`). The launcher wraps the OUTERMOST command
   and hands `sentinel.pane_command` to the spawn backend — so the events stream
   exists **regardless of whether tmux ever runs.**

3. **Seat lifecycle record** (`seat_lifecycle.register_spawn`,
   `lane_runtime.py:1047-1074`). Consumes a generic `terminal` mapping
   (`seat_lifecycle.py:436-444` reads `terminal.get("kind")` with an `unknown`
   default) — already terminal-kind-agnostic. No tmux assumption in the record;
   the optional `tmux` *probe* is injectable and skipped when absent
   (`seat_lifecycle.py:453-455`).

4. **Governance sidecar JSON** (`lane_runtime.py:1014-1040`). Carries CC-G-D
   governed-Claude audit, `events_ref`, brain-bootstrap pointers, reviewer-venue
   identity. tmux-independent.

5. **v3 cockpit read-model** (`runner/cockpit_readmodel.py`). Projects board cards
   from the Pane Registry `terminal.kind` generically (`:631-638, :1374-1387`)
   and reads `events.jsonl` via `seat_sentinel.load_seat_events`
   (`cockpit_readmodel.py:1834-1843, :2002`). It derives `terminal_state`
   (live/exited/unknown) from the **events**, not from tmux (`:1457-1464`). **The
   cockpit has no tmux dependency** — a headless seat is already renderable there
   as long as it produces a Pane Registry record + events.jsonl.

6. **Transcript archive** (`transcript_archive.py`; `ce lane archive`, RV1-032).
   Copies transcript *bytes from a source path* (`transcript_archive.py:1-9,
   77`); source-agnostic, no tmux/`capture-pane`. (The only `tmux capture-pane`
   in the tree is `v3_seat_bridge.py:708` — an idle-detection/auto-drive concern,
   out of #207 scope.)

7. **Teardown executor selection** (`reaper_executors.default_executor_for`,
   `reaper_executors.py:337-347`). Already keyed on `terminal_kind` and returns
   `None` for an unsupported kind; the docstring anticipates "a future
   worker/container executor." A headless kind needs a matching executor (see
   work-unit W4).

**Bottom line:** the portable evidence spine (sentinel events, lifecycle record,
sidecar, cockpit read-model, transcript archive) is *already* tmux-free. The work
is concentrated at **C1/C2/C2′/C3** plus a thin **headless backend** that produces
the same Pane Registry + lifecycle terminal record without a tmux server.

### 2.3 Groundwork already in the schema

`schemas/pane-registry.schema.yaml` already:
- enumerates `terminal.kind: [tmux, plain_terminal, unknown]` (`:87-89`) — so
  non-tmux kinds are *schema-legal* already;
- guards the session/window/pane-required block behind `if kind == tmux`
  (`:144-154`) — i.e. **only tmux** requires pane ids; a headless kind is already
  exempt at the schema level;
- carries `container_instance_id` / `container_instance_ref` fields (`:134-140`)
  — pre-existing container groundwork.

The *validator* `checks/pane_registry.py:182` is **stricter than the schema** — it
rejects any `operator_visible` record whose `terminal.kind != "tmux"`. This is the
real C3 gate to relax.

---

## 3. Proposed design — headless visibility backend behind a terminal-kind registry

### 3.1 The seam: a `VisibilityBackend` registry (mirror of `RunnerBackend`)

Introduce a **visibility-backend abstraction** modeled on the existing
`RunnerBackend` registry (`runner/backend.py:152-274`: an ABC + `register_backend`
/ `get_backend` / `_REGISTRY` keyed by a string). This is the named seam the
ticket asks for ("a backend/terminal-kind registry; tmux remains one backend").

New module `validators/creator_engine_validator/visibility_backend.py`:

```
class VisibilityBackend(abc.ABC):
    terminal_kind: str                 # "tmux" | "headless"
    visibility_class: str              # "operator_visible" | "operator_inspectable"
    def is_available(self) -> bool: ...
    def ensure_surface(self, *, session, window, command, cwd, env, seat_dir) -> SurfaceHandle: ...
    # SurfaceHandle carries the terminal record dict the Pane Registry writes.

# registry, mirroring runner/backend.py:244-274
register_visibility_backend(kind, factory) / get_visibility_backend(kind) / available_visibility_kinds()
```

Why a *new* registry rather than overloading `RunnerBackend`: `RunnerBackend` is
the **sandbox/runtime** tier (os-native / openshell / gvisor — *where* the process
runs); visibility is the **witnessability/surface** tier (*how* the lane is
observed/recorded). They compose orthogonally (a gVisor-sandboxed seat with a
headless surface). Keep them separate; the container image (#208) selects one of
each. The new registry deliberately copies the proven `RunnerBackend` ergonomics
(string key, factory, fail-closed `get_*`).

### 3.2 Two backends

- **`TmuxVisibilityBackend`** (`terminal_kind="tmux"`, `visibility_class=
  "operator_visible"`) — a thin adapter wrapping the **existing**
  `tmux_adapter.TmuxAdapter` unchanged. `ensure_surface` calls `ensure_pane(...)`
  and returns the existing tmux terminal record (`{kind, session_id, window_id,
  pane_id, pane_tty?, pane_pid?}`). **Zero behavior change** on the tmux path
  (regression-green requirement). `tmux_adapter.py` itself is untouched.

- **`HeadlessVisibilityBackend`** (`terminal_kind="headless"`, `visibility_class=
  "operator_inspectable"`) — spawns the sentinel-wrapped command as a **detached
  local subprocess** (no tmux server), with stdout/stderr redirected to a
  per-seat log under the seat dir (e.g. `<seat_dir>/headless.log`), and returns a
  terminal record `{kind: "headless", surface_log_ref, pid}`. Witnessability is
  satisfied by: (a) the Pane Registry record (claim-bound identity), (b) the
  sentinel `events.jsonl` (lifecycle, already produced — the wrapper is the
  foreground child), and (c) the captured log surface. The operator (or cockpit)
  inspects the log + events instead of attaching a pane.
  `is_available()` is always true (subprocess + a writable seat dir are the only
  requirements), making it the correct fallback for a no-tmux host/container.

**Capture parity (how headless preserves the same evidence without a pane):**
| tmux renders via | headless renders via |
|---|---|
| live pane attach | `headless.log` (stdout/stderr capture) + `ce lane status` |
| pane identity (session/window/pane) | pid + `surface_log_ref` in terminal record |
| pane lifecycle (operator sees crash) | `events.jsonl` `exited` event (already produced) |
| `pane_current_path` cwd verification | subprocess `cwd=` is authoritative (no settle race) |

### 3.3 Wiring `lane_runtime.launch` to the registry (minimal diff)

At C2 (`lane_runtime.py:891-941`): replace the direct `TmuxAdapter` use with
`backend = get_visibility_backend(terminal_kind)` (default still
`TMUX_TERMINAL_KIND` for byte-identical default behavior), then
`backend.ensure_surface(...)`. Keep the existing `tmux_adapter` kwarg as an
injection seam by routing it into the tmux backend factory (preserves every
existing test that injects a fake adapter).

At C1 (`lane_runtime.py:741-746`): replace `terminal_kind != TMUX_TERMINAL_KIND`
with **`get_visibility_backend(terminal_kind) is unknown OR backend.
visibility_class not in SATISFYING_VISIBILITY_CLASSES`**, where
`SATISFYING_VISIBILITY_CLASSES = {"operator_visible", "operator_inspectable"}`.
The refusal is preserved — it now refuses an *unknown / non-satisfying* terminal
kind, not "anything but tmux." Governance invariant intact: a visibility-required
role still cannot launch onto a surface that fails the contract.

Terminal record (`lane_runtime.py:980-992`): build from the backend's
`SurfaceHandle` instead of hardcoding `kind: tmux`. Set `visibility` from
`backend.visibility_class`.

The `ce launch` path (`launch_runtime.py:497-505, 581-589`) gets the parallel
change (W3) so containerized **controllers** are also headless-capable.

### 3.4 Schema + validator (C3)

- `schemas/pane-registry.schema.yaml`: add `headless` to the `terminal.kind` enum
  (`:89`); add an `allOf` branch `if kind == headless then required:
  [surface_log_ref]` (mirror the existing tmux conditional at `:144-154`); add
  `surface_log_ref` + `pid` properties to the `terminal` object; add
  `operator_inspectable` to the `visibility` enum (`:79-81`).
- `checks/pane_registry.py:178-203`: generalize `_operator_visible_errors` →
  `_visibility_surface_errors`: for `kind == tmux` require session/window/pane (as
  today); for `kind == headless` require `surface_log_ref`; reject only an
  *unknown* visibility class. The refusal stays load-bearing.

### 3.5 CLI (flip `--no-tmux` from refuse-only to satisfiable)

`--no-tmux` already maps to `terminal_kind="headless"` (`ce_cli.py:1012`) — the
mapping stays; only its *meaning* changes (it now resolves to a real backend
rather than the C1 refusal). Update help text (`ce_cli.py:255, 915`). The `ce
launch` path threads `visible=not args.no_tmux` → a `terminal_kind`/`visible`
parameter into `launch_runtime.launch` (W3). No new top-level `ce` command group
is added → `test_v1_docs_reconciliation.py` group inventory is **untouched**
(it guards groups, not flags — `:52-69`).

### 3.6 Fit with the container image (#208)

#208 consumes this directly: the OCI image sets the seat's default
`terminal_kind=headless`, runs the sentinel wrapper as `ENTRYPOINT` (already
designed, `seat_sentinel.py:27-29`), composes the headless visibility backend
with a `RunnerBackend` (gVisor/OpenShell) for sandboxing, and the cockpit
read-model renders the seat from the Pane Registry record + `events.jsonl`
mounted out of the container. `container_instance_id` / `container_instance_ref`
(schema `:134-140`) bind the record to the container. **No host tmux anywhere.**

### 3.7 Degrade / compose

- Explicit `--no-tmux` → headless backend (deterministic).
- Default (no flag) → tmux backend, regression-identical.
- **Optional auto-degrade** (recommend deferring to #208, flag as open question
  §5): when tmux is requested but `TmuxVisibilityBackend.is_available()` is false
  AND the host is a container, auto-fall-back to headless. Defer because silent
  visibility-class downgrade is a governance-policy decision (operator may *want*
  the refusal). Keep #207 explicit-only; let #208/policy decide auto-degrade.

---

## 4. Work breakdown (ordered, PR-sized, strict-TDD)

The repo is strict-TDD: tests first, one worker per unit. Each PR needs a path
manifest `.ce/pr-manifests/<slug>.md` matching `base..HEAD` (CI
`verify-path-manifest` blocks otherwise) and a changelog fragment
`.ce/changelog/<slug>.md` (per-PR obligation). None of these add a `ce` command
group, so `test_v1_docs_reconciliation.py` group inventory is not touched; the
**prose** docs (lane protocol, sentinel contract) ARE touched in W5.

**W1 — `VisibilityBackend` registry + tmux backend (no behavior change).**
~250-350 lines. New `visibility_backend.py` (ABC + registry mirroring
`runner/backend.py`) + `TmuxVisibilityBackend` wrapping `tmux_adapter` unchanged.
Re-point `lane_runtime.launch` C2 spawn (`:891-941`) through
`get_visibility_backend("tmux")`, preserving the `tmux_adapter` injection kwarg.
*Tests:* new `tests/unit/test_visibility_backend.py` (registry register/get/
fail-closed, tmux backend availability + ensure_surface returns the existing
record); existing `test_lane_runtime*` MUST stay green (proves zero tmux-path
regression). *Touches:* `visibility_backend.py`, `lane_runtime.py`.

**W2 — Headless backend + relax the C1 gate + C3 schema/validator.**
~300-400 lines. `HeadlessVisibilityBackend` (detached subprocess, log capture,
headless terminal record). Generalize C1 (`lane_runtime.py:741-746`) to the
visibility-class check. Schema: add `headless` kind + `surface_log_ref`/`pid` +
conditional + `operator_inspectable` (`pane-registry.schema.yaml`). Validator:
generalize `_operator_visible_errors` (`checks/pane_registry.py:178-203`).
*Tests:* headless launch reaches LAUNCHED-state on a host with **no tmux**
(the ticket's headline acceptance — use a fake/absent tmux + a tmpdir seat dir),
produces a schema-valid Pane Registry record + `events.jsonl`; `pane_registry`
check accepts headless, still rejects an unknown kind. *Touches:*
`visibility_backend.py`, `lane_runtime.py`, `schemas/pane-registry.schema.yaml`,
`checks/pane_registry.py`, `tests/unit/test_visibility_backend.py`,
`tests/unit/test_pane_registry*.py`, `tests/unit/test_lane_runtime*.py`.
*Coupling note:* the wheelhouse-wheel rebuild + SHA256SUMS re-pin footgun applies
because schema + validator ship in the wheel — rebuild wheel, `rm -rf` egg-info
before the suite.

**W3 — `ce launch` controller path → registry.** ~150-250 lines. Thread
`terminal_kind`/`visible` through `launch_runtime.launch` (`:497-505, 581-589`)
to use the registry so a containerized **controller** is headless-capable; wire
`ce_cli.py:2378` (`--no-tmux` for `ce launch`). *Tests:* `test_launch_runtime*`
— headless controller-seat launches with no tmux; tmux path regression-green.
*Touches:* `launch_runtime.py`, `ce_cli.py`, `tests/unit/test_launch_runtime*.py`.

**W4 — Headless teardown executor (reaper).** ~150-250 lines. Add a headless
executor + register it in `reaper_executors.default_executor_for`
(`:337-347`) so a headless seat is reapable (terminate pid, mark Pane Registry
closed) — closing the lifecycle so headless seats aren't un-retireable.
*Tests:* `test_reaper*` / `test_seat_reaper*`. *Touches:* `reaper_executors.py`,
`seat_reaper.py` (if selection logic lives there), reaper tests.

**W5 — Docs + protocol reconciliation.** ~100-200 lines (docs only). Update
`docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md:16-18, 36, 103-125, 181` (tmux
no longer mandatory; document headless as a satisfying visibility class and
`--no-tmux` as a real mode, not "always refused"); update
`docs/architecture/seat-sentinel-contract.md` to reference the headless backend;
note the new visibility backend in any `ce-knowledge` SSOT surface. *Tests:* any
doc-contract test; confirm `test_v1_docs_reconciliation.py` still green (it
will — no group change). *Touches:* the two docs + manifest/changelog.

> **Sequencing:** W1 → W2 are the critical path (W2 depends on the W1 registry).
> W3/W4 depend on W1 and can run in parallel after W1 lands. W5 lands last (or
> alongside W2 as the protocol-of-record). Recommended dispatch wave:
> **[W1]** then **[W2, W3 parallel]** then **[W4, W5 parallel]**.
> Total ~5 PRs, each within the ~200-400-line band.

---

## 5. Risks / open questions (escalate the architecture ones)

**A. Visibility-class semantics — needs an Operator/architecture decision.**
Is "headless / operator_inspectable" an *equal* satisfaction of the visibility
contract, or a *lower* tier that some roles/operating-modes may not use? Today
all four visibility-required roles are treated identically. Recommendation:
treat headless as an equal satisfying class for #207 (the belt + container need
it), but **flag** that whether `reviewer`/`approval`-adjacent roles may run
headless under `strict` mode is a governance call beyond #207. *Escalate.*

**B. Auto-degrade policy (tmux-unavailable → headless).** §3.7 — should a
requested tmux lane silently fall back to headless on a no-tmux host, or refuse?
This is a visibility-downgrade governance decision. Recommendation: **#207 stays
explicit-only** (`--no-tmux` opt-in); defer auto-degrade to #208 + a policy
binding. *Escalate as an #208 decision.*

**C. Headless log surface = transcript-grade evidence?** The `headless.log`
capture is the operator-inspectable surface, but it is NOT the governed
`transcript_archive` (which copies bytes into a repo, RV1-032). Open question:
does a headless seat's archived evidence-of-record route through
`transcript_archive` (pointing at `headless.log`) or is the log a separate tier?
Recommendation: keep `headless.log` as the live surface and let `ce lane archive`
point at it for durable archival — no new evidence mechanism. *Confirm during W2/W5.*

**D. Secret hygiene parity.** The tmux backend never prints secrets and passes
env via tmux `-e` (`tmux_adapter.py:121-136`). The headless backend redirects
stdout/stderr to a file — must guarantee the seat command cannot leak the
`CE_LEDGER_ROOT` / `CE_REVIEWER_AUTHORITY_REF` env *values* into the log (env is
passed to the subprocess environment, never echoed; same posture as tmux `-e`).
A test must assert the log never contains injected env values. *In-scope for W2.*

**G. Harness seat-contract `terminal_visibility` (C4) — needs the §5.A ruling.**
`checks/harness_seat_contract.py:220` hard-requires `launch_posture.terminal_visibility
== operator_visible` and `:71` refuses `print_headless`. A containerized *governed
controller seat* (#208) running headless would, today, fail to author a compliant
seat-contract posture doc — because the contract conflates "headless" (no archivable
surface, refused) with the new "inspectable-headless" (archivable, the #207 backend).
Recommendation: do NOT weaken C4 in #207. Either (a) keep governed *controllers* on
tmux for #207 and ship only headless *worker lanes*, or (b) the Operator rules that
"operator_inspectable" is a sanctioned `terminal_visibility` token for seat-contracts,
in which case a follow-up adds that token + the distinction from `print_headless`. This
is the same ruling as §5.A and gates how far #208 can go headless. *Escalate.*

**H. Reuse `plain_terminal` vs add `headless` kind?** The schema already enumerates
`terminal.kind: plain_terminal` (`pane-registry.schema.yaml:89`) with no implementation.
Open question: name the headless backend's kind `headless` (clearer intent) or reuse
`plain_terminal` (no schema enum change). Recommendation: use a distinct `headless` kind
(a `plain_terminal` reads as "a non-tmux interactive tty," which is not what a detached
container subprocess is); add it to the enum in W2. Minor — confirm at W2.

**E. `RunnerBackend` vs `VisibilityBackend` composition (touches #208).** #207
delivers visibility-only; the *composition* of a visibility backend with a
sandbox `RunnerBackend` (and which tier owns the subprocess spawn inside a
container) is a #208 integration decision. #207 should keep the headless backend
spawn-mechanism simple (detached local subprocess) so #208 can swap the spawn for
a `RunnerBackend.run()` call without re-litigating the visibility seam. *Note for
#208.*

**F. cgroup / OOM-group interaction.** The sentinel wrapper sits OUTSIDE the
resource-bound `systemd --scope` so it survives an OOM group-kill to write the
`exited` event (`lane_runtime.py:913-918`). The headless backend must preserve
that ordering (wrapper outermost, resource-bound wrap inside) — it already does,
because the launcher builds the bounded+wrapped command *before* handing it to the
backend (`lane_runtime.py:861-930`); the backend only spawns the final argv. *No
change needed, but assert in W2 tests.*

---

## Appendix — primary evidence (verified file:line)

- Visibility gate / refusal: `lane_runtime.py:741-746`; constant `:80`; default param `:622`.
- tmux spawn seam: `lane_runtime.py:891-941`; terminal record `:980-992`.
- `ce launch` parallel seam: `launch_runtime.py:497-505, 581-589`.
- tmux adapter (untouched backend): `tmux_adapter.py` (whole file; `ensure_pane` `:101-177`).
- Pane Registry validator tmux gate: `checks/pane_registry.py:178-223`.
- Pane Registry schema (groundwork): `schemas/pane-registry.schema.yaml:79-89, 134-154`.
- RunnerBackend registry (the pattern to mirror): `runner/backend.py:152-274`.
- Sentinel wrapper (portable witnessability, container-anticipating): `seat_sentinel.py:1-29, 139, 196-`.
- Sentinel wiring at launch: `lane_runtime.py:924-930`; `launch_runtime.py:573-579`.
- Seat lifecycle (terminal-kind-agnostic): `seat_lifecycle.py:436-455`; wiring `lane_runtime.py:1047-1074`.
- Cockpit read-model (tmux-free, events-driven): `runner/cockpit_readmodel.py:631-638, 1374-1387, 1457-1464, 1834-1843`.
- Reaper executor selection (terminal-kind-keyed, container-anticipating): `reaper_executors.py:337-347`.
- Transcript archive (source-agnostic): `transcript_archive.py:1-9, 77`.
- CLI `--no-tmux` (refuse-only today): `ce_cli.py:252-256, 912-916, 1012, 2378`.
- Docs to reconcile (W5): `docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md:16-18, 36, 103-125`; `docs/architecture/seat-sentinel-contract.md`.
- Docs-reconciliation test (guards groups only, untouched): `validators/tests/unit/test_v1_docs_reconciliation.py:52-69`. As-built group inventory (`:54`) = `{lane, ledger, worker, fanin, queue, event, pcl, brain, connector, reviewer-triage, claim, pickup, check, doctor, init, launch, hud}` — #207 adds no group → inventory unchanged.
- Harness seat-contract governance gate (C4, do NOT naively weaken): `checks/harness_seat_contract.py:71, 220`; `print_headless` = Claude `--print` (`claude_launch_spec.py:25, 161`).
- Path-manifest carrier + check: `checks/path_manifest_fidelity.py` (`MANIFEST_DIR=.ce/pr-manifests`, `:468`); format/fields in `tests/unit/test_path_manifest_fidelity.py:27-41`.
- Container-instance groundwork (#208 consumer): `schemas/container-instance.schema.yaml`; `checks/container_instance.py`; pane↔container cross-check `checks/pane_registry.py:321-442`.

### Test files a #207 PR must keep green / extend (from coupling sweep)
- `tests/unit/test_lane_runtime.py`, `test_lane_runtime_reviewer_venue.py`, `test_lane_runtime_resource_bound.py`; `tests/integration/test_lane_launch_tmux.py`, `test_ce_lane_cli.py`.
- `tests/unit/test_tmux_adapter.py`, `test_tmux_adapter_env.py` (must stay byte-green — tmux backend unchanged).
- `tests/unit/test_pane_registry.py`; `tests/integration/test_pane_registry_examples.py`.
- `tests/unit/test_cockpit_readmodel.py` (+ cockpit_journey/board/governance_panel/meters) — assert headless seat renders.
- `tests/unit/test_seat_sentinel.py`, `test_seat_reaper.py`.
- New: `tests/unit/test_visibility_backend.py`.
