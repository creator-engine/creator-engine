# BRAIN EMBEDDER DECISION — live thread — 2026-06-28 ~11:15Z (Operator-driven)

> Companion to RESUME_STATE_CE_DEV2_DAYARC_20260628T1020Z.md (full fleet state). This file = the embedder sub-decision only.

## CONTEXT
Brain Slice A is ACTIVATED with a PLACEHOLDER deterministic embedder → recall is keyword/BM25-only. Need a REAL embedder for semantic recall. Brain = ratified PRODUCT FEATURE → embedder license MUST allow commercial use + redistribution. Operator steered: SELF-HOST via the DGX's vLLM (GB10, 121GB unified — big models fine), not a tiny CPU model.

## ⚠️ HARD PREREQUISITE (any model): GB10 vLLM build
GB10 = Grace-Blackwell SM121/aarch64. Stock vLLM wheels ship kernels only through SM120 → `pip install vllm` crashes / eager-mode on this box. MUST use community Docker `Hellohal2064/vllm-dgx-spark-gb10` OR from-source build (CUDA-13 + SM121, ~20-30min) via `eelbaz/dgx-spark-vllm-setup`. Refs: vLLM issues #36821 (open), #31128, PR #37700 (in review). This gates ALL vLLM-on-GB10 work.

## GROUNDED MODEL COMPARISON (research aef0f69e, 2026-06-28; sources in transcript)
| Model | License | Commercial | vLLM embed | MTEB retrieval | Specs |
|---|---|---|---|---|---|
| **Qwen3-Embedding-8B** | Apache-2.0 | ✅ | ✅ confirmed (`--runner pooling`) | ~70.6 (#1 multiling mid-2025) | 8B, 4096-dim MRL, 32K ctx, ~16GB |
| KaLM-Embedding-Gemma3-12B | Apache-2.0 | ✅ | ✅ (Gemma3 supported) | ~75.7 (HIGHEST known) | 12B, ~24GB — future ceiling |
| Harrier-OSS-0.6B (MS) | MIT | ✅ | ⚠️ UNCONFIRMED | 69.0 MMTEB-v2 (Mar2026) | 0.6B, ~1.2GB, 94 langs, Qwen3-arch |
| BGE-M3 (BAAI) | MIT | ✅ | ✅ confirmed | ~57.9 | 568M, hybrid dense+sparse, safe fallback |
| ~~Jina-v3~~ / ~~NV-Embed-v2~~ | CC-BY-NC | ❌ DISQUALIFIED | — | — | non-commercial |
| ~~NVIDIA Llama-Embed-Nemotron-8B~~ | NSCL-v1 + Llama-3.1 | ❌ DISQUALIFIED | yes (--trust-remote-code) | 69.46 MMTEB mean (#1 Borda) | NON-COMMERCIAL (research a7184eb); even on merit Qwen3-8B mean 70.58 > 69.46. NVIDIA commercial embedder = llama-nemotron-embed-1b-v2 (NVOML) but 1B/lower. |

## CURRENT RECOMMENDATION = Qwen3-Embedding-8B
Only candidate hitting every hard constraint: Apache-2.0 (clean for product) + vLLM-confirmed + top multilingual retrieval + 32K ctx + trivial 16GB. KaLM-12B = higher ceiling once vLLM/GB10 proven. Harrier-0.6B needs vLLM-compat probe.

## OPEN (in flight at checkpoint)
- Operator asked to also evaluate **NVIDIA Llama-Embed-Nemotron-8B** (NVIDIA-hw-optimized + pitch angle). Research worker a7184eb running. GATING Q = its LICENSE (NVIDIA embed models often CC-BY-NC; "Llama-Embed" may carry Llama Community License). → ON return: present head-to-head vs Qwen3-8B + license verdict → Operator picks → then build.

## NEXT STEPS once model chosen
1. Build/install vLLM on GB10 (community Docker or from-source) — prerequisite lane (implementer, host setup).
2. Serve chosen model: `vllm serve <model> --runner pooling` → local `/v1/embeddings`.
3. Point brain embedder adapter at the local vLLM endpoint (may need adapter generalization beyond brain_embedding_gemma.py — small build lane).
4. Re-ingest conservative corpus (`ce brain ingest --embedder <vllm-endpoint>`); re-run 5 smoke queries; verify SEMANTIC lift vs keyword baseline; record assertion.
