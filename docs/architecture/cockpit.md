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
  the spine. The Cockpit **writes no governance state**.
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

## `CE_DEMO=1` (the seeded demo board)

One flag swaps the data source for a seeded, schema-true, hash-chain-verified
fleet telling the grader-outside story: a populated five-column board with one
seat **refused a `git push`** by the deploy boundary (attribution visible), an
envelope-scope denial, a spend hard-breach pause, and a reviewer seat with a
clean `verify_chain()` badge. A persistent **"DEMO — seeded data, not a live
fleet"** watermark renders the honesty tier — a pitch demo is never mistaken
for live governance.

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
