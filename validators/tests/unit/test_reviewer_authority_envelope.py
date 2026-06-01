"""Unit tests for the G2.007.2 reviewer-authority envelope validator. Offline."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import reviewer_authority_envelope as r


def _valid() -> dict:
    return {
        "envelope_id": "rva-pr106-reviewer",
        "mechanic": "pr_review",
        "pr_number": 106,
        "head_sha": "aa02b0ceb192b38f52da0d99f798e1e2710a8a22",
        "actor": "ubuntuaws745-cmyk",
        "ratified_prompt_sha": "ae1b9db11155f4ad841ef3fa399cd508c64d1ff184d1e0d1437e859c0dacfe27",
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T10:43:13Z",
    }


def _write(tmp_path: Path, rec: dict) -> Path:
    p = tmp_path / "rva.ce.yml"
    p.write_text(yaml.safe_dump({"reviewer_authority_envelope": rec}), encoding="utf-8")
    return p


def _codes(tmp_path: Path, mutate) -> set[str]:
    rec = copy.deepcopy(_valid())
    mutate(rec)
    return {e.code for e in r.validate_reviewer_authority_envelope_file(_write(tmp_path, rec))}


def test_registered():
    assert "reviewer_authority_envelope" in registered_checks()


def test_valid_passes(tmp_path):
    assert r.validate_reviewer_authority_envelope_file(_write(tmp_path, _valid())) == []


def test_unknown_mechanic_rejected(tmp_path):
    assert "VAL-RVA-MECHANIC" in _codes(tmp_path, lambda r: r.update(mechanic="merge"))


@pytest.mark.parametrize("field", ["pr_number", "head_sha", "actor", "ratified_prompt_sha"])
def test_missing_binding_rejected(tmp_path, field):
    assert "VAL-RVA-BINDING" in _codes(tmp_path, lambda r: r.pop(field))


def test_reserved_role_rejected(tmp_path):
    assert "VAL-RVA-ROLE" in _codes(tmp_path, lambda r: r.update(emitting_role="agent_ratifier"))


def test_unknown_mode_rejected(tmp_path):
    assert "VAL-RVA-MODE" in _codes(tmp_path, lambda r: r.update(operating_mode="yolo"))


def test_secret_value_rejected(tmp_path):
    assert "VAL-RVA-SECRET" in _codes(tmp_path, lambda r: r.setdefault("metadata", {}).update(token="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"))


def test_record_level_validator_usable_in_memory():
    # build_context uses validate_reviewer_authority_envelope_record on a loaded mapping.
    assert r.validate_reviewer_authority_envelope_record({"reviewer_authority_envelope": _valid()}, Path(".")) == []
    bad = {"reviewer_authority_envelope": {**_valid(), "mechanic": "merge"}}
    assert any(e.code == "VAL-RVA-MECHANIC" for e in r.validate_reviewer_authority_envelope_record(bad, Path(".")))
