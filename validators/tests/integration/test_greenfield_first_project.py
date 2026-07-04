"""Integration-style coverage for the E4 greenfield first-project projection."""

from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import v3_cli
from validators.tests.unit.test_v3_cli import _GREENFIELD_ANSWERS_YAML, _brownfield_cli_probe, _spec
import pytest

pytestmark = pytest.mark.slow



def test_greenfield_onboard_plan_is_read_only_and_bootstrap_not_ship(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe(origin_remote=None))
    root = tmp_path / "state"
    answers = tmp_path / "ce-install.answers.yaml"
    answers.write_text(_GREENFIELD_ANSWERS_YAML, encoding="utf-8")

    code = v3_cli.main([
        "install",
        "--spec", str(_spec(tmp_path)),
        "--answers", str(answers),
        "--plan",
        "--root", str(root),
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    first = payload["first_project"]
    assert first["mode"] == "greenfield"
    assert first["e2_apply_required"] is True
    assert first["first_ship_not_yet_counted"] is True
    assert first["frame_to_ship"]["first_pr_merged"] is False
    assert first["scaffold_input"]["kind"] == "minimal"
    assert first["scaffold_input"]["supplied_to_e2_leg"] == "workspace_checkout"

    assert not (root / "onboard" / "ledger.ndjson").exists()
    assert not (root / "onboard" / "apply.lock").exists()
    assert not (Path(first["project_root"]) / "README.md").exists()
