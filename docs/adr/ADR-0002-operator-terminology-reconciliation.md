# ADR-0002 — Operator terminology reconciliation (docs-only policy gate)

- **Status:** Accepted (recorded at the docs-only terminology policy/ADR
  gate; Operator ratification carried by the ratified implementation
  prompt cited under Authority basis).
- **Date:** 2026-05-28
- **Gate:** T1 — Docs-only terminology policy/ADR (mutation class:
  `docs` / `governance` documentation only).
- **Mutation class:** docs/governance documentation only. This ADR
  changes no schema enum value, no validator behavior, no template
  output, no CLI/runtime text, and no example fixture.
- **Authority basis (verified by SHA256 before authoring):**
  - **Operator decision answers** (Q1–Q12), recorded at
    `.hermes/research/operator-terminology-reconciliation-architect-20260528T042835Z/SOURCE_DECISION_ANSWERS.md`,
    SHA256 `412f0ea87a020c0c8fcff4d7d3bdc75d2227eca1c834335a8d39a690e92a8886`.
  - **Architect assessment report** (verdict
    `PROCEED_WITH_CAVEATS`), recorded at
    `.hermes/research/operator-terminology-decision-review-visible-architect-20260528T060452Z/ARCHITECT_ASSESSMENT_REPORT.txt`,
    SHA256 `6d4a38e76e464ddd3e15c36f1947f7f7fedb29ddb7c643c499d1eaa4abfbc9bf`.
  - **Processed Operator answers**, recorded at
    `.hermes/research/operator-terminology-reconciliation-plan-20260528T061633Z/OPERATOR_TERMINOLOGY_SOURCE_ANSWERS_PROCESSED.md`,
    SHA256 `4e643cf34f40c3ea61ddb5c06f811f7f24bbe566cc71a388af162d6cb30276e2`.
  - **Implementation plan**, recorded at
    `.hermes/research/operator-terminology-reconciliation-plan-20260528T061633Z/OPERATOR_TERMINOLOGY_IMPLEMENTATION_PLAN.md`,
    SHA256 `2a26052d02ba0337c26624543bbdc26d82f0191f938ead110797bd29835d9aae`.
  - **Ratified implementation prompt for this gate**, recorded at
    `.hermes/research/operator-terminology-reconciliation-plan-20260528T061633Z/recommended-next/NEXT_OPERATOR_TERMINOLOGY_IMPLEMENTATION_PROMPT.md`,
    SHA256 `213752c5487d2b02854601400da87c7a3ef767207ff7156e6c2750bc0ef975ca`.

> This ADR **records** locked Operator decisions and ratifies the
> docs-only policy. It re-decides nothing and authorizes no schema,
> validator, template, example, CLI, runtime, or migration change. The
> decisions below carry **no hedged or probabilistic wording** — they
> are locked by the Operator and the named authority basis.

---

## 1. Apex human authority term

**Decision (Q1).** The product-facing apex human authority term in
Creator Engine is **`Operator`**.

- `Operator` is the primary product-facing label for the human party
  who holds apex authority (the role historically named `Source` in
  internal prose and v1 machine surfaces).
- `Human Ratifier` is **precision-only** governance terminology. It
  remains usable where governance prose must disambiguate human
  ratification from agent/CI/review work; it is not the primary
  product-facing label.
- `Approver` is rejected as too weak; it blurs ordinary review
  approval with the stronger ratification act.
- `Tenant Admin` is rejected as overfitting hosted/team deployments
  outside v1.0 scope.

This decision governs new product-facing prose. It does **not**
retroactively rewrite historical artifacts, ignored archives, local
memories/profiles, or existing v1 machine values.

## 2. v1 machine enum compatibility and display-label mapping

**Decision (Q2).** The v1 machine enum value **`source`** is preserved
through the entire v1.x line. The product-facing **display label** for
that machine value is **`Operator`**.

- `role_category: source`, `required_ratifier_role: source`,
  `merged_by_role: source`, `grant_authority: source`, and any other
  v1 machine values that encode the apex authority remain valid
  through v1.x.
- Product-facing surfaces (docs, prompts, completion reports, CLI/
  runtime text, examples) display the label `Operator` when rendering
  this machine value.
