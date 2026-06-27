# Design learning (gotcha): deterministic citations for doc-grounded agents

Scope: any outward-facing, doc-grounded / customer-support agent (the general
pattern; CE's own `ce ask` is one instance).

Type: architecture gotcha — a non-obvious essential that the naive build gets
wrong. Indexed in the Knowledge-SSOT ledger (`.ce/brain/assertions.yaml`,
type `gotcha`, scope `global`); this note is its content-addressed evidence.

## Principle

Ground the agent through **docs-as-skills** — load specific, allowlisted doc
files on demand — rather than RAG / embedding-retrieval or context-stuffing.
Because the agent loads exact files, it can cite the **exact source file and
section it loaded**: deterministic, verifiable provenance, not a fuzzy
retrieved chunk or an unsourced claim.

## Why it is load-bearing

1. **It makes cite-or-refuse enforceable.** A hard "cite a real source or say
   I-don't-know" contract is only enforceable if a citation can be *checked* to
   point at a real loaded doc. Deterministic citations are that checkable
   anchor; fuzzy retrieval is not.
2. **Verifiable trail for the user.** Every answer resolves to a real file the
   user can open.
3. **Confidentiality is enforced at bundle-build time.** The agent can only
   cite what is in its allowlisted bundle, so it cannot leak what it never
   loaded ("can't leak what you never loaded").
4. **Freshness is checkable.** Stamp the loaded doc's sha and bind it to the
   release-parity guard, so stale answers are detectable.

## Why it is a GOTCHA (the non-obvious part)

The naive build reaches for RAG / embeddings, which gives fuzzy provenance and
lets the model paraphrase or hallucinate sources. **Without deterministic
citations you cannot enforce cite-or-refuse**, so hallucinated install steps and
invented sources become the dominant failure mode of a customer-facing agent.
Deterministic citation is the single mechanism that makes accuracy, zero-leak,
and the refusal posture work *together* — remove it and all three degrade.
