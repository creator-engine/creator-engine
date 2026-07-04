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


def _clear_recall_env(monkeypatch):
    for name in (
        doctor_runtime.launch_runtime.RECALL_EMBEDDER_ENV,
        doctor_runtime.launch_runtime.RECALL_ENDPOINT_ENV,
        doctor_runtime.launch_runtime.RECALL_ENDPOINT_MODEL_ID_ENV,
        doctor_runtime.launch_runtime.RECALL_ENDPOINT_DIM_ENV,
    ):
        monkeypatch.delenv(name, raising=False)


def _facts(**overrides) -> guard.EnvironmentFacts:
    base = dict(
        version_info=(3, 14, 5),
        repo_root_is_git=True,
        hermes_ignored=True,
        tmux_available=True,
        podman_available=True,
        podman_rootless=True,
        uv_available=True,
        packaging=PackagingContractResult(
            ok=True,
            violations=[],
            details={"dependency_wheelhouse_ok": True, "dependency_wheelhouse_violations": []},
        ),
        hidden_continuation=False,
        active_work_ledger_present=True,
    )
    base.update(overrides)
    return guard.EnvironmentFacts(**base)


@pytest.fixture()
def inject_facts(monkeypatch, tmp_path):
    _clear_recall_env(monkeypatch)
    missing_target_python = tmp_path / "missing-python"
    monkeypatch.setattr(
        doctor_runtime.bootstrap_runtime,
        "default_target_python",
        lambda repo_root: missing_target_python,
    )

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
    assert payload["prerequisites"]["dependency_wheelhouse_offline"] is True
    assert payload["prerequisites"]["dependency_wheelhouse_violations"] == []
    assert payload["prerequisites"]["first_party_app_wheel_committed"] is False
    assert payload["prerequisites"]["ce_dogfood_installed"] is False
    assert payload["requested"]["require_installed_ce"] is False


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


def test_doctor_refuses_source_checkout_when_installed_ce_required(inject_facts, capsys):
    inject_facts(
        ce_invocation="python_module",
        ce_package_origin="source_checkout",
        ce_dogfood_installed=False,
    )
    ret = ce_cli.main(["doctor", "--json", "--repo-root", ".", "--require-installed-ce"])
    assert ret != 0
    payload = json.loads(capsys.readouterr().out)
    assert guard.CLAUSE_INSTALLED_CE in payload["refused_clauses"]
    assert payload["prerequisites"]["ce_dogfood_invocation"] == "python_module"
    assert payload["prerequisites"]["ce_package_origin"] == "source_checkout"


def test_doctor_surfaces_recall_endpoint_probe_without_refusing(
    inject_facts, monkeypatch, capsys
):
    inject_facts()
    monkeypatch.setattr(
        doctor_runtime.launch_runtime,
        "probe_controller_recall_endpoint",
        lambda repo_root: {
            "state": "unavailable",
            "reason": "endpoint down",
            "endpoint": "http://127.0.0.1:8989/v1/embeddings",
            "line": (
                "brain recall: UNAVAILABLE (endpoint down endpoint "
                "http://127.0.0.1:8989/v1/embeddings) - semantic recall disabled "
                "for this session; SSOT assertions unaffected"
            ),
        },
    )

    ret = ce_cli.main(["doctor", "--json", "--repo-root", "."])

    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    check = next(c for c in payload["checks"] if c["clause"] == "CE-BRAIN-RECALL")
    assert check["ok"] is False
    assert check["status"]["state"] == "unavailable"
    assert payload["ok"] is True
    assert "CE-BRAIN-RECALL" not in payload["refused_clauses"]


def test_doctor_human_marks_advisory_recall_probe_as_warning(
    inject_facts, monkeypatch, capsys
):
    inject_facts()
    monkeypatch.setattr(
        doctor_runtime.launch_runtime,
        "probe_controller_recall_endpoint",
        lambda repo_root: {
            "state": "unavailable",
            "reason": "endpoint down",
            "endpoint": "http://127.0.0.1:8989/v1/embeddings",
            "line": (
                "brain recall: UNAVAILABLE (endpoint down endpoint "
                "http://127.0.0.1:8989/v1/embeddings) - semantic recall disabled "
                "for this session; SSOT assertions unaffected"
            ),
        },
    )

    ret = ce_cli.main(["doctor", "--repo-root", "."])

    assert ret == 0
    out = capsys.readouterr().out
    assert "[WARN] CE-BRAIN-RECALL brain recall endpoint" in out
    assert "[FAIL] CE-BRAIN-RECALL brain recall endpoint" not in out


def test_doctor_accepts_installed_console_when_required(inject_facts, capsys):
    inject_facts(
        ce_invocation="console_script",
        ce_package_origin="installed",
        ce_dogfood_installed=True,
    )
    ret = ce_cli.main(["doctor", "--json", "--repo-root", ".", "--require-installed-ce"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert guard.CLAUSE_INSTALLED_CE not in payload["refused_clauses"]
    check = next(c for c in payload["checks"] if c["clause"] == guard.CLAUSE_INSTALLED_CE)
    assert check["applicable"] is True
    assert check["ok"] is True


def test_doctor_detects_source_checkout_python_module(tmp_path):
    repo_root = tmp_path / "repo"
    module_file = repo_root / "validators" / "creator_engine_validator" / "doctor_runtime.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("# test module\n", encoding="utf-8")

    posture = doctor_runtime.detect_ce_dogfood_posture(
        repo_root,
        argv0="creator_engine_validator.ce_cli",
        module_file=module_file,
    )

    assert posture["invocation"] == "python_module"
    assert posture["package_origin"] == "source_checkout"
    assert posture["installed_ce"] is False


def test_doctor_detects_installed_console_script(tmp_path):
    repo_root = tmp_path / "repo"
    module_file = (
        tmp_path
        / "venv"
        / "lib"
        / "python3.14"
        / "site-packages"
        / "creator_engine_validator"
        / "doctor_runtime.py"
    )
    module_file.parent.mkdir(parents=True)
    module_file.write_text("# test module\n", encoding="utf-8")

    posture = doctor_runtime.detect_ce_dogfood_posture(
        repo_root,
        argv0="/home/operator/.local/bin/cev3",
        module_file=module_file,
    )

    assert posture["invocation"] == "console_script"
    assert posture["package_origin"] == "installed"
    assert posture["installed_ce"] is True


def test_doctor_human_output_is_nonempty(inject_facts, capsys):
    inject_facts()
    ret = ce_cli.main(["doctor", "--repo-root", "."])
    assert ret == 0
    out = capsys.readouterr().out
    assert "doctor" in out.lower()
