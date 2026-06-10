# Contract: Decision Record — the durable decision artifact (v3.5-C A-C1)

**Status:** Canonical. Enforced by the `decision_record` check against
`schemas/decision-record.schema.yaml`.

## Purpose

A **Decision Record** is the durable knowledge artifact recording a ratified
decision — a *sibling of Skill*, **not** a Scope type. Where a Scope is the
ephemeral atom of work, a Decision Record is governed at the **Skill cadence**:
ratified-once, **supersede-don't-delete**, and higher-blast-because-referenced
(other artifacts — including a Scope's `binding_decisions` — cite it as binding
context, so changing it has wide blast radius).

Two mature prior-art forms are adopted verbatim and wrapped with CE's
grader-outside governance fields:

- **ADR (`record_type: adr`)** — MADR 4.0.0 lineage, for reversible decisions.
  Lives in `docs/decisions/ADR-NNNN-*.md` (convention: `docs/decisions/README.md`).
- **RFC (`record_type: rfc`)** — Rust RFC + **Final Comment Period** lineage,
  for structural/contested decisions needing convergence. Lives in
  `docs/rfcs/RFC-NNNN-*.md` (convention: `docs/rfcs/README.md`). Adds
  `disposition` (`merge | close | postpone`) and the `fcp` block
  (`opened_at`, blocking `concerns`).

## The record

A Decision Record is a Markdown file whose YAML front-matter carries
`kind: decision-record` and validates against
`schemas/decision-record.schema.yaml`:

- `id` — stable `ADR-NNNN` / `RFC-NNNN` id, cited by `crosswalk` links and by
  a Scope's `binding_decisions`.
- `status` — `proposed → accepted → deprecated | superseded`.
- `decision_makers` — the owner stamp (who made/owns the decision);
  `consulted` / `informed` — MADR communication trail.
- `review_by` — **required** freshness horizon (decisions rot).
- `mutation_class` — the blast-radius axis (shared taxonomy); privileged
  classes raise the ratification bar.
- `evidence_refs` — **required, non-empty**, each entry `{kind, ref, tag}`
  with a **required citation tag** (an untagged evidence ref is rejected).
- `policy_sha` — optional opaque pin to the governing policy/mandate document.
- `ratification` — the human-ratification attestation
  `{ratified_by, ratified_at, ratification_prompt_sha}`.
- `crosswalk` — `supersedes` / `superseded_by` / `informs` links.

## Enforced invariants (the `decision_record` check)

| Code | Invariant |
| --- | --- |
| `VAL-DR-SCHEMA` | front-matter validates against the schema (required fields, enums, evidence tags, ADRs carry no RFC-only fields). |
| `VAL-DR-INVALID` | a file naming itself a record (`ADR-NNNN`/`RFC-NNNN` filename) parses as one. |
| `VAL-DR-RATIFICATION-MISSING` | `status: accepted` carries the `ratification` block. **`accepted` is a human-ratification event** — no agent, check, or code path promotes a record to `accepted`; the check validates the recorded shape only. |
| `VAL-DR-SELF-RATIFIED` | for privileged `mutation_class` (`PRIVILEGED_NAMES`), `ratified_by` differs from every `decision_makers` entry — the ratifier is the *other* peer (design §A.5), never the owner. |
| `VAL-DR-SUPERSEDED-UNRESOLVED` | `status: superseded` links a `crosswalk.superseded_by` id that resolves to a record discovered in the same scan (supersede-don't-delete). |
| `VAL-DR-FCP-OPEN-CONCERN` | an `accepted` RFC has no `open` FCP concern (the FCP cannot complete while a blocking concern is open — Rust model). |

## The `binding_decisions` seam (A↔B)

`schemas/scope.schema.yaml` gains the optional `binding_decisions` field: a
list of Decision-Record ids a Scope cites as binding context. **A-C1 adds the
field + schema only.** The readiness enforcement — every cited record must be
`status: accepted` before autonomy may start — is the **B-C2** gate, not this
check.

## Honesty boundary

This check validates a record's **governance well-formedness** (shape +
invariants). It does **not** verify the *truth* of the decision, the quality of
its reasoning, or the live resolution of `evidence_refs` pointers. Templates
(`*-template.md`) and Markdown without the `kind: decision-record`
front-matter discriminator are out of scope.

This is a **shared** check (CODE_UNALLOWED ratchet): it imports only the
shared engine and the shared `mutation_class` check module
(`PRIVILEGED_NAMES`); it never imports a v3 module.
