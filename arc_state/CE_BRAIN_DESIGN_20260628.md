# CE Company Brain — Design Document
## Status, Gaps, Next Slices, and Operator Decisions

**Date:** 2026-06-28  
**Author:** Implementer worker (Sonnet 4.6), grounded in live repo + ce-ops issue text.  
**Scope:** Design/research synthesis only. No source code modified.  
**Grounding sources:**
- ce-ops#79 (envelope ticket, 7 comments including ratification records)
- ce-ops#167/#176/#177/#178/#179/#180/#181 (all 7 sub-issues — all CLOSED/Done)
- ce-ops#344 / PR #609 (bootstrap overlay, MERGED 2026-06-28)
- ce-ops#166 (Knowledge SSOT parent, OPEN)
- `~/F6_recall_design.md` (F6 research+design deliverable, 2026-06-21)
- `.ce/state/research/RESUME_STATE_*` (session checkpoints)
- `validators/creator_engine_validator/brain_*.py` (live code)
- `docs/design/controller-bootstrap-ssot.json` + `scripts/gen-controller-bootstrap.py`

---

## 1. Problem and Goal

### 1.1 The recurring failure the brain is built to fix

CE's institutional knowledge has accumulated in three non-unified stores:

1. **MEMORY.md** — a flat-file, keyword-indexed, size-budgeted (historically 24.4 KB hard cut) per-agent notepad. When it exceeds budget, entries are silently truncated. Entries that land below the cut never load. Recall depends on a human or agent hand-writing a pointer to the right file and the right keyword appearing in a fixed budget window. Both fail silently.

2. **Resume-state checkpoints** (`RESUME_STATE_CE_DEV2_*.md`) — per-session hand-carried state capturing in-flight work, decisions, and fleet topology. They are point-in-time and unreferenced except by the controller who writes them. A controller starting after `/clear` must know to open the newest one; there is no enforced load.

3. **ce-ops issues, playbook files, and `.claude/agents/` briefs** — durable but queryable only by exact keyword or manual recall of a ticket number. Decisions and doctrines written here are invisible unless the controller recalls they exist.

