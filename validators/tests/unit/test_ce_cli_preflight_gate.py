"""CLI-layer coverage for T4's retained preflight-gate adapters.

These tests deliberately invoke :func:`ce_cli.main`, rather than calling the
adapter functions directly.  They therefore prove that the parser's option
destinations and the main dispatcher agree with ``_preflight_gate``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator import ce_cli


def test_main_maps_current_tail_options_to_the_adapter_destinations(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    def current_tail(repo_root: Path, *, comparison_base: str, live_base: str) -> str:
        captured.update(
            repo_root=repo_root,
            comparison_base=comparison_base,
            live_base=live_base,
        )
        return "current tail is valid"

    monkeypatch.setattr(ce_cli.pr_preflight, "run_brain_current_tail_gate", current_tail)

    assert ce_cli.main(
        [
            "preflight-gate",
            "brain-current-tail",
            "--comparison-base",
            "comparison-sha",
            "--live-base",
            "live-sha",
            "--repo-root",
            str(tmp_path),
        ]
    ) == 0
    assert captured == {
        "repo_root": tmp_path.resolve(),
        "comparison_base": "comparison-sha",
        "live_base": "live-sha",
    }


def test_main_maps_append_intent_options_to_the_adapter_destinations(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    def append_intent(repo_root: Path, *, comparison_base: str) -> str:
        captured.update(repo_root=repo_root, comparison_base=comparison_base)
        return "append intent is valid"

    monkeypatch.setattr(ce_cli.pr_preflight, "run_brain_append_intent_xor_gate", append_intent)

    assert ce_cli.main(
        [
            "preflight-gate",
            "brain-append-intent-xor",
            "--comparison-base",
            "comparison-sha",
            "--repo-root",
            str(tmp_path),
        ]
    ) == 0
    assert captured == {
        "repo_root": tmp_path.resolve(),
        "comparison_base": "comparison-sha",
    }


def test_main_maps_fleet_manifest_repo_root_to_the_adapter_destination(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    def fleet_manifest(repo_root: Path) -> str:
        captured["repo_root"] = repo_root
        return "fleet manifests are valid"

    monkeypatch.setattr(ce_cli.pr_preflight, "run_fleet_manifest_guard", fleet_manifest)

    assert ce_cli.main(
        ["preflight-gate", "fleet-manifest", "--repo-root", str(tmp_path)]
    ) == 0
    assert captured == {"repo_root": tmp_path.resolve()}


@pytest.mark.parametrize(
    ("command", "handler", "error"),
    [
        pytest.param(
            [
                "brain-current-tail",
                "--comparison-base",
                "comparison-sha",
                "--live-base",
                "live-sha",
            ],
            "run_brain_current_tail_gate",
            OSError("current tail unavailable"),
            id="current-tail-oserror",
        ),
        pytest.param(
            ["brain-append-intent-xor", "--comparison-base", "comparison-sha"],
            "run_brain_append_intent_xor_gate",
            RuntimeError("append intent unavailable"),
            id="append-intent-runtimeerror",
        ),
        pytest.param(
            ["fleet-manifest"],
            "run_fleet_manifest_guard",
            OSError("fleet manifests unavailable"),
            id="fleet-manifest-oserror",
        ),
    ],
)
def test_main_reports_preflight_gate_adapter_failures(monkeypatch, capsys, command, handler, error):
    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(ce_cli.pr_preflight, handler, fail)

    assert ce_cli.main(["preflight-gate", *command]) == 1
    assert capsys.readouterr().err == f"FAIL: preflight-gate {command[0]}: {error}\n"


def test_main_rejects_missing_preflight_gate_subcommand(capsys):
    assert ce_cli.main(["preflight-gate"]) == 2
    assert capsys.readouterr().err == "ERROR: preflight-gate requires a supported subcommand\n"
