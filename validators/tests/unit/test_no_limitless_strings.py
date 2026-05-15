from pathlib import Path

import pytest

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.no_limitless_strings import (
    CHECK_NAME,
    GENERIC_PATHS,
    _scan_text,
    run,
)
from creator_engine_validator.cli import main


def test_no_limitless_strings_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = set(checks[CHECK_NAME].frs)
    assert {"FR-024", "FR-024a", "SC-004"}.issubset(frs)


def test_scan_text_flags_bare_limitless():
    hits = _scan_text("hostname: limitless-host\n", ["limitless"])
    assert hits, "expected a violation for a bare LIMITLESS hostname"
    line, col, token = hits[0]
    assert line == 1
    assert col == 11
    assert token == "limitless"


def test_scan_text_allows_scanner_self_reference():
    text = (
        "Run `python -m creator_engine_validator scan-no-limitless`.\n"
        "This is the no-LIMITLESS generic-path scan.\n"
        "Module: no_limitless_strings.\n"
        "Stub: no LIMITLESS scanner registered yet.\n"
        "Note: LIMITLESS scanner self-references are allowed.\n"
        "FR-024 forbids LIMITLESS-specific identifiers in generic paths.\n"
    )
    assert _scan_text(text, ["limitless"]) == []


def test_scan_text_is_case_insensitive():
    assert _scan_text("Token Limitless inside generic doc.", ["limitless"])
    assert _scan_text("Token LIMITLESS inside generic doc.", ["limitless"])


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / "validators").mkdir()
    for sub in GENERIC_PATHS:
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_run_passes_on_clean_generic_paths(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "docs/contracts/clean.md").write_text("Generic contract; no tenant strings.\n")
    (repo / "schemas/example.schema.yaml").write_text("type: object\n")
    result = run([repo])
    assert result.ok, [e.format() for e in result.errors]


def test_run_flags_limitless_in_generic_contract(tmp_path):
    repo = _make_repo(tmp_path)
    bad = repo / "docs/contracts/example.md"
    bad.write_text("Owner: limitless-team\n")
    result = run([repo])
    assert not result.ok
    assert any(error.code == "FR-024" for error in result.errors)
    assert any("limitless" in error.message.lower() for error in result.errors)


def test_run_skips_scanner_self_reference_files(tmp_path):
    repo = _make_repo(tmp_path)
    scanner_path = repo / "validators/creator_engine_validator/checks/no_limitless_strings.py"
    scanner_path.parent.mkdir(parents=True, exist_ok=True)
    scanner_path.write_text("LIMITLESS LIMITLESS LIMITLESS\n")
    result = run([repo])
    assert result.ok, [e.format() for e in result.errors]


def test_run_allows_self_reference_phrases_in_validator_docs(tmp_path):
    repo = _make_repo(tmp_path)
    readme = repo / "validators/README.md"
    readme.write_text(
        "Invoke `python -m creator_engine_validator scan-no-limitless`.\n"
        "This runs the no-LIMITLESS generic-path scan.\n"
    )
    result = run([repo])
    assert result.ok, [e.format() for e in result.errors]


def test_run_loads_tenant_identifier_list(tmp_path):
    repo = _make_repo(tmp_path)
    tenant_dir = repo / "tenants/limitless"
    tenant_dir.mkdir(parents=True)
    (tenant_dir / "limitless-identifiers.yml").write_text(
        "identifiers:\n"
        "  - limitless-agent\n"
        "  - limitless-host\n"
    )
    bad = repo / "schemas/example.schema.yaml"
    bad.write_text("owner: limitless-agent\n")
    result = run([repo])
    assert not result.ok
    assert any("limitless-agent" in error.message for error in result.errors)


def test_run_skips_wheelhouse_and_pycache(tmp_path):
    repo = _make_repo(tmp_path)
    wheel = repo / "validators/wheelhouse"
    wheel.mkdir(parents=True)
    (wheel / "package-limitless.whl").write_bytes(b"\x00\x01\x02LIMITLESS\x00")
    cache = repo / "validators/__pycache__"
    cache.mkdir(parents=True)
    (cache / "limitless.cpython-311.pyc").write_bytes(b"LIMITLESS")
    result = run([repo])
    assert result.ok, [e.format() for e in result.errors]


def test_cli_scan_no_limitless_runs_real_check(capsys, monkeypatch, tmp_path):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    exit_code = main(["scan-no-limitless"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "PASS no_limitless_strings" in out
    assert "stub" not in out.lower()


def test_cli_scan_no_limitless_reports_violation(capsys, monkeypatch, tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "docs/contracts/bad.md").write_text("tenant: limitless\n")
    monkeypatch.chdir(repo)
    exit_code = main(["scan-no-limitless"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL no_limitless_strings" in out
    assert "FR-024" in out


def test_cli_scan_no_limitless_json_output(capsys, monkeypatch, tmp_path):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)
    exit_code = main(["--json", "scan-no-limitless"])
    assert exit_code == 0
    import json as _json

    payload = _json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["results"][0]["name"] == "no_limitless_strings"
