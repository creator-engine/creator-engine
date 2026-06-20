"""Unit tests for the CE playbook format gate (ce-ops#145)."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import ce_playbook_format as p
from creator_engine_validator.cli import main


def _workflow(name: str) -> str:
    return dedent(
        f"""
        kind: ce-playbook
        schema_version: "1"
        playbook:
          name: {name}
          title: "{name} playbook"
          type: workflow
          owner_issue: ce-ops#145
          status: active
        preconditions:
          - id: ready
            description: "Dispatch brief and authority envelope are present."
        outputs:
          - id: report
            description: "Closed-set result report."
        dispatch:
          default_target: governed-seat
          authority_envelope: envelope.template.yml
        gates:
          - id: evidence
            type: evidence
            description: "Evidence is captured before closeout."
            required: true
        stages:
          - id: prepare
            title: "Prepare"
            brief: briefs/prepare.md
            dispatch_target: governed-seat
            gates: [evidence]
        ratified_flow_hooks:
          - id: stop-line
            trigger: stage-complete
            action: "Record completion evidence."
        references:
          - ce-ops#145
        """
    ).lstrip()


def _write_playbook(playbooks_root: Path, name: str) -> Path:
    root = playbooks_root / name
    (root / "briefs").mkdir(parents=True)
    (root / "README.md").write_text(f"# {name}\n\nA test playbook.\n", encoding="utf-8")
    (root / "workflow.ce.yml").write_text(_workflow(name), encoding="utf-8")
    (root / "envelope.template.yml").write_text(
        "scope:\n  issue: ce-ops#145\nauthority:\n  dispatch_target: governed-seat\n",
        encoding="utf-8",
    )
    (root / "briefs" / "prepare.md").write_text("# Prepare\n", encoding="utf-8")
    (root / "harness.md").write_text("# Harness\n\nHalt on missing authority.\n", encoding="utf-8")
    return root


def _write_index(playbooks_root: Path, names: list[str]) -> None:
    rows = "\n".join(f"| [{name}]({name}/) | workflow | Test playbook |" for name in names)
    playbooks_root.mkdir(parents=True, exist_ok=True)
    playbooks_root.joinpath("README.md").write_text(
        "# CE Playbooks\n\n| Playbook | Type | Purpose |\n| --- | --- | --- |\n" + rows + "\n",
        encoding="utf-8",
    )


@pytest.fixture()
def valid_scaffold(tmp_path: Path) -> Path:
    playbooks_root = tmp_path / "playbooks"
    _write_playbook(playbooks_root, "alpha")
    _write_playbook(playbooks_root, "beta")
    _write_index(playbooks_root, ["alpha", "beta"])
    return playbooks_root


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_check_registered():
    checks = registered_checks()
    assert p.CHECK_NAME in checks
    assert p.CODE_REQUIRED_FILE in checks[p.CHECK_NAME].frs
    assert p.CODE_INDEX in checks[p.CHECK_NAME].frs


def test_valid_scaffold_passes(valid_scaffold: Path):
    result = p.run([valid_scaffold])
    assert result.errors == (), [error.format() for error in result.errors]


def test_missing_required_file_fails(valid_scaffold: Path):
    (valid_scaffold / "alpha" / "harness.md").unlink()

    result = p.run([valid_scaffold])

    assert p.CODE_REQUIRED_FILE in _codes(result)
    assert "alpha/harness.md" in "\n".join(error.format() for error in result.errors)


def test_invalid_workflow_schema_fails(valid_scaffold: Path):
    (valid_scaffold / "alpha" / "workflow.ce.yml").write_text(
        "kind: ce-playbook\nschema_version: '1'\nplaybook:\n  name: alpha\n",
        encoding="utf-8",
    )

    result = p.run([valid_scaffold])

    assert p.CODE_SCHEMA in _codes(result)


def test_folder_name_must_match_workflow_name(valid_scaffold: Path):
    (valid_scaffold / "alpha" / "workflow.ce.yml").write_text(
        _workflow("wrong-name"),
        encoding="utf-8",
    )

    result = p.run([valid_scaffold])

    assert p.CODE_NAME in _codes(result)


def test_stage_brief_reference_must_exist(valid_scaffold: Path):
    (valid_scaffold / "alpha" / "briefs" / "prepare.md").unlink()

    result = p.run([valid_scaffold])

    assert p.CODE_BRIEF_REF in _codes(result)


def test_index_must_list_every_playbook(valid_scaffold: Path):
    _write_index(valid_scaffold, ["alpha"])

    result = p.run([valid_scaffold])

    assert p.CODE_INDEX in _codes(result)
    assert "beta" in "\n".join(error.format() for error in result.errors)


def test_cli_check_surfaces_playbook_format_failure(valid_scaffold: Path, capsys):
    (valid_scaffold / "beta" / "README.md").unlink()

    assert main(["check", str(valid_scaffold)]) == 1
    out = capsys.readouterr().out
    assert "FAIL ce_playbook_format" in out
    assert p.CODE_REQUIRED_FILE in out
