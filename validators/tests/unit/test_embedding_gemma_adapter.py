from __future__ import annotations

import builtins
import importlib
import sys
from types import SimpleNamespace

import pytest


def _gemma_module(monkeypatch):
    sys.modules.pop("creator_engine_validator.brain_embedding_gemma", None)
    blocked = {"sentence_transformers", "torch"}
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.partition(".")[0] in blocked:
            raise AssertionError(f"heavy dependency imported at module import time: {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    return importlib.import_module("creator_engine_validator.brain_embedding_gemma")


class FakeEmbeddingModel:
    def __init__(self, *, dim: int = 768) -> None:
        self.dim = dim
        self.calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def encode(self, texts, **kwargs):
        values = tuple(texts)
        self.calls.append((values, kwargs))
        rows = []
        for text in values:
            seed = sum(text.encode("utf-8")) % 1000
            rows.append([float(seed + index) for index in range(self.dim)])
        return rows


def _torch(cuda: bool = False, mps: bool = False):
    return SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: cuda),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps)),
    )


def test_module_import_has_no_heavy_dependency_requirement(monkeypatch):
    previously_loaded = {name: name in sys.modules for name in ("sentence_transformers", "torch")}
    module = _gemma_module(monkeypatch)

    assert module.DEFAULT_MODEL_ID == "google/embeddinggemma-300m"
    for name, was_loaded in previously_loaded.items():
        if not was_loaded:
            assert name not in sys.modules


def test_default_adapter_is_local_first_and_requires_no_egress():
    from creator_engine_validator.brain_embedding_gemma import EmbeddingGemmaAdapter

    adapter = EmbeddingGemmaAdapter(model=FakeEmbeddingModel())

    assert adapter.requires_egress is False
    assert adapter.model_id == "google/embeddinggemma-300m"
    assert adapter.dim == 768


def test_missing_local_model_path_fails_with_clear_error():
    from creator_engine_validator.brain_embedding_gemma import (
        BrainEmbeddingGemmaUnavailable,
        EmbeddingGemmaAdapter,
    )

    adapter = EmbeddingGemmaAdapter()

    with pytest.raises(BrainEmbeddingGemmaUnavailable, match="local model_path, cache_dir, or injected model"):
        adapter.embed(("hello",))


def test_missing_dependency_for_local_path_fails_without_network_fallback(tmp_path, monkeypatch):
    from creator_engine_validator.brain_embedding_gemma import (
        BrainEmbeddingGemmaUnavailable,
        EmbeddingGemmaAdapter,
    )
    import creator_engine_validator.brain_embedding_gemma as gemma

    real_import_module = importlib.import_module

    def missing_import(name):
        if name == "sentence_transformers":
            raise ImportError(name)
        return real_import_module(name)

    monkeypatch.setattr(gemma.importlib, "import_module", missing_import)

    adapter = EmbeddingGemmaAdapter(model_path=tmp_path)

    with pytest.raises(BrainEmbeddingGemmaUnavailable, match="sentence_transformers is not installed|No model weights"):
        adapter.embed(("hello",))


def test_injected_fake_model_embeds_deterministic_vectors():
    from creator_engine_validator.brain_embedding_gemma import EmbeddingGemmaAdapter

    model = FakeEmbeddingModel()
    adapter = EmbeddingGemmaAdapter(model=model)

    first = adapter.embed(("alpha", "beta"))
    second = adapter.embed(("alpha", "beta"))

    assert first == second
    assert len(first) == 2
    assert len(first[0]) == 768
    assert len(first[1]) == 768
    assert first[0][:3] == (518.0, 519.0, 520.0)
    assert model.calls[0][0] == ("alpha", "beta")


def test_output_dim_may_be_reduced_to_known_dimensions():
    from creator_engine_validator.brain_embedding_gemma import EmbeddingGemmaAdapter

    adapter = EmbeddingGemmaAdapter(model=FakeEmbeddingModel(), output_dim=128)
    vectors = adapter.embed(("alpha",))

    assert adapter.dim == 128
    assert len(vectors) == 1
    assert len(vectors[0]) == 128


def test_rejects_unknown_output_dim():
    from creator_engine_validator.brain_embedding_gemma import BrainEmbeddingGemmaInvalid, EmbeddingGemmaAdapter

    with pytest.raises(BrainEmbeddingGemmaInvalid, match="output_dim"):
        EmbeddingGemmaAdapter(model=FakeEmbeddingModel(), output_dim=384)


def test_device_selection_prefers_cuda_then_mps_then_cpu():
    from creator_engine_validator.brain_embedding_gemma import select_best_device

    assert select_best_device(_torch(cuda=True, mps=True)) == "cuda"
    assert select_best_device(_torch(cuda=False, mps=True)) == "mps"
    assert select_best_device(_torch(cuda=False, mps=False)) == "cpu"
    assert select_best_device(SimpleNamespace()) == "cpu"


def test_local_loader_uses_gpu_and_local_files_only_with_fake_modules(tmp_path):
    from creator_engine_validator.brain_embedding_gemma import EmbeddingGemmaAdapter

    captured: dict[str, object] = {}

    class FakeSentenceTransformer:
        def __init__(self, source, **kwargs):
            captured["source"] = source
            captured["kwargs"] = kwargs
            self.model = FakeEmbeddingModel()

        def encode(self, texts, **kwargs):
            return self.model.encode(texts, **kwargs)

    st_module = SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)
    adapter = EmbeddingGemmaAdapter(
        model_path=tmp_path,
        sentence_transformers_module=st_module,
        torch_module=_torch(cuda=True),
    )

    vectors = adapter.embed(("hello",))

    assert captured["source"] == str(tmp_path)
    assert captured["kwargs"] == {"device": "cuda", "local_files_only": True}
    assert adapter.device == "cuda"
    assert len(vectors) == 1
    assert len(vectors[0]) == 768


def test_vector_count_and_dim_are_validated():
    from creator_engine_validator.brain_embedding_gemma import BrainEmbeddingGemmaInvalid, EmbeddingGemmaAdapter

    class WrongCount:
        def encode(self, texts, **kwargs):
            return [[0.0] * 768]

    class WrongDim:
        def encode(self, texts, **kwargs):
            return [[0.0] * 767 for _ in texts]

    with pytest.raises(BrainEmbeddingGemmaInvalid, match="1 vectors for 2 texts"):
        EmbeddingGemmaAdapter(model=WrongCount()).embed(("one", "two"))

    with pytest.raises(BrainEmbeddingGemmaInvalid, match="expected at least 768"):
        EmbeddingGemmaAdapter(model=WrongDim()).embed(("one",))
