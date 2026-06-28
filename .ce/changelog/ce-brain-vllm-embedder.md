---
slug: ce-brain-vllm-embedder
date: 2026-06-28
kind: feat
scope: brain
issue: ce-ops#N/A
---

**feat(brain): wire Qwen3-Embedding-8B vLLM endpoint as new vllm-openai embedder backend.**

Add OpenAI-compatible HTTP endpoint embedder adapter (vllm-openai) backed by the local Qwen3-Embedding-8B vLLM server; re-ingest 1890-chunk corpus to a new embedder-keyed SQLite store; verify semantic lift on 5 Slice-A smoke queries.

- **Declared work class:** story