- The mapping is one-way for v1.x: enum value `source` → display
  label `Operator`. No machine enum hard-rename occurs in v1.x.
- Removal or hard deprecation of the `source` machine value is
  deferred to a future v2/schema-version decision; it is **out of
  scope** for this gate and for the v1.x line.

## 3. Ratification-line compatibility (executable governance syntax)

**Decision (Q3, Q4).** The canonical attestation parser preserves
acceptance of both ratification phrases for the entire v1.x line. New
canonical emit form changes after the migration lands.

> **Normative clause.** Canonical-attestation parsers MUST accept both
> `Operator ratifies prompt:` and `Source ratifies prompt:` for the
> entire v1.x line. Only the canonical emit form changes to
> `Operator ratifies prompt:` after the migration lands. Removal of
> legacy acceptance is deferred to v2/schema-version.

This clause is binding on every gate that touches the canonical-
attestation parser, the Controller↔Operator communication path, or
any executable governance syntax that consumes a ratification line.
A gate that proposes to remove legacy acceptance within v1.x is out
of policy and must be refused.

## 4. Controller agent / Controller harness / Hermes Agent taxonomy

**Decision (Q5).** Three terms are used with strict referents.

- **`Controller agent`** — the active agent occupying the Controller
  seat at a given moment. The referent is an **agent**, not tooling.
- **`Controller harness`** — the tooling / runtime / profile /
  template / wrapper layer that supports a Controller seat. The
  referent is **tooling**, not an agent.
- **`Hermes Agent`** — reserved exclusively for the explicit supported
  Hermes integration / profile / template / harness. The referent is a
  specific named integration, not generic CE language.

Generic product-facing CE prose uses `Controller agent` or
`Controller harness` according to referent. Generic prose does not
use `Hermes Agent` as a synonym for either.

### Worked examples

