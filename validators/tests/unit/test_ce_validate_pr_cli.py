from __future__ import annotations

import pytest

from creator_engine_validator import ce_cli


def test_ce_validate_pr_dispatches_to_preflight(monkeypatch):
    captured = {}

    def fake_run_cli(args):
        captured["repo_root"] = args.repo_root
        captured["base"] = args.base
        captured["declared_work_class"] = args.declared_work_class
        captured["head_ref"] = args.head_ref
        captured["allow_dirty"] = args.allow_dirty
        return 17

    monkeypatch.setattr(ce_cli.pr_preflight, "run_cli", fake_run_cli)

    rc = ce_cli.main(
        [
            "validate-pr",
            "--repo-root",
            "/worktree",
            "--base",
            "origin/main",
            "--declared-work-class",
            "feature",
            "--head-ref",
            "dev4-night-lane0-pr-preflight",
            "--allow-dirty",
        ]
    )

    assert rc == 17
    assert captured == {
        "repo_root": "/worktree",
        "base": "origin/main",
        "declared_work_class": "feature",
        "head_ref": "dev4-night-lane0-pr-preflight",
        "allow_dirty": True,
    }


def test_ce_validate_pr_requires_declared_work_class():
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(["validate-pr"])

    assert exc.value.code == 2
