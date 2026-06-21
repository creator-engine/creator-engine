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


def _ingest_with_embedder(tmp_path: Path, embedder, scope: str = "public") -> tuple[Path, Path]:
    """Ingest the standard corpus through a caller-supplied embedder.

    Mirrors a real F6.2 ``--embedder embeddinggemma`` store: the store records the
    embedder's (non-default) vector dimension, so a default-embedder recall query
    can no longer silently match against it.
    """

    corpus = tmp_path / "corpus"
    corpus.mkdir(exist_ok=True)
    _write(corpus, "merge.md", "# Merge throughput\n\nReviewed-vs-merged head merge queue prior art.\n")
    _write(corpus, "topology.md", "# Seat identity topology\n\nThe DGX spark host controller seat map.\n")
    state_root = tmp_path / ".ce" / "state"
    db_path = state_root / "brain" / "recall.sqlite"
    ingest.ingest_markdown(
        sources=[str(corpus)],
        state_root=str(state_root),
        db_path=str(db_path),
        scope=scope,
        as_of=AS_OF,
        embedder=embedder,
    )
    return state_root, db_path


def test_recall_queries_non_default_embedder_store(tmp_path: Path):
    """A store built with an EmbeddingGemma-like 768-dim embedder is queryable.

    Regression for the F6.3 contract escape: recall must use the SAME embedder
    selection ingest used. Querying a 768-dim store with a matching 768-dim
    embedder returns hybrid hits (no dimension mismatch).
    """

    gemma_like = DeterministicFakeEmbedding(model_id="google/embeddinggemma-300m", dim=768)
    state_root, db_path = _ingest_with_embedder(tmp_path, gemma_like)

    store = SqliteVecStore(str(db_path), state_root=str(state_root))
    assert store.dim == 768

    matching = DeterministicFakeEmbedding(model_id="google/embeddinggemma-300m", dim=768)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root), embedder=matching)
    result = surf.recall("merge queue prior art", top_k=5)
    assert result.recall_items, "recall must query a non-default embedder store"


def test_recall_default_embedder_against_gemma_store_fails_closed(tmp_path: Path):
    """A dimension mismatch between query embedder and store must fail closed.

    Opening recall with the default (32-dim) embedder over a 768-dim store must
    raise an actionable configuration error up front, never silently return
    garbage or trip a late opaque store error.
    """

    gemma_like = DeterministicFakeEmbedding(model_id="google/embeddinggemma-300m", dim=768)
    state_root, db_path = _ingest_with_embedder(tmp_path, gemma_like)

    with pytest.raises(brain_recall.BrainRecallInvalid) as exc:
        # No embedder selection => deterministic 32-dim default, mismatching the
        # 768-dim store.
        surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    message = str(exc.value)
    assert "768" in message and "32" in message
    assert "embedder" in message.lower()


def test_open_surface_named_embedder_reuses_ingest_factory(tmp_path: Path):
    """``embedder_name`` selection routes through the F6.2 ingest factory.

    Selecting an unknown/misconfigured embedder by name surfaces the SAME ingest
    validation (reused, not duplicated) as a recall-side configuration error.
    """

    state_root, db_path = _ingest(tmp_path)
    # embeddinggemma without a --model-path is invalid in the shared ingest
    # factory; recall must surface that as a fail-closed configuration error.
    with pytest.raises(brain_recall.BrainRecallInvalid) as exc:
        surface.open_surface(
            db_path=str(db_path),
            state_root=str(state_root),
            embedder_name="embeddinggemma",
            model_path=None,
        )
    assert "model-path" in str(exc.value)
    # The named default selection still works and matches the default store.
    surf = surface.open_surface(
        db_path=str(db_path), state_root=str(state_root), embedder_name="deterministic"
    )
    assert surf.recall("merge queue", top_k=3).recall_items


def test_malformed_ssot_ledger_fails_closed(tmp_path: Path):
    """A present-but-malformed SSOT ledger must FAIL CLOSED, not downgrade.

    Regression for the HIGH finding: catching ``BrainRuntimeError`` and
    continuing with probabilistic recall defeats the SSOT tier boundary.
    """

    state_root, db_path = _ingest(tmp_path)
    ledger = brain_runtime.ledger_path(str(state_root))
    ledger.parent.mkdir(parents=True, exist_ok=True)
    # records must be a list; "not-a-list" is present-but-malformed.
    ledger.write_text("kind: brain-assertion-ledger\nrecords: not-a-list\n", encoding="utf-8")

    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    with pytest.raises(brain_runtime.BrainRuntimeError):
        surf.recall("merge queue", top_k=5)


def test_absent_ssot_ledger_is_empty_not_error(tmp_path: Path):
    """An ABSENT ledger is a legitimate empty-SSOT case — recall still answers.

    Distinguishes absent/empty (ok) from present-but-malformed (fail closed).
    """

    state_root, db_path = _ingest(tmp_path)
    ledger = brain_runtime.ledger_path(str(state_root))
    assert not ledger.exists(), "fixture must not create an SSOT ledger"

    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))
    result = surf.recall("merge queue", top_k=5)
    assert result.ssot_items == ()
    assert result.recall_items, "probabilistic recall still answers with no SSOT ledger"


