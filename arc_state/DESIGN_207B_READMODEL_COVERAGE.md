# DESIGN 207B — Read-model coverage for a headless *controller*: can it be watched live?

**Author:** CE-DEV-2 worker (research/analysis only) · **Date:** 2026-06-23
**Companion to:** `.ce/state/research/DESIGN_207_VISIBILITY_BACKEND.md` (the headless visibility backend).
**Status:** coverage report + gap-sizing — NO production code, NO PR. Feeds controller dispatch on #207/#208.
**Repo paths cited:** canonical tree `validators/creator_engine_validator/`, `schemas/`.

---

## 0. The question, sharpened

The visibility contract is being re-stated: a controller/lane emits its **live state**
to the canonical read-model (L2); any renderer (CE TUI, WebUI, App, comms channel)
renders that. "Headless" = "no tmux renderer, but fully visible via the
read-model/control-plane," NOT "dark."

This doc answers the crux #207's headless backend leaves open: **does the read-model
+ existing `ce` inspectors actually render a LIVE controller's *work* today — its
commands, tool calls, output stream — or only its lifecycle/governance?** If we flip a
governed *controller* headless right now, can an operator still watch what it is doing
through the control plane, or must we close a coverage gap first?

Granularity is scored in three tiers:
- **(a) lifecycle** — spawned / exited / claim / terminal_state (live/exited/unknown).
- **(b) governance** — decisions, refusals, posture, reviewer identity, spend, escalations.
- **(c) live-work-stream** — the agent's *ongoing work*: commands it runs, tool calls,
  stdout/stderr, current activity, progress. **This is what a tmux pane shows live and is
  the entire crux of "can a headless controller be watched."**

---

## 1. Coverage map — inspection surfaces × what live-state each captures

| Surface | file:line | (a) lifecycle | (b) governance | (c) live-work-stream | Notes |
|---|---|:--:|:--:|:--:|---|
| **Seat sentinel `events.jsonl`** | `seat_sentinel.py:64-68`; schema `seat-event.schema.yaml:45-58` | ✅ `launched`/`exited` | ⚠️ `outcome_resolved` only (terminal outcome) | ❌ | Closed enum; `progress`/`heartbeat` **RESERVED but UNEMITTED** (`seat_sentinel.py:67-68`, schema `:56-58`). **Value-free by law** — carries `command_sha256` *digest*, NEVER command text (`seat_sentinel.py:101-104`). No output, no tool calls. |
| **Pane Registry record** | `lane_runtime.py:964-1012`; schema `pane-registry.schema.yaml` | ✅ `status` (starting/active/blocked/exited), `last_seen_at` | ⚠️ `role`, `envelope_ref` | ❌ | Durable claim-bound identity. A static record, re-read on demand — not a stream. |
| **Seat lifecycle record** | `seat_lifecycle.register_spawn`, `lane_runtime.py:1047-1074`; `seat_lifecycle.py:436-455` | ✅ spawn + terminal-kind-agnostic | ❌ | ❌ | Terminal-kind-agnostic already; pure spawn fact. |
| **Governance sidecar JSON** | `lane_runtime.py:1014-1040` | ❌ | ✅ CC-G-D audit, `events_ref`, reviewer-venue identity, harness | ❌ | Authorization posture, not activity. |
| **Refusal chain / observations** | `cockpit_readmodel.py:813-841, 1696-1702`; `refusal-chain.yaml` | ❌ | ✅ `op`, `classification` (denied/escalate/allowed), `decision_reason` (G-clause), hash-chain verify | ❌ | Records governance *decisions* as they happen — but only at refusal/decision points, not continuous work. |
| **Runtime-evidence chain** | `runs/*.runtime-evidence.yaml`; folded `cockpit_readmodel.py:1718-1743, 886-936` | ✅ run outcome | ✅ agent-action classifications | ⚠️ **collapsed post-hoc** | The closest thing to (c): `_stream_groups` projects `op`/`target`/`tool`/`classification` spans with retry counts. But this is a **collapsed summary of structured records the agent/hooks wrote**, not a live byte stream — and it depends on records being appended to the chain. No stdout/stderr, no command text, no tool *results*. |
| **v3 cockpit read-model (L2)** | `runner/cockpit_readmodel.py` (whole) | ✅ seats/dispatches/seat_events | ✅ governance matrix, escalations, spend banners | ❌ (only the collapsed evidence stream above) | **PURE fold** of structured state (`cockpit_readmodel.py:1-31`). Reads `events.jsonl`, pane registry, chains, escalations, refusals, claims, sidecars. **Reads NO `.log`, NO `capture-pane`, NO transcript bytes, NO stdout/stderr.** |
| **`ce cockpit` TUI / `--json` / `--serve`** | `v3_cli.py:3450-3515` | ✅ | ✅ | ❌ | Renders the L2 snapshot. `--watch` **re-folds the snapshot from disk on file change** — a fresh structured snapshot each reload, NOT a tail of live output. |
| **`ce lane status`** | `ce_cli.py:1074-1086`; `lane_runtime.py:1114-1132` | ✅ static `status`/`terminal`/`session`/`pane` | ⚠️ `role` | ❌ | One-shot read of the static Pane Registry record. Prints a one-line `summary`. Not a stream. |
| **`ce hud`** | `ce_cli.py:994` | — | — | — | Explicitly **"alias/seam label for `ce launch` (not a CE-native TUI)."** Not an inspector at all. |
| **`ce lane verify`** | `ce_cli.py:1089-1106`; `lane_runtime.py:1140-1183` | — | — | ❌ | **Post-hoc** stop-line check on an operator-**supplied** `--transcript` file. Does not capture live; consumes a finished file. |
| **Transcript archive** | `transcript_archive.py:41-91` (`shutil.copyfile`, `:77`) | — | — | ❌ | Post-hoc **byte copy of a finished, caller-supplied** transcript path. Source-agnostic; no live capture, no tail. |
| **`tmux capture-pane`** | `v3_seat_bridge.py:708-713` | — | — | ⚠️ live pane read, but **not for the operator** | The ONLY live-pane read in the tree. Scans the bottom ~region for the prompt box to drive **idle-detection/auto-drive pacing** (`_looks_idle`, `:740`). Never persisted, never surfaced to an operator or read-model. tmux-only. |
| **Operator-notify feed** | `runner/notify_feed.py` | — | ✅ AWAITING-OPERATOR entry/exit edges | ❌ | The contact-on-need channel layer (see §4). Fires only on escalation edges. |

