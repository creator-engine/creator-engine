"""G2.007.3 — hook-check CLI carries a reviewer-authority ref into the event.

The live CC-G-C PreToolUse hook cannot rely on Claude to populate the event's
``ce`` extension block. The reviewer venue's launch-pinned authority reference is
therefore passed to the validator as ``--reviewer-authority-ref <path>``; the CLI
injects it as ``ce.reviewer_authority_ref`` *before* ``hook_check.build_context()``
resolves the event, so the same bounded positive/negative semantics already proven
synthetically (mechanic + PR match) now hold on the live path.

Fail-closed: with no ref (or a non-matching PR) the restricted ``pr_review``
mechanic stays denied. Offline; no Claude launch, no pane spawn.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import yaml

from creator_engine_validator.cli import main


def _envelope(**override) -> dict:
    rec = {
        "envelope_id": "rva-pr108-reviewer",
        "mechanic": "pr_review",
        "pr_number": 108,
        "head_sha": "aa02b0ceb192b38f52da0d99f798e1e2710a8a22",
        "actor": "ubuntuaws745-cmyk",
        "ratified_prompt_sha": "ae1b9db11155f4ad841ef3fa399cd508c64d1ff184d1e0d1437e859c0dacfe27",
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T10:43:13Z",
    }
    rec.update(override)
    return rec


def _write_envelope(tmp_path: Path, name: str = "reviewer-authority.ce.yml", **override) -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump({"reviewer_authority_envelope": _envelope(**override)}), encoding="utf-8")
    return path


def _pr_review_event(pr: int = 108, *, approve: bool = False) -> dict:
    flag = "--approve" if approve else "--comment"
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": f"gh pr review {pr} {flag} --body governed-redo"},
        "ce": {"posture": "governed"},
    }


def _run(argv, capsys, monkeypatch, stdin_text):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
    code = main(argv)
    return code, json.loads(capsys.readouterr().out)


def test_cli_reviewer_authority_ref_allows_matching_pr_review(tmp_path, capsys, monkeypatch):
    _write_envelope(tmp_path)
    code, payload = _run(
        [
            "hook-check", "--stdin", "--format", "claude", "--posture", "governed",
            "--posture-root", str(tmp_path),
            "--reviewer-authority-ref", "reviewer-authority.ce.yml",
        ],
        capsys, monkeypatch, json.dumps(_pr_review_event(108)),
    )
    assert code == 0
    assert payload["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_cli_reviewer_authority_ref_denies_matching_pr_review_approve(tmp_path, capsys, monkeypatch):
    _write_envelope(tmp_path)
    code, payload = _run(
        [
            "hook-check", "--stdin", "--format", "claude", "--posture", "governed",
            "--posture-root", str(tmp_path),
            "--reviewer-authority-ref", "reviewer-authority.ce.yml",
        ],
        capsys, monkeypatch, json.dumps(_pr_review_event(108, approve=True)),
    )
    assert code == 0
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_cli_reviewer_authority_ref_denies_wrong_pr(tmp_path, capsys, monkeypatch):
    _write_envelope(tmp_path)
    code, payload = _run(
        [
            "hook-check", "--stdin", "--format", "claude", "--posture", "governed",
            "--posture-root", str(tmp_path),
            "--reviewer-authority-ref", "reviewer-authority.ce.yml",
        ],
        capsys, monkeypatch, json.dumps(_pr_review_event(999)),
    )
    assert code == 0
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_cli_without_ref_denies_pr_review(tmp_path, capsys, monkeypatch):
    # Fail-closed: no launch-pinned ref => no authority => pr_review denied.
    code, payload = _run(
        [
            "hook-check", "--stdin", "--format", "claude", "--posture", "governed",
            "--posture-root", str(tmp_path),
        ],
        capsys, monkeypatch, json.dumps(_pr_review_event(108)),
    )
    assert code == 0
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_cli_ref_does_not_override_inline_event_ce(tmp_path, capsys, monkeypatch):
    # An event that already carries ce.reviewer_authority_ref wins; the CLI flag is a
    # fallback carrier, not an override, so a deliberately wrong flag cannot widen an
    # event that names a different (here absent) ref.
    _write_envelope(tmp_path, name="inline.ce.yml")
    event = _pr_review_event(108)
    event["ce"]["reviewer_authority_ref"] = "inline.ce.yml"
    code, payload = _run(
        [
            "hook-check", "--stdin", "--format", "claude", "--posture", "governed",
            "--posture-root", str(tmp_path),
            "--reviewer-authority-ref", "does-not-exist.ce.yml",
        ],
        capsys, monkeypatch, json.dumps(event),
    )
    assert code == 0
    assert payload["hookSpecificOutput"]["permissionDecision"] == "allow"