def _ingest_scoped_corpus(
    tmp_path: Path,
    *,
    public_count: int,
    confidential_as_of: str = AS_OF,
) -> tuple[Path, Path]:
    """Ingest ``public_count`` ``public`` chunks plus a single ``confidential`` one.

    Reproduces ce-ops#181 finding 3: the lone filtered match must survive even
    when the surrounding (unfiltered) corpus is far larger than ``top_k * 4``, so
    a fixed unfiltered retrieval window would otherwise drop it.
    """

    state_root = tmp_path / ".ce" / "state"
    db_path = state_root / "brain" / "recall.sqlite"

    # Public chunks repeat every query token heavily, so they dominate BOTH the
    # semantic and the keyword leg and crowd the lone confidential record well
    # outside the unfiltered `top_k * 4` window (semantic ~rank 16, keyword last).
    public_corpus = tmp_path / "public"
    public_corpus.mkdir(exist_ok=True)
    for idx in range(public_count):
        _write(
            public_corpus,
            f"public_{idx:03d}.md",
            f"# Merge queue prior art {idx}\n\n"
            f"merge queue prior art merge queue prior art merge queue prior art note {idx}.\n",
        )
    ingest.ingest_markdown(
        sources=[str(public_corpus)],
        state_root=str(state_root),
        db_path=str(db_path),
        scope="public",
        as_of=AS_OF,
    )

    # The confidential record matches only weakly (one query token, once) so it
    # ranks at the bottom of both legs — exactly the slice a truncated window drops.
    conf_corpus = tmp_path / "confidential"
    conf_corpus.mkdir(exist_ok=True)
    _write(
        conf_corpus,
        "secret.md",
        "# Merge\n\nmerge.\n",
    )
    ingest.ingest_markdown(
        sources=[str(conf_corpus)],
        state_root=str(state_root),
        db_path=str(db_path),
        scope="confidential",
        as_of=confidential_as_of,
    )
    return state_root, db_path


def test_scope_filter_pushes_past_truncated_retrieval_window(tmp_path: Path):
    """ce-ops#181 finding 3: a lone scoped match outside top_k*4 must survive.

    30 ``public`` chunks + 1 ``confidential`` chunk, queried top_k=1 with
    ``scope='confidential'``, used to return ZERO because the unfiltered leg
    fetch (top_k*4 = 4 candidates) never reached the single confidential record.
    The filter must be honoured as part of retrieval (paged), so it returns the
    confidential record, not nothing.
    """

    state_root, db_path = _ingest_scoped_corpus(tmp_path, public_count=30)
    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))

    result = surf.recall("merge queue prior art", top_k=1, scope="confidential")
    recall_items = result.recall_items
    assert len(recall_items) == 1, "the lone confidential match must survive filtering"
    assert recall_items[0].scope == "confidential"
    assert recall_items[0].source_path == "secret.md"

    # And the public scope still returns its matches (no regression).
    public = surf.recall("merge queue prior art", top_k=3, scope="public")
    assert public.recall_items
    assert all(item.scope == "public" for item in public.recall_items)


def test_as_of_filter_pushes_past_truncated_retrieval_window(tmp_path: Path):
    """ce-ops#181 finding 3 (as-of variant): a lone in-window record survives.

    Many ``public`` records stamped AS_OF plus a single record stamped in the
    far future; an ``as_of`` bound BELOW AS_OF excludes the bulk corpus, leaving
    only... well, here we invert it: the bulk is future-stamped and the lone
    match is the in-bound record, which must page through past the truncated
    unfiltered window rather than being dropped.
    """

    state_root = tmp_path / ".ce" / "state"
    db_path = state_root / "brain" / "recall.sqlite"

    # 30 future-stamped public records that dominate both legs (excluded by an
    # AS_OF bound) — they crowd the lone in-bound record outside the window.
    future_corpus = tmp_path / "future"
    future_corpus.mkdir(exist_ok=True)
    for idx in range(30):
        _write(
            future_corpus,
            f"future_{idx:03d}.md",
            f"# Merge queue prior art {idx}\n\n"
            f"merge queue prior art merge queue prior art merge queue prior art future {idx}.\n",
        )
    ingest.ingest_markdown(
        sources=[str(future_corpus)],
        state_root=str(state_root),
        db_path=str(db_path),
        scope="public",
        as_of=LATER_AS_OF,
    )

    # ... plus one weakly-matching in-bound record stamped AS_OF (ranks last).
    past_corpus = tmp_path / "past"
    past_corpus.mkdir(exist_ok=True)
    _write(
        past_corpus,
        "inbound.md",
        "# Merge\n\nmerge.\n",
    )
    ingest.ingest_markdown(
        sources=[str(past_corpus)],
        state_root=str(state_root),
        db_path=str(db_path),
        scope="public",
        as_of=AS_OF,
    )

    surf = surface.open_surface(db_path=str(db_path), state_root=str(state_root))

    # An as_of bound at AS_OF excludes the 30 future records, leaving the lone
    # inbound record — which must survive the paged retrieval, not be truncated.
    result = surf.recall("merge queue prior art", top_k=1, as_of=AS_OF)
    recall_items = result.recall_items
    assert len(recall_items) == 1, "the lone in-as_of-bound match must survive filtering"
    assert recall_items[0].source_path == "inbound.md"
    assert recall_items[0].as_of == AS_OF


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
