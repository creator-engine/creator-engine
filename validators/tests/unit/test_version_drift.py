from __future__ import annotations

from pathlib import Path

from creator_engine_validator.checks import version_drift as chk
from creator_engine_validator.cli import main


def _write_repo(root: Path, line: str) -> None:
    package = root / "validators" / "creator_engine_validator"
    package.mkdir(parents=True)
    (package / "version.py").write_text('__version__ = "0.3.2"\n', encoding="utf-8")
    (root / "README.md").write_text(line + "\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "llms.txt").write_text("https://creator-engine.dev/downloads/0.3.2/SHA256SUMS\n", encoding="utf-8")
    (root / "deploy" / "oci").mkdir(parents=True)
    (root / "deploy" / "oci" / "README.md").write_text("creator-engine/ce-validator:0.3.2\n", encoding="utf-8")
    (root / "deploy" / "oci" / "build-image.sh").write_text("creator-engine/ce-validator:0.3.2\n", encoding="utf-8")
    (root / "deploy" / "daemons").mkdir(parents=True)
    (root / "deploy" / "daemons" / "Dockerfile").write_text("creator-engine/ce-validator:0.3.2\n", encoding="utf-8")
    (root / "deploy" / "daemons" / "README.md").write_text(
        "ghcr.io/creator-engine/creator-engine/ce-runtime:0.3.2\n",
        encoding="utf-8",
    )
    (root / "deploy" / "daemons" / "run-daemon-container.sh").write_text(
        "ghcr.io/creator-engine/creator-engine/ce-runtime:0.3.2\n",
        encoding="utf-8",
    )
    (root / "deploy" / "runtime-image").mkdir(parents=True)
    (root / "deploy" / "runtime-image" / "Dockerfile").write_text("CE_IMAGE_VERSION=0.3.2\n", encoding="utf-8")
    (root / "deploy" / "seat-image").mkdir(parents=True)
    (root / "deploy" / "seat-image" / "Dockerfile").write_text("CE_IMAGE_VERSION=0.3.2\n", encoding="utf-8")


def _surface(path: str = "README.md") -> chk.CurrentVersionSurface:
    return chk.CurrentVersionSurface(path, (chk.PACKAGE_PIN,))


def _readme_surface(path: str = "README.md") -> chk.CurrentVersionSurface:
    return chk.CurrentVersionSurface(path, (chk.README_CE_VERSION_TEXT,))


def _readme_surface_with_package_pin(path: str = "README.md") -> chk.CurrentVersionSurface:
    return chk.CurrentVersionSurface(path, (chk.PACKAGE_PIN, chk.README_CE_VERSION_TEXT))


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


def test_readme_ce_version_text_matching_current_version_passes(tmp_path: Path):
    matching_forms = [
        "Current release: 0.3.2",
        "CE version 0.3.2",
        "CE v0.3.2 is current",
        "Creator Engine Version 0.3.2 is current",
        "creator-engine version 0.3.2 is current",
        "creator engine version 0.3.2 is current",
    ]

    for idx, line in enumerate(matching_forms):
        repo = tmp_path / f"matching-{idx}"
        _write_repo(repo, line=line)

        errors = chk.evaluate(repo, surfaces=(_readme_surface(),))

        assert errors == ()


def test_readme_ce_version_text_stale_version_fails_for_public_current_claim_forms(tmp_path: Path):
    stale_forms = [
        "Current release: 0.3.1",
        "CE version 0.3.1",
        "CE v0.3.1 is current",
        "Creator Engine Version 0.3.1 is current",
        "creator-engine version 0.3.1 is current",
        "creator engine version 0.3.1 is current",
        "CE release 0.3.1 is current",
    ]

    for idx, line in enumerate(stale_forms):
        repo = tmp_path / f"stale-{idx}"
        _write_repo(repo, line=line)

        errors = chk.evaluate(repo, surfaces=(_readme_surface(),))

        assert len(errors) == 1, line
        assert errors[0].code == chk.CODE_STALE
        assert errors[0].path == "README.md:1"
        assert "'0.3.1'" in errors[0].message
        assert "'0.3.2'" in errors[0].message


def test_readme_without_version_text_passes(tmp_path: Path):
    _write_repo(tmp_path, line="Creator Engine points readers to the release badge and changelog.")

    errors = chk.evaluate(tmp_path, surfaces=(_readme_surface(),))

    assert errors == ()


def test_readme_python_version_text_does_not_trigger_ce_version_drift(tmp_path: Path):
    _write_repo(
        tmp_path,
        line="Requires Python version 3.14.0 and creator-engine-validator==0.3.2.",
    )

    errors = chk.evaluate(tmp_path, surfaces=(_readme_surface_with_package_pin(),))

    assert errors == ()


def test_readme_ce_version_current_claim_passes(tmp_path: Path):
    _write_repo(
        tmp_path,
        line="CE version 0.3.2 ships with creator-engine-validator==0.3.2.",
    )

    errors = chk.evaluate(tmp_path, surfaces=(_readme_surface_with_package_pin(),))

    assert errors == ()


def test_readme_ce_version_stale_claim_fails(tmp_path: Path):
    _write_repo(
        tmp_path,
        line="CE version 0.2.9 ships with creator-engine-validator==0.3.2.",
    )

    errors = chk.evaluate(tmp_path, surfaces=(_readme_surface_with_package_pin(),))

    assert len(errors) == 1
    assert errors[0].code == chk.CODE_STALE
    assert errors[0].path == "README.md:1"
    assert "'0.2.9'" in errors[0].message
    assert "'0.3.2'" in errors[0].message


def test_readme_common_runtime_version_text_does_not_trigger_ce_version_drift(tmp_path: Path):
    for idx, line in enumerate(
        [
            "Requires Python version 3.12.0 or later.",
            "Node version 20.0.0 is used by the website toolchain.",
        ]
    ):
        repo = tmp_path / f"runtime-{idx}"
        _write_repo(repo, line=line)

        errors = chk.evaluate(repo, surfaces=(_readme_surface(),))

        assert errors == ()


def test_llms_txt_is_current_version_surface():
    assert any(surface.path == "docs/llms.txt" for surface in chk.CURRENT_VERSION_SURFACES)


def test_readme_is_current_version_surface_with_ce_version_text_pattern():
    readme = next(surface for surface in chk.CURRENT_VERSION_SURFACES if surface.path == "README.md")

    assert chk.README_CE_VERSION_TEXT in readme.patterns


def test_verify_version_drift_cli_returns_nonzero_for_stale_claim(tmp_path: Path, capsys):
    _write_repo(
        tmp_path,
        line="Install with `creator-engine-validator==0.3.1` for the current release.",
    )

    assert main(["verify-version-drift", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "FAIL version_drift_current_surfaces" in out
    assert "README.md:1" in out


def test_verify_version_drift_allows_annotated_historical_claim(tmp_path: Path):
    _write_repo(
        tmp_path,
        "Historical note: creator-engine-validator==0.3.1 was the prior release. "
        "<!-- ce-version-drift: allow-historical 0.3.1 -->",
    )

    assert main(["verify-version-drift", str(tmp_path)]) == 0


def test_check_invocation_does_not_run_repo_wide_version_drift(monkeypatch, capsys):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("version drift evaluator must not run from generic ce check")

    monkeypatch.setattr(chk, "evaluate", fail_if_called)

    assert main(["check", "examples/well-formed/identity-record.yml"]) == 0

    out = capsys.readouterr().out
    assert "version_drift_current_surfaces" not in out
    assert "version_drift_stale_current_claim" not in out
