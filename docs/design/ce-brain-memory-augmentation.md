# Company Brain Memory Augmentation Design

**Status**: Design-only proposal. No implementation is authorized by this
document.

**Scope**: Define a future Company Brain launch-context model that augments
flat `MEMORY.md` recall with shipped semantic recall capabilities while
preserving deterministic source-of-truth precedence.

## Problem

The current memory shape depends on an always-loaded `MEMORY.md` index and
plain-text discovery. That gives a stable baseline, but it does not reliably
surface lower-ranked or older durable knowledge when the launch context is
small, the relevant wording differs from the task wording, or a worker needs
to find historical rationale rather than a literal token match.

The shipped Company Brain pieces now make a stronger launch model possible:

- `brain_recall_surface` returns hybrid semantic and keyword recall pointers
  instead of inlining remembered content.
- The launch hydration from BRAIN-A already allows controller launch context
  to include advisory recall hints when the local recall surface is available.
- The eval harness from BRAIN-B provides a repeatable way to test recall
  quality and regressions.
- The SSOT precedence invariant keeps deterministic assertion-ledger entries
  structurally ahead of probabilistic recall.

This document proposes how those pieces should be composed in a future
implementation slice. It does not change launch code, schemas, storage,
validators, or policy.

## Goals

- Preserve the always-loaded `MEMORY.md` index as the stable, low-latency
  memory table of contents.
- Add top-K semantic recall pointers during controller launch so relevant
  durable knowledge can be discovered without relying on exact text matches.
- Keep deterministic SSOT assertion-ledger facts above advisory recall in the
  launch context and in agent instructions.
- Require agents to re-verify recalled pointers against the live source before
  acting on them.
- Exclude confidential scopes from semantic recall unless an explicit local,
  policy-approved recall path exists.
- Provide a migration path from flat grep-based recall to tiered pointer
  injection without breaking current launch behavior.

## Non-Goals

- No new embedder, vector store, schema, broker, CLI, or launch-runtime
  implementation in this slice.
- No inlining of recalled source bodies into launch context.
- No replacement of the assertion ledger with semantic recall.
- No automatic action based only on recalled memory.
- No broadening of confidential data handling, network behavior, or credential
  exposure.

## Proposed Model

Controller launch context should be assembled from three tiers:

| Tier | Source | Launch role |
|---|---|---|
| 1 | Deterministic SSOT assertion ledger | Canonical facts and governance assertions with structural precedence. |
| 2 | Top-K semantic recall pointers | Advisory pointers returned by `brain_recall_surface`, ranked for the launch task. |
| 3 | Always-loaded `MEMORY.md` index | Stable index and fallback navigation surface loaded for every launch. |

The injection should be pointer-first. A recall item should carry enough
metadata for verification, such as source path, chunk reference, content hash,
timestamp or corpus generation marker, retrieval tier, score or rank, and the
query context that selected it. The launch payload should not paste the recalled
body text into the prompt. Agents should open the cited source and verify the
current content before depending on the memory.

### Precedence Rules

1. SSOT assertion-ledger entries win over all recall pointers.
2. If an SSOT assertion and a recall pointer disagree, the launch context must
   instruct the agent to follow the SSOT assertion and treat the recall pointer
   as stale until re-verified.
3. If multiple recall pointers conflict and no SSOT assertion resolves the
   conflict, the agent must re-open the cited sources and prefer the freshest
   live source that is within scope.
4. The `MEMORY.md` index remains a navigation aid, not an authority override.
5. Missing recall must not fail launch when the SSOT ledger and `MEMORY.md`
   index are available.

These rules preserve the SSOT precedence invariant: deterministic governance
facts remain authoritative, while semantic recall improves discovery only.

### Staleness and Verification

Recall is advisory. A recalled pointer may be stale because the source changed,
the corpus was built from an older commit, the content hash no longer matches,
or a later document superseded the cited source.

A future implementation should therefore:

- label recall pointers as advisory in launch context;
- include enough metadata to detect stale pointers;
- require agents to re-open and re-check the cited source before using the
  recalled fact;
- degrade to the SSOT ledger plus `MEMORY.md` when recall metadata is missing,
  malformed, or unavailable;
- prefer a smaller verified recall set over a larger unverified one.

If verification fails, the agent should ignore the recalled content for
decision-making and report the stale pointer as evidence for corpus refresh.

### Confidential Scope Exclusion

The tiered model must exclude confidential scopes from semantic recall by
default. Confidential content should not be embedded, queried, ranked, or
injected unless the launch context is using a local, approved recall path whose
policy explicitly covers that scope.

The default behavior should be:

- no remote embedding or recall over confidential material;
- no launch injection of confidential recall pointers into unrelated work;
- no cross-scope blending where a pointer from one confidentiality scope appears
  in another;
- fail closed to SSOT-only and `MEMORY.md` index behavior when scope handling is
  ambiguous.

### Launch Context Shape

A future controller launch payload can expose the tiers in a compact structure:

```text
Company Brain launch memory

SSOT assertions:
- <assertion id, source, hash, summary>

Semantic recall pointers:
- <rank, tier, source path, chunk ref, content hash, as-of marker, reason>

Always-loaded index:
- MEMORY.md
```

The exact serialization can remain implementation-specific, but the rendered
prompt should make the distinction visible: SSOT assertions are canonical,
semantic recall pointers are advisory, and `MEMORY.md` is the always-loaded
index.

## Migration Path

1. **Document-only framing**: land this design without code changes.
2. **Shadow injection**: have launch hydration emit the tiered structure in a
   dry-run or debug artifact while preserving the current live prompt.
3. **Eval calibration**: use the eval harness from BRAIN-B to measure whether
   top-K recall pointers improve task-relevant discovery without introducing
   stale or out-of-scope references.
4. **Advisory launch enablement**: inject recall pointers into controller launch
   context only when the recall surface is healthy and scope checks pass.
5. **Flat recall retirement**: reduce dependence on grep-based memory discovery
   after tiered injection is stable, while keeping `MEMORY.md` as the always
   loaded index.
6. **Corpus hygiene loop**: feed stale-pointer findings into corpus rebuild and
   source cleanup work so recall quality improves over time.

## Acceptance Criteria for a Future Slice

- Launch context explicitly separates SSOT assertions, semantic recall
  pointers, and the `MEMORY.md` index.
- The implementation preserves the SSOT precedence invariant under malformed,
  missing, stale, or conflicting recall.
- Recall pointers are advisory and include verification metadata.
- Confidential-scope exclusion is enforced before embedding, querying, ranking,
  or injecting recall.
- BRAIN-B evaluation coverage demonstrates that the new launch context improves
  relevant pointer discovery without weakening deterministic precedence.
- Existing launch behavior remains available as a fallback.
