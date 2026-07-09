# Daemon vs. Agent-organ: routing rubric for CE factory organs

## 1. Why the distinction matters

Factory organs need a routing rule before implementation. Authority, transport,
token custody, and other mechanics should fail closed and stay token-free.
Judgment should be isolated in bounded agent-organs that propose into a
deterministic disposer.

## 2. Routing rubric

| Axis | Deterministic daemon | Agent-organ |
|---|---|---|
| Primary invariant | Fail-closed; never calls an LLM | Judgment layer; must call an LLM |
| Function type | Authority enforcement, mechanics, transport, token custody | Proposal-only output into deterministic disposer |
| Error model | Hard fail; no output is safer than wrong output | Graceful-degrade on miss; never blocks the skeleton |
| Token budget | Zero; token-free | Token-rationed; Haiku class; bounded per activation |

### 2.1 Deterministic daemons

Deterministic daemons execute mechanics and enforce authority boundaries. They do
not call an LLM. A missing, malformed, or ambiguous input is a hard failure.

Use a deterministic daemon for:

- Authority enforcement.
- Signed carrier production.
- Merge, gate, or queue mechanics.
- Transport, polling, token custody, and ledger disposal.

### 2.2 Agent-organs

Agent-organs perform bounded judgment. They call an LLM and emit structured,
advisory proposals into a deterministic disposer. They do not apply authority,
approve, merge, label, or mutate state directly.

Use an agent-organ for:

- Review judgment.
- Expertise tie-breaks after deterministic policy is exhausted.
- Triage recommendations.
- Summaries or classifications that can be discarded safely.

### 2.3 The four invariants (agent-organs only)

All four invariants must hold. If any invariant is absent, the component is not
an agent-organ; it is an unbounded agent.

| Invariant | Requirement |
|---|---|
| Deterministic trigger | Activation comes from a GitHub event, belt tick, merge-queue state change, or another deterministic event. It never self-schedules. |
| Versioned plain-text policy input | Policy is read from the repository at activation time, for example `AGENTS.md` or `policy/`. Prompts are not hardcoded. |
| Proposal-only output into deterministic disposer | The organ proposes. The daemon or ledger disposes. Grader-outside applies to the organ layer. |
| Token-rationed small-model execution | Execution is Haiku class and bounded per activation. |

## 3. Applied: organ-by-organ classification

| Organ | Classification | Rationale |
|---|---|---|
| Gate daemon | Deterministic daemon | Authority enforcement; fail-closed is non-negotiable. |
| Option A materializer | Deterministic daemon | Authority path that produces signed carriers; wrong output is worse than no output. |
| Reviewer assignment | Deterministic matrix plus optional agent expertise tie-break | The matrix is authority. The tie-break is judgment only when the matrix is ambiguous. |
| Review execution | Agent-organ | Fresh-context per-commit review is judgment and proposes into a deterministic approval gate. |
| Seat-ticket triage | Agent-organ judgment riding the polling belt; advisory disposal into deterministic disposer | Triage is judgment. The belt is the deterministic skeleton. |
| Belt-poller | Deterministic daemon | Polling is transport and mechanics; it stays token-free. |

## 4. Organ hydration contract

Agent-organs access memory through the hydrate contract.

| Source | Contract |
|---|---|
| Authoritative source | Deterministic ledger, always consulted and authoritative. |
| Advisory source | Vector or graph recall, graceful-degrade on miss, never blocks activation. |
| Policy injection | Organ receives a versioned plain-text policy file path at spawn time; prompts are not hardcoded. |
| Dual-store write | SSOT ledger write and advisory recall index write happen in the same commit; neither is optional. |

## 5. Two Steinberger steals — first implementations

Both first implementations use a deterministic skeleton, an ephemeral
agent-organ, advisory structured output, and a deterministic disposer. A human
can override by changing policy; the next activation reads the updated policy.

### 5.1 S1 — AutoReview analog

| Field | Value |
|---|---|
| Trigger | GitHub Actions webhook per commit. |
| Agent work | Review the PR with fresh context for that commit. |
| Output | Structured verdict proposal. |
| Disposer | Deterministic approval gate. |
| Authority limit | The organ never self-approves. |
| Policy | `AGENTS.md` reviewer rubric at HEAD of the PR branch. |
| Token budget | Haiku class; one activation per commit. |

### 5.2 S2 — Triage analog

| Field | Value |
|---|---|
| Trigger | Belt tick with configurable polling interval. |
| Agent work | Read open issues and triage policy. |
| Output | Proposed label and lane assignment. |
| Disposer | Deterministic disposer writes labels through the GitHub API only when confidence is at or above threshold. |
| Policy | `policy/triage-rules.md` at HEAD. |
| Token budget | Haiku class; one activation per batch of up to 20 issues. |

## 6. Governance note

This document is a DESIGN-PREVIEW artifact. It has been HELD for Operator
review before the merge gate is opened. The rubric is ratified as of
2026-07-08; the doc is the governed repo form of the ratification. Do not
implement organ classication changes without first updating this doc and
obtaining Operator sign-off.
