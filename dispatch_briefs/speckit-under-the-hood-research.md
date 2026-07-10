# Research Handoff — Should CE adopt spec-kit (SDD) "under the hood" in its proven orchestration build path?

**Requested by:** Operator (2026-06-30) · **Model:** Opus, high effort · **Role:** architect_research (READ-ONLY; return a decision-grade report, no code changes)
**Decision owner:** Operator (this report informs a ratification, it does not make the call)

## Why this is being asked (frame — read carefully)
CE has TWO distinct ways to drive build work, and right now we only use one:

1. **Our proven, codified orchestration path (what we actually run):** a controller (dev-2 orchestrator + dev-1/3/4 codex controllers) dispatches governed worker roles — **implementer / reviewer / harvest_intake / ops_triage / verification / architect_research** — each in an isolated worktree, then **harvest → independent review → merge-gate**. This path is (a) **proven** — it ships our PRs daily, and (b) **codified** in `playbooks/controller/briefs/{dispatch,harvest,merge-gate,seat-refresh}.md`, the role definitions in `.claude/agents/*.md`, and the `ce-dispatch`/`ce-harvest` skills. Governance (Scope/Done-when/ratify/gate) is CE's own machinery via `cev3` (`validators/creator_engine_validator/v3_cli.py`).

2. **spec-kit's SDD inner-loop (which we ship to users but do NOT use ourselves):** `specify → clarify → plan → tasks → implement → analyze`, vendored as `.specify/` (templates/scripts) + `.claude/skills/speckit-*`. Currently pinned 0.8.7 (upstream 0.12.0; sync in flight). The ratified mode-axes canon asserts that in CEO/Autonomous-Fleet cells "the agent invokes the speckit pipeline **under the hood**" — but **that is design aspiration, NOT wired.** Our agents run the orchestration path above, which is a *different* build mechanism than the speckit pipeline.

The Operator's instruction: **do not decide on vibes** whether speckit is "Solo-Dev-only." Rigorously research whether wiring spec-kit's SDD pipeline *under the hood* into our proven orchestration path would **improve our dev performance, consistency, and methodology adherence** — or whether our orchestration already subsumes SDD and speckit would add ceremony/dependency without value at our tier.

## Core questions to answer (with evidence, not theory)
1. **Marginal value over what we already have.** Map speckit's `spec → plan → tasks` artifact chain against CE's existing machinery: the `cev3` **Scope (Goal / Done-when / Budget / Change-type)**, the existing `specs/00X-*` spec docs (CE itself was bootstrapped with spec-kit — examine `specs/001…`, `002…`, `005…` and the `_traceability_matrix.md`), the constitution check (`.specify/templates/plan-template.md` 12-gate fork), and the `ce validate-pr` gate suite. **Where is speckit redundant with what CE already enforces, and where is it genuinely additive?** Be specific per pipeline stage.
2. **Consistency / drift reduction.** Would a mandatory spec+plan+tasks front-half measurably reduce the failure modes we actually hit — scope drift, "done ≠ done", rework, mid-stream re-briefs? **Ground this in our real history:** sample recent merged PRs and the harvest/review notes; look for evidence of drift/rework our current gate did NOT catch but an SDD front-half would have. If the gate already catches them, say so.
3. **SDD + TDD adherence.** Does speckit's `tasks-template.md` enforce test-first / spec-first more tightly than our current `implementer.md` role + `validate-pr` baseline-diff-test gate? Is the improvement real or already covered?
4. **Cost / friction / conveyor impact.** Quantify the overhead of running the full pipeline per work-unit: added latency, token cost, extra artifacts to gate, effect on the batch-dispatch conveyor and bounded-work-unit tenet. Does it slow throughput more than it improves quality?
5. **Integration shape (only if value is found).** Which slot-in is best, with rationale:
   - (a) **Full** — every implementer dispatch runs specify→plan→tasks→implement under the hood;
   - (b) **Partial** — adopt speckit's spec/plan *templates* as the brief/Scope format, skip the rest;
   - (c) **Selective** — pipeline only for feature/epic-class work, not tiny/story;
   - (d) **None** — orchestration already subsumes SDD; recommend against.
6. **Strategic + rented-surface coherence.** CE's moat is the correctness spine + "grader outside the agent." Does an under-the-hood SDD loop *strengthen* that, or just deepen a **rented dependency we must keep synced** (the exact drift that produced ce-ops#114)? Factor the maintenance/sync burden into the cost side.
7. **Does this change the "Solo-Dev-only" answer?** If under-the-hood adoption is valuable, then the canon's "agent invokes speckit under the hood in CEO/Fleet" stops being aspiration and becomes something we should *build* — note that implication and what it would take.

## Grounding discipline (mandatory)
- **Ground in CURRENT (2026) external research, not pre-training** ([[agent-research-discipline]]): use web search/fetch for the present state of Spec-Driven Development (GitHub spec-kit's own thesis + changelog 0.8.7→0.12.0), and any current evidence on SDD/TDD for *autonomous/agentic* coding under orchestration. Distinguish vendor marketing from evidence.
- **Ground in OUR actual repo + practice**, not assumptions: read the role defs, the controller playbooks, the cev3 Scope/gate machinery, the existing `specs/` artifacts, and real recent PR/harvest/review history. Cite file paths + PR numbers.
- Reuse-before-reinvent ([[ce-rent-or-fork-before-reinvent]]) and prevent-by-design ([[ce-no-mvp-quality-from-day-1]]) are CE doctrines — weigh the recommendation against them.

## Deliverable (decision-grade)
A single report with:
- **A clear recommendation:** adopt-full / adopt-partial / adopt-selective / don't-adopt, stated up front with confidence level.
- **The evidence** for each core question (with citations to our files/PRs and to current external sources).
- **A redundancy/additivity map:** speckit stage → does CE already cover it (where) → net-new value (if any).
- **If adopt:** the concrete integration design (where it slots into dispatch→implement→harvest→gate), the per-unit cost, and a **measurable pilot** to prove it — e.g. run the SAME real ticket through both paths (current orchestration vs orchestration+speckit-under-the-hood) and compare drift/rework/quality/throughput on defined metrics.
- **Risks**, including the rented-surface sync burden and any conflict with cev3/constitution machinery.
- **The implication for the mode-axes canon** ("agent invokes speckit under the hood") — keep aspirational, build it, or drop it.

Return the report as your final message (it is the deliverable; the controller will persist it and bring it to the Operator).
