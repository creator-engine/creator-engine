"""Integration coverage for the in-tree playbook scaffold (ce-ops#145)."""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.checks import ce_playbook_format as p
from creator_engine_validator.cli import main
pytestmark = pytest.mark.slow


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _cwd_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def test_in_tree_playbooks_pass_format_gate(capsys):
    assert main(["check", "playbooks"]) == 0
    out = capsys.readouterr().out
    assert "PASS ce_playbook_format" in out


def test_playbook_format_check_is_listed(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert p.CHECK_NAME in out
    assert p.CODE_INDEX in out
