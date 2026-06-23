"""ce-ops#197 PR-5 — ``ce onboard`` CLI surface (drives ce_cli.main).

Exercises the argparse wiring + dispatch through the real entrypoint, with the
orchestrator's legs replaced via the ``ce_onboard.run_onboard`` seam so no host
mutation occurs.
"""
from __future__ import annotations

import json

import pytest

from creator_engine_validator import ce_cli, ce_onboard


def test_emit_manifest_via_cli(capsys):
    rc = ce_cli.main(["onboard", "--emit-manifest"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "ce.onboard.manifest/v1"
    assert len(out["phases"]) == 6


def test_onboard_json_surface(monkeypatch, capsys):
    fake = ce_onboard.OnboardResult(
        ok=True,
        install_mode="hybrid",
        phases=[
            ce_onboard._record("doctor", status="ok", detail="PASS"),
        ],
    )
    monkeypatch.setattr(ce_onboard, "run_onboard", lambda config, **k: fake)
    rc = ce_cli.main(["onboard", "--json", "--install-mode", "hybrid"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["install_mode"] == "hybrid"
    assert out["phases"][0]["consequence_class"] == "read_only"


def test_onboard_nonzero_exit_on_incomplete(monkeypatch):
    fake = ce_onboard.OnboardResult(ok=False, install_mode="skip", reason="x")
    monkeypatch.setattr(ce_onboard, "run_onboard", lambda config, **k: fake)
    assert ce_cli.main(["onboard", "--install-mode", "skip"]) == 1


def test_onboard_rejects_bad_install_mode():
    # argparse choices guard rejects an unknown mode before dispatch.
    with pytest.raises(SystemExit):
        ce_cli.main(["onboard", "--install-mode", "bogus"])


def test_onboard_passes_flags_into_config(monkeypatch):
    seen = {}

    def capture(config, **k):
        seen["config"] = config
        return ce_onboard.OnboardResult(ok=True, install_mode="guided")

    monkeypatch.setattr(ce_onboard, "run_onboard", capture)
    ce_cli.main([
        "onboard", "--no-launch", "--no-fix-path", "--offline",
        "--install-mode", "guided", "--harness", "codex",
        "--repo-root", "/tmp/x", "--ledger-root", "/tmp/led",
    ])
    cfg = seen["config"]
    assert cfg.no_launch and cfg.no_fix_path and cfg.offline
    assert cfg.install_mode == "guided"
    assert cfg.harness == "codex"
    assert cfg.repo_root == "/tmp/x"
    assert cfg.ledger_root == "/tmp/led"
