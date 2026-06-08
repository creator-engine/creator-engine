# CE v3 — Pilot UI/UX Model

*Curated, redacted design reference (provenance: 2026-06-06 design session). **DESIGNED / pilot-target** — re-ground at the implementing gate. Execution status lives in [`docs/v3-roadmap.md`](../v3-roadmap.md).*

## Surface decision (pilot)
The pilot surface = the Operator's **own agent** (Claude Code / Codex) as the conversational co-pilot + the **`ce` CLI** for explicit commands + **GitHub** as the review/merge surface. **No CE-spawned conversational Controller; the full CE Cockpit is deferred post-pilot.** The earlier tmux / visible-Controller / canonical-line model is the **build harness** (the v2 lane/tmux machinery deleted at D2), NOT the product.

## Requirement: CE must FEEL like CE — even on your own agent
"On your own agent" must NOT mean "indistinguishable from your bare agent." This is a differentiator for **UX and sales/marketing**: CE injects a **branded, structured, stateful, artifact-aware** experience into the dev's agent TUI. Four elements:
1. **CE session frame (you're under CE).** A `ce session` launch banner + a **persistent status line** (CE branding + current workflow stage + work counts); every CE action renders **◆ CE-prefixed**. Always-on "your agent, *under CE*."
2. **A named, staged workflow (where am I).** The user-facing cognitive phases **Frame → Shape → Build → Review → Ship** (canon — see [`stage-vocabulary.md`](./stage-vocabulary.md)), shown in the status line with counts, riding over the **conserved** board/mechanical states (`BACKLOG / SHAPE / READY / RUN / REVIEW / MERGE`) underneath. The dev is never lost.
3. **CE language + the ◆ CE Completion Report.** Per run: **Outcome · Verdict · Next** — the heir to the build-harness completion report, with "CE" in it. Ratification is lightweight (ratify-Scope / merge-PR); the SHA-pinned rigor stays in the plan-approval gate.
4. **Artifact awareness (inspect anything).** The Completion Report (and `ce artifacts <run>`) enumerate every run artifact with locations + inspect commands: PR · Scope · ratification · closed manifest · evidence-chain (verified) · fidelity-tagged action records · run-outcome · spend.

## Mechanism (pilot)
CE = an **MCP tool surface + the `ce` CLI + the session frame/skin**, observed/driven via the scenario transport (CC-hooks/stream-json; ACP post-pilot). The dev's agent calls CE tools; CE returns **branded structured payloads** (stage, completion report, artifacts). No new agent to babysit.

## Literal TUI (illustrative)
```
~/myproject $ ce session
◆ Creator Engine · governed session · repo <owner/repo> · transport cc-hooks · backend gvisor
  stage ▸ FRAME   ·   2 shaping · 1 building · 1 awaiting your review
──────────────────────────────────────────────────────────────────────────
› add rate-limiting to POST /api/login — 100/min per IP, with tests
  ◆ CE · SHAPE → Scope cs-4f2 "rate-limit /api/login"  (Done-when 3 · Budget S · Change-type code · Ready ✓)
  ◆ CE · ratify & dispatch the bet? › yes
  ◆ CE · BUILD r-91a dispatched (boxed · cap S)
       ⚠ escalation — wants to edit .github/workflows/ci.yml (Change-type deploy↑). Allow? › no
  ┌─ ◆ CE COMPLETION REPORT · run r-91a · Scope cs-4f2 ───────────────────────
  │ Outcome    PR opened → #7  (ce-app[bot])
  │ Verdict    Done-when 3/3 met · tests green · in scope ✓ · 14% of Budget S
  │ Next       → Review PR #7  (Change-type code → your approval)
  │ Artifacts  PR #7 · Scope cs-4f2 · ratification · manifest(2 paths)
  │            · evidence-chain ✓verified · 14 action records · outcome record · spend
  │ Inspect    ce show r-91a   |   ce artifacts r-91a   |   gh pr view 7
  └──────────────────────────────────────────────────────────────────────────
  stage ▸ REVIEW   ·   2 shaping · 0 building · 2 awaiting your review
```

## v1 → v3 mapping (the Controller dissolves)
| build harness (today) | pilot (the product) |
|---|---|
| visible Controller agent in a tmux pane | the dev's **own agent** (co-pilot) + the `ce session` frame |
| Controller spawns workers watched in panes | a ratified Scope **dispatches a boxed, headless worker** → a PR; only escalations surface |
| completion report + recommended next step | the **◆ CE Completion Report** + the PR + evidence; the board surfaces what's next |
| ratify by typing a canonical line into the pane | **ratify a Scope / merge a PR** (SHA rigor stays in the plan-approval gate) |
| screen = a tmux session of agent panes | screen = your terminal (your agent) + a GitHub tab |

## Why the shift is deliberate
1. Boxed gVisor agents driven via hooks/ACP are **headless by construction** — no pane to watch (and the watching surface, lane/tmux, is deleted at D2). 2. **"The grader lives outside the agent"** ⇒ you judge **artifacts** (the PR, the manifest-scoped diff, the evidence), not transcripts. 3. **Agent-native** ⇒ CE governs *your* agent's work + the boxed workers — it doesn't hand you another agent to babysit.

## Marketing / trajectory
This branded structured layer **is** the pre-cockpit product identity — what makes "your agent under CE" a distinct product, not your bare agent. It is also the **seed that graduates into the full CE Cockpit** (a mission-control board + cost meter + fleet view; *"ACP makes CE a cockpit"*) post-pilot — same language, same stages, same artifacts, re-rendered visually.

## Companions
[`pilot-roadmap.md`](./pilot-roadmap.md) · [`pilot-deployment-transport.md`](./pilot-deployment-transport.md) · [`agent-interaction-model.md`](./agent-interaction-model.md).
