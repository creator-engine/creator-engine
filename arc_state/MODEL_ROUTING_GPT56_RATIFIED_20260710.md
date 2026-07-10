# FLEET MODEL ROUTING — GPT-5.6 ADOPTION — OPERATOR-RATIFIED 2026-07-10
# Ratified verbatim in the supervising session ("your recs are approved as written" with one
# modification: test terra-high BEFORE any xhigh decision). Executor: main VPS controller.
# Context: OpenAI shipped the GPT-5.6 family 2026-07-09 (Sol $5/$30 · Terra $2.50/$15 ·
# Luna $1/$6 per 1M in/out). Seats currently run gpt-5.5 high.

## Ratified routing table

| Tier | Model · effort | Applies to |
|---|---|---|
| Seat default | **gpt-5.6-terra · high** | All contained seats + dev-1, all implementation units |
| Escalation | **gpt-5.6-sol · medium** | Authority-adjacent code only (gate/broker/wall/signing surfaces), controller-approved per unit; Sol's own guidance: start at LOWER efforts |
| Agent-organs / verify | **gpt-5.6-luna** | Mechanical/advisory organs per the daemon-vs-agent rubric token-rationing: PV routine adjudication, triage organ, verify-class chores (codex-side analog of Haiku=verify-only) |
| ⏸️ Deferred | terra · xhigh | NOT adopted yet — decide only AFTER the terra-high canary reads out; then one comparative unit vs sol-medium before codifying the escalation rule |

## Canary discipline (required before fleet flip)
1. Canary = the dev-4 relaunch (already in flight — launch it on terra-high) or dev-3 if
   sequencing prefers; ONE seat, ONE arc.
2. Measure against this week's gpt-5.5-high baseline from the arc ledgers:
   (a) preflight-green rate on first READY, (b) review-bounce count per unit,
   (c) corrective round-trips per unit. Pool burn per unit is the bonus metric.
3. Green after one arc → flip the fleet default; update seat launch configs + the
   model-effort routing policy memory as ONE unit (policy memory and configs must not drift).
4. Any regression → revert canary seat to gpt-5.5 high, report to Operator, hold.

## Rationale (one line each)
- Seats' binding constraint is the shared weekly subscription pool (at ~20%, resets Jul 14);
  Terra ≈ 5.5-quality at ~half burn = ~2x units/week at equal quality.
- Sol = escalation, not default: pays its 2x premium only where a review bounce costs more
  than the model delta.
- Luna fills the codex-side small-model gap the rubric requires for event-fired organs.
- Live datapoint: terra-high executed the PV research (40 primary sources, correct source
  hedging) in <5 min on day one.

## Codex CLI update (same window — Operator-directed)
Latest is 0.144.1 (fleet on 0.144.0). All devs are at stop-points NOW — update in this window:
- dev-1 (VPS host): update its codex install (npm global or vendored binary — check which).
- dev-3 / dev-4 (contained): update per the seat-image/native-binary path — dev-3's launcher
  uses CE_VPS_CODEX_BIN standalone binary (the npm package vendors it: node_modules/@openai/
  codex/vendor/<arch>/); dev-4 per its runsc launch canon. If image rebuild is required,
  fold into the dev-4 relaunch already in flight rather than a second relaunch.
- DGX host codex: already updated to 0.144.1 by the supervising session.
- Verify each with `codex --version` + one `codex -m gpt-5.6-terra exec "say ok"` smoke.
