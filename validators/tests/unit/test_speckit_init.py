from pathlib import Path

import pytest

from creator_engine_validator import ce_cli, speckit_init


def test_scaffold_creates_specify_tree_and_skill_artifacts(tmp_path: Path):
    result = speckit_init.scaffold_speckit(tmp_path)

    assert ".specify/templates/spec-template.md" in result.created
    assert ".specify/scripts/bash/common.sh" in result.created
    assert ".specify/extensions/git/commands/speckit.git.feature.md" in result.created
    assert ".ce/skills/speckit-specify.md" in result.created
    assert ".ce/skills/speckit-git-validate.md" in result.created
    assert result.skipped == ()
    assert result.overwritten == ()
    assert (tmp_path / ".specify" / "templates" / "spec-template.md").is_file()
    assert (tmp_path / ".ce" / "skills" / "speckit-specify.md").is_file()


def test_scaffold_is_idempotent_and_does_not_clobber_user_edits(tmp_path: Path):
    speckit_init.scaffold_speckit(tmp_path)
    edited = tmp_path / ".specify" / "templates" / "spec-template.md"
    edited.write_text("user edit\n", encoding="utf-8")

    result = speckit_init.scaffold_speckit(tmp_path)

    assert ".specify/templates/spec-template.md" in result.skipped
    assert result.created == ()
    assert result.overwritten == ()
    assert edited.read_text(encoding="utf-8") == "user edit\n"


def test_scaffold_force_overwrites_existing_files(tmp_path: Path):
    speckit_init.scaffold_speckit(tmp_path)
    edited = tmp_path / ".specify" / "templates" / "spec-template.md"
    edited.write_text("user edit\n", encoding="utf-8")

    result = speckit_init.scaffold_speckit(tmp_path, force=True)

    assert ".specify/templates/spec-template.md" in result.overwritten
    assert result.skipped == ()
    assert edited.read_text(encoding="utf-8").startswith("# Feature Specification:")


def test_scaffold_missing_target_errors_cleanly(tmp_path: Path):
    missing = tmp_path / "missing"

    with pytest.raises(speckit_init.MissingTargetError) as exc:
        speckit_init.scaffold_speckit(missing)

    assert exc.value.code == "missing_target"
    assert str(missing.resolve()) in str(exc.value)


def test_scaffold_uses_injected_writer_and_artifacts(tmp_path: Path):
    writes: list[tuple[Path, str]] = []
    artifact = speckit_init.ScaffoldArtifact("nested/file.txt", "payload\n")

    result = speckit_init.scaffold_speckit(
        tmp_path,
        artifacts=(artifact,),
        writer=lambda path, content: writes.append((path, content)),
    )

    assert result.created == ("nested/file.txt",)
    assert writes == [(tmp_path / "nested" / "file.txt", "payload\n")]
    assert not (tmp_path / "nested" / "file.txt").exists()


def test_ce_speckit_init_reports_missing_target(tmp_path: Path, capsys):
    rc = ce_cli.main(["speckit", "init", "--target", str(tmp_path / "missing")])

    captured = capsys.readouterr()
    assert rc == 1
    assert "ERROR: ce speckit init failed [missing_target]" in captured.err


def test_ce_speckit_init_defaults_to_cwd(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    rc = ce_cli.main(["speckit", "init"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "ce speckit init:" in captured.out
    assert (tmp_path / ".specify" / "templates" / "spec-template.md").is_file()
