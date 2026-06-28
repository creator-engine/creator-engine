"""Offline golden-set recall eval for CE brain retrieval.

The harness is intentionally small and deterministic. It evaluates a fixed set
of controller-context queries against embedded Markdown snippets without any
network, vLLM, or live endpoint dependency.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import brain_recall

DEFAULT_K_VALUES = (3, 5)
AS_OF = "2026-06-28T00:00:00Z"
SCOPE = "brain-eval"

_TOKEN_RE = re.compile(r"[a-z0-9#]+")


@dataclass(frozen=True)
class FixtureSnippet:
    ref: str
    title: str
    markdown: str

    def to_dict(self) -> dict[str, str]:
        return {"ref": self.ref, "title": self.title, "markdown": self.markdown}


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    query: str
    expected_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "query": self.query,
            "expected_refs": list(self.expected_refs),
        }


@dataclass(frozen=True)
class CaseLegResult:
    hits_by_k: Mapping[int, tuple[str, ...]]
    recall_by_k: Mapping[int, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits_by_k": {str(k): list(self.hits_by_k[k]) for k in sorted(self.hits_by_k)},
            "recall_by_k": {f"recall@{k}": self.recall_by_k[k] for k in sorted(self.recall_by_k)},
        }


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    query: str
    expected_refs: tuple[str, ...]
    passed: bool
    legs: Mapping[str, CaseLegResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "query": self.query,
            "expected_refs": list(self.expected_refs),
            "passed": self.passed,
            "legs": {name: self.legs[name].to_dict() for name in sorted(self.legs)},
        }


@dataclass(frozen=True)
class EvalReport:
    ok: bool
    case_count: int
    passed_count: int
    failed_count: int
    k_values: tuple[int, ...]
    metrics: Mapping[str, Mapping[str, float]]
    cases: tuple[CaseResult, ...]
    fixture_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "case_count": self.case_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "k_values": list(self.k_values),
            "metrics": {
                leg: {metric: values[metric] for metric in sorted(values)}
                for leg, values in sorted(self.metrics.items())
            },
            "fixture_count": self.fixture_count,
            "cases": [case.to_dict() for case in self.cases],
        }


FIXTURES: tuple[FixtureSnippet, ...] = (
    FixtureSnippet(
        ref="brain/worktree",
        title="Exact-base worktree discipline",
        markdown=(
            "# Exact-base worktree discipline\n\n"
            "Create a fresh git worktree from the requested base commit before "
            "branch work. Do not reuse a dirty controller checkout, and never "
            "overwrite unrelated user changes."
        ),
    ),
    FixtureSnippet(
        ref="brain/path-manifest",
        title="Closed path-set carriers",
        markdown=(
            "# Closed path-set carriers\n\n"
            "Every PR carries a changelog fragment and path manifest. The "
            "manifest declares the authorized file set, canonical path count, "
            "and sha256 over sorted unique paths."
        ),
    ),
    FixtureSnippet(
        ref="brain/preflight",
        title="Validator preflight",
        markdown=(
            "# Validator preflight\n\n"
            "Before validate-pr, remove validators/*.egg-info and "
            "validators/build. Run the validator with TMPDIR=/var/tmp and "
            "PYTHONPATH=validators so the committed tree is checked cleanly."
        ),
    ),
    FixtureSnippet(
        ref="brain/assertions",
        title="Knowledge-SSOT assertion ledger",
        markdown=(
            "# Knowledge-SSOT assertion ledger\n\n"
            "ce brain init bootstraps a valid genesis ledger. Assertions, "
            "checks, corrections, and verification are deterministic local "
            "operations over the ledger under .ce state."
        ),
    ),
    FixtureSnippet(
        ref="brain/recall-derived",
        title="Derived recall store",
        markdown=(
            "# Derived recall store\n\n"
            "Markdown remains the source of truth. ce brain ingest builds a "
            "rebuildable recall projection with semantic vectors and keyword "
            "index entries that can be regenerated from source snippets."
        ),
    ),
    FixtureSnippet(
        ref="brain/foreman-worker",
        title="Foreman worker delegation",
        markdown=(
            "# Foreman worker delegation\n\n"
            "A foreman seat plans, dispatches, monitors, and triages. "
            "Substantive implementation and review work is delegated to "
            "governed worker sub-agents."
        ),
    ),
    FixtureSnippet(
        ref="brain/review-boundary",
        title="Author reviewer separation",
        markdown=(
            "# Author reviewer separation\n\n"
            "The author of a branch must not be the reviewer. Route PR review "
            "to a distinct non-author seat, and do not self-merge."
        ),
    ),
    FixtureSnippet(
        ref="brain/egress",
        title="Credential and egress boundary",
        markdown=(
            "# Credential and egress boundary\n\n"
            "Secrets stay behind credential brokers. Offline work must not call "
            "network endpoints or print tokens; live egress requires explicit "
            "authorization."
        ),
    ),
    FixtureSnippet(
        ref="brain/containment",
        title="Containment posture",
        markdown=(
            "# Containment posture\n\n"
            "Worker execution is contained by filesystem mediation, bounded "
            "tool authority, and runtime evidence. Ring 1 guards deny unsafe "
            "side effects."
        ),
    ),
    FixtureSnippet(
        ref="brain/automerge",
        title="Automerge decision surface",
        markdown=(
            "# Automerge decision surface\n\n"
            "automerge-decide is a dry-run classifier that emits an AUTO or "
            "GESTURE decision. It must not merge branches or mutate the queue."
        ),
    ),
    FixtureSnippet(
        ref="brain/pickup",
        title="Proactive pickup belt",
        markdown=(
            "# Proactive pickup belt\n\n"
            "When a seat reaches a breakpoint, scan own PRs, requested reviews, "
            "and then ready unblocked tickets. Respect in-compose locks and "
            "dependency order."
        ),
    ),
    FixtureSnippet(
        ref="brain/packaging",
        title="Packaging artifact hygiene",
        markdown=(
            "# Packaging artifact hygiene\n\n"
            "Wheel and egg-info artifacts can contaminate packaging tests. Clean "
            "build outputs and keep environment artifacts outside the repo."
        ),
    ),
)


GOLDEN_CASES: tuple[GoldenCase, ...] = (
    GoldenCase("case-worktree-base", "fresh worktree exact base commit dirty checkout", ("brain/worktree",)),
    GoldenCase("case-carriers", "path manifest changelog authorized paths sha256", ("brain/path-manifest",)),
    GoldenCase("case-preflight", "clean egg-info build before validate-pr TMPDIR PYTHONPATH", ("brain/preflight",)),
    GoldenCase("case-ledger", "brain init assertion ledger verify corrections", ("brain/assertions",)),
    GoldenCase("case-recall", "markdown source truth rebuildable recall projection vectors keyword", ("brain/recall-derived",)),
    GoldenCase("case-foreman", "foreman dispatch worker implementation review sub-agent", ("brain/foreman-worker",)),
    GoldenCase("case-review", "author cannot review own PR distinct non-author seat", ("brain/review-boundary",)),
    GoldenCase("case-egress", "offline no network endpoint credential broker secrets tokens", ("brain/egress",)),
    GoldenCase("case-containment", "ring1 guard filesystem mediation contained worker side effects", ("brain/containment",)),
    GoldenCase("case-automerge", "automerge decide dry-run classifier no merge mutation", ("brain/automerge",)),
    GoldenCase("case-pickup", "ready unblocked tickets in-compose locks dependency order", ("brain/pickup",)),
    GoldenCase("case-packaging", "stale wheel egg-info build artifact contamination", ("brain/packaging",)),
)

_CONCEPT_ALIASES: Mapping[str, tuple[str, ...]] = {
    "worktree": ("worktree", "checkout", "base", "branch", "commit", "dirty"),
    "carrier": ("carrier", "manifest", "changelog", "authorized", "sha256", "paths"),
    "preflight": ("preflight", "validate", "validate-pr", "tmpdir", "pythonpath", "egg-info"),
    "ledger": ("ledger", "assertion", "assertions", "init", "verify", "corrections"),
    "recall": ("recall", "markdown", "vectors", "semantic", "keyword", "projection", "rebuildable"),
    "foreman": ("foreman", "dispatch", "worker", "sub-agent", "delegate", "implementation"),
    "review": ("review", "reviewer", "author", "non-author", "pr", "self-merge"),
    "egress": ("egress", "network", "endpoint", "credential", "secrets", "tokens", "offline"),
    "containment": ("containment", "contained", "ring1", "filesystem", "mediation", "guards"),
    "automerge": ("automerge", "dry-run", "classifier", "auto", "gesture", "merge"),
    "pickup": ("pickup", "ready", "unblocked", "locks", "dependencies", "tickets"),
    "packaging": ("packaging", "wheel", "egg-info", "build", "artifacts", "contamination"),
}


class MockSemanticEmbedding:
    """Deterministic concept-vector embedder for the offline eval corpus."""

    requires_egress = False
    model_id = "ce-brain-eval-mock-semantic-v1"
    dim = len(_CONCEPT_ALIASES)

    def embed(self, texts: Sequence[str]) -> tuple[brain_recall.Vector, ...]:
        if isinstance(texts, str):
            raise TypeError("texts must be a sequence, not a string")
        return tuple(_semantic_vector(text) for text in texts)


def run_eval(k_values: Sequence[int] = DEFAULT_K_VALUES) -> EvalReport:
    """Run the offline recall eval and return a stable structured report."""

    normalized_k = _normalize_k_values(k_values)
    fixtures = FIXTURES
    cases = GOLDEN_CASES
    max_k = max(normalized_k)
    keyword_index = _build_keyword_index(fixtures)
    semantic_store = _build_semantic_store(fixtures)
    embedder = MockSemanticEmbedding()

    case_results: list[CaseResult] = []
    for case in cases:
        keyword_hits = tuple(ref for ref, _score in _keyword_search(case.query, keyword_index, max_k))
        semantic_vector = embedder.embed((case.query,))[0]
        semantic_hits = tuple(hit.record.source_path for hit in semantic_store.query(semantic_vector, top_k=max_k))
        legs = {
            "keyword": _case_leg(case.expected_refs, keyword_hits, normalized_k),
            "semantic": _case_leg(case.expected_refs, semantic_hits, normalized_k),
        }
        passed = all(leg.recall_by_k[max_k] >= 1.0 for leg in legs.values())
        case_results.append(
            CaseResult(
                case_id=case.case_id,
                query=case.query,
                expected_refs=case.expected_refs,
                passed=passed,
                legs=legs,
            )
        )

    passed_count = sum(1 for case in case_results if case.passed)
    metrics = _aggregate_metrics(case_results, normalized_k)
    return EvalReport(
        ok=passed_count == len(case_results),
        case_count=len(case_results),
        passed_count=passed_count,
        failed_count=len(case_results) - passed_count,
        k_values=normalized_k,
        metrics=metrics,
        cases=tuple(case_results),
        fixture_count=len(fixtures),
    )


def _normalize_k_values(k_values: Sequence[int]) -> tuple[int, ...]:
    values = tuple(sorted({int(value) for value in k_values}))
    if not values or any(value <= 0 for value in values):
        raise ValueError("k_values must contain positive integers")
    return values


def _build_semantic_store(fixtures: Sequence[FixtureSnippet]) -> brain_recall.InMemoryVectorStore:
    chunks = []
    for fixture in fixtures:
        record = brain_recall.RecallRecord(
            source_path=fixture.ref,
            chunk_ref="fixture",
            content_hash=hashlib.sha256(fixture.markdown.encode("utf-8")).hexdigest(),
            as_of=AS_OF,
            scope=SCOPE,
            requires_egress=False,
        )
        chunks.append(brain_recall.RecallChunk(record=record, text=fixture.markdown))
    store = brain_recall.InMemoryVectorStore()
    store.rebuild_from_source(chunks, MockSemanticEmbedding())
    return store


def _build_keyword_index(fixtures: Sequence[FixtureSnippet]) -> tuple[tuple[FixtureSnippet, Counter[str]], ...]:
    return tuple((fixture, Counter(_tokens(fixture.markdown))) for fixture in fixtures)


def _keyword_search(
    query: str,
    index: Sequence[tuple[FixtureSnippet, Counter[str]]],
    top_k: int,
) -> tuple[tuple[str, float], ...]:
    query_counts = Counter(_tokens(query))
    if not query_counts:
        return ()
    hits: list[tuple[str, float]] = []
    for fixture, counts in index:
        overlap = sum(min(query_counts[token], counts[token]) for token in query_counts)
        if overlap <= 0:
            continue
        coverage = overlap / sum(query_counts.values())
        density = overlap / max(1, sum(counts.values()))
        score = round(coverage + density, 12)
        hits.append((fixture.ref, score))
    return tuple(sorted(hits, key=lambda item: (-item[1], item[0]))[:top_k])


def _case_leg(expected_refs: Sequence[str], hits: Sequence[str], k_values: Sequence[int]) -> CaseLegResult:
    expected = set(expected_refs)
    hits_by_k = {k: tuple(hits[:k]) for k in k_values}
    recall_by_k = {
        k: round(len(expected.intersection(hits_by_k[k])) / len(expected), 6)
        for k in k_values
    }
    return CaseLegResult(hits_by_k=hits_by_k, recall_by_k=recall_by_k)


def _aggregate_metrics(
    case_results: Sequence[CaseResult],
    k_values: Sequence[int],
) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for leg in ("keyword", "semantic"):
        values: dict[str, float] = {}
        for k in k_values:
            mean = sum(case.legs[leg].recall_by_k[k] for case in case_results) / len(case_results)
            values[f"recall@{k}"] = round(mean, 6)
        metrics[leg] = values
    return metrics


def _semantic_vector(text: str) -> brain_recall.Vector:
    tokens = set(_tokens(text))
    values = []
    for aliases in _CONCEPT_ALIASES.values():
        values.append(float(sum(1 for alias in aliases if alias in tokens)))
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0.0:
        return tuple(0.0 for _ in values)
    return tuple(round(value / norm, 12) for value in values)


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(text.lower()))


__all__ = [
    "AS_OF",
    "DEFAULT_K_VALUES",
    "FIXTURES",
    "GOLDEN_CASES",
    "EvalReport",
    "FixtureSnippet",
    "GoldenCase",
    "MockSemanticEmbedding",
    "run_eval",
]
