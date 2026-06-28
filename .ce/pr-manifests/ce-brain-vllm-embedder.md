# PR path manifest — ce-ops#N/A · feat(brain): wire Qwen3-Embedding-8B vLLM endpoint as new vllm-openai embedder backend

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-brain-vllm-embedder` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=599236611e72a937d01c876856afd8f6802ed18af833728a0ec7c7e2fc613f26

```text
.ce/changelog/ce-brain-vllm-embedder.md
.ce/pr-manifests/ce-brain-vllm-embedder.md
.ce/reference/cli.generated.md
validators/creator_engine_validator/brain_embedding_openai_endpoint.py
validators/creator_engine_validator/brain_ingest_runtime.py
validators/creator_engine_validator/brain_recall_surface.py
validators/creator_engine_validator/ce_cli.py
validators/tests/unit/test_brain_embedding_openai_endpoint.py
```
