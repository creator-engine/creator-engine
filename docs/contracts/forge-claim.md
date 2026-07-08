# Contract: Forge-projected claim + deterministic dedup (v3.5-C A-C4)

**Status:** Canonical. Enforced by the `forge_claim_dedup` check against
`schemas/forge-claim.schema.yaml`; the live projection adapter is
`creator_engine_validator/forge/backlog.py` (the α-precursor).

## Purpose

A PCO claim lives instance-local (`.ce/state/active-work-ledger/` for v3;
`.hermes/active-work-ledger/` is the v1-frozen layout) — invisible to the
other peer. By the A.0 invariant (**the forge is the only shared state**), a
*team-visible* claim is **projected onto the forge**: the backlog item's
**assignee + Projects `Status=Running`**. The projection is **re-read and
drift-checked immediately before** the local claim (`forge.backlog.claim_item`:
read → drift-check → write → randomized back-off → re-read → reconcile). The
instance-local ledger remains the per-instance detail; the forge projection is
the shared truth.

## ⚠ The advisory-lock limit — read this first

**Assignee + Status are advisory, NOT atomic** (claim-side TOCTOU,
coordination-layer §11.1). Two seats can claim the same hot item between the
drift-check read and the `Status=Running` write. **Nothing in this gate is a
hard lock, and neither the adapter nor this record format claims one.** What
ships instead:

1. **Idempotency key** = SHA256 over `(repo, item_id, claimant_instance,
   lease_window)` — a retry inside the lease window is the *same* claim, not
   a second one. Recomputed and enforced by the check
   (`VAL-FC-IDEMPOTENCY`); derivation twinned in `forge.backlog`
   (drift-guarded by tests).
2. **Short randomized back-off + re-read after write** — narrows (does not
   close) the race window.
3. **Earlier-`claimed_at`-wins reconciliation surfaced as an ESCALATION** —
   the colliding claim is *reported* with a proposed winner; it is **never
   silently overwritten** (`forge.backlog` has no force/overwrite path, and a
   record claiming `silent-overwrite` is rejected:
   `VAL-FC-SILENT-OVERWRITE`).

The live webhook-ingestion receiver (design §9.4) is **out of scope** — this
gate ships projection + drift-check + dedup, not a distributed event plane.

## Deterministic dedup — the grader outside the LLM

The triage side may **propose** a dedup link (`dedup.duplicate_of`); the
link **binds only on deterministic evidence** (`VAL-FC-DEDUP-NONDETERMINISTIC`
otherwise):

- **sufficient alone:** an `embedding_similarity` measurement at/over its
  **pinned threshold** with a **pinned `model_ref`** (high embedding
  similarity *can* suffice);
- **sufficient together (additive corroboration, not an exclusive OR):**
  non-empty `title_token_overlap` **plus** a `cross_reference`;
- **never:** an LLM's unevidenced judgment — there is no evidence kind for
  it.

## Enforced invariants (the `forge_claim_dedup` check)

| Code | Invariant |
| --- | --- |
| `VAL-FC-SCHEMA` | the record validates (claim tuple, ISO `claimed_at`, status enum, 64-hex key). |
| `VAL-FC-INVALID` | the record parses as YAML. |
| `VAL-FC-IDEMPOTENCY` | `idempotency_key` equals the canonical derivation over the claim tuple. |
| `VAL-FC-SILENT-OVERWRITE` | a collision surfaces as an escalation (`contention.surfaced_as: escalation`; `contended` status requires the block). |
| `VAL-FC-DEDUP-NONDETERMINISTIC` | a dedup link meets the deterministic-evidence bar above. |

## Honesty boundary

The check grades the **record**; it cannot make the underlying lock atomic,
verify the embedding score was honestly measured, or resolve an escalation —
the escalation's `winner` is a *proposal* (earlier `claimed_at`); a human
resolves it.
