from __future__ import annotations

from creator_engine_validator.brain_intent_xor_gate import CHECK_NAME, check_xor


def test_hybrid_intent_and_direct_ledger_edit_returns_hard_error():
    errors = check_xor([".ce/brain/append-intents/ce-foo.yaml", ".ce/brain/assertions.yaml"])

    assert len(errors) == 1
    assert errors[0].code == CHECK_NAME
    assert "hybrid PRs are refused" in errors[0].message


def test_only_intent_file_returns_no_errors():
    assert check_xor([".ce/brain/append-intents/ce-foo.yml"]) == []


def test_only_assertions_file_returns_no_errors():
    assert check_xor([".ce/brain/assertions.yaml"]) == []


def test_empty_path_set_returns_no_errors():
    assert check_xor([]) == []


def test_error_is_independent_of_other_path_content():
    errors = check_xor(["docs/readme.md", ".ce/brain/append-intents/ce-foo.yaml", ".ce/brain/assertions.yaml"])

    assert len(errors) == 1
