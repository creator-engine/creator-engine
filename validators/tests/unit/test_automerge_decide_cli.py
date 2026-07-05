from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from creator_engine_validator import ce_cli
from creator_engine_validator.forge import automerge_policy


def test_automerge_decide_cli_forwards_repo_root_from_non_root_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    non_root_cwd = tmp_path / "elsewhere"
    repo_root.mkdir()
    non_root_cwd.mkdir()
    captured: dict[str, object] = {}

    def fake_decide_automerge(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            to_dict=lambda: {
                "decision": "GESTURE",
                "mutation_class": "docs",
                "size_band": "XS",
            }
        )

    monkeypatch.setattr(automerge_policy, "decide_automerge", fake_decide_automerge)
    monkeypatch.chdir(non_root_cwd)

    rc = ce_cli.main(
        [
            "automerge-decide",
            "--repo-root",
            str(repo_root),
            "--paths",
            "README.md",
            "--json",
        ]
    )

    assert rc == 0
    assert captured["repo_root"] == repo_root
