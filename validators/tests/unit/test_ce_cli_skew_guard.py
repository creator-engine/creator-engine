from __future__ import annotations

from pathlib import Path

from creator_engine_validator import ce_cli


def _write_checkout(root: Path, version: str) -> Path:
    repo = root / "repo"
    package = repo / "validators" / "creator_engine_validator"
    package.mkdir(parents=True)
    (package / "ce_cli.py").write_text("# source checkout marker\n", encoding="utf-8")
    (repo / "validators" / "pyproject.toml").write_text(
        f'[project]\nname = "creator-engine-validator"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    return repo


def _as_installed_wheel(monkeypatch, tmp_path: Path, running_version: str = "0.3.1") -> None:
    installed = tmp_path / "venv" / "lib" / "python3.14" / "site-packages" / "creator_engine_validator" / "ce_cli.py"
    installed.parent.mkdir(parents=True)
    installed.write_text("# installed wheel marker\n", encoding="utf-8")
    monkeypatch.setattr(ce_cli, "__file__", str(installed))
    monkeypatch.setattr(ce_cli.importlib_metadata, "version", lambda package: running_version)


def test_stale_wheel_refuses_validate_pr_gate(monkeypatch, tmp_path, capsys):
    repo = _write_checkout(tmp_path, "0.3.2")
    _as_installed_wheel(monkeypatch, tmp_path)
    monkeypatch.chdir(repo)

    ret = ce_cli.main(["validate-pr", "--repo-root", str(repo)])

    assert ret == 2
    err = capsys.readouterr().err
    assert "stale-wheel/source-version skew detected" in err
    assert "validators version 0.3.2" in err
    assert "running package creator-engine-validator is 0.3.1" in err
    assert "PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr" in err
    assert "CE_ALLOW_STALE_WHEEL=1" in err


def test_stale_wheel_refuses_brain_gate(monkeypatch, tmp_path, capsys):
    repo = _write_checkout(tmp_path, "0.3.2")
    _as_installed_wheel(monkeypatch, tmp_path)
    monkeypatch.chdir(repo)

    ret = ce_cli.main(["brain", "verify"])

    assert ret == 2
    err = capsys.readouterr().err
    assert "Refusing gate-relevant `ce brain verify`" in err
    assert "creator_engine_validator.ce_cli brain verify" in err


def test_stale_wheel_override_allows_gate(monkeypatch, tmp_path, capsys):
    repo = _write_checkout(tmp_path, "0.3.2")
    _as_installed_wheel(monkeypatch, tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("CE_ALLOW_STALE_WHEEL", "1")
    monkeypatch.setattr(ce_cli.pr_preflight, "run_cli", lambda args: 0)

    ret = ce_cli.main(["validate-pr", "--repo-root", str(repo)])

    assert ret == 0
    assert "proceeding by explicit override" in capsys.readouterr().err


def test_stale_wheel_warns_for_non_gate_command(monkeypatch, tmp_path, capsys):
    repo = _write_checkout(tmp_path, "0.3.2")
    _as_installed_wheel(monkeypatch, tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(ce_cli, "_doctor", lambda args: 0)

    ret = ce_cli.main(["doctor", "--repo-root", str(repo), "--no-check-packaging"])

    assert ret == 0
    err = capsys.readouterr().err
    assert err.count("stale-wheel/source-version skew detected") == 1
    assert "Non-gate `ce doctor` will proceed" in err
    version_idx = err.index("validators version 0.3.2")
    running_idx = err.index("running package creator-engine-validator is 0.3.1")
    pythonpath_idx = err.index("PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli doctor")
    override_idx = err.index("CE_ALLOW_STALE_WHEEL=1")
    assert version_idx < running_idx < pythonpath_idx < override_idx


def test_matching_installed_wheel_version_is_silent_and_proceeds(monkeypatch, tmp_path, capsys):
    repo = _write_checkout(tmp_path, "0.3.1")
    _as_installed_wheel(monkeypatch, tmp_path, running_version="0.3.1")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(ce_cli.pr_preflight, "run_cli", lambda args: 0)

    ret = ce_cli.main(["validate-pr", "--repo-root", str(repo)])

    assert ret == 0
    assert capsys.readouterr().err == ""


def test_source_module_invocation_does_not_guard(monkeypatch, tmp_path, capsys):
    repo = _write_checkout(tmp_path, "0.3.2")
    monkeypatch.setattr(
        ce_cli,
        "__file__",
        str(repo / "validators" / "creator_engine_validator" / "ce_cli.py"),
    )
    monkeypatch.setattr(ce_cli.importlib_metadata, "version", lambda package: "0.3.1")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(ce_cli.pr_preflight, "run_cli", lambda args: 0)

    ret = ce_cli.main(["validate-pr", "--repo-root", str(repo)])

    assert ret == 0
    assert "stale-wheel/source-version skew" not in capsys.readouterr().err
