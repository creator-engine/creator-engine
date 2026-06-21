"""F6.3 brain recall surface: hybrid ranking, pointer return, SSOT precedence,
session hydration, and privacy fail-closed — all offline and deterministic.

Network / model dependencies (``sentence_transformers``, ``torch``) are blocked
at import time so this slice can never reach for a model download in CI.
"""

from __future__ import annotations

import builtins
import importlib
import sys
from pathlib import Path

import pytest

from creator_engine_validator import brain_recall, brain_runtime
from creator_engine_validator import brain_ingest_runtime as ingest
from creator_engine_validator import brain_recall_surface as surface
from creator_engine_validator.brain_recall import (
    BrainRecallPrivacyRefused,
    DeterministicFakeEmbedding,
)
from creator_engine_validator.brain_sqlite_vec import SqliteVecStore

AS_OF = "2026-06-21T00:00:00Z"
LATER_AS_OF = "2026-12-31T00:00:00Z"


@pytest.fixture(autouse=True)
def _block_heavy_deps(monkeypatch):
    """Fail loudly if any test path imports a network/model dependency."""

    blocked = {"sentence_transformers", "torch", "huggingface_hub"}
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.partition(".")[0] in blocked:
            raise AssertionError(f"recall surface must not import heavy dependency: {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    # Force a clean import under the guard so module-load never pulls a model.
    sys.modules.pop("creator_engine_validator.brain_recall_surface", None)
    importlib.import_module("creator_engine_validator.brain_recall_surface")


def _write(corpus: Path, name: str, body: str) -> None:
    (corpus / name).write_text(body, encoding="utf-8")


def _ingest(tmp_path: Path, scope: str = "public") -> tuple[Path, Path]:
    corpus = tmp_path / "corpus"
    corpus.mkdir(exist_ok=True)
    _write(
        corpus,
        "merge.md",
        "# Merge throughput\n\nReviewed-vs-merged head merge queue prior art for the merge tax.\n",
    )
    _write(
        corpus,
        "topology.md",
        "# Seat identity topology\n\nThe DGX spark host controller seat map and topology.\n",
    )
    state_root = tmp_path / ".ce" / "state"
    db_path = state_root / "brain" / "recall.sqlite"
    ingest.ingest_markdown(
        sources=[str(corpus)],
        state_root=str(state_root),
        db_path=str(db_path),
        scope=scope,
        as_of=AS_OF,
    )
    return state_root, db_path


def test_hybrid_recall_returns_context_relevant_top_k(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))

    result = surf.recall("merge queue throughput prior art", top_k=5)

    recall_items = result.recall_items
    assert recall_items, "hybrid recall should return at least one pointer"
    # The merge chunk shares keyword overlap with the query, so the keyword leg
    # lifts it above the topology chunk via reciprocal-rank fusion.
    assert recall_items[0].source_path == "merge.md"
    assert {item.source_path for item in recall_items} == {"merge.md", "topology.md"}


def test_recall_is_deterministic(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    first = surf.recall("merge queue", top_k=5).to_dict()
    second = surf.recall("merge queue", top_k=5).to_dict()
    assert first == second


def test_recall_hit_is_pointer_with_as_of_not_inlined_content(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))

    item = surf.recall("merge queue prior art", top_k=1).recall_items[0]
    payload = item.to_dict()

    # Pointer fields present, body absent: the agent re-verifies against source.
    assert payload["source_path"] == "merge.md"
    assert payload["chunk_ref"] == "heading:merge-throughput"
    assert payload["content_hash"]
    assert payload["as_of"] == AS_OF
    assert payload["verify_against"] == "merge.md"
    assert "text" not in payload
    assert "merge tax" not in str(payload), "recall must not inline chunk content"


def test_ssot_takes_precedence_over_conflicting_recall_hit(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path)
    brain_runtime.assert_claim(
        claim={"fact": "merge queue uses the reviewed-vs-merged head"},
        scope="merge",
        evidence_ref="design:merge-queue",
        state_root=str(state_root),
    )
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))

    result = surf.recall("merge queue", top_k=5)

    # Structural precedence: every SSOT item precedes every recall item.
    tiers = [item.tier for item in result.items]
    assert tiers[0] == surface.TIER_SSOT
    first_recall = tiers.index(surface.TIER_RECALL)
    assert all(t == surface.TIER_SSOT for t in tiers[:first_recall])
    ssot = result.ssot_items[0]
    assert ssot.score == 1.0
    assert ssot.assertion_id and ssot.assertion_id.startswith("brain-assertion-")


