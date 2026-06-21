"""Company-brain recall surface (F6.3).

This is the single brain *recall* surface shared with the Knowledge-SSOT layer.
It does not stand up a second store, model, or server: it composes the merged
F6.1 adapters (``brain_recall``) and the F6.2 SQLite store + ingest runtime
(``brain_sqlite_vec``) with the F-first SSOT assertion ledger (``brain_runtime``)
into one tier-tagged callable.

Design invariants (per F6 Option A / ce-ops#181):

* **Hybrid retrieval** fuses the sqlite-vec semantic leg with the FTS5 keyword
  leg (the column F6.2 populated but never queried) by reciprocal-rank fusion.
* **Pointers, not content.** A recall hit returns ``source_path`` + ``chunk_ref``
  + ``content_hash`` + ``as_of`` so the agent re-verifies against the live
  Markdown source-of-truth (staleness handling). Chunk *text* is never inlined.
* **Tier boundary.** Verifiable SSOT / deterministic assertions
  (``tier == "ssot"``) always precede probabilistic recall hits
  (``tier == "recall"``); precedence is structural, not score-based.
* **Privacy fail-closed.** The semantic leg only embeds the query when the
  configured embedder needs no egress, or when explicit consent is supplied —
  reusing the F6.1 gate. By default no egress occurs.
* **Session hydration** injects a top-K, context-relevant recall slice alongside
  an unchanged (already-loaded) CORE markdown, additively over today's flat-file
  memory — it never replaces or truncates the file source-of-truth.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._versions import V3_LOCAL_STATE_ROOT
from . import brain_recall, brain_runtime
from .brain_recall import (
    BrainRecallError,
    BrainRecallInvalid,
    BrainRecallPrivacyRefused,
    RecallHit,
    RecallRecord,
    require_embedding_allowed,
)

TIER_SSOT = "ssot"
TIER_RECALL = "recall"

# Reciprocal-rank-fusion constant. The classic k=60 damps the dominance of any
# single leg's top rank so a hit strong in both legs out-ranks one strong in one.
_RRF_K = 60
DEFAULT_TOP_K = 5
DEFAULT_CORE_BUDGET_NOTE = (
    "CORE markdown stays the always-loaded source-of-truth; recall is additive."
)


@dataclass(frozen=True)
class SurfaceItem:
    """One tier-tagged surface item: an SSOT assertion or a recall pointer.

    Recall items are pointers (``source_path``/``chunk_ref``/``content_hash``/
    ``as_of``) so the caller re-reads the live Markdown; the chunk body is never
    embedded here. SSOT items carry the deterministic assertion record.
    """

    tier: str
    score: float
    source_path: str | None = None
    chunk_ref: str | None = None
    content_hash: str | None = None
    as_of: str | None = None
    scope: Any = None
    assertion_id: str | None = None
    claim: Mapping[str, Any] | None = None
    evidence_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"tier": self.tier, "score": self.score}
        if self.tier == TIER_SSOT:
            payload.update(
                {
                    "assertion_id": self.assertion_id,
                    "claim": self.claim,
                    "scope": self.scope,
                    "evidence_ref": self.evidence_ref,
                    "content_hash": self.content_hash,
                }
            )
        else:
            payload.update(
                {
                    "source_path": self.source_path,
                    "chunk_ref": self.chunk_ref,
                    "content_hash": self.content_hash,
                    "as_of": self.as_of,
                    "scope": self.scope,
                    # Explicitly advertise that the body is NOT inlined: the agent
                    # must re-read the live source-of-truth at this pointer.
                    "verify_against": self.source_path,
                }
            )
        return payload


@dataclass(frozen=True)
class RecallSurfaceResult:
    """The tier-ordered surface for a context query: SSOT first, then recall."""

    context: str
    items: tuple[SurfaceItem, ...]

    @property
    def ssot_items(self) -> tuple[SurfaceItem, ...]:
        return tuple(item for item in self.items if item.tier == TIER_SSOT)

    @property
    def recall_items(self) -> tuple[SurfaceItem, ...]:
        return tuple(item for item in self.items if item.tier == TIER_RECALL)

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True)
class HydrationResult:
    """Session-hydration payload: the unchanged CORE markdown plus recall pointers.

    The recall slice is *additive*: ``core_loaded`` reflects the always-load CORE
    markdown that hydration never edits, so existing flat-file memory cannot
    regress. ``recall`` carries only pointers + ``as_of`` for re-verification.
    """

    context: str
    core_loaded: bool
    core_path: str | None
    recall: tuple[SurfaceItem, ...]
    note: str = DEFAULT_CORE_BUDGET_NOTE

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context,
            "core_loaded": self.core_loaded,
            "core_path": self.core_path,
            "note": self.note,
            "recall": [item.to_dict() for item in self.recall],
        }


@dataclass(frozen=True)
class BrainRecallSurface:
    """The one brain recall surface (SSOT + probabilistic recall), tier-tagged."""

    store: Any
    embedder: Any
    state_root: Path | str = V3_LOCAL_STATE_ROOT

    def recall(
        self,
        context: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        scope: str | None = None,
        as_of: str | None = None,
        allow_confidential_egress: bool = False,
    ) -> RecallSurfaceResult:
        """Return the tier-ordered surface for ``context``.

        SSOT assertions matching the context come first (deterministic, always
        precedence); probabilistic recall pointers follow, hybrid-ranked.
        """

        if not isinstance(context, str) or not context.strip():
            raise BrainRecallInvalid("context must be a non-empty string")
        if top_k <= 0:
            return RecallSurfaceResult(context=context, items=())

        ssot_items = self._ssot_items(context, scope=scope)
        recall_items = self._recall_items(
            context,
            top_k=top_k,
            scope=scope,
            as_of=as_of,
            allow_confidential_egress=allow_confidential_egress,
        )
        # Structural precedence: SSOT always before recall, regardless of score.
        items = (*ssot_items[:top_k], *recall_items[:top_k])
        return RecallSurfaceResult(context=context, items=items)

    def hydrate_session(
        self,
        context: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        core_path: Path | str | None = None,
        scope: str | None = None,
        as_of: str | None = None,
        allow_confidential_egress: bool = False,
    ) -> HydrationResult:
        """Build an additive session-hydration payload for ``context``.

        ``core_path`` (e.g. a shrunken always-load CORE markdown) is reported as
        loaded but never read/edited here — hydration is strictly additive over
        the flat-file memory so no existing entry can regress.
        """

        result = self.recall(
            context,
            top_k=top_k,
            scope=scope,
            as_of=as_of,
            allow_confidential_egress=allow_confidential_egress,
        )
        core_loaded = core_path is not None
        return HydrationResult(
            context=context,
            core_loaded=core_loaded,
            core_path=str(core_path) if core_path is not None else None,
            # Hydration surfaces SSOT first then recall pointers, like recall().
            recall=result.items,
        )

    # -- internals -------------------------------------------------------------

    def _ssot_items(self, context: str, *, scope: str | None) -> tuple[SurfaceItem, ...]:
        # SSOT precedence must FAIL CLOSED on a malformed/tampered ledger: a
        # present-but-invalid `.ce/state/brain/assertions.yaml` must surface its
        # error rather than silently downgrade to probabilistic recall (which
        # would defeat the SSOT tier boundary). An ABSENT ledger is a legitimate
        # empty-SSOT case — `brain_runtime.load_records()` returns `[]` for that
        # and only raises `BrainRuntimeError` for present-but-malformed, so we
        # let the malformed case propagate untouched.
        records = brain_runtime.load_records(self.state_root)
        if not records:
            return ()
        latest, _indexes = brain_runtime._latest_by_id(records)
        items: list[SurfaceItem] = []
        for record in latest.values():
            if record.get("status") != "active":
                continue
            if scope is not None and record.get("scope") != scope:
                continue
            if not _ssot_matches_context(record, context):
                continue
            items.append(
                SurfaceItem(
                    tier=TIER_SSOT,
                    score=1.0,
                    assertion_id=record.get("id"),
                    claim=record.get("claim"),
                    scope=record.get("scope"),
                    evidence_ref=record.get("evidence_ref"),
                    content_hash=record.get("content_hash"),
                )
            )
        # Deterministic order: assertion id is content-addressed + unique.
        return tuple(sorted(items, key=lambda item: item.assertion_id or ""))

    def _recall_items(
        self,
        context: str,
        *,
        top_k: int,
        scope: str | None,
        as_of: str | None,
        allow_confidential_egress: bool,
    ) -> tuple[SurfaceItem, ...]:
        # CORRECTNESS (ce-ops#181 finding 3): the scope/as-of filters must be
        # honoured AS PART OF retrieval, not applied to an already-truncated
        # window. A naive fixed `top_k * 4` leg fetch drops valid filtered
        # records when the matching slice falls outside that unfiltered window
        # (e.g. 30 `public` + 1 `confidential`, top_k=1 --scope confidential
        # used to return zero). We page each leg with a geometrically growing
        # window, re-fusing and re-filtering, until we have `top_k` matching
        # records OR every leg is exhausted — so a single rare match anywhere in
        # the store is still surfaced. The legs are scanned-in-full + ranked by
        # the store, so paging only widens how deep we look, never re-orders.
        leg_k = max(top_k * 4, top_k)
        while True:
            semantic = self._semantic_hits(
                context, top_k=leg_k, allow_confidential_egress=allow_confidential_egress
            )
            keyword = self._keyword_hits(context, top_k=leg_k)
            fused = _reciprocal_rank_fusion(semantic, keyword)
            items = self._filtered_recall_items(
                fused, top_k=top_k, scope=scope, as_of=as_of
            )
            # Enough matches after filtering, or both legs are exhausted (each
            # returned fewer than we asked for => the store has no deeper
            # candidates to page into). Either way, stop.
            legs_exhausted = len(semantic) < leg_k and len(keyword) < leg_k
            if len(items) >= top_k or legs_exhausted:
                return items
            leg_k *= 2

    @staticmethod
    def _filtered_recall_items(
        fused: Sequence[tuple[RecallRecord, float]],
        *,
        top_k: int,
        scope: str | None,
        as_of: str | None,
    ) -> tuple[SurfaceItem, ...]:
        items: list[SurfaceItem] = []
        for record, score in fused:
            if scope is not None and record.scope != scope:
                continue
            if as_of is not None and record.as_of > as_of:
                continue
            items.append(
                SurfaceItem(
                    tier=TIER_RECALL,
                    score=score,
                    source_path=record.source_path,
                    chunk_ref=record.chunk_ref,
                    content_hash=record.content_hash,
                    as_of=record.as_of,
                    scope=record.scope,
                )
            )
            if len(items) >= top_k:
                break
        return tuple(items)

    def _semantic_hits(
        self, context: str, *, top_k: int, allow_confidential_egress: bool
    ) -> tuple[RecallHit, ...]:
        query_fn = getattr(self.store, "query", None)
        if not callable(query_fn):
            return ()
        # Privacy fail-closed: never embed the query through an egress embedder
        # over a confidential corpus without explicit consent. We gate on the
        # store's own confidential records so a mixed corpus still refuses.
        self._guard_query_egress(allow_confidential_egress)
        try:
            vector = self.embedder.embed((context,))[0]
        except BrainRecallError:
            raise
        return tuple(query_fn(vector, top_k=top_k))

    def _keyword_hits(self, context: str, *, top_k: int) -> tuple[RecallHit, ...]:
        keyword_fn = getattr(self.store, "keyword_search", None)
        if not callable(keyword_fn):
            return ()
        return tuple(keyword_fn(context, top_k=top_k))

    def _guard_query_egress(self, allow_confidential_egress: bool) -> None:
        if not bool(getattr(self.embedder, "requires_egress", False)):
            return
        if allow_confidential_egress is True:
            return
        records = _store_records(self.store)
        confidential = [
            record for record in records if brain_recall.is_confidential_scope(record.scope)
        ]
        if confidential:
            raise BrainRecallPrivacyRefused(
                "recall query would embed against confidential corpus through an "
                "egress embedder without explicit consent"
            )


def open_surface(
    *,
    db_path: Path | str | None = None,
    state_root: Path | str = V3_LOCAL_STATE_ROOT,
    embedder: Any | None = None,
    embedder_name: str | None = None,
    model_path: Path | str | None = None,
    store: Any | None = None,
) -> BrainRecallSurface:
    """Open the recall surface over the F6.2 SQLite store + an embedder.

    Recall MUST query a store with the SAME embedder F6.2 ingest built it with:
    a default-embedder query against an EmbeddingGemma (768-dim) store would hit
    a dimension mismatch (or, worse, silently query the wrong vector space). So
    the surface exposes the SAME ``embedder_name`` / ``model_path`` selection as
    ingest and builds the adapter through the SAME ``brain_ingest_runtime``
    factory (reused, not duplicated). ``embedder`` (an already-built adapter)
    still wins when supplied directly.

    Selection precedence: an explicit ``embedder`` object > a named
    ``embedder_name`` (+ ``model_path``) > the deterministic offline default
    (so CI never touches a model download).

    When the store records a vector dimension (F6.2 metadata) that the selected
    embedder cannot match, this FAILS CLOSED with an actionable
    ``BrainRecallInvalid`` rather than letting a mismatched query silently return
    garbage or trip a late, opaque store error.
    """

    if store is None:
        from .brain_sqlite_vec import SqliteVecStore

        store = SqliteVecStore(db_path, state_root=state_root)
    if embedder is None:
        if embedder_name is not None:
            # Reuse the F6.2 ingest embedder construction so recall and ingest
            # can never drift apart in how an embedder is selected/built.
            from . import brain_ingest_runtime

            try:
                embedder = brain_ingest_runtime.make_embedder(embedder_name, model_path=model_path)
            except brain_ingest_runtime.BrainIngestError as exc:
                raise BrainRecallInvalid(str(exc)) from exc
        else:
            embedder = brain_recall.DeterministicFakeEmbedding()
    _require_embedder_matches_store(store, embedder)
    return BrainRecallSurface(store=store, embedder=embedder, state_root=state_root)


def _require_embedder_matches_store(store: Any, embedder: Any) -> None:
    """Fail closed when the selected embedder cannot query this store.

    F6.2 records both the store's vector *dimension* and the ingest embedder's
    *model identity* in metadata. Two checks are needed, because dimension alone
    is not enough: two different models can share a dimension (e.g. two 768-dim
    models, or two 32-dim test models) yet live in incompatible vector spaces, so
    a same-dimension wrong-model query returns garbage from a mismatched embedding
    space without ever tripping the dimension guard.

    1. **Dimension** — if the embedder's output dim disagrees with the store dim,
       the query would dimension-mismatch deep inside the store.
    2. **Model identity** — if both the store's recorded ``model_id`` and the
       embedder's ``model_id`` are known and disagree, the query would silently
       use the wrong vector space even when the dims match.

    Either mismatch raises an actionable ``BrainRecallInvalid`` up front so an
    operator re-runs recall with the embedder/model the store was built with.
    """

    store_model = getattr(store, "model_id", None)
    embedder_model = getattr(embedder, "model_id", None)

    store_dim = getattr(store, "dim", None)
    embedder_dim = getattr(embedder, "dim", None)
    try:
        store_dim = int(store_dim) if store_dim is not None else None
        embedder_dim = int(embedder_dim) if embedder_dim is not None else None
    except (TypeError, ValueError):
        store_dim = embedder_dim = None

    if store_dim is not None and embedder_dim is not None and store_dim != embedder_dim:
        hint = f" (store model_id={store_model!r})" if store_model else ""
        raise BrainRecallInvalid(
            "recall embedder does not match the store it was built with: store vectors are "
            f"{store_dim}-dim but the selected embedder produces {embedder_dim}-dim vectors{hint}; "
            "re-run recall with the same --embedder/--model-path the store was ingested with"
        )

    # Same-dimension wrong-model guard: a different model that happens to share the
    # store's dimension is still a different embedding space, so fail closed when
    # both model identities are known and disagree.
    if (
        isinstance(store_model, str)
        and isinstance(embedder_model, str)
        and store_model != embedder_model
    ):
        raise BrainRecallInvalid(
            "recall embedder does not match the store it was built with: store was ingested "
            f"with model_id={store_model!r} but the selected embedder is model_id={embedder_model!r} "
            "(same vector dimension is not enough — a different model is a different vector space); "
            "re-run recall with the same --embedder/--model-path the store was ingested with"
        )


# -- module-level helpers ------------------------------------------------------


def _store_records(store: Any) -> tuple[RecallRecord, ...]:
    records = getattr(store, "records", None)
    if callable(records):
        records = records()
    if records is None:
        return ()
    coerced: list[RecallRecord] = []
    for raw in records:
        if isinstance(raw, RecallRecord):
            coerced.append(raw)
        else:
            record = getattr(raw, "record", None)
            if isinstance(record, RecallRecord):
                coerced.append(record)
    return tuple(coerced)


def _reciprocal_rank_fusion(
    semantic: Sequence[RecallHit], keyword: Sequence[RecallHit]
) -> tuple[tuple[RecallRecord, float], ...]:
    """Fuse two ranked legs by reciprocal rank, deterministically tie-broken.

    RRF score = sum over legs of 1 / (k + rank). It needs no score calibration
    between cosine and bm25 (different scales), only their *ranks*, which is why
    it is the standard hybrid-recall fusion. Ties break on the stable record key
    so output order never depends on dict/storage order.
    """

    scores: dict[brain_recall.RecallKey, float] = {}
    records: dict[brain_recall.RecallKey, RecallRecord] = {}
    for leg in (semantic, keyword):
        for rank, hit in enumerate(leg):
            key = hit.record.key
            scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + rank + 1)
            records.setdefault(key, hit.record)
    ordered = sorted(
        scores.items(),
        key=lambda item: (
            -item[1],
            item[0].source_path,
            item[0].chunk_ref,
        ),
    )
    return tuple((records[key], round(score, 12)) for key, score in ordered)


def _ssot_matches_context(record: Mapping[str, Any], context: str) -> bool:
    """Decide whether an SSOT assertion is relevant to the free-form context.

    SSOT recall is keyword/substring based (deterministic, no embedding): an
    assertion surfaces when any alphanumeric token of its scope or claim values
    appears in the lower-cased context. This keeps the tier purely verifiable.
    """

    haystack = context.lower()
    tokens = _ssot_tokens(record.get("scope")) | _ssot_tokens(record.get("claim"))
    return any(token in haystack for token in tokens if len(token) >= 3)


def _ssot_tokens(value: Any) -> set[str]:
    tokens: set[str] = set()
    if isinstance(value, str):
        for raw in value.replace("-", " ").replace("_", " ").split():
            cleaned = "".join(ch for ch in raw.lower() if ch.isalnum())
            if cleaned:
                tokens.add(cleaned)
    elif isinstance(value, Mapping):
        for child in value.values():
            tokens |= _ssot_tokens(child)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for child in value:
            tokens |= _ssot_tokens(child)
    return tokens


__all__ = [
    "BrainRecallSurface",
    "DEFAULT_TOP_K",
    "HydrationResult",
    "RecallSurfaceResult",
    "SurfaceItem",
    "TIER_RECALL",
    "TIER_SSOT",
    "open_surface",
]
