# Architecture Decision Records (ADRs)

This directory holds CE's **ADR-form Decision Records** — the durable artifact
for **reversible** decisions, in **MADR 4.0.0** lineage, wrapped with CE's
grader-outside governance front-matter (v3.5-C A-C1, design §A.1/§A.2).

Contract: `docs/contracts/decision-record.md` ·
Schema: `schemas/decision-record.schema.yaml` ·
Check: `decision_record` ·
Template: [`ADR-0000-template.md`](ADR-0000-template.md)

## Convention

- **File:** `ADR-NNNN-<slug>.md` — `NNNN` is a zero-padded monotonically
  increasing number; the `id` front-matter field matches (`ADR-NNNN` or
  `ADR-NNNN-<slug>`).
- **Form:** YAML front-matter (`kind: decision-record`, `record_type: adr`)
  followed by the MADR body — Context and Problem Statement, Decision Drivers,
  Considered Options, Decision Outcome, Consequences.
- **A Decision Record is a sibling of Skill, not a Scope type:** governed at
  the Skill cadence — ratified-once, supersede-don't-delete,
  higher-blast-because-referenced.

## Lifecycle

```
proposed ──(human ratification)──► accepted ──► deprecated
                                       │
                                       └──► superseded ──► crosswalk.superseded_by
```

- **`proposed`** — drafted (an agent may draft; the shaping move is: agent
  drafts, external rubric grades, human ratifies). No `ratification` block yet.
- **`accepted`** — a **human-ratification event**, recorded in the
  `ratification` block (`ratified_by`, `ratified_at`,
  `ratification_prompt_sha`). Nothing auto-promotes a record to `accepted`.
  For privileged `mutation_class` (deploy, governance, identity, security,
  attestation, redaction) the ratifier must be **independent** of
  `decision_makers` — for two peers: the *other* peer (design §A.5).
- **`deprecated`** — no longer recommended, kept for the record.
- **`superseded`** — replaced; the record **stays in place** and MUST link its
  successor via `crosswalk.superseded_by` (**supersede-with-link, never
  delete** — referenced decisions must keep resolving).

## Freshness

Every record carries a required `review_by` date — decisions rot; an
unreviewable-forever record is rejected by the schema.

## When to use an RFC instead

Structural or **contested** decisions (two peers disagree; N drafts must
converge) use the RFC + Final-Comment-Period form in
[`docs/rfcs/`](../rfcs/README.md), not an ADR.
