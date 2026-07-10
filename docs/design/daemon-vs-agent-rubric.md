# Daemon vs. Agent-organ: routing rubric for CE factory organs

**Status:** DESIGN-PREVIEW proposal held for Operator review. This document
does not ratify policy, authorize implementation, or change current runtime or
gate behavior. Statements labeled "proposed" below are future design; cited
repository contracts and runtime behavior are current constraints on that
proposal.

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
| Versioned plain-text policy input | Policy is read from an explicitly trusted ref and bound by content digest at activation time. Governance, reviewer, security, or authority policy must come from a ratified control-plane or trusted base ref; candidate policy edits are reviewed input, never the policy governing their own review. Prompts are not hardcoded. |
| Proposal-only output into deterministic disposer | The organ proposes. The daemon or ledger disposes. Grader-outside applies to the organ layer. |
| Token-rationed small-model execution | Execution is Haiku class and bounded per activation. |

## 3. Applied: organ-by-organ classification

| Organ | Classification | Rationale |
|---|---|---|
| Gate daemon | Deterministic daemon | Authority enforcement; fail-closed is non-negotiable. |
| Option A materializer | Deterministic daemon | Authority path that produces signed carriers; wrong output is worse than no output. |
| Reviewer assignment | Deterministic matrix plus optional agent expertise tie-break | The matrix is authority. The tie-break is judgment only when the matrix is ambiguous. |
| Review execution | Agent-organ | Fresh-context per-commit review is judgment and proposes evidence into a deterministic disposer; any authorized approval decision is separate. |
| Seat-ticket triage | Agent-organ judgment riding the polling belt; advisory disposal into deterministic disposer | Triage is judgment. The belt is the deterministic skeleton. |
| Belt-poller | Deterministic daemon | Polling is transport and mechanics; it stays token-free. |

## 4. Organ hydration contract

This proposed contract preserves the current repository rule that structural
source-of-truth state is authoritative and recall is only an advisory
projection. Hydration may improve discovery, but correctness must not depend on
recall availability.

| Source | Contract |
|---|---|
| Authoritative write | The repo-native structural SSOT or deterministic assertion-ledger write is canonical and complete on its own. It does not wait for, share a commit with, or derive validity from a recall-index write. |
| Advisory projection | Vector or graph recall is derived, rebuildable, non-canonical, and independently fallible. Projection refresh may occur asynchronously after the SSOT write; a missed or failed refresh does not roll back or weaken the SSOT. |
| Hydration precedence and fallback | Deterministic SSOT entries structurally precede recall regardless of score. Recall is additive to the unchanged CORE/flat-file source-of-truth. Missing, malformed, stale, or unavailable recall degrades deterministically to SSOT plus CORE/flat-file navigation and never blocks activation. |
| Pointer verification | Recall returns pointers rather than remembered bodies. Each pointer carries verification metadata such as `source_path`, `chunk_ref`, `content_hash`, `as_of`, scope, and retrieval tier/rank. The organ re-opens the live source and verifies the pointer before acting; a mismatch or unavailable source makes the recalled item unusable, not authoritative. |
| Confidentiality and privacy | Scope is checked before embedding, querying, ranking, or injection. Confidential material is excluded unless an explicit policy-approved local path covers that scope; egress requires explicit consent. Missing or ambiguous scope fails closed to the deterministic SSOT/CORE fallback. |
| Policy injection | Organ receives a versioned plain-text policy file path at spawn time; prompts are not hardcoded. |

## 5. Two Steinberger steals — proposed first implementations

Neither implementation in this section is ratified or authorized by this
document. Both proposals use a deterministic skeleton, an ephemeral
agent-organ, advisory structured output, and a deterministic disposer. Policy
changes take effect only after they enter the applicable trusted, ratified
control-plane or base ref and the activation binds their digest.

### 5.1 S1 — AutoReview analog

| Field | Value |
|---|---|
| Status | Proposed; no implementation authority. |
| Trigger | GitHub Actions webhook per commit. |
| Agent work | Review the PR with fresh context for that commit. |
| Output | Structured reviewer evidence with either advisory `COMMENT` or blocking `REQUEST_CHANGES`. |
| Disposer | Deterministic governed review transport that accepts only `COMMENT` or `REQUEST_CHANGES`, binds the evidence to the reviewed head, and records it without converting it into approval or ratification. |
| Authority limit | AutoReview never emits `APPROVE`, never ratifies, and never satisfies an independent approval or merge predicate. An authorized human/controller decision remains a separate action under the applicable authority and author-separation rules. |
| Governing policy | Load the reviewer rubric from a trusted ratified control-plane or trusted base ref, then bind the exact bytes by digest for the activation. Never load the governing rubric from candidate HEAD. Candidate changes to `AGENTS.md`, reviewer rubrics, or related policy are ordinary reviewed input only and cannot govern their own review. |
| Token budget | Haiku class; one activation per commit. |

### 5.2 S2 — Triage analog

| Field | Value |
|---|---|
| Status | Proposed; no implementation authority. |
| Trigger | Belt tick with configurable polling interval. |
| Agent work | Read open issues and triage policy. |
| Output | Proposed label and lane assignment. |
| Disposer | Deterministic disposer writes labels through the GitHub API only when confidence is at or above threshold. |
| Policy | `policy/triage-rules.md` from the applicable trusted ref, bound by digest. |
| Token budget | Haiku class; one activation per batch of up to 20 issues. |

## 6. Governance note

This document is a DESIGN-PREVIEW artifact. It has been HELD for Operator
review before the merge gate is opened. The rubric and implementation sketches
are proposals, not ratified/current behavior, and this document carries no
implementation, approval, ratification, or merge authority. Do not implement
organ classification changes without a separate Operator-ratified decision and
the governed implementation process.