**The whole right-hand column is empty** except (i) the collapsed runtime-evidence
stream (structured, post-hoc, depends on the agent/hooks writing records), and (ii) the
tmux `capture-pane` that exists solely for auto-drive timing and is never surfaced.

---

## 2. Verdict on the crux

**NO. A headless controller cannot be watched *live at the work-stream layer* through
the read-model today.** Flip a governed controller headless right now and an operator
would still see, via the control plane:

- **lifecycle** — it launched, it is `active`/`blocked`/`exited`, its pid/exit_code
  (`events.jsonl` + Pane Registry, rendered by `ce cockpit` / `ce lane status`); and
- **governance** — its refusals, its envelope/authority matrix, its escalations, its
  spend banners, a collapsed action-classification stream from the evidence chain.

But the operator would **lose the entire (c) live-work-stream** — the moment-to-moment
commands, tool calls, and stdout/stderr that a tmux pane renders today. The cause is
structural, not incidental:

1. **The sentinel emits no work events.** `EVENT_KINDS` is the closed set
   `{launched, exited, outcome_resolved}`; `progress`/`heartbeat` are reserved and
   unemitted (`seat_sentinel.py:67-68`). And it is **value-free by design** — the launch
   event carries `command_sha256`, never the command text (`seat_sentinel.py:101-104`).
   The sentinel is a lifecycle supervisor, not a work tap.
