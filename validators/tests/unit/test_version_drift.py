from __future__ import annotations

from pathlib import Path

from creator_engine_validator.checks import version_drift as chk
from creator_engine_validator.cli import main


def _write_repo(root: Path, *, line: str) -> None:
    package = root / "validators" / "creator_engine_validator"
    package.mkdir(parents=True)
    (package / "version.py").write_text('__version__ = "0.3.2"\n', encoding="utf-8")
    (root / "README.md").write_text(line + "\n", encoding="utf-8")


def _surface(path: str = "README.md") -> chk.CurrentVersionSurface:
    return chk.CurrentVersionSurface(path, (chk.PACKAGE_PIN,))


def test_stale_current_version_claim_fails_with_line_and_version(tmp_path: Path):
    _write_repo(
        tmp_path,
        line="Install with `creator-engine-validator==0.3.1` for the current release.",
    )

    errors = chk.evaluate(tmp_path, surfaces=(_surface(),))

    assert len(errors) == 1
    assert errors[0].code == chk.CODE_STALE
    assert errors[0].path == "README.md:1"
    assert "'0.3.1'" in errors[0].message
    assert "'0.3.2'" in errors[0].message


def test_historical_annotated_mention_passes(tmp_path: Path):
    _write_repo(
        tmp_path,
        line=(
            "Historical note: creator-engine-validator==0.3.1 was the prior "
            f"release. <!-- {chk.ANNOTATION} 0.3.1 -->"
        ),
    )

    errors = chk.evaluate(tmp_path, surfaces=(_surface(),))

    assert errors == ()


def test_allow_historical_without_matching_pin_fails_for_real_drift(tmp_path: Path):
    _write_repo(
        tmp_path,
        line=(
            "Install with `creator-engine-validator==0.3.1` for the current release. "
            f"<!-- {chk.ANNOTATION} -->"
        ),
    )

    errors = chk.evaluate(tmp_path, surfaces=(_surface(),))

    assert len(errors) == 1
    assert errors[0].code == chk.CODE_STALE
    assert errors[0].path == "README.md:1"


def test_allow_historical_wrong_pin_fails_for_real_drift(tmp_path: Path):
    _write_repo(
        tmp_path,
        line=(
            "Install with `creator-engine-validator==0.3.1` for the current release. "
            f"<!-- {chk.ANNOTATION} 0.3.0 -->"
        ),
    )

    errors = chk.evaluate(tmp_path, surfaces=(_surface(),))

    assert len(errors) == 1
    assert errors[0].code == chk.CODE_STALE
    assert errors[0].path == "README.md:1"


def test_current_version_claim_passes(tmp_path: Path):
    _write_repo(
        tmp_path,
        line="Install with `creator-engine-validator==0.3.2` for the current release.",
    )

    errors = chk.evaluate(tmp_path, surfaces=(_surface(),))

    assert errors == ()


def test_llms_txt_is_current_version_surface():
    assert any(surface.path == "docs/llms.txt" for surface in chk.CURRENT_VERSION_SURFACES)


def test_verify_version_drift_cli_returns_nonzero_for_stale_claim(tmp_path: Path, capsys):
    _write_repo(
        tmp_path,
        line="Install with `creator-engine-validator==0.3.1` for the current release.",
    )

    assert main(["verify-version-drift", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "FAIL version_drift_current_surfaces" in out
    assert "README.md:1" in out


def test_check_invocation_does_not_run_repo_wide_version_drift(monkeypatch, capsys):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("version drift evaluator must not run from generic ce check")

    monkeypatch.setattr(chk, "evaluate", fail_if_called)

    assert main(["check", "examples/well-formed/identity-record.yml"]) == 0

    out = capsys.readouterr().out
    assert "version_drift_current_surfaces" not in out
    assert "version_drift_stale_current_claim" not in out
