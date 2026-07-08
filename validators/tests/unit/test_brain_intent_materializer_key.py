from __future__ import annotations

import hashlib
import re

from creator_engine_validator.brain_intent_materializer import MaterializationKey


def test_materialization_key_uses_design_byte_sequence():
    key = MaterializationKey.compute("merge", ".ce/brain/append-intents/branch.yaml", "intent")

    expected = hashlib.sha256(b"merge\n.ce/brain/append-intents/branch.yaml\nintent\n").hexdigest()

    assert key.key_hex == expected
    assert key.merge_commit_sha == "merge"
    assert key.intent_path == ".ce/brain/append-intents/branch.yaml"
    assert key.intent_sha256 == "intent"


def test_materialization_key_is_stable_for_same_inputs():
    first = MaterializationKey.compute("a" * 40, "intent.yaml", "b" * 64)
    second = MaterializationKey.compute("a" * 40, "intent.yaml", "b" * 64)

    assert first == second


def test_materialization_key_changes_when_any_input_changes():
    base = MaterializationKey.compute("a" * 40, "intent.yaml", "b" * 64).key_hex

    assert MaterializationKey.compute("c" * 40, "intent.yaml", "b" * 64).key_hex != base
    assert MaterializationKey.compute("a" * 40, "other.yaml", "b" * 64).key_hex != base
    assert MaterializationKey.compute("a" * 40, "intent.yaml", "d" * 64).key_hex != base


def test_materialization_key_is_64_lowercase_hex():
    key = MaterializationKey.compute("a" * 40, "intent.yaml", "b" * 64)

    assert re.fullmatch(r"[0-9a-f]{64}", key.key_hex)