2. **No stdout/stderr is captured anywhere today.** `build_wrapper_script` runs the inner
   command as a foreground child with **no redirection** — output goes to the pane tty and
   is ephemeral (`seat_sentinel.py:184-185`). There is no `headless.log` in the tree (that
   string appears only in the #207 *proposal*). The tmux pane buffer is the *only* place
   the live work-stream exists, and it dies with tmux.
3. **The read-model reads only structured state.** `cockpit_readmodel` is a pure fold of
   `events.jsonl` + pane registry + chains + escalations + refusals; it reads **no `.log`,
   no `capture-pane`, no transcript bytes** (`cockpit_readmodel.py:1-31`, input seams
   `:1718-1888`). `--watch` re-folds that structured state — it is not a live tail.
4. **No CE code tails a harness transcript.** Claude Code writes
   `~/.claude/projects/.../*.jsonl`, but CE only ever consumes a transcript **post-hoc**
   (archive byte-copy `transcript_archive.py:77`; `ce lane verify` stop-line check on a
   supplied path). Nothing reads it live.

**Caveat that softens "dark," but does not close the gap:** the runtime-evidence chain
+ refusal chain give a *near-real-time, structured* picture of governance-relevant
actions (each tool op's `op`/`target`/`tool`/`classification`, refusals with clauses) —
which is arguably the *governance-relevant* slice of (c). For a CEO-mode operator who
wants "is it behaving / what did it touch / does it need me," that is already
substantial and renders fine headless. What is missing is the **raw, continuous
work-stream** (command text, output bytes, the "watch it think" pane). For #207's
acceptance — a visibility-required lane LAUNCHED with an operator-inspectable record —
this is satisfied (the record + events.jsonl exist). For the *richer* claim "an operator
can watch a headless controller work like a tmux pane," it is **not**.

---

## 3. Gap-closing work — what a headless *controller* needs to be fully observable

The #207 backend (DESIGN_207) already gives headless a Pane Registry record + an
`events.jsonl` lifecycle + a captured `headless.log` surface. That clears the
**visibility-contract** bar (lifecycle + governance are renderable headless today, no new
work). The gap is purely the **(c) live-work-stream**. Sizing:

**Does controller-headless ship WITH #207?** — Decompose:
- **Headless *worker lanes* ship with #207 as-is.** Workers already produce
  governed evidence chains + refusal records; the operator's "live watch" of a worker is
  a CEO-mode retrospective (forge artifacts + escalations), and the §5.A/§5.G governance
  ruling (DESIGN_207) — not a read-model gap — is what gates them.
- **Headless *controllers* clear the *contract* with #207** (LAUNCHED + inspectable
  record), but to be **watchable like a tmux controller** they need ONE read-model-emission
  PR first. A controller's value to an operator is precisely its live driving activity;
  shipping it headless *without* a work-stream surface is the part that would feel "dark."

**Read-model-emission PR-units (each ~200-400 lines, the band DESIGN_207 uses):**

- **G1 — `headless.log` becomes a read-model input + a `tail`/follow inspector.**
  ~250-350 lines. Have `cockpit_readmodel` (or a sibling loader) optionally read the
  per-seat `headless.log` `surface_log_ref` from the Pane Registry terminal record, and add
  a `ce lane logs --follow <controller>/<lane>` (or `ce cockpit --logs`) that tails it.
  This is the **minimal** "watch a headless seat work" surface and the smallest unit that
  turns the #207 raw capture into an operator-renderable live stream. *Depends on #207-W2
  (the headless.log capture) landing first.* **This is the one PR controller-headless should
  ship behind.**

- **G2 (optional, richer) — emit `progress`/`heartbeat` sentinel events.** ~200-300 lines.
  Activate the already-reserved `progress`/`heartbeat` enum (`seat_sentinel.py:67-68`,
  schema `:56-58`) so the read-model can render liveness/last-activity without parsing log
  bytes — useful for a structured "is it alive and moving" badge that `--watch` folds
  cheaply. **Keep value-free** (no command text/output in the event) to preserve the
  ps-leak/secret-hygiene law; this is a *liveness* signal, not the work content. Composes
  with G1, not a substitute for it.

- **G3 (optional, structured stream) — promote the harness transcript to a first-class,
  governed live tail.** Larger (~400+ lines, may exceed band → split). A loader that tails
  the harness `*.jsonl` (Claude Code / codex) into a value-screened, read-model-shaped event
  stream. This is the *highest-fidelity* (c) surface (you see tool calls/results as the
  agent emits them) but carries the most secret-hygiene + schema work; defer past #207 unless
  the Operator wants pane-parity. The collapsed runtime-evidence stream
  (`cockpit_readmodel.py:886-936`) is the cheaper structured approximation already shipping.

**Recommendation:** ship **headless workers with #207**; ship **headless controllers behind
G1** (one read-model-emission PR: log-as-input + `--follow` inspector). G2 is a cheap
liveness nicety; G3 is the pane-parity stretch, post-#207. Net: controller-headless does
**not** ship inside #207 — it needs **one** read-model-emission PR (G1) so the live-work
surface exists, *plus* the §5.A/§5.G governance ruling from DESIGN_207 that lets a governed
*controller* seat-contract declare an inspectable-headless posture.

---

## 4. Channel-emission layer (strangeLoop / CEO-mode surface)

Most users want **contact-on-need + retrospective audit via forge artifacts**, NOT live
watching. CE already has the spine for this.

**What exists today — `runner/notify_feed.py`** (Operator-notify feed, ce-ops#31):
- A **pure edge-detection fold** over the AWAITING-OPERATOR escalation queue:
  `fold_notify_feed(escalations, ledger, config)` emits `awaiting_operator_entry` /
  `awaiting_operator_exit` events (`notify_feed.py:259-346, 66-71`). This is exactly the
  "need-your-input" / "resolved" contact-on-need signal.
- **Pluggable sinks** (`notify_feed.py:81-92, 453-506`): a `desktop` sink (`notify-send`)
  and a generic **`exec` sink** that invokes a user-supplied **argv list (no shell, no
  injection surface)** with the **event JSON on stdin** (`dispatch_exec`, `:475-493`).
- **Confidential-by-default payload shaping** (`shape_payload`, `:231-256`): off-host sinks
  default to `pointer` (id + class + source_ref, **no prose**); local desktop gets `full`.
- **At-least-once delivery** with a durable, notifier-private NDJSON ledger and idempotent
  re-fold by `(escalation_id, event_kind, sink_id)` (`notify_feed.py:14-24, 513-566`).

**This is already a Discord/Slack/NanoClaw-capable channel layer for need-your-input.**
A Discord/Slack webhook is a one-line `exec` sink today: configure `kind: exec, argv:
[curl, -X, POST, ...webhook...]` and the event JSON is piped to it. No code change needed
for **contact-on-need** to reach a comms channel — only an `exec` adapter script. The
`reports/status` retrospective is **already** the forge artifacts (PRs, evidence chains,
transcripts) per the CEO-mode doctrine — the audit trail is the forge.

**What is missing for the fuller channel ask:**
1. **A native webhook sink kind.** Today off-host delivery rides the generic `exec` sink
   (you bring the `curl`). A first-class `kind: webhook` (URL + content-type + payload
   shape) would make Discord/Slack/NanoClaw a config line, not a shell script. ~200-300
   lines, additive — fits the `_VALID_SINK_KINDS` frozenset + `_dispatch_event` switch
   (`notify_feed.py:83, 496-506`). **The right home for the channel-emission layer.**
2. **More event kinds than escalation edges.** The feed only folds AWAITING-OPERATOR
   entry/exit (`notify_feed.py:66-67`). To emit periodic **reports/status** ("seat finished,
   PR #N opened", "spend at 60%", run-outcome) it needs to fold additional read-model
   sections (run outcomes from the evidence chain, spend banners from `_fold_meters`). The
   read-model **already projects** all of these (§1) — the gap is a fold that turns
   read-model deltas into notify events, not new capture. ~250-350 lines.
3. **An opt-in live ascii/event stream to a channel.** This rides on **G1/G3** above (a
   live `headless.log` / transcript stream) plus a streaming sink. There is **no** live-tail
   sink today (the notify feed is edge-triggered, not streaming). This is the
   "watch it in Discord" premium surface; it is gated on the §3 live-work-stream gap being
   closed first. Build order: §3 (capture/emit live work) → then a streaming channel sink.

**Net for the channel layer:** the **contact-on-need + retrospective** surface most users
want is **buildable today** on `notify_feed.py` — a webhook sink kind (item 1) + a
read-model-delta→notify-event fold (item 2) are two small additive PRs, no new capture. The
**live-stream-to-channel** surface (item 3) is the premium tier and depends on §3's
live-work-stream gap closing first. This matches the doctrine: sell contact-on-need +
forge-audit; live watching is opt-in/premium.

---

## 5. Risks / escalations for the Operator

- **R1 — "Headless ≠ dark" is true for lifecycle+governance, NOT yet for live-work.**
  If the headless-controller story is pitched as "fully visible via the control plane,"
  be precise: lifecycle + governance + a *collapsed* action stream render headless today;
  the *raw live-work-stream* (tmux-pane parity) does **not** until G1 (and G3 for full
  fidelity). Recommend framing headless-controller GA as gated on **G1**, and treating
  pane-parity (G3) as explicitly post-#207. *Decision: does controller-headless GA require
  G1, or is governance+lifecycle+collapsed-evidence "visible enough" for the first cut?*

- **R2 — Governance gate (C4 / DESIGN_207 §5.A,§5.G) still binds controllers.** Even with
  G1's read-model surface, `checks/harness_seat_contract.py:71,220` refuses a non-
  `operator_visible` controller seat-contract posture. A headless *controller* needs the
  Operator's §5.A/§5.G ruling that "operator_inspectable" is a sanctioned `terminal_visibility`
  token. **The read-model gap (G1) and the governance gap (C4) are independent and BOTH must
  close** for a governed controller to run headless. *Escalate the C4 ruling — it is the
  harder gate.*

- **R3 — Secret hygiene on any (c) surface.** Every new live-work surface (headless.log
  capture, progress events, transcript tail, channel stream) crosses the value-free
  invariant the sentinel guards (`seat_sentinel.py:101-104`; DESIGN_207 §5.D). The current
  spine leaks nothing (digests only); a log/transcript stream is the first surface that can
  leak command text/secrets/output. Each G-unit and the streaming channel sink **must** carry
  a redaction/screening gate + a test asserting injected env/secret values never reach the
  surface. *Make this a standing acceptance criterion on G1/G2/G3 and item-3.*

- **R4 — Don't overbuild live-watching against the doctrine.** The CEO-mode/strangeLoop
  doctrine says most users want contact-on-need + forge-audit, not live watching. Recommend
  ordering: **(1)** webhook sink + read-model-delta fold (§4 items 1-2, cheap, high-value,
  doctrine-aligned) **before** **(2)** the live-stream surfaces (§3 G1/G3 + streaming sink).
  Live watching is the premium/opt-in tier, not the default path. *No escalation — a
  sequencing recommendation.*

---

## Appendix — primary evidence (verified file:line)

- Sentinel closed enum (no work events): `seat_sentinel.py:64-68`; schema `seat-event.schema.yaml:45-58`.
- Sentinel value-free (digest not text): `seat_sentinel.py:101-104`.
- Wrapper no stdout/stderr redirection: `seat_sentinel.py:184-185` (`build_wrapper_script`).
- cockpit read-model purity + input seams: `cockpit_readmodel.py:1-31, 1718-1888`.
- Collapsed action stream (the partial (c)): `cockpit_readmodel.py:886-936`; chains `:1718-1743`.
- Governance/refusal/escalation/spend folds: `cockpit_readmodel.py:737-758, 813-841, 1102-1132, 1286-1308, 1647-1702`.
- `ce cockpit` (TUI/--json/--serve, re-fold not tail): `v3_cli.py:3450-3515`.
- `ce lane status` (one-shot static record): `ce_cli.py:1074-1086`; `lane_runtime.py:1114-1132`.
- `ce hud` = alias, not a TUI: `ce_cli.py:994`.
- `ce lane verify` post-hoc stop-line: `ce_cli.py:1089-1106`; `lane_runtime.py:1140-1183`.
- Transcript archive (post-hoc byte copy): `transcript_archive.py:41-91, 77`.
- Only `capture-pane` = auto-drive timing: `v3_seat_bridge.py:708-713, 740`.
- Notify feed (channel layer): `runner/notify_feed.py:14-24, 66-92, 231-256, 259-346, 453-506, 513-566`.
- Governance seat-contract gate (C4, binds controllers): `checks/harness_seat_contract.py:71, 220`.
- #207 backend companion (visibility contract, C4 §5.A/§5.G, headless.log proposal): `.ce/state/research/DESIGN_207_VISIBILITY_BACKEND.md`.
