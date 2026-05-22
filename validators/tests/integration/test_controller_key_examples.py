"""Integration coverage for bundled controller-key examples and focused CLI scan."""

from __future__ import annotations

from creator_engine_validator.cli import main


def test_scan_controller_keys_accepts_well_formed_examples(capsys):
    exit_code = main(["scan-controller-keys", "examples/well-formed/controller-keys"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "PASS controller_key_schema" in captured.out


def test_scan_controller_keys_rejects_malformed_examples(capsys):
    for path in (
        "examples/malformed/controller-keys/missing-required-fields.yaml",
        "examples/malformed/controller-keys/bad-controller-id-pattern.yaml",
        "examples/malformed/controller-keys/private-key-material.yaml",
    ):
        exit_code = main(["scan-controller-keys", path])
        captured = capsys.readouterr()
        assert exit_code == 1, path
        assert "FAIL controller_key_schema" in captured.out
        assert "PCO-025" in captured.out
