from __future__ import annotations

from pathlib import Path

from creator_engine_validator import ce_cli


def test_ce_validate_pr_dispatches_to_preflight(monkeypatch):
    captured = {}

    def fake_run_cli(args):
        captured["repo_root"] = args.repo_root
        captured["base"] = args.base
        captured["declared_work_class"] = args.declared_work_class
        captured["head_ref"] = args.head_ref
        captured["allow_dirty"] = args.allow_dirty
        captured["test_command"] = args.test_command
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
        "test_command": ce_cli.pr_preflight.DEFAULT_TEST_COMMAND,
    }


def test_ce_validate_pr_allows_carrier_declared_work_class_discovery(monkeypatch):
    captured = {}

    def fake_run_cli(args):
        captured["declared_work_class"] = args.declared_work_class
        captured["test_command"] = args.test_command
        return 0

    monkeypatch.setattr(ce_cli.pr_preflight, "run_cli", fake_run_cli)

    rc = ce_cli.main(["validate-pr", "--test-command", "python -m pytest validators/tests/unit/test_pr_preflight.py"])

    assert rc == 0
    assert captured == {
        "declared_work_class": None,
        "test_command": "python -m pytest validators/tests/unit/test_pr_preflight.py",
    }


def test_ce_validate_pr_accepts_pr_body_flags(monkeypatch):
    captured = {}

    def fake_run_cli(args):
        captured["pr_body_file"] = args.pr_body_file
        captured["pr_body"] = args.pr_body
        return 0

    monkeypatch.setattr(ce_cli.pr_preflight, "run_cli", fake_run_cli)

    rc = ce_cli.main(["validate-pr", "--pr-body-file", "body.md", "--pr-body", "inline body"])

    assert rc == 0
    assert captured == {
        "pr_body_file": Path("body.md"),
        "pr_body": "inline body",
    }
