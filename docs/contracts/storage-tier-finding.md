# Contract: Storage-tier advisory finding (v3.5-C A-C2)

**Status:** Canonical. Enforced by the `storage_tier_finding` check against
`schemas/storage-tier-finding.schema.yaml`. The governing tier policy is
`docs/decisions/ADR-0001-public-private-storage-policy.md` (a ratified
`governance`-class Decision Record, validated by the A-C1 `decision_record`
check — the classification rule is the same kind of object as the things it
classifies).

## Purpose

When a CE instance produces a knowledge artifact, **two advisory
classifications** run **before** anything reaches a shared surface
(design §A.3):

1. **Relevance** — project/team-relevant, or instance-local noise?
2. **Storage tier** (if relevant) — `instance-local` (private to the
   instance) · `repo-docs` (`docs/` in the code repo; shareable, travels with
   the repo) · `ops-private` (the single private ops repo; project-relevant
   but genuinely sensitive).

The classifier emits a **finding** proposing relevance + tier per artifact
part. A finding may **split** one artifact across tiers (e.g. the
architecture half → `repo-docs`, the strategy-sensitive half →
`instance-local`/`ops-private`).

## Advisory by construction — relevance and tier are PROPOSALS

**A finding never promotes.** Both classifications are *proposals a human
ratifies*. Promotion into the backlog / opening a committing record is a
**human-ratified event recorded on the evidence-spine**:
`promotion.promoted: true` is valid **only** with a
`promotion.ratification_ref` (the spine record's content digest). The check
rejects the rest (`VAL-STF-AUTO-PROMOTED`), and **there exists no code path
that flips `promoted` without a ratification reference** — the only
constructor (`emit_finding`) emits `advisory: true`, `promoted: false`, and
the module deliberately defines no `promote()`.

## The 5-stage triage seam

The classifier reuses the 5-stage triage loop (re-implemented here as the
pure `TRIAGE_STAGES` data + `emit_finding` helper — a `shared` check never
imports a v3 module):

```
read_only_classify → schema_finding → deterministic_gates → discard_on_drift → guarded_mutation
        (1)              (2 = this record)      (3)               (4)                (5)
```

The finding is the **stage-2 output**. The **live** LLM classification call
(stage 1 in a stripped sandbox) is a **deferred seam** — A-C2 ships the
advisory finding contract + the written policy only. Nothing in this gate
opens an issue, writes to a remote, or mutates anything (stage 5 happens only
after human ratification).

## Enforced invariants (the `storage_tier_finding` check)

| Code | Invariant |
| --- | --- |
| `VAL-STF-SCHEMA` | the record validates (advisory is `const true`; tier/relevance enums; per-part rationale required). |
| `VAL-STF-INVALID` | the record file parses as YAML. |
| `VAL-STF-AUTO-PROMOTED` | `promoted: true` carries the spine `ratification_ref` — the no-auto-promotion hard invariant. |
| `VAL-STF-SPLIT-DUPLICATE-PART` | a split classifies each part exactly once (distinct `part_ref`s). |
| `VAL-STF-NOISE-SHARED-TIER` | a part classified `instance-local-noise` is never proposed into `repo-docs`/`ops-private`. |

## Honesty boundary

This check validates the finding's **shape + governance invariants**. It does
not (and cannot) verify that the proposed relevance/tier is *correct* — that
judgment is the human ratifier's, guided by the written policy (ADR-0001).
The check guarantees only that a finding cannot masquerade as a decision.