**The failure class (ce-ops#79, grounded in lived evidence):** "durable != discoverable." Merge-throughput prior-art was saved in two places but undiscoverable when needed an hour later. Seat identity/topology memories existed below the MEMORY.md size cut and never loaded. The wrong fact ("codex lacks fan-out") sat in one controller's private auto-memory, invisible to peer controllers, and propagated as truth for a week. Orchestration knowledge (harvest sequence, dispatch territory-map check, subagent model routing) loads by recall-or-reflex, not enforcement — recurring misses after every `/clear`.

**The goal (two-layer):**

- **Deterministic layer (Knowledge SSOT, ce-ops#166):** Shared, verifiable facts live as machine-checkable assertions that every controller loads and checks independently at bootstrap, deterministically. A wrong fact is fixed once and corrects fleet-wide. Capabilities are PROBED against reality, not remembered. Drift-CI catches divergence between assertions and reality. This is what makes CE advance instead of re-learn.

- **Probabilistic layer (Recall, ce-ops#79 original scope):** Every durable artifact (memories, design docs, resume states, conclusions, ratifications) is embedded into a rebuildable vector index. At session start, top-K semantically-relevant memories surface for the current task without a hand-written pointer. This dissolves the size-budget truncation problem and the manual-pointer gap.

**Success criteria:**
- A controller after `/clear` loads deterministic facts (seat topology, capability probes, dispatch rules) without recalling that they exist — they are injected.
- A controller working on ticket T sees, without prompting, the design decisions, prior-art notes, and doctrines most semantically relevant to T.
- A wrong shared fact, corrected once via `ce brain correct`, is corrected for every controller on next bootstrap — no per-agent re-learning.
- The recall layer produces no false positives on verified facts (every recall hit is a pointer + as-of, never substitutes for a SSOT check).

---

## 2. Scope Boundary

### 2.1 What is built (as of 2026-06-28)

All seven sub-issues of ce-ops#79 are CLOSED and marked Done on the CE Program Board. The following is live in `main`:

**Deterministic SSOT layer (F1–F4, #167/#176/#177/#178):**
- `brain_runtime.py` — assertion ledger: `assert_claim`, `check_claim` (returns verified assertion or `unknown`, never guesses), `correct_claim`, hash-chained, schema-gated YAML at `.ce/state/brain/assertions.yaml`. No external datastore.
- `brain_probe.py` — capability probes: freshly interrogate named facts against reality at call time rather than storing them.
- Checks `ce_brain_assertions.py` + `ce_brain_drift.py` — drift-CI: schema + hash-chain validation; assertions verified vs reality in CI.
- `brain_bootstrap.py` — deterministic bootstrap projection: reads the local ledger, syncs from the repo-versioned authoritative ledger if present, emits a JSON-serializable bootstrap payload for controller/foreman sessions. Wires to `ce brain bootstrap` CLI command.

**Probabilistic recall layer (F6.1–F6.3, #179/#180/#181):**
- `brain_recall.py` — `EmbeddingAdapter` + `VectorStoreAdapter` protocol ABCs, `RecallRecord`, `RecallChunk`, `RecallKey`, `RecallHit` data types.
- `brain_sqlite_vec.py` — `SqliteVecStore` concrete backend (single `.db` file, pure-C SQLite extension, daemonless, aarch64-clean).
- `brain_embedding_gemma.py` — `EmbeddingGemma` local-first embedding adapter (EmbeddingGemma-300m; auto-routes to DGX GPU; CPU path for laptop/VPS).
- `brain_ingest_runtime.py` — ingest pipeline: enumerate durable artifacts → heading-aware chunk → stamp (`source_path`, `source_sha`, `scope`, `decay_class`) → embed → upsert with incremental re-embed by `source_sha`; `recall-manifest.yaml` tracks corpus sha-set + model metadata.
- `brain_recall_surface.py` — `BrainRecallSurface`: hybrid retrieve (sqlite-vec + FTS5 keyword) → RRF rank → top-K pointers; `SurfaceItem` tier-tagged (`ssot` | `recall`); `hydrate_session` method for session-start hydration; privacy guard (`requires_egress × scope` fail-closed).

**CLI surface (all shipped):**
```
ce brain assert      # append structured Knowledge-SSOT assertion
ce brain check       # return active assertion or unknown (never guesses)
ce brain correct     # append supersession + correction
ce brain verify      # validate ledger schema + hash chain
ce brain probe       # run named capability probes against reality
ce brain bootstrap   # emit deterministic JSON bootstrap payload
ce brain ingest      # derive/update rebuildable recall vector store
ce brain recall      # hybrid semantic+keyword recall, tier-tagged pointers
```

**Bootstrap overlay (ce-ops#344 / PR #609, MERGED 2026-06-28):**
- `docs/design/controller-bootstrap-ssot.json` — SSOT for canonical worker roles, foreman directive, safety floor, vocabulary mapping, worker selection policy.
- `scripts/gen-controller-bootstrap.py` — renders preview bootstrap artifacts from the JSON SSOT for human review before any live injection step.
- Status: preview-only. The live injection step (wiring `brain bootstrap` output into `~/.claude/CLAUDE.md` or the `ce launch` flow) is the **next ratification-gated act** — explicitly not yet done (preview_warning in JSON metadata).

**Knowledge assertions filed (ce-ops#310):**
- The `deterministic-citations` gotcha is persisted as a `ce brain assert --type gotcha` entry, with a backing design note at `.ce/brain/notes/deterministic-citations.md`. This is the first real use of the SSOT for a design-learning, demonstrating the mechanism end-to-end.

### 2.2 What is NOT yet built

1. **F5 — MCP server surface.** The brain surface currently exposes only a CLI (`ce brain recall`, `ce brain bootstrap`). The designed `ce_brain.*` MCP tools (`ce_brain.assert`, `ce_brain.probe`, `ce_brain.recall`, `ce_brain.pack`, `ce_brain.cite`) are not yet wired as an MCP server. Agents cannot call the brain as a tool; they must shell out to the CLI or use the Python API directly.

2. **Live bootstrap injection.** `ce brain bootstrap` emits a preview payload; wiring it into the controller launch path (writing the overlay into `~/.claude/CLAUDE.md` or injected into `ce launch`'s seat configuration) is explicitly gated as a separate ratification step (PR #609 metadata: "Do not install into live CLAUDE.md, AGENTS.md, or .claude/agents without a separate ratified injection step").

3. **Corpus population.** The `.ce/state/recall/` directory does not yet exist on the DGX (confirmed). The recall index has not been ingested. The brain's recall capability exists in code but has not been initialized against the live corpus (MEMORY.md, design docs, resume states).

4. **F7 — MEMORY.md migration.** The gradual migration from MEMORY.md to SSOT assertions + recall is designed but not started. MEMORY.md remains the dominant load mechanism at 258+ files. The "always-loaded CORE" / "on-demand recall tier" split has not been actuated.

5. **Phase 2 recall upgrades (deferred):** Cross-encoder rerank on DGX (F6.4); bi-temporal decay + background consolidation (F6.5, Letta sleep-time pattern); API embedding adapters behind the privacy gate (F6.6); LanceDB/pgvector graduate adapters (F6.7). Cognee graph recall and Zep/Graphiti bi-temporal graph remain Operator-gated future features.

6. **`ce brain` as a CE product feature.** The brain is currently a CE internal ops tool. Whether it surfaces as a product capability for CE-governed projects is an open Operator decision (secondary scope per ce-ops#79, but relevant to the NVIDIA pitch arc's "dogfood exhibit" framing).

### 2.3 How the layers compose

```
        ┌──────────────────────────────────────────────────────────┐
        │        CE Brain — surface (CLI today; MCP = F5, gap)      │
        │  SSOT tools: assert / check / correct / verify / probe    │
        │  Recall tools: ingest / recall / bootstrap               │
        │  (designed pack / cite / MCP not yet wired)              │
        └────────────────┬─────────────────────┬───────────────────┘
                         │ DETERMINISTIC        │ PROBABILISTIC
        ┌────────────────▼──────────┐   ┌───────▼──────────────────────────┐
        │ KNOWLEDGE SSOT (BUILT)     │   │ RECALL LAYER (BUILT, NOT INGESTED)│
        │ brain_runtime.py           │   │ brain_recall.py (ABCs)           │
        │ brain_probe.py             │   │ brain_sqlite_vec.py (store)      │
        │ brain_bootstrap.py         │   │ brain_embedding_gemma.py (embed) │
        │ checks/ce_brain_*.py       │   │ brain_ingest_runtime.py          │
        │ .ce/state/brain/           │   │ brain_recall_surface.py          │
        │   assertions.yaml          │   │ .ce/state/recall/ (NOT YET)      │
        └────────────────────────────┘   └──────────────────────────────────┘
                         │                         │ derived from
        ┌────────────────▼─────────────────────────▼───────────────────────┐
        │ FILES = SOURCE OF TRUTH (markdown): MEMORY.md, memory/*.md,      │
        │   .ce/state/research/ (resume-states, design docs), .ce/brain/   │
        │   notes/, .ce/changelog/                                          │
        │ DERIVED INDEX (gitignored, rebuildable): .ce/state/recall/*.db   │
        └───────────────────────────────────────────────────────────────────┘

COMPOSES WITH:
  #344/#609 bootstrap overlay  →  preview generates; live injection = next ratification
  #32 context lifecycle        →  at resume, brain.pack(task) hydrates; #32 drives timing
  ce launch                    →  should inject bootstrap payload into seat config (gap)
```

**What the brain subsumes vs leaves alone:**
- Subsumes: the recall/discovery burden currently carried by MEMORY.md size-budgeted always-load + manual pointers.
- Leaves alone: MEMORY.md as the human-readable source-of-truth notepad (files stay SoT; brain is a derived index over them).
- Leaves alone: resume-state checkpoints as the session-continuity mechanism (#32 drives; brain augments resume hydration when F5/pack is wired).
- Does NOT subsume: per-agent scratch context, which stays in agent memory by design (shared verifiable facts → SSOT; per-agent scratch → memory files).

---

## 3. Architecture Options and Recommendation

The architecture was finalized and ratified on 2026-06-21 by the Operator (sha e803962967…, n1_solo) and is now built. The section below summarizes what was decided, for what reasons, and what remains to decide.

### 3.1 The ratified two-layer design

**Layer 1: Deterministic Knowledge SSOT** — CE-native, no new external datastore. Hash-chained, schema-gated assertion ledger on the existing evidence-spine idiom. Capabilities probed at invocation time, not stored. Drift-CI asserts assertions match reality. Every controller loads the same ledger at bootstrap and gets the same answers — no per-agent divergence possible.

*Why not a vector store for this layer:* A probabilistic retrieval mechanism cannot satisfy the requirement "every controller checks independently and DETERMINISTICALLY." Semantic recall has no notion of "this assertion is false against reality." The SSOT layer must be deterministic, verifiable, and independently checkable — these properties come from the hash-chain + schema-gated ledger idiom CE already uses for evidence, not from a vector store.

**Layer 2: Probabilistic Recall** — sqlite-vec (single rebuildable `.db` file, pure-C daemonless, aarch64-clean, FTS5 hybrid in-process), EmbeddingGemma-300m local-first (privacy by construction; <200MB RAM on any host; GPU-accelerated automatically on DGX). Hybrid retrieve (vector + FTS5/BM25) → RRF rank → top-K pointers with `as-of` stamps. Each hit is a pointer, not an answer — the agent re-reads the live file or runs `ce brain check` for any load-bearing fact.

*Alternatives preserved (per user-choice doctrine, behind the adapter ABCs):*
- Vector store: txtai (prior pick, in-process), LanceDB (ANN + dataset versioning, scale-up), pgvector (server tier, opt-in).
- Embeddings: bge-m3 (MIT/long-ctx), Qwen3-8B (DGX power tier, #1 MTEB Apache-2.0), Voyage voyage-3.5-lite (consent-gated API fallback at $0.02/1M).
- Scale path: Cognee (graph recall, Operator-gated) or Zep/Graphiti (bi-temporal graph, deferred Phase 3).

**Privacy posture (ratified):** local-only embeddings for the ce-ops (CONFIDENTIAL) corpus; API embeddings opt-in per-scope with explicit consent. Enforced by `EmbeddingAdapter.requires_egress × scope` fail-closed gate; default config ships no API key. Public corpus (`creator-engine` OSS) may use API embeddings freely if configured.

**Brain-origin model (ratified):** solo = local file, small team = git-synced derived index, scale = server. CE's own fleet binding: brain-origin on the DGX (heavy ingest routes there; every other host rebuilds from the manifest or syncs the index).

### 3.2 What remains architecturally open

The two-layer design and the embedding/store choices are ratified. What remains undecided is:

1. Whether the brain graduates from an internal ops tool to a CE **product feature** (affects how the adapter surface is packaged and documented).
2. How the brain composes with the #344 bootstrap overlay — specifically, whether `ce brain bootstrap` output is the canonical injection mechanism or whether the JSON SSOT in `controller-bootstrap-ssot.json` diverges into its own injection path.
3. The corpus boundary — which artifacts get ingested (just MEMORY.md + design docs, or also session transcripts, ce-ops issue text, PR bodies)?

---

## 4. Build Slices (Next Work)

All 7 original slices are shipped. The remaining work is activation and extension.

### Slice A — Corpus initialization + first recall (smallest shippable, ~story size)
**Gate:** Operator decision on corpus scope (§5 Decision 1).  
**What:** Run `ce brain ingest` against the live MEMORY.md + `.ce/state/research/` design docs on the DGX. Verify the `.ce/state/recall/` index is built and `ce brain recall "dispatch territory map"` returns relevant hits. Record the initialization in a brain assertion. No new code; activates the built recall capability.  
**Files:** `.ce/state/recall/` (gitignored, derived), `.ce/state/recall/manifest.yaml` (tracked), optionally a one-time ingest runbook in `docs/operations/`.  
**Why smallest:** Zero new code. Confirms the end-to-end path works on the real corpus on real hardware (especially the EmbeddingGemma + sqlite-vec stack on the GB10 aarch64 — the open build-time verification flag from the F6 design doc).

### Slice B — Live bootstrap injection (story size, Operator-gated ratification)
**Gate:** Operator ratification of the injection form (§5 Decision 2).  
**What:** Wire `ce brain bootstrap` output into the controller launch path. Write the overlay into `~/.claude/CLAUDE.md` (or inject via `ce launch`'s `--setting-sources` mechanism) so every controller session and post-`/clear` resume deterministically loads the Knowledge-SSOT assertions. This is the activation step PR #609 explicitly gates.  
**Files:** `scripts/install-bootstrap-overlay.py` or an extension of the existing `gen-controller-bootstrap.py`; a change to `ce launch` or the installer.  
**Why next after A:** The bootstrap overlay has no value until the SSOT ledger is populated; corpus init (Slice A) makes the ledger meaningful.

### Slice C — F5 MCP server surface (~story size)
**Gate:** Operator decision on MCP exposure scope (§5 Decision 3).  
**What:** Wrap `brain_recall_surface.BrainRecallSurface` and `brain_runtime` functions as an MCP server (`ce_brain_mcp.py`) exposing `ce_brain.assert`, `ce_brain.check`, `ce_brain.probe`, `ce_brain.recall`, `ce_brain.pack`, `ce_brain.cite`. Wire into the `ce launch` MCP config. Each tool carries the tier tag (`verified` | `advisory`) in its response schema. This is the designed F5 — absent today.  
**Files:** `validators/creator_engine_validator/brain_mcp.py`; updates to `ce launch` MCP config.  
**Why high-leverage:** Once wired, agents can call the brain as a tool during sessions — the designed recall modality. Without F5, recall is CLI-only (out-of-band, manual).

### Slice D — MEMORY.md migration, domain 1 (story size)
**Gate:** Operator decision on migration pace (§5 Decision 4).  
**What:** Migrate the seat-identity / host-topology entries from MEMORY.md to `ce brain assert` SSOT entries (these are the most load-bearing and most often missed below the size cut). Shrink MEMORY.md; let the recall layer surface the rest on demand. Update the CORE always-loaded markdown to a smaller, stable set of invariants.  
**Files:** `.ce/state/brain/assertions.yaml` (new entries); MEMORY.md (pruned); `.claude/projects/.../memory/MEMORY.md` shrunk.  
**Why:** This is ce-ops#166's "first domain" (ce-ops#162 target, referenced repeatedly in design history). It directly fixes the "seat identity didn't load because it was below the 24.4KB cut" failure that motivated the brain.

### Slice E — Corpus auto-ingest hook (feature size)
**What:** Add an ingest trigger to the harvest/merge workflow (or a git post-merge hook) so that when new MEMORY.md entries or design docs are committed, `ce brain ingest --incremental` runs automatically, keeping the recall index current. Add a `ce brain status` command showing index freshness vs corpus mtime.  
**Files:** Hook script or `ce-harvest` skill extension; `ce brain status` CLI sub-command.  
**Why:** Without this, the recall index drifts stale as new memories accumulate. The build-time manifest tracks `source_sha` for incremental re-embed; the trigger is what keeps it live.

### Slice F — Phase 2 recall (epic, deferred)
Cross-encoder rerank (DGX), bi-temporal decay + background consolidation, API embedding adapters, LanceDB graduate adapter. File as separate features when Slices A-C are live and recall quality can be measured.

---

## 5. Key Scope Decisions for the Operator

The following decisions are gated on Operator authority and cannot be made by the controller or implementer workers. They are surfaced in priority order.

**Decision 1 — Corpus boundary: what gets ingested into the recall index**  
Should the recall corpus include: (a) MEMORY.md + memory/*.md files only; (b) (a) plus `.ce/state/research/` design docs and resume-states; (c) (b) plus session transcripts (`.jsonl` / `.readable.md`); (d) (b) plus ce-ops issue text (requires periodic export/sync from GitHub API since ce-ops is private)?  
Option (b) is the recommended default: it covers the known "durable but undiscoverable" failure cases (merge prior-art in design docs, topology in resume-states) without the storage overhead of full transcripts. Option (c) adds significant volume and may dilute recall quality. Option (d) closes the issue-text gap but adds a periodic sync dependency.  
*Why Operator:* wider corpus = more surface area for confidential content + a storage/re-embed cost decision on the DGX.

**Decision 2 — Live bootstrap injection form and authority**  
PR #609 (MERGED) explicitly withholds live injection behind "a separate ratified injection step." The injection writes to `~/.claude/CLAUDE.md` or modifies `ce launch` seat configuration — mutating the controller's live session configuration. This is an installation act (aligns with `ce-authority-attaches-to-form.md`). Who ratifies it, in what form, and is the `ce-root-v1` signature required?  
*Recommended:* Operator-ratified form-echo; if the injection targets `~/.claude/CLAUDE.md` on the DGX it is a host-mutation and warrants the same posture as spec-signing (non-delegable).  
*Why Operator:* live injection of bootstrap content into the controller's session is a high-authority act; it is explicitly gated in the merged PR metadata.

**Decision 3 — MCP exposure scope: internal ops tool vs product feature**  
The `brain_recall_surface.BrainRecallSurface` Python API exists but the F5 MCP server is not built. When built, who can call it? Options: (a) CE fleet controllers only (internal ops tool, no product surface); (b) CE-governed project seats via the per-seat MCP config (product feature, same tool surface available to users' agents); (c) (b) with a separate product-branded API/namespace.  
Option (a) is the safe incremental default — activate internally, prove quality, then extend. Option (b) enables the "dogfood → NVIDIA pitch" exhibit (CE manages its own memory the AI-native way) and makes the brain a product differentiator.  
*Why Operator:* the product angle changes the documentation posture (public docs product-lens doctrine), packaging, and the confidentiality boundary (product users must not see CE's internal ce-ops corpus).

**Decision 4 — MEMORY.md migration pace**  
The migration from MEMORY.md to SSOT assertions + recall is additive and gradual by design. Three pace options: (a) migrate only the most critical entries (seat identity, host topology, capability probes) and leave the rest in MEMORY.md indefinitely; (b) migrate all shared verifiable facts to SSOT + let recall handle the rest, shrinking MEMORY.md to a small invariant notepad over several slices; (c) move aggressively in one slice.  
Recommended: (b) domain-by-domain, starting with the seat-identity/topology cluster (the lived failure case). The CORE always-loaded markdown shrinks in proportion; (c) is too risky (recall must be confirmed accurate on real queries before MEMORY.md entries are removed).  
*Why Operator:* the pace decision changes how long the controller depends on MEMORY.md as the primary recall mechanism, and what size it must remain.

**Decision 5 — Confidential corpus: ce-ops issue text ingestion**  
If ce-ops issue text is included in the recall corpus (Decision 1 option d), it requires a periodic GitHub API export and an explicit classification that ce-ops content (which contains internal architecture decisions, competitive intel, and private references) is in-scope for local embedding. This content MUST NEVER be sent to an external embedding API, and MUST NEVER appear in the public `creator-engine` product surface.  
If issue text is excluded, design decisions recorded only in ce-ops comments (not copied to design docs or memory files) remain undiscoverable. The recommended bridge: enforce a "decisions in design docs, not only in issue comments" discipline and ingest the design docs (Decision 1 option b).  
*Why Operator:* this is a confidentiality boundary decision (ties `ce-public-private-ops-architecture.md` + `ce-public-docs-product-lens-doctrine.md`); only the Operator can set the boundary.

**Decision 6 — Brain-as-product confidentiality architecture**  
If the brain becomes a product feature (Decision 3 option b or c), CE must ensure the brain's MCP surface, when exposed to a user's CE-governed project, cannot reveal CE's internal corpus. The designed `scope` + `requires_egress` mechanism handles the embedding privacy (confidential corpus stays local), but it does not prevent a product user from querying the brain's recall surface and receiving pointers into CE's internal design docs. A product instance of the brain must operate against a *user-scoped* corpus (their project's docs, not CE's internal files). Is this a per-install corpus isolation (the clean model), or a namespace/scope filter on the shared index?  
Recommended: per-install corpus isolation — a product user's brain is initialized against their own project's artifacts only; CE's internal brain (on the DGX) is CE-ops-only. Two instances, not one shared with scope filters.  
*Why Operator:* this decision determines the product architecture (one shared service with scope isolation vs per-install corpus) and has compliance implications.

---

## 6. Risks and Dependencies

### 6.1 GB10 / aarch64 wheel verification (open build-time flag)

The F6 design doc explicitly notes: "verify EmbeddingGemma runtime + store wheel import on the GB10 at F6.2." The sub-issues are CLOSED but the `.ce/state/recall/` directory does not exist — the index has never been built on the DGX. Until `ce brain ingest` completes a full run on the DGX with EmbeddingGemma + sqlite-vec, the aarch64 compatibility is unconfirmed on the GB10. The code exists; the hardware validation is still the open risk.

*Mitigation:* Slice A (corpus init) is the verification step. If EmbeddingGemma fails on GB10, the fallback is nomic-embed-text-v1.5 via Ollama (already supported by the `OllamaAdapter` protocol) or the CPU-only torch path.

### 6.2 Recall quality vs MEMORY.md dependency

The recall layer cannot replace MEMORY.md as the primary controller memory mechanism until its recall quality is confirmed against real CE queries ("dispatch territory map", "harvest sequence", "model routing", "seat topology"). Premature migration (Decision 4 option c) before quality is validated risks degrading controller knowledge load below current MEMORY.md reliability. The CORE always-loaded markdown must cover the true invariants for the transition period.

### 6.3 Bootstrap injection mutation risk

Live injection of the bootstrap payload into `~/.claude/CLAUDE.md` modifies the controller's session configuration permanently. A wrong assertion in the ledger that gets injected at bootstrap propagates to every session. The hash-chained ledger and drift-CI guards mitigate fabricated assertions; the `ce brain verify` CI check catches hash-chain tampering. But the injection gate (Decision 2) must include a staged test on a non-controller seat before production rollout.

### 6.4 Public/private confidentiality boundary

The corpus contains internal ce-ops references, competitive intel, and architecture decisions that must not appear in: (a) the public `creator-engine` repository, (b) public product documentation, (c) a product user's recall surface. Current mitigations: the `scope` field on every assertion/recall record; the gitignored `.ce/state/recall/` derived index; the `requires_egress × scope` privacy gate on embedding adapters. The gap: if F5 (MCP server) is exposed as a product feature without per-install corpus isolation (Decision 6), a user's agent could receive pointers to CE's internal design docs.

The `ce-public-private-ops-architecture.md` doctrine (ADR-0001: PUBLIC `creator-engine` vs PRIVATE `ce-ops`; default PRIVATE) and the `ce-public-docs-product-lens-doctrine.md` must be enforced structurally: the product brain instance must be initialized against a user-scoped corpus only.

### 6.5 Composition with ce-ops#32 (context lifecycle)

ce-ops#32 (autonomous context lifecycle — harness-measured usage → threshold → state-save → clear → resume) is open. The brain is the substrate #32's resume step drives: at resume, `ce_brain.pack(task)` hydrates the session with task-relevant context. Until #32 is built, the hydration step is manual (the controller shells out to `ce brain recall`). The seam is clean; the dependency is one-directional (#32 calls the brain, not vice versa).

### 6.6 Model-bound index

The recall index is model-bound: every vector is stamped with `{provider, model, dim}`. Switching embedding models (e.g. from EmbeddingGemma-300m to Qwen3-8B for quality) requires a full re-embed of the corpus. The manifest tracks the model used; `ce recall rebuild` is the recovery path. Cost at CE's corpus scale (~258 files × ~3 chunks each ≈ ~10³ documents) is low on the DGX GPU; cost grows with transcript ingestion.

### 6.7 No MCP server yet (F5 gap)

Until F5 is built (Slice C), agents cannot call the brain as a tool. They can shell out to `ce brain recall` via Bash or call the Python API directly from within the validator package. The CLI path is functional but breaks the designed "one MCP surface" model. The F5 gap means that the designed `ce_brain.pack(task)` session-hydration tool call (the central mechanism for surfacing relevant context at session start) is not yet available to agent sessions.

---

## 7. What the Brain is NOT

- Not a replacement for git or the hash-chain evidence spine. The brain derives from files; files stay authoritative.
- Not a secret store. The ledger and recall index must never embed host/port/credential/account identifiers (the `evidence_sink.py` no-secrets rule applies; the F1 schema already forbids secret-shaped claim fields).
- Not a replacement for per-agent scratch context (MEMORY.md files continue to serve as personal notepads for per-agent ephemeral state; the SSOT is for shared verifiable facts only).
- Not a knowledge graph (Cognee/Graphiti are deferred, Operator-gated; the current stack is vector + keyword hybrid, not a graph).

---

## 8. Summary: Current State vs Target State

| Capability | Status |
|---|---|
| SSOT assertion ledger (F1) | BUILT + ACTIVE (`brain_runtime.py`, ledger at `.ce/state/brain/`) |
| Capability probes (F2) | BUILT (`brain_probe.py`, `ce brain probe`) |
| Drift-CI (F3) | BUILT (`checks/ce_brain_drift.py`, runs in CI) |
| Born-knowing bootstrap (F4) | BUILT (`brain_bootstrap.py`, `ce brain bootstrap`) |
| MCP server surface (F5) | NOT BUILT (Slice C) |
| Bootstrap live injection | NOT DONE (Slice B; Operator-gated ratification) |
| Recall adapter ABCs (F6.1) | BUILT (`brain_recall.py`) |
| sqlite-vec + EmbeddingGemma + ingest (F6.2) | BUILT, NOT INITIALIZED (`.ce/state/recall/` absent) |
| Hybrid recall + session hydration (F6.3) | BUILT, NOT WIRED INTO SESSIONS |
| Corpus ingested | NOT YET (Slice A — first activation step) |
| MEMORY.md migration | NOT STARTED (Slice D; awaits Slice A quality confirmation) |
| Auto-ingest hook | NOT BUILT (Slice E) |
| Phase 2 (rerank, decay, API adapters) | DEFERRED |
| Brain as CE product feature | UNDECIDED (Decision 3) |
