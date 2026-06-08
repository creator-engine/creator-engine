# CE v3 — Shaping UX (the Frame→Shape dialogue + the chat→Scope trigger)

*Curated design reference (provenance: 2026-06-08 design session). **DESIGNED / pilot-target** — re-ground at the implementing gate (G-7). Execution status lives in [`docs/v3-roadmap.md`](../v3-roadmap.md). Vocabulary canon: [`stage-vocabulary.md`](./stage-vocabulary.md). User-facing walk-through: [`../guide/understanding-ce.md`](../guide/understanding-ce.md).*

This is how a developer's free-form chat becomes a **Scope** — a tracked, ratifiable, ticket-sized bet — and how CE shapes it. It is the UX of the **Frame** and **Shape** stages.

## The principle: agent drafts, an external rubric grades, the human ratifies

Every place CE shapes something is the same move: the agent **drafts** a proposal → checks it against an **external rubric** of "what must be present and valid here" → **flags the gaps** → asks the **minimum** questions to close them → the human supplies the **human-only fields** and **ratifies**. This is "the grader lives outside the agent" expressed at the dialogue layer: the rubric is the grader, the agent drafts, the human decides.

### One grill-me engine + per-locus rubrics
Build **one reusable engine**, not five bespoke dialogues. Only the **rubric** and the **human-only field set** vary per locus — and the rubrics are mostly **existing CE checks** (the Scope-shaping rubric *is* the `definition_of_ready` predicate; the plan-approval rubric is plan-completeness; …), so the engine reuses governance rather than re-deriving "ready." The five shaping loci map onto BMAD's four phases: (1) discovery/analysis · (2) Scope-shaping (`SHAPE → READY`) · (3) plan-approval (solutioning) · (4) run-escalation · (5) review.

## Frame is the free, pre-Scope zone — which resolves the trigger

A **Scope artifact does not exist during Frame.** Free chat — questions, exploring, thinking out loud — is Frame, untracked. A Scope crystallizes only at the **Frame→Shape transition**. So *"when does chat become a Scope?"* is exactly *"when does Frame become Shape?"* — and that one move both answers the trigger question and **bounds Scope proliferation** (nothing is tracked until intent is concrete enough to draft a bet).

## The "Ready" gate (Shape→Build)

The Definition-of-Ready gate is a **visible, compact checklist** that fills as the dialogue closes gaps, then the human ratifies the bet:

```
◆ CE · Shape → "rate-limit /api/login"   (Goal ✓ · Done-when 3 · Budget S · Change-type code · Ready ✓)
◆ CE · ratify & dispatch the bet? › yes
```

The gate is **legible, not hidden state** — the user watches it go green. It is enforced (a Scope cannot dispatch until Ready + ratified) but fast to reach. (`Goal/Done-when/Budget/Change-type/Ready` are the user-facing labels over the conserved schema fields — see the vocabulary canon.)

- **Change type (`mutation_class`) derivation:** the agent **proposes** the risk tier; the human may **tighten it for free**; **loosening requires ratification** (safe-by-default — the agent can never unilaterally enlarge blast radius).
- **Budget (`appetite`) is human-only:** the agent drafts every field *except* the budget; the fixed bet is the human's to place.
- **BMAD phase-1 (heavy Analysis) is light in the pilot** (Frame = understand-the-ticket discovery only); the full PRD-hierarchy Analysis defers to CEO-mode, crosswalk-bridged, per the fractal-collapse property (`Frame` folds into `Shape` at small grain).

## The chat→Scope trigger dial — detect-and-offer, risk-aware

**Detect-and-offer (E3):** chat stays free; when CE detects a concrete mutation intent (or the user invokes `ce scope`), the agent **drafts the Scope inline and asks one cheap confirm** — nothing is tracked until that yes. The confirm *is* the Frame→Shape gate.

**Eagerness = `f(persona, risk-class)`.** Persona sets the baseline bar; the Scope's `mutation_class` (risk) modulates it, both tightening as blast radius rises:

| | low-risk (docs, small code) | high-risk (deploy, schema, security) |
| --- | --- | --- |
| **Dev mode** | offer on a fairly clear signal | offer only on an *explicit* signal-to-act |
| **CEO mode** | offer eagerly on any actionable intent | still tightens — confirm-heavier as risk climbs |

CE is the only tool positioned to do this because it already carries the risk tier (`mutation_class`) as a first-class field.

**Delivery constraints (evidence-driven — see grounding):**
- The offer is a **cheap, inline, cancel-safe keystroke — never a blocking modal.** Interrupt-modal fatigue is worse than auto-execute fatigue (it taxes the user even on decline); reversibility is paramount.
- **Bias conservative** when uncertain — declining has a compounding cost.
- Eagerness is a **telemetry-tuned parameter, not a fixed constant** — instrument the offer→accept-vs-decline ratio. CE's state-as-artifacts substrate provides this signal natively.

## Why this is differentiated

CE's position is **detect-and-offer + artifact-as-contract + risk-aware eagerness** — three patterns each validated separately in the current market, never combined, and two of which (the *tracked* unit, the *risk* modulator) need substrate only CE has (the Scope + `mutation_class` + state-as-artifacts). Competitors that detect-and-offer surface an *ephemeral plan*; CE surfaces a *governed, ratifiable Scope*.

## Grounding (current-date research sweep, 2026-06-08)

Sweep across the leading agentic coding tools (Cursor, GitHub Copilot, Devin, OpenAI Codex, Claude Code, Google Jules, Windsurf, Cline, Aider, Replit, Factory, AWS Kiro, the BMAD method). Validated findings, dated:

- **Detect-and-offer is real but narrow.** Cursor auto-suggesting Plan Mode on detected complexity is the closest production analogue — and it offers a *plan*, not a *tracked unit* (Cursor Plan Mode, 2025-10). The field converges on **explicit-mode + plan-gate**, not silent-auto → CE's "offer a ratifiable Scope" is largely unoccupied space.
- **Mode-differentiated eagerness is well-precedented as a concept** (Ask/Agent/Auto in Cursor & Copilot; Plan/Act in Cline; Default/acceptEdits/Plan in Claude Code; approval presets in Codex) — but every existing dial governs how much the agent **executes**, never how readily it **proposes a tracked unit**. CE's CEO-vs-Dev *detection* dial is a novel application of an accepted axis.
- **Plan-then-approve is the converged safety norm**; "nothing tracked until yes" aligns with the mandatory-gate camp. Spec-first tools (AWS Kiro's EARS specs; the BMAD method's PRDs) validate "acceptance-criteria-as-contract before code = less rework" — exactly CE's Scope.
- **Over-eager autonomy has documented backlash** (GitHub's own hedge that auto-edit agent mode can "feel like giving up control," 2025; Continue.dev removing then re-petitioning auto-accept, issues #8310 / #12500; Cursor users rating rollback the most-valued feature; Swarmia's "Five Levels of Agent Autonomy," 2026-03: *agents are optimistic; higher autonomy = larger blast radius; agents need to know when to stop and ask*). The lesson lands on the eager side → key eagerness off **risk class**.
- **Caution:** the precise failure "it created a task I didn't want" is **under-evidenced** — almost nobody auto-creates tracked units yet — so CE cannot free-ride on others' tuning and must instrument and tune the threshold empirically.

## Non-goals / deferred

This is the *design*; the build is **G-7** (the product surface). Deferred design: the full cockpit (post-pilot graduation — see [`pilot-uiux-model.md`](./pilot-uiux-model.md)); the ◆ CE Completion-Report field vocabulary (the third user-facing surface); the durable Skill axis.
