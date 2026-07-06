"""Focused unit tests for the CE-native project initializer."""
from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator import ce_cli, journey_guidance, project_init


def test_embedded_templates_are_ce_native():
    templates = project_init.embedded_templates()
    paths = {t.path for t in templates}
    combined = "\n".join(t.content for t in templates).lower()

    assert ".ce/scopes/templates/XS-scope-card.md" in paths
    assert ".ce/scopes/templates/S-intent-scope-tasks.md" in paths
    assert ".ce/scopes/templates/M-spec.md" in paths
    assert ".ce/pr-manifests/_template.md" in paths
    assert ".ce/changelog/_template.md" in paths
    assert ".ce/skills/ce-shape-scope/SKILL.md" in paths
    assert ".specify" not in paths
    assert ("spec" + "kit") not in combined
    assert ("spec" + "-kit") not in combined


def test_init_project_creates_right_sized_ce_scaffold(tmp_path: Path):
    result = project_init.init_project(tmp_path / "project")
    root = result.target

    assert result.created
    assert (root / "README.md").is_file()
    assert (root / ".gitignore").read_text(encoding="utf-8") == ".hermes/\n.ce/state/\n"
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "Frame -> Shape -> Build -> Review -> Ship" in readme
    for line in journey_guidance.STAGE_MAP_LINES:
        assert line in readme
    assert "`XS`: `scope_card` only" in readme
    assert "`S`: `intent` + `scope` + `tasks`" in readme
    assert "`M`: full `spec.md` + `plan.md` + `tasks.md`" in readme
    assert "Do not write a full spec for every unit" in readme
    assert "Declared work class: XS|S|M|L" in (
        root / ".ce" / "pr-manifests" / "_template.md"
    ).read_text(encoding="utf-8")


def test_ce_init_output_prints_shared_stage_map(tmp_path: Path, capsys):
    code = ce_cli.main(["init", str(tmp_path / "project")])

    out = capsys.readouterr().out
    assert code == 0
    for line in journey_guidance.STAGE_MAP_LINES:
        assert line in out


def test_init_project_is_idempotent(tmp_path: Path):
    root = tmp_path / "project"
    first = project_init.init_project(root)
    second = project_init.init_project(root)

    assert first.created
    assert second.created == ()
    assert second.overwritten == ()
    assert ".ce/scopes/templates/M-plan.md" in second.skipped


def test_plan_actions_preserves_user_edits_without_force(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "README.md").write_text("custom\n", encoding="utf-8")

    actions = project_init.plan_actions(root, force=False)
    readme = next(a for a in actions if a.path == "README.md")
    assert readme.status == "skipped"
    assert readme.reason == "would overwrite user edits"


def test_init_project_force_overwrites_user_edits(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    readme = root / "README.md"
    readme.write_text("custom\n", encoding="utf-8")

    result = project_init.init_project(root, force=True)
    assert "README.md" in result.overwritten
    assert "CE-Governed Project" in readme.read_text(encoding="utf-8")


def test_init_project_skips_non_file_collision(tmp_path: Path):
    root = tmp_path / "project"
    (root / ".ce" / "README.md").mkdir(parents=True)
    result = project_init.init_project(root, force=True)

    collision = next(a for a in result.actions if a.path == ".ce/README.md")
    assert collision.status == "skipped"
    assert collision.reason == "path exists and is not a file"


def test_init_project_refuses_directory_symlink_escape(tmp_path: Path):
    root = tmp_path / "project"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / ".ce").symlink_to(outside, target_is_directory=True)

    with pytest.raises(project_init.ProjectInitRefused):
        project_init.init_project(root)

    assert list(outside.rglob("*")) == []


def test_init_project_refuses_force_leaf_symlink_escape(tmp_path: Path):
    root = tmp_path / "project"
    outside_file = tmp_path / "outside-readme.md"
    original = b"do not clobber\n"
    root.mkdir()
    outside_file.write_bytes(original)
    (root / "README.md").symlink_to(outside_file)

    with pytest.raises(project_init.ProjectInitRefused):
        project_init.init_project(root, force=True)

    assert outside_file.read_bytes() == original
