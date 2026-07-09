"""ce-ops#197 PR-5 — ``ce onboard`` CLI surface (drives ce_cli.main).

Exercises the argparse wiring + dispatch through the real entrypoint, with the
orchestrator's legs replaced via the ``ce_onboard.run_onboard`` seam so no host
mutation occurs.
"""
from __future__ import annotations

import json

import pytest

from creator_engine_validator import ce_cli, ce_onboard


@pytest.mark.parametrize(
    ("flag", "extra"),
    [
        ("--spec", ["spec.yaml"]),
        ("--answers", ["answers.yaml"]),
        ("--answers-schema", ["schema.yaml"]),
        ("--plan", []),
        ("--apply", []),
        ("--inventory", []),
    ],
)
def test_onboard_installer_flags_hint_ce_install(flag, extra, monkeypatch, capsys):
    def should_not_dispatch(_args):
        raise AssertionError("native onboard should not run for installer-only flags")

    monkeypatch.setattr(ce_onboard, "run_cli", should_not_dispatch)

    rc = ce_cli.main(["onboard", flag, *extra])

    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert flag in captured.err
    assert "ce install <same args>" in captured.err
    assert "unrecognized arguments" not in captured.err


def test_onboard_without_installer_flags_still_dispatches_native(monkeypatch):
    seen = {}

    def capture(args):
        seen["args"] = args
        return 17

    monkeypatch.setattr(ce_onboard, "run_cli", capture)

    rc = ce_cli.main(["onboard", "--install-mode", "skip"])

    assert rc == 17
    assert seen["args"].group == "onboard"
    assert seen["args"].install_mode == "skip"


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


def test_onboard_human_surface_prints_red_g4_guidance(monkeypatch, capsys):
    fake = ce_onboard.OnboardResult(
        ok=False,
        install_mode="skip",
        reason="doctor refused (ungoverned host)",
        phases=[
            ce_onboard._record(
                "doctor",
                status="refused",
                detail="doctor refused: RED-G-4",
                verify={"refused_clauses": ["RED-G-4"]},
                data=ce_onboard._state_path_guidance("."),
            ),
        ],
    )
    monkeypatch.setattr(ce_onboard, "run_onboard", lambda config, **k: fake)

    assert ce_cli.main(["onboard", "--install-mode", "skip"]) == 1
    out = capsys.readouterr().out
    assert "guidance:" in out
    assert ".ce/state/" in out
    assert ".hermes/" not in out
    assert ".gitignore" not in out
    assert "ce brain init" in out
    assert "ce onboard --repo-root ." in out


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
