"""RV1-061 — unit tests for the ``ce doctor`` CLI surface (strict refusal-TDD).

Drives ``creator_engine_validator.ce_cli.main`` directly. Host detection is
replaced by a crafted :class:`EnvironmentFacts` snapshot via the monkeypatchable
``doctor_runtime.detect_environment`` seam, so the guard PASS/FAIL branches are
exercised deterministically and offline.
"""
from __future__ import annotations

import json

import pytest

from creator_engine_validator import ce_cli, doctor_runtime
from creator_engine_validator import environment_guard as guard
from creator_engine_validator.packaging_runtime import PackagingContractResult


def _facts(**overrides) -> guard.EnvironmentFacts:
    base = dict(
        version_info=(3, 14, 5),
        repo_root_is_git=True,
        hermes_ignored=True,
        tmux_available=True,
        podman_available=True,
        podman_rootless=True,
        uv_available=True,
        packaging=PackagingContractResult(ok=True, violations=[], details={}),
        hidden_continuation=False,
        active_work_ledger_present=True,
    )
    base.update(overrides)
    return guard.EnvironmentFacts(**base)


@pytest.fixture()
def inject_facts(monkeypatch):
    def _install(**overrides):
        facts = _facts(**overrides)
        monkeypatch.setattr(doctor_runtime, "detect_environment", lambda *a, **k: facts)
        return facts

    return _install


def test_doctor_help_is_reachable():
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(["doctor", "--help"])
    assert exc.value.code == 0


def test_doctor_json_passes_on_governed_host(inject_facts, capsys):
    inject_facts()
    ret = ce_cli.main(["doctor", "--json", "--repo-root", "."])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["refused_clauses"] == []


def test_doctor_refuses_out_of_contract_interpreter(inject_facts, capsys):
    inject_facts(version_info=(3, 13, 13))
    ret = ce_cli.main(["doctor", "--json", "--repo-root", "."])
    assert ret != 0
    payload = json.loads(capsys.readouterr().out)
    assert guard.CLAUSE_INTERPRETER in payload["refused_clauses"]


def test_doctor_refuses_ungoverned_hermes_posture(inject_facts, capsys):
    inject_facts(hermes_ignored=False)
    ret = ce_cli.main(["doctor", "--json", "--repo-root", "."])
    assert ret != 0
    payload = json.loads(capsys.readouterr().out)
    assert guard.CLAUSE_STATE_PATH in payload["refused_clauses"]


def test_doctor_refuses_missing_tmux_with_require_visible_launch(inject_facts, capsys):
    inject_facts(tmux_available=False)
    ret = ce_cli.main(["doctor", "--json", "--repo-root", ".", "--require-visible-launch"])
    assert ret != 0
    payload = json.loads(capsys.readouterr().out)
    assert guard.CLAUSE_TMUX in payload["refused_clauses"]


def test_doctor_refuses_rootful_podman_with_require_worker(inject_facts, capsys):
    inject_facts(podman_available=True, podman_rootless=False)
    ret = ce_cli.main(["doctor", "--json", "--repo-root", ".", "--require-worker"])
    assert ret != 0
    payload = json.loads(capsys.readouterr().out)
    assert guard.CLAUSE_PODMAN in payload["refused_clauses"]


def test_doctor_human_output_is_nonempty(inject_facts, capsys):
    inject_facts()
    ret = ce_cli.main(["doctor", "--repo-root", "."])
    assert ret == 0
    out = capsys.readouterr().out
    assert "doctor" in out.lower()