def test_surface_is_the_single_brain_surface_tier_tagged(tmp_path: Path):
    """Recall is exposed on the SAME brain surface as the SSOT, tier-tagged."""

    state_root, db_path = _ingest(tmp_path)
    brain_runtime.assert_claim(
        claim={"fact": "topology: DGX spark is the controller host"},
        scope="topology",
        evidence_ref="memory:topology",
        state_root=str(state_root),
    )
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))

    result = surf.recall("DGX spark topology controller", top_k=5)
    tiers = {item.tier for item in result.items}
    assert tiers == {surface.TIER_SSOT, surface.TIER_RECALL}
    for item in result.items:
        assert item.tier in (surface.TIER_SSOT, surface.TIER_RECALL)


def test_session_hydration_top_k_is_additive(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    core = tmp_path / "MEMORY-CORE.md"
    core.write_text("# CORE\n\nalways-load core.\n", encoding="utf-8")
    before = core.read_text(encoding="utf-8")

    hydration = surf.hydrate_session("seat topology", top_k=1, core_path=str(core))

    # CORE markdown is reported loaded and never mutated (no regression).
    assert hydration.core_loaded is True
    assert hydration.core_path == str(core)
    assert core.read_text(encoding="utf-8") == before
    # Recall is additive pointers, bounded by top_k per tier.
    assert hydration.recall
    recall_only = [i for i in hydration.recall if i.tier == surface.TIER_RECALL]
    assert len(recall_only) <= 1
    payload = hydration.to_dict()
    assert payload["core_loaded"] is True
    assert all("text" not in item for item in payload["recall"])


def test_session_hydration_without_core_path(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    hydration = surf.hydrate_session("merge", top_k=2)
    assert hydration.core_loaded is False
    assert hydration.core_path is None


def test_privacy_fail_closed_for_egress_embedder_over_confidential(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path, scope="confidential")

    class _EgressEmbedder:
        requires_egress = True
        model_id = "fake-egress"
        dim = 32

        def embed(self, texts):
            return tuple((1.0,) * self.dim for _ in texts)

    store = SqliteVecStore(str(db_path), state_root=str(state_root))
    surf = surface.BrainRecallSurface(store=store, embedder=_EgressEmbedder(), state_root=str(state_root))

    with pytest.raises(BrainRecallPrivacyRefused):
        surf.recall("merge queue", top_k=3)


def test_privacy_egress_allowed_with_explicit_consent(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path, scope="confidential")

    class _EgressEmbedder:
        requires_egress = True
        model_id = "fake-egress"
        dim = 32

        def embed(self, texts):
            return tuple((1.0,) * self.dim for _ in texts)

    store = SqliteVecStore(str(db_path), state_root=str(state_root))
    surf = surface.BrainRecallSurface(store=store, embedder=_EgressEmbedder(), state_root=str(state_root))

    result = surf.recall("merge queue", top_k=3, allow_confidential_egress=True)
    assert result.recall_items  # consent permits the egress embed path


def test_local_default_embedder_needs_no_consent(tmp_path: Path):
    """The local-first default embedder never triggers the egress gate."""

    state_root, db_path = _ingest(tmp_path, scope="confidential")
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    assert surf.embedder.requires_egress is False
    result = surf.recall("merge queue", top_k=3)
    assert result.recall_items


def test_as_of_filters_future_records(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    # All ingested records are stamped AS_OF; an earlier as_of bound excludes them.
    early = surf.recall("merge queue", top_k=5, as_of="2020-01-01T00:00:00Z")
    assert early.recall_items == ()
    later = surf.recall("merge queue", top_k=5, as_of=LATER_AS_OF)
    assert later.recall_items


def test_scope_filters_recall(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    assert surf.recall("merge queue", top_k=5, scope="nonexistent").recall_items == ()
    assert surf.recall("merge queue", top_k=5, scope="public").recall_items


def test_empty_context_refused(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    with pytest.raises(brain_recall.BrainRecallInvalid):
        surf.recall("   ", top_k=3)


def test_zero_top_k_returns_empty(tmp_path: Path):
    state_root, db_path = _ingest(tmp_path)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    assert surf.recall("merge", top_k=0).items == ()


def test_keyword_leg_queries_fts5(tmp_path: Path):
    """The FTS5 column populated by F6.2 is now queried (keyword leg)."""

    state_root, db_path = _ingest(tmp_path)
    store = SqliteVecStore(str(db_path), state_root=str(state_root))
    hits = store.keyword_search("topology DGX", top_k=5)
    assert hits, "FTS5 keyword search should match the topology chunk"
    assert hits[0].record.source_path == "topology.md"
    # Pure-keyword miss returns empty, not an error.
    assert store.keyword_search("zzzznomatch", top_k=5) == ()
    assert store.keyword_search("!!!", top_k=5) == ()
