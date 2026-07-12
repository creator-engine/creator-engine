from __future__ import annotations

import json
import subprocess
from pathlib import Path

from creator_engine_validator import ce_cli
from creator_engine_validator import checkpoint_runtime as runtime


def _facts() -> dict[str, object]:
    fact = {"label": "unknown", "fact": "not safely available", "source": "next safe probe"}
    return {
        "facts": {name: dict(fact) for name in runtime.FACT_SECTIONS},
        "delta": [dict(fact)],
        "next_safe_act": "Perform the next safe probe.",
        "reload_sources": ["next safe probe"],
    }


def test_checkpoint_cli_json_and_human_parity(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps(_facts()), encoding="utf-8")
    argv = ["checkpoint", "--facts", str(facts), "--clean-boundary", "clean", "--repo-root", str(tmp_path), "--as-of", "2026-07-12T10:11:12Z"]
    assert ce_cli.main([*argv, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "green"
    assert payload["complete"] is True
    assert payload["clear"] == "not-claimed"
    assert ce_cli.main(argv) == 0
    human = capsys.readouterr().out
    assert payload["path"] in human
    assert payload["sha256"] in human
    assert "/clear was not performed or claimed" in human


def test_checkpoint_cli_help_is_self_describing(capsys) -> None:
    try:
        ce_cli.main(["checkpoint", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "--facts" in capsys.readouterr().out
