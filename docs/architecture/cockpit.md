# CE v3.5-B — The Cockpit (the LIVE governed-fleet surface)

*Build-input doc for the v3.5-B Cockpit arc. Supersedes this file's earlier
"post-pilot graduation — NOT a deliverable" framing (provenance: the 2026-06-08
design session, landed #165): the Operator ratified the v3.5-B arc on
2026-06-09, and the Cockpit is now a LIVE build lane. Design-of-record: the
v3.5-B Cockpit design (CE-Cockpit-B-Architect, 2026-06-09 — an Operator-held
reference report) plus the ratified B.1–B.7 gate cluster (2026-06-09). Execution
status lives in [`docs/v3-roadmap.md`](../v3-roadmap.md). Vocabulary canon:
[`stage-vocabulary.md`](./stage-vocabulary.md).*

## What the cockpit is

The Cockpit is CE's first **visible governance/operations surface** — a
mission-control board where the Operator watches a fleet of governed seats, and
where "the grader lives outside the agent" becomes something you can *see*:
a standing capability envelope, a live feed of what an agent was **REFUSED**,
and who ratified the boundary. It is **observation + request + visible
authority — never a new authority and never a gate bypass**: it can display and
it can request; it can never authorize, never expand an envelope, never
self-approve, never bypass branch protection.

## The L1/L2/L3 contract (principle 6 — the HARD law)

Three layers; the split is enforced by tests, not convention:

- **L1 — source of truth (read-only to the Cockpit):** the hash-chained
  runtime-evidence chains under the v3 local-state root (`.ce/state/
  <run_id>.runtime-evidence.yaml`), the Scope artifacts
  (`.ce/state/scopes/*.scope.yaml`), the v1 instance-local pane/claims registry
  and hook-observation log (reached ONLY via the launch-pinned environment
  seams `CE_LEDGER_ROOT` and `CE_HOOK_OBSERVATIONS_DIR` — v3 code never embeds
  the v1 state-root names), envelope artifacts, and the spend-ledger records on
  the spine, local escalation records (`.ce/state/escalations/*.yaml`), and G1
  dispatch records (`.ce/state/dispatches/*/dispatch.yaml` plus sibling runtime
  policies). The Cockpit **writes no governance state**.
- **L2 — the pure projection/read-model** (`runner/cockpit_readmodel.py` — this
  IS the harness-paper **F1** "read-only Deep-Telemetry projection"): one pure,
  JSON-serializable snapshot fold over L1. ALL board/refusal/envelope/meter
  computation lives here, NEVER in a Textual widget callback. `ce cockpit
  --json` dumps the snapshot with `textual` never imported — the future-GUI
  seam as a first-class invocation.
- **L3 — the Textual view** (`v3_cockpit.py`): binds to L2 snapshots and
  renders; nothing else. A future full GUI (web / Tauri / Electron / native)
  replaces L3 only. The TUI and a future GUI may coexist long-term.

## The module family (one coherent set; F1 is not a separate track)

| Module | Layer | Gate |
|---|---|---|
| `runner/cockpit_readmodel.py` | **L2 — THE F1 core** | B.1 (extended B.2–B.5, B.7) |
| `runner/cockpit_demo_seed.py` | L1-shaped seed data (pure constructor) | B.1 |
| `v3_cockpit.py` | L3 — the Textual app | B.1 (extended B.2–B.6) |
| `runner/cockpit_dispatch.py` | the request-execution edge | B.5 (later) |
| `runner/cockpit_insights.py` | the F1 aggregate-telemetry extension | B.7 (later) |

## The board = the stages

Columns are `Frame · Shape · Build · Review · Ship` — the canon presentation
skin derived via `coordination.PHASE_BY_STATE` over the conserved Scope
`state` projection; cards are **Scopes**; never a third vocabulary. A blocked
card surfaces *why* (a refusal or a spend breach) inline — the grader-outside
twist no cooperative-verification competitor can show.

## Live feeds in snapshot version 2

`snapshot_version: 2` adds two first-class, JSON-serializable L2 feeds:

- **`escalations`** — the AWAITING-OPERATOR queue. Records live one per file at
  `.ce/state/escalations/<escalation_id>.yaml`, validate against
  `schemas/escalation-record.schema.yaml`, and carry only value-free decision
  metadata: title, decision needed, required recommendation, timestamps, and an
  optional `source_ref`. Open items sort oldest-first and render at the top of
  the governance rail. This is the machine guard for ce-ops#10: an
  awaiting-Operator marker must not rot invisibly in prose.
- **`dispatches`** — the local G1 dispatch read-model. The loader reads
  `.ce/state/dispatches/*/dispatch.yaml` and best-effort reads the sibling
  `runtime-policy.yaml` to surface the run-scope spend envelope. State is
  derived only from stamps: `assembled`, `spawned`, `collected`, or `failed`
  when `spawn_failed_at` is present. Failure-stamped spawns are shown
  distinctly and never project a Scope as live Build/RUN.

Both feeds follow the existing honesty-tier rule: absent directories produce
`availability.<feed> = "unavailable"` with empty entries; reachable empty
directories produce `ok` with zero entries. `ce cockpit --json` and `--serve`
receive the whole snapshot automatically; the Textual view only renders these
sections from snapshot data.

## Escalation sync edge

`ce escalation open` and `ce escalation resolve` write local escalation records.
`ce escalation sync --repo <owner/repo> [--label awaiting-operator]` is the only
forge mirror edge: it runs `gh issue list` at the CLI boundary, projects the
JSON payload to escalation records, validates every planned record, then writes
all-or-nothing. A non-zero `gh` exit, unparsable JSON, or malformed issue body
refuses with zero partial writes. The Cockpit fold never calls `gh`, polls a
forge, or performs network I/O.

## Operator alerting (v3.1-B.8 — the notify feed)

The Cockpit makes the AWAITING-OPERATOR queue *visible*; the **notify feed**
(`runner.notify_feed`) makes it *announce itself*, so the queue no longer depends
on someone watching a screen. It is a delivery layer over the same escalation
records — not a queue, not a cockpit-UI change, not a Ring-1/governance-authority
change.

**The ledger-as-memory adjudication.** Entry/exit are file-state transitions
(`escalations/*.yaml` appears; `resolved_at` appears) that no component observes
as *events* — open-ness is recomputed statelessly per fold, and the L2 fold is
pure by hard law. The edge-detection memory therefore lives in a **durable,
append-only, notifier-private delivery ledger**, `<root>/notifications/ledger.ndjson`,
owned by the `cev3 notify` composition root. Detection itself stays a **pure fold
of two L1-shaped inputs** — `fold_notify_feed(escalations, ledger_records, config)`
— with delivery identity `(escalation_id, event_kind, sink_id)`, so it is
idempotent across restarts and re-folds by construction (no clock cursor, no
consecutive-snapshot diffing). An entry is pending iff the escalation is open and
no successful entry delivery is recorded; an exit is pending iff it is resolved,
an entry *was* delivered, and no exit delivery is recorded (resolved-before-ever-
notified pings nothing). This is not a purity violation: the ledger is *delivery*
state, not *governance* state — the notifier appends only to its own
`notifications/` subdir, REUSES `cockpit_readmodel.load_escalations`, and never
touches `escalations/`, `scopes/`, chains, or the pane registry. Clearing falls
out of the same mechanism: resolution IS the clear (the exit event), and the
delivered-entry record permanently blocks re-alerting — no separate ack store, no
stale alerts.

**Config** (`<root>/notify.yaml`, instance-local beside `scopes/`/`escalations/`).
Absent ⇒ working defaults (one `desktop` sink, both classes `immediate`).
Malformed-but-present ⇒ a LOUD refusal (exit 2) with the reasons — never a silent
fallback, because a half-applied alerting config is a missed alert wearing a green
light. Per-class dial is `immediate | off`; `digest` is a reserved enum the
validator refuses loudly (it ships with the #28-M2/email rung).

```yaml
kind: notify-config
schema_version: "1"
classes:
  ratify-needed: immediate   # immediate|off ("digest" refused until shipped)
  clear: immediate
sinks:
  - id: desktop
    kind: desktop
    payload: full            # local D-Bus transport — content stays on host
  - id: ntfy-tailnet
    kind: exec
    argv: ["curl", "-fsS", "-d", "@-", "http://ntfy.tailnet:8080/ce-operator"]
    payload: pointer         # confidential-by-default off-host
```

**Sink contract.** `desktop` shells `notify-send` (`critical` urgency for
`ratify-needed`, `normal` for `clear`). `exec` invokes a user-supplied **argv
list** (never a shell string — no injection surface) with the event JSON on the
child's stdin; it covers ntfy/email/Telegram/tailnet-webhooks without CE shipping
or vouching for any one integration. Delivery is **at-least-once,
deliver-then-record**: a duplicate ping is benign, a lost AWAITING-OPERATOR alert
is the exact failure this layer exists to prevent. A failed sink is recorded
`ok: false` and stays pending (retried next tick); it never crashes the loop.

**Payload modes** (`payload: pointer | full`). `pointer` carries only
`event`/`class`/`escalation_id`/`created_at`/`source_ref`/`open_count` — no
title, decision text, recommendation, or hostname (the value-free off-host shape).
`full` adds the prose fields. Defaults: `desktop = full` (local transport, content
never leaves the host), `exec = pointer` (CE cannot see where the command forwards
— confidential-by-default).

**Surface.** `cev3 notify once` is a single fold→dispatch→record pass (the
cron-able, testable primitive); `cev3 notify watch [--interval 30]` is the poll
loop; `cev3 notify status [--json]` is pure-fold counts with no dispatch. Both
`once` and `watch` accept `--sync-repo <owner/repo> [--sync-label awaiting-operator]`
to mirror forge escalations (REUSING the existing `escalation sync` legs) before
folding — the cross-host fan-in — with sync failure tolerated so forge downtime
never blocks local alerting.

## `CE_DEMO=1` (the seeded demo board)

One flag swaps the data source for a seeded, schema-true, hash-chain-verified
fleet telling the grader-outside story: a populated five-column board with one
seat **refused a `git push`** by the deploy boundary (attribution visible), an
envelope-scope denial, a spend hard-breach pause, and a reviewer seat with a
clean `verify_chain()` badge. The demo also includes an open hard-breach
Operator escalation, a resolved escalation, a spawned dispatch, and a collected
dispatch. A persistent **"DEMO — seeded data, not a live fleet"** watermark
renders the honesty tier — a pitch demo is never mistaken for live governance.

## Meters and honesty tiers

The unified resource/health strip (B.4) reuses the shipped D.0.3/G-5/G-7
projections (`fleet_spend_meter`, `fleet_token_rate`, `context_meter`) —
re-implementing nothing — and badges every tile `MEASURED | ESTIMATED |
UNAVAILABLE`. An estimate is never rendered with measured-grade authority; the
subscription-headroom tile ships as a labelled ESTIMATED placeholder until its
estimator lands.

## Transport and posture

Daemonless: `ce cockpit` is a process you run; `--serve` (B.6) is an on-demand
127.0.0.1-only, token-gated subprocess serving the *same* Textual app to a
browser. Runs are headless; every agent permission-request routes through the
external gate; only **escalations + bet-ratifications + reviews** surface to
the human. The Operator is a mission controller working a queue — not a
babysitter watching panes.

## Pairs with CEO mode (still later)

The Cockpit remains the natural home of **CEO mode** (a fleet over a ratified
backlog). CEO mode, the ACP/Tier-A adapter, and the durable Skill axis stay
post-pilot; the Cockpit no longer waits for them.
