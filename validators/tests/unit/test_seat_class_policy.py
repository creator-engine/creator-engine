"""Unit tests for the seat-class-policy validator check."""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import seat_class_policy as chk


def _valid() -> dict:
    return {
        "kind": "seat-class-policy-record",
        "schema_version": "1",
        "policy_id": "seat-class-default",
        "policy_sha": "a" * 64,
        "seat_class": "foreman",
        "default_seat_class": "foreman",
        "recursion": {
            "foreman_of_foreman_allowed": True,
            "max_depth": 3,
        },
        "delegation_required_mutation_classes": [
            "code",
            "schema",
            "deploy",
            "governance",
            "identity",
            "security",
        ],
        "coordination_path_prefixes": [
            ".ce/state/",
            ".ce/changelog/",
            "brief.md",
            "docs/contracts/",
        ],
    }


def _write(tmp_path: Path, rec: dict) -> Path:
    path = tmp_path / "seat-class-policy.yaml"
    path.write_text(yaml.safe_dump(rec), encoding="utf-8")
    return path


def _codes(tmp_path: Path, mutate) -> set[str]:
    rec = copy.deepcopy(_valid())
    mutate(rec)
    return {err.code for err in chk.validate_seat_class_policy(rec, _write(tmp_path, rec))}


def test_check_is_registered():
    assert chk.CHECK_NAME in registered_checks()


def test_valid_policy_passes(tmp_path):
    path = _write(tmp_path, _valid())
    assert chk.validate_seat_class_policy(_valid(), path) == []


def test_default_must_be_foreman(tmp_path):
    assert chk.CODE_DEFAULT in _codes(tmp_path, lambda r: r.update(default_seat_class="worker"))


def test_max_depth_must_be_at_least_one(tmp_path):
    assert chk.CODE_RECURSION in _codes(tmp_path, lambda r: r["recursion"].update(max_depth=0))


def test_delegation_classes_must_be_baseline(tmp_path):
    assert chk.CODE_MUTATION_CLASS in _codes(
        tmp_path,
        lambda r: r["delegation_required_mutation_classes"].append("tracker_mirror"),
    )


def test_secret_value_rejected(tmp_path):
    assert chk.CODE_SECRET in _codes(
        tmp_path,
        lambda r: r.setdefault("metadata", {}).update(token="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"),
    )


def test_run_green_on_valid_dir(tmp_path):
    _write(tmp_path, _valid())
    result = chk.run([tmp_path])
    assert result.ok, [err.format() for err in result.errors]


def test_run_ignores_non_policy_records(tmp_path):
    (tmp_path / "other.yaml").write_text(yaml.safe_dump({"kind": "scope-record"}), encoding="utf-8")
    assert chk.run([tmp_path]).ok