1. **Active agent in the seat (use `Controller agent`).** "The
   Controller agent reads the ratified prompt, verifies its SHA, and
   writes the handoff." Referent is the active agent. `Controller
   agent` is correct; `Hermes Agent` is incorrect here unless the
   active agent is specifically the supported Hermes integration.
2. **Runtime tooling (use `Controller harness`).** "`ce launch`
   opens or attaches a Controller seat. It is part of the Controller
   harness syscall surface." Referent is the tooling/launcher layer.
   `Controller harness` is correct; `Controller agent` is incorrect
   because no agent is acting yet.
3. **Wrapper that bundles tooling and an agent profile (use
   `Controller harness` for the wrapper layer, `Controller agent`
   for the active agent inside it).** "The Hermes Controller harness
   bundles a TUI, a profile, and templates. The agent occupying the
   seat under that harness is the Controller agent." This splits the
   tooling referent from the agent referent.
4. **Explicit supported Hermes integration (use `Hermes Agent`).**
   "The validator-hermes integration tests exercise the Hermes Agent
   integration end-to-end." Referent is the named integration. Using
   `Controller agent` here would lose integration identity.
5. **Cross-harness governance prose (use `Controller agent` for the
   active agent class).** "An ungoverned Controller agent session
   must not implement, verify, and land its own governance." The
   sentence applies to whatever agent is in the seat; `Controller
   agent` is correct because the prose is harness-agnostic.
6. **Generic CE marketing-adjacent prose (avoid both `Hermes Agent`
   and harness-specific names).** "Creator Engine governs the
   Controller seat through a Controller harness; the active
   Controller agent operates under deterministic substrate." This
   neither implies CE is tied to Hermes nor erases the harness/agent
   split.

## 5. `Nefarious` replacement policy (per referent)

**Decision (Q6).** The local-identity name `Nefarious` is replaced
**by referent**, not by sed-style global substitution.

- Where the referent is the **active agent** occupying the Controller
  seat: replace with `Controller agent`.
- Where the referent is **tooling / runtime / profile / template /
  wrapper**: replace with `Controller harness`.
- Where the referent is a **physical or local host**: replace with the
  appropriate host-oriented term (see fixture conventions below);
  never reuse `Controller agent` for a host.

### Fixture ID conventions

- `controller-agent-a` — fixture identifier for the active Controller
  agent.
- `controller-host-a` — fixture identifier for a physical / local
  host. Only used when the value actually denotes a host or machine.
- `example-controller-agent` — generic placeholder for prose/examples
  that need a stand-in for an active Controller agent without
  asserting a specific identity.

Per-occurrence classification is mandatory; global search/replace is
forbidden under this gate and under later migration gates that
consume this policy.

**Historical note (allowed historical reference).** The local-identity
name `Nefarious` continues to appear in historical artifacts, in
ignored `.hermes/` archives, in local memories/profiles, and in
already-tracked operating-model surfaces that this gate does not
modify. Those references are historical fixtures and are not
retroactively rewritten by this docs-only gate.

## 6. Validator / scanner enforcement policy

**Decision (Q8).** Two-tier enforcement.

- **Warn (compatibility-preserved).** Legacy authority terminology
  (`Source` as an apex-authority noun; `Source ratifies prompt:` as
  the canonical-attestation phrase) is **compatibility-preserved**.
  Validators and scanners MAY warn when this terminology appears in
  newly generated or newly changed product-facing surfaces. They MUST
  NOT hard-fail on legacy authority terminology during v1.x.
- **Hard-fail (no compatibility contract).** Local identity leakage —
  `Nefarious`, nefarious-derived identifiers, personal hostnames,
  local profile names, and other operator-local persona/host names —
  is **not** a compatibility contract. Validators and scanners
  hard-fail when local identity leakage appears outside explicit
  legacy/ignored allowlists, after fixture migration lands in a later
  gate.

### Enforcement scope clause

Validator warnings for legacy authority terminology apply to (a)
changed lines in pull-request diffs, or (b) files matching the
in-scope path-glob allowlist defined in §7, whichever scope a later
ratified gate selects. Existing untouched files are **not**
retroactively warned. Until a later gate ratifies the runtime scope
implementation, the policy here governs intent only; no validator/
scanner behavior is changed by this docs-only ADR.

## 7. In-scope path-glob list paired with out-of-scope exclusions

**Decision (Q9 plus Architect non-blocking refinement).** Scope is
expressed as a positive in-scope list paired with the negative
exclusion list.

### In-scope (product-facing CE surfaces governed by Operator terminology)

- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `GOVERNANCE.md`
- `docs/product/**`
- `docs/architecture/**`
- `docs/governance/**`
- `docs/delivery/**`
- `docs/operations/**`
- `specs/**/spec.md`
- Generated templates under `recommended-next/`
- Prompt templates and completion-report templates (tracked template
  surfaces under `templates/**` that emit product-facing prose)
- `.github/PULL_REQUEST_TEMPLATE*`
- `.github/ISSUE_TEMPLATE/**`
- `CHANGELOG.md` (if and when present)

### Out-of-scope (explicit exclusions)

- Ignored `.hermes/` archives, including run artifacts, transcripts,
  evidence, manifests, and completion reports.
- Historical commit messages.
- Local memories and profiles (operator-local state).
- External docs and sites, unless separately ratified.
- Tenant-specific fixtures, e.g. `tenants/limitless/`, **except**
  where tenant or local naming leaks into generic product-facing CE
  docs, examples, templates, schemas, or paths.

### Worked exclusion example

Content authored inside `tenants/limitless/` that names
`LIMITLESS` is in-tenant content and is **not** a leak. The same
content quoted inside `docs/product/ROADMAP.md` (a generic CE
product-facing surface) is a leak and is governed by this policy.

## 8. `source-controlled:` provenance terminology (preserved)

**Decision (Q11).** The token **`source-controlled:`** is **source-
control / provenance terminology**, not apex-authority terminology.
It is **preserved unchanged** by this gate and by every later
migration gate that consumes this policy.

### Worked example

A provenance frontmatter line such as

```text
source-controlled: true
```

states that the artifact is under source-control determinism. The
prefix `source-` here denotes source control, not the apex authority
formerly named `Source`. Any future contributor or future agent
session sweeping for legacy authority terminology MUST NOT rewrite
`source-controlled:` under this gate. Renaming to `repo-controlled:`
or `fixture-controlled:` requires a separate compatibility-scoped
gate.

## 9. Tenant / project-name hygiene separation

**Decision (Q12).** This gate is the **authority/persona terminology
gate**. It does not expand into tenant/project-name hygiene.

- Tenant identifiers (e.g., `tenants/limitless/`) remain governed by
  their tenant overlays.
- Project/integration identifiers such as `LIMITLESS`, `OpenClaw`,
  and `NanoClaw` are not touched by this gate, except where they
  leak into generic product-facing CE docs, examples, templates,
  schemas, or paths and are not explicitly supported integration
  names.
- The pre-existing no-`LIMITLESS` generic-path policy is preserved.
- Any comprehensive tenant/project-name cleanup is a separate
  follow-on gate (T7 in the implementation plan) and requires its
  own Operator ratification.

## 10. Migration-guide timing

**Decision (Q10).** This docs-only policy/ADR gate includes the
authoritative terminology policy and the compatibility note. It does
**not** publish a full migration guide.

A dedicated migration guide MUST be published with the **first**
implementation gate that changes any of:

- generated templates;
- validators;
- CLI/runtime text;
- examples;
- schemas or display labels;
- prompt or report wording.

The dedicated migration guide MUST document:

- old → new mappings for terminology in the touched surface;
- v1.x compatibility behavior for legacy `source` machine values and
  legacy `Source ratifies prompt:` phrases;
- validator warning / hard-fail behavior in that surface;
- allowlisted legacy surfaces;
- worked examples of the new `Operator` / `Controller agent` /
  `Controller harness` terminology in that surface.

Automated fixer / checker support is deferred and requires a
separately scoped gate.

## 11. Rollback / abort conditions consumed by this gate

This gate halts and reports a blocker, rather than continuing, if any
of the following occurs during execution of a later gate that cites
this ADR as authority basis:

- A proposal to hard-rename the `source` machine enum value during
  v1.x.
- A proposal to remove legacy `Source ratifies prompt:` acceptance
  during v1.x.
- An attempt to rewrite ignored `.hermes/` archives or historical
  commit messages under this terminology policy.
- An attempt to mutate `schemas/**`, `validators/**`, `templates/**`,
  `examples/**`, `tenants/**`, or runtime text inside the T1 docs-
  only gate.
- An attempt to broaden tenant/project-name cleanup into the
  authority terminology workstream without separate Operator
  ratification.
- An attempt by any agent to select or revise Operator decisions
  autonomously.
- A global search/replace without per-occurrence referent
  classification.

## 12. References

- `docs/governance/V1_CANONICAL_TERMINOLOGY.md` — central terminology
  lock; updated by this gate to add `Operator`, `Human Ratifier`,
  `Operator ratification`, `Controller agent`, `Controller harness`,
  `Hermes Agent` (integration), and the `source-controlled:`
  provenance preservation note, with reference back to this ADR.
- `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md` — authority
  matrix summary; updated by this gate with a compatibility / display-
  label note next to the role-category table and ratifier taxonomy.
  No enum value or authority semantic is changed.
- `docs/adr/ADR-0001-v1-baseline-and-product-form.md` — v1 baseline
  and locked product form; this ADR layers on top of ADR-0001's v1
  posture.
- `.hermes/research/operator-terminology-reconciliation-architect-20260528T042835Z/SOURCE_DECISION_ANSWERS.md`
  — Operator Q1–Q12 decision record (authority basis).
- `.hermes/research/operator-terminology-decision-review-visible-architect-20260528T060452Z/ARCHITECT_ASSESSMENT_REPORT.txt`
  — Architect verdict `PROCEED_WITH_CAVEATS` and the non-blocking
  ADR caveats this gate incorporates.
- `.hermes/research/operator-terminology-reconciliation-plan-20260528T061633Z/OPERATOR_TERMINOLOGY_IMPLEMENTATION_PLAN.md`
  — gate sequence T1–T7.
- `.hermes/research/operator-terminology-reconciliation-plan-20260528T061633Z/recommended-next/NEXT_OPERATOR_TERMINOLOGY_IMPLEMENTATION_PROMPT.md`
  — ratified implementation prompt that authorizes this gate.
