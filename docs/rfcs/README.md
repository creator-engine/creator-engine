# RFCs — Request for Comments with Final Comment Period

This directory holds CE's **RFC-form Decision Records** — the durable artifact
for **structural or contested** decisions, in **Rust RFC + Final Comment
Period (FCP)** lineage, wrapped with CE's grader-outside governance
front-matter (v3.5-C A-C1, design §A.1/§A.2).

Contract: `docs/contracts/decision-record.md` ·
Schema: `schemas/decision-record.schema.yaml` ·
Check: `decision_record` ·
Template: [`RFC-0000-template.md`](RFC-0000-template.md)

## When an RFC, not an ADR

When two peers *disagree* on a decision (not just a code diff), or N competing
drafts must converge, the lightweight ADR is the wrong instrument. The RFC +
FCP mechanics are CE's answer to **multi-author convergence** (coordination
design §11.4): a motion with an explicit disposition, a timed comment window
with tracked blocking concerns, and an explicit human sign-off. Losing drafts
are deterministically closed (`superseded` with a `crosswalk.superseded_by`
link), never silently dropped.

## Convention

- **File:** `RFC-NNNN-<slug>.md`; front-matter `kind: decision-record`,
  `record_type: rfc`; the `id` field matches.
- **Disposition:** every RFC moves toward an explicit `disposition` —
  `merge` (adopt) · `close` (reject) · `postpone` (defer).
- **Final Comment Period (`fcp`):** a timed window (`opened_at`; Rust uses 10
  days) during which **blocking concerns** are tracked as
  `concerns: [{name, status: open | resolved}]`. **The FCP cannot complete
  while any concern is `open`** — an `accepted` RFC with an open concern is
  rejected by the `decision_record` check (`VAL-DR-FCP-OPEN-CONCERN`).
- **Ratification:** the transition to `accepted` is a **human-ratification
  event** recorded in the `ratification` block; for privileged
  `mutation_class` the ratifier must be independent of `decision_makers`
  (design §A.5 — for two peers, the other peer / both peers).
- **Supersession:** as for ADRs — supersede-with-link, never delete.

## Lifecycle

```
proposed ──► fcp opened (disposition: merge|close|postpone)
   │              │  blocking concerns raised + resolved
   │              ▼
   │        all concerns resolved ──(human ratification)──► accepted
   └────────────────────────────────────────────────────► superseded | deprecated
```
