"""Unit tests for public PLAYBOOK.md projection and CLI dry-run (ce-ops#248)."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest

from creator_engine_validator import ce_cli, playbook_runtime, v3_cli
from creator_engine_validator.schema import validate_with_schema


def _playbook_text(*, playbook_id: str = "first-governed-pr", title: str = "Ship your first governed PR") -> str:
    return dedent(
        f"""
        ---
        id: {playbook_id}
        title: "{title}"
        goal: "Take a small governed change from plan to merged PR."
        status: active
        prerequisites:
          - id: onboarded-repo
            description: "A CE-onboarded repository is available."
        triggers:
          - "I want to ship a governed change."
        steps:
          - id: plan
            action: "Frame the change and confirm done."
            expected_result: "The change is framed."
          - id: author
            action: "Author the change on a branch."
            command: "python -c 'print(1)'"
            expected_result: "The branch is updated."
          - id: review
            action: "Review the current PR head."
          - id: merge
            action: "Ratify and land the PR."
        expected_outcome:
          - id: merged-pr
            description: "A reviewed, green PR is merged."
        mode: dev
        gates:
          - plan
          - author
          - review
          - merge
        work_class: tiny
        related:
          - review/governed-code-review
        ---

        ## Overview

        A public playbook for a governed PR.

        ## What you need

        A CE-onboarded repository.

        ## Steps

        Follow the listed gates.

        ## Customization

        Tune the work class.

        ## Related

        See governed review.
        """
    ).lstrip()


def _write_public_playbook(root: Path, spine: str = "author", playbook_id: str = "first-governed-pr") -> Path:
    path = root / spine / playbook_id / "PLAYBOOK.md"
    path.parent.mkdir(parents=True)
    path.write_text(_playbook_text(playbook_id=playbook_id), encoding="utf-8")
    return path


def test_public_playbook_projects_to_internal_schema(tmp_path: Path):
    path = _write_public_playbook(tmp_path)

    playbook = playbook_runtime.load_playbook(path)

    descriptor = playbook.descriptor
    assert descriptor["kind"] == "ce-playbook"
    assert descriptor["playbook"]["name"] == "first-governed-pr"
    assert descriptor["metadata"]["mode"] == "dev"
    assert descriptor["metadata"]["work_class"] == "XS"
    assert {gate["id"]: gate["type"] for gate in descriptor["gates"]}["author"] == "dod"
    assert descriptor["stages"][1] == {
        "id": "author",
        "title": "Author",
        "action": "Author the change on a branch.",
        "command": "python -c 'print(1)'",
        "expected_result": "The branch is updated.",
        "brief": "briefs/author.md",
        "dispatch_target": "author-seat",
        "gates": ["author"],
    }
    assert validate_with_schema(
        descriptor,
        "schemas/playbook.schema.yaml",
        path,
        code="TEST",
        contract="schemas/playbook.schema.yaml",
    ) == []


def test_invalid_frontmatter_refuses(tmp_path: Path):
    path = _write_public_playbook(tmp_path)
    text = path.read_text(encoding="utf-8").replace("status: active", "status: unknown")
    path.write_text(text, encoding="utf-8")

    with pytest.raises(playbook_runtime.PlaybookError) as excinfo:
        playbook_runtime.load_playbook(path)

    assert playbook_runtime.CODE_PUBLIC in {error.code for error in excinfo.value.errors}
    assert "/status" in "\n".join(error.path for error in excinfo.value.errors)
    assert all("/tmp/ce-playbooks" not in error.contract for error in excinfo.value.errors)
    assert {error.contract for error in excinfo.value.errors} == {"docs/contracts/playbook-format.md"}


def test_list_show_and_run_dry_run_cli(tmp_path: Path, capsys):
    path = _write_public_playbook(tmp_path)

    assert ce_cli.main(["playbook", "list", "--playbooks-root", str(tmp_path), "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["playbooks"][0]["id"] == "first-governed-pr"

    assert ce_cli.main(["playbook", "show", "first-governed-pr", "--playbooks-root", str(tmp_path), "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["descriptor"]["playbook"]["name"] == "first-governed-pr"
    assert shown["playbook"]["path"] == str(path)

    assert ce_cli.main(["playbook", "run", str(path), "--dry-run", "--json"]) == 0
    planned = json.loads(capsys.readouterr().out)
    assert planned["action"] == "playbook_run_planned"
    assert planned["dry_run"] is True
    assert planned["has_authority"] is False
    assert planned["mode"] == "dev"
    assert planned["work_class"] == "XS"
    assert [gate["type"] for gate in planned["gates"] if gate["id"] == "author"] == ["dod"]
    assert planned["plan"]["dry_run"] is True
    assert planned["plan"]["mode"] == "dev"
    assert [stage["id"] for stage in planned["plan"]["stages"]] == ["plan", "author", "review", "merge"]
    assert planned["plan"]["stages"][1]["command"] == "python -c 'print(1)'"


def test_run_with_mocked_executor_reports_step_and_final_status(tmp_path: Path):
    path = _write_public_playbook(tmp_path)
    playbook = playbook_runtime.load_playbook(path)
    seen: list[str] = []

    def executor(step: playbook_runtime.StepExecution, cwd: Path) -> playbook_runtime.StepExecution:
        seen.append(step.id)
        return playbook_runtime.StepExecution(
            id=step.id,
            title=step.title,
            action=step.action,
            command=step.command,
            expected_result=step.expected_result,
            returncode=0,
            stdout=f"{step.id} ok\n",
            stderr="",
            governance_decision={"decision": "allow", "reason": "mocked"},
        )

    payload = playbook_runtime.run_playbook(playbook, executor=executor, cwd=tmp_path)

    assert payload["ok"] is True
    assert payload["action"] == "playbook_run_completed"
    assert payload["final_status"] == "PASS"
    assert [step["status"] for step in payload["steps"]] == ["PASS", "PASS", "PASS", "PASS"]
    assert [step["id"] for step in payload["steps"]] == seen == ["plan", "author", "review", "merge"]
    assert payload["steps"][1]["command"] == "python -c 'print(1)'"


def test_v3_cli_exposes_playbook_dry_run(tmp_path: Path, capsys):
    _write_public_playbook(tmp_path)

    assert v3_cli.main(["playbook", "run", "first-governed-pr", "--playbooks-root", str(tmp_path), "--dry-run", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "playbook_run_planned"
    assert payload["dry_run"] is True
    assert payload["has_authority"] is False
    assert payload["mode"] == "dev"
    assert payload["plan"]["work_class"] == "XS"


def test_smoke_first_governed_pr_exemplar_projects_to_schema():
    exemplar = Path("/tmp/ce-playbooks/author/first-governed-pr/PLAYBOOK.md")
    if not exemplar.is_file():
        pytest.skip("/tmp/ce-playbooks exemplar is not present")

    playbook = playbook_runtime.load_playbook(exemplar)

    assert playbook.id == "first-governed-pr"
    assert playbook.descriptor["metadata"]["work_class"] == "XS"
    assert validate_with_schema(
        playbook.descriptor,
        "schemas/playbook.schema.yaml",
        exemplar,
        code="TEST",
        contract="schemas/playbook.schema.yaml",
    ) == []
