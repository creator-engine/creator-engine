# CE v3 — Session frame + the unified resource status line (G-7.1)

*Curated design/contract note (provenance: G-7 product-surface build, 2026-06-08).
**BUILT — `creator_engine_validator/v3_session.py` (pure render) + `cev3 session`.**
Companions: [`pilot-uiux-model.md`](./pilot-uiux-model.md) (the surface),
[`stage-vocabulary.md`](./stage-vocabulary.md) (the stage skin),
[`../contracts/spend-envelope.md`](../contracts/spend-envelope.md) (the G-5 spend
projection), and GH #157 (the context meter). Execution status:
the project README's **Current Status** section.*

## What this is

The branded **"your agent, under CE"** session frame: a launch banner plus a
**single, persistent status line** that fuses three signals into ONE
resource/health surface —

1. the canon **stage skin** (`Frame → Shape → Build → Review → Ship`, with counts)
   over the conserved board/spec-lifecycle states — *reused from
   `coordination.project_scope_state` / `COGNITIVE_PHASES`; never a third
   vocabulary*;
2. the **context-window meter** (GH #157); and
3. the **spend meter** (the G-5 `runner.spend_gate.project_spend` projection vs the
   run cap) —

with **boundary-aware** checkpoint / `/clear` nudges.

```
◆ Creator Engine · governed session · repo o/r · transport cc-hooks · backend gvisor · state .ce/state
◆ CE · Frame 0 · Shape 0 · Build 1 · Review 1 · Ship 0  │  ctx 52% ⚠  │  spend $4.5/$5 90% ⚠
◆ CE · context 52% — consider checkpointing soon (save resume state first)
◆ CE · spend at 90% of cap — alert (continue)
```

## The two decisions this note records

### 1. Where the surface lives — **project-level / CE-native** (resolves #157)

A governed CE seat launches with `--setting-sources project`, which loads **only**
the repo's settings and **excludes** the user `~/.claude` settings. Consequently a
user-level `statusLine` is **never loaded by a governed seat** — so the resource
surface cannot live in user settings. CE's surface is therefore **CE-native and
project-scoped**: it ships *with the v3 CLI* (`cev3 session` renders it), not in
user config. This is what makes the meter survive the hermetic governed posture
that #157 flagged.

The context-% is the **harness's authoritative `context_window.used_percentage`**,
**consumed, never recomputed** — the assistant historically guesses high, and the
harness number is the only authority.

### 2. One surface, not two — **unify the context and spend meters**

Context-exhaustion and spend-exhaustion are the same operational concern (a session
resource running out mid-arc), so they share **one** status line rather than two
competing indicators. The spend meter **reuses the G-5 breaker ratios verbatim**
(soft `SOFT_BREACH_RATIO` ≈ 0.8, hard 1.0 of cap) — single source of truth. The
context thresholds are #157's (`warn ≥ 45%` / `urgent ≥ 60%`).

## Boundary-aware nudges

The checkpoint / `/clear` nudge fires **only at a turn/batch boundary** (never
mid-output — an interrupt mid-stream taxes the user even on decline). The **hard**
spend breach is the one exception: it is a governance event and surfaces
immediately. The soft spend alert is boundary-gated like the context nudge.

## Boundary (CI-pure; the LIVE seam is deferred)

`v3_session.py` is the **pure render + threshold + nudge logic**, fed
`(context_pct, spend projection)`. The **live `statusLine`-command tap** into a
running TUI (reading the harness number each turn and wiring the line into the
session) is the **deferred live seam** — exactly as G-4/G-5/G-6 deferred their live
taps. The spend meter folds the **real** G-5 `project_spend` over an evidence spine
today (`spend_meter_from_spine`); only the per-turn context read is injected.

## Standing requirements honored

- **Naming hygiene (G-4.1):** `v3_session` is v3-classified + residue-clean; the
  surface defaults to the neutral `.ce/state` root, never `.hermes/` / `.claude/`.
- **Vocabulary fidelity:** the stage skin derives from the canon dual-mapping
  (`coordination`), conserving the machine — no third vocabulary.
- **v1↔v3 coexistence:** additive; no v1 change.
