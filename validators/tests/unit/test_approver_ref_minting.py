"""Tests for approver_ref minting and provenance schema validation."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

from creator_engine_validator.approver_ref_minting import (
    mint_approver_ref,
    verify_approver_ref,
)

_VALID_SHA = "a" * 64
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "creator_engine_validator"
    / "schemas"
    / "install-answers.schema.yaml"
)


def _ratification_binding_validator() -> Draft202012Validator:
    schema = yaml.safe_load(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema["$defs"]["ratification_binding"])


def test_mint_returns_64_hex_chars():
    ref = mint_approver_ref("Iv23liuJpXXXXXXX", _VALID_SHA)
    assert len(ref) == 64
    assert all(c in "0123456789abcdef" for c in ref)


def test_mint_is_deterministic():
    ref1 = mint_approver_ref("Iv23liuJpXXXXXXX", _VALID_SHA, "deadbeef")
    ref2 = mint_approver_ref("Iv23liuJpXXXXXXX", _VALID_SHA, "deadbeef")
    assert ref1 == ref2


def test_mint_differs_by_client_id():
    ref_a = mint_approver_ref("client-a", _VALID_SHA)
    ref_b = mint_approver_ref("client-b", _VALID_SHA)
    assert ref_a != ref_b


def test_mint_differs_by_prompt_sha():
    ref1 = mint_approver_ref("client-a", "a" * 64)
    ref2 = mint_approver_ref("client-a", "b" * 64)
    assert ref1 != ref2


def test_mint_differs_by_gesture_salt():
    ref_no_salt = mint_approver_ref("client-a", _VALID_SHA)
    ref_with_salt = mint_approver_ref("client-a", _VALID_SHA, "cafebabe")
    assert ref_no_salt != ref_with_salt


def test_mint_raises_on_empty_client_id():
    with pytest.raises(ValueError, match="client_id"):
        mint_approver_ref("", _VALID_SHA)


def test_mint_raises_on_invalid_prompt_sha_length():
    with pytest.raises(ValueError, match="64"):
        mint_approver_ref("client-a", "abc")


def test_verify_returns_true_for_correct_inputs():
    client_id = "Iv23liuJp6OxfCWvwfSl"
    salt = "0011aabb"
    ref = mint_approver_ref(client_id, _VALID_SHA, salt)
    assert verify_approver_ref(ref, client_id, _VALID_SHA, salt) is True


def test_verify_returns_false_for_wrong_client_id():
    ref = mint_approver_ref("real-client", _VALID_SHA, "salt")
    assert verify_approver_ref(ref, "fake-client", _VALID_SHA, "salt") is False


def test_verify_returns_false_for_tampered_ref():
    ref = mint_approver_ref("client-a", _VALID_SHA)
    tampered = "0" * 64
    assert verify_approver_ref(tampered, "client-a", _VALID_SHA) is False


def test_verify_returns_false_on_invalid_prompt_sha():
    assert verify_approver_ref("a" * 64, "client-a", "not-a-sha") is False


def test_schema_accepts_legacy_ratification_binding_without_provenance():
    _ratification_binding_validator().validate(
        {
            "ratified_prompt_sha": _VALID_SHA,
            "approver_ref": "b" * 64,
            "educate_acknowledged": True,
        }
    )


def test_schema_accepts_ratification_binding_with_provenance():
    _ratification_binding_validator().validate(
        {
            "ratified_prompt_sha": _VALID_SHA,
            "approver_ref": "b" * 64,
            "educate_acknowledged": True,
            "approver_ref_provenance": {
                "client_id": "Iv23liuJp6OxfCWvwfSl",
                "gesture_salt": "0011aabb",
            },
        }
    )


def test_schema_rejects_provenance_without_gesture_salt():
    with pytest.raises(ValidationError):
        _ratification_binding_validator().validate(
            {
                "ratified_prompt_sha": _VALID_SHA,
                "approver_ref": "b" * 64,
                "educate_acknowledged": True,
                "approver_ref_provenance": {
                    "client_id": "Iv23liuJp6OxfCWvwfSl",
                },
            }
        )
