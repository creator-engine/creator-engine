"""Unit tests for the ce-ops#38 Cockpit claims feed (L1 load seam + L2 fold + L3 bind).

Asserts the ``load_claims()`` absent-directory tolerance, the PURE ``fold_snapshot``
claims section (no disk/process/network/clock/rng in the fold), stale-cache
availability honesty, invalid-marker counts, and — only where ``textual`` is
installed — that ``v3_cockpit`` renders the band from the precomputed snapshot only.
"""
from __future__ import annotations

import importlib.util
import json

import pytest

from creator_engine_validator.runner import cockpit_readmodel as cr

_HAS_TEXTUAL = importlib.util.find_spec("textual") is not None

WK = "creator-engine/ce-ops:issue:38"


def _cache(entries, *, fetched_at="2026-06-12T15:00:00Z", invalid_count=0):
    return {
        "kind": "ce-work-claim-cache", "schema_version": 1, "fetched_at": fetched_at,
        "repo": "creator-engine/ce-ops", "work_key": WK, "entries": entries,
        "active_count": len([e for e in entries if e["status"] == "active"]),
        "stale_count": len([e for e in entries if e.get("stale")]),
        "invalid_count": invalid_count, "comment_ids": [e["comment_id"] for e in entries],
    }


def _entry(claim_id, holder, *, status="active", stale=False, comment_id=1, kind="structured", host="H"):
    return {"claim_id": claim_id, "holder": holder, "host": host, "status": status,
            "claimed_at": "2026-06-12T14:00:00Z", "stale": stale, "comment_id": comment_id, "kind": kind}


# --- load seam ---------------------------------------------------------------


def test_load_claims_absent_dir_is_none(tmp_path):
    assert cr.load_claims(tmp_path) is None


def test_load_claims_malformed_is_none(tmp_path):
    d = tmp_path / cr.CLAIMS_SUBDIR
    d.mkdir()
    (d / cr.CLAIMS_CACHE_FILENAME).write_text("{ not json", encoding="utf-8")
    assert cr.load_claims(tmp_path) is None


def test_load_claims_reads_cache(tmp_path):
    d = tmp_path / cr.CLAIMS_SUBDIR
    d.mkdir()
    cache = _cache([_entry("wclaim-a", "ce-dev-2")])
    (d / cr.CLAIMS_CACHE_FILENAME).write_text(json.dumps(cache), encoding="utf-8")
    loaded = cr.load_claims(tmp_path)
    assert loaded["work_key"] == WK


# --- pure fold ---------------------------------------------------------------


def test_fold_claims_unavailable_when_none():
    snap = cr.fold_snapshot()
    assert snap["availability"]["claims"] == cr.UNAVAILABLE
    assert snap["claims"]["availability"] == cr.UNAVAILABLE
    assert snap["claims"]["active_count"] == 0


def test_fold_claims_section_counts():
    cache = _cache([
        _entry("wclaim-a", "ce-dev-2", comment_id=1),
        _entry("wclaim-b", "ce-dev-1", status="conflict", comment_id=2),
        _entry("wclaim-c", "ce-dev-3", stale=True, comment_id=3),
    ])
    snap = cr.fold_snapshot(claims=cache, controller_id="ce-dev-2")
    claims = snap["claims"]
    assert snap["availability"]["claims"] == cr.AVAILABLE
    assert claims["active_count"] == 2  # a + c are active, b is conflict
    assert claims["stale_count"] == 1
    # foreign = active not held by ce-dev-2 → only wclaim-c
    assert claims["foreign_count"] == 1
    assert claims["cache_fetched_at"] == "2026-06-12T15:00:00Z"


def test_fold_claims_invalid_count_from_cache():
    cache = _cache([_entry("wclaim-a", "ce-dev-2")], invalid_count=3)
    snap = cr.fold_snapshot(claims=cache)
    assert snap["claims"]["invalid_count"] == 3


def test_fold_claims_is_pure_json_serializable():
    cache = _cache([_entry("wclaim-a", "ce-dev-2")])
    snap = cr.fold_snapshot(claims=cache, controller_id="ce-dev-2")
    json.dumps(snap)  # must not raise — fully JSON-serializable


def test_fold_claims_empty_cache_available_but_empty():
    snap = cr.fold_snapshot(claims=_cache([]))
    assert snap["claims"]["availability"] == cr.AVAILABLE
    assert snap["claims"]["active_count"] == 0
    assert snap["claims"]["entries"] == []


# --- watch paths -------------------------------------------------------------


def test_watch_paths_includes_existing_claims_dir(tmp_path):
    (tmp_path / cr.CLAIMS_SUBDIR).mkdir()
    paths = cr.watch_paths(tmp_path)
    assert str(tmp_path / cr.CLAIMS_SUBDIR) in paths


# --- L3 render binding (textual-only) ----------------------------------------


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="textual extra not installed")
def test_cockpit_renders_claims_band_from_snapshot_only():
    from creator_engine_validator import v3_cockpit as vc

    cache = _cache([
        _entry("wclaim-a", "ce-dev-2", comment_id=1),
        _entry("wclaim-b", "ce-dev-1", status="conflict", comment_id=2),
    ])
    snap = cr.fold_snapshot(claims=cache, controller_id="ce-dev-1")
    text = vc._right_rail_text(snap)
    assert "WORK CLAIMS" in text
    assert "ce-dev-2@H (wclaim-a)" in text
    assert "CONFLICT" in text  # the loser is labelled


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="textual extra not installed")
def test_cockpit_renders_unavailable_band():
    from creator_engine_validator import v3_cockpit as vc

    text = vc._right_rail_text(cr.fold_snapshot())
    assert "claim cache unavailable" in text
