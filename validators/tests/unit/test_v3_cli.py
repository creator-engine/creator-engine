"""Unit tests for the v3 work-driving CLI (``cev3`` / ``v3_cli``) — G-7.0.

Drives ``creator_engine_validator.v3_cli.main`` directly with argv lists over a
tmp ``--root``. Asserts: filing writes a schema-shaped Scope artifact under the
neutral ``.ce/state`` root; ``drive`` REFUSES (front gate) unless the Scope is
DoR-ready AND ratified, and assembles correct G-4/G-5 run inputs (the
appetite→cap ``run`` spend envelope) when ready+ratified; the canon vocabulary
surfaces (stage phases + Scope-card labels) over the conserved schema fields;
the module is v3-classified and imports no v1.
"""
from __future__ import annotations

import hashlib
import json
from argparse import Namespace
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import _versions as ver
from creator_engine_validator import pickup_search
from creator_engine_validator import onboard_apply, v3_cli, v3_installer, v3_seat_bridge
from creator_engine_validator.forge.approval_capability import ApprovalCapabilityVerifier
from creator_engine_validator.schema import validate_with_schema

_REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
APPROVER = "a" * 64  # a value-free 64-hex opaque digest


@pytest.fixture(autouse=True)
def _ssh_keygen_present_for_stubbed_cli_verifier(monkeypatch):
    original_which = v3_cli.shutil.which

    def fake_which(command, *args, **kwargs):
        if command == "ssh-keygen":
            return "/usr/bin/ssh-keygen"
        return original_which(command, *args, **kwargs)

    monkeypatch.setattr(v3_cli.shutil, "which", fake_which)


def _file_ready(root: Path, scope_id: str = "rate-limit-login", **over) -> int:
    argv = [
        "scope", scope_id,
        "--goal", over.get("goal", "rate-limit POST /api/login"),
        "--change-type", over.get("change_type", "code"),
        "--root", str(root),
    ]
    for ac in over.get("done_when", ["returns 429 over 100/min", "has a unit test", "docs updated"]):
        argv += ["--done-when", ac]
    if over.get("budget", "S") is not None:
        argv += ["--budget", str(over.get("budget_amount", 5)), "--budget-unit", over.get("budget_unit", "$")]
    return v3_cli.main(argv)


def _scope_on_disk(root: Path, scope_id: str) -> dict:
    p = root / v3_cli.SCOPES_SUBDIR / f"{scope_id}{v3_cli._SCOPE_SUFFIX}"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _escalation_on_disk(root: Path, escalation_id: str) -> dict:
    p = root / v3_cli.ESCALATIONS_SUBDIR / f"{escalation_id}.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _assert_escalation_schema(record: dict):
    errors = validate_with_schema(
        record,
        "schemas/escalation-record.schema.yaml",
        "test-escalation",
        code="test_escalation",
        contract="schemas/escalation-record.schema.yaml",
    )
    assert not errors, [e.format() for e in errors]


# ---------------------------------------------------------------------------
# filing — writes a schema-shaped Scope under the neutral .ce/state root
# ---------------------------------------------------------------------------
def test_scope_filed_writes_artifact_under_root(tmp_path, capsys):
    code = _file_ready(tmp_path)
    assert code == 0
    rec = _scope_on_disk(tmp_path, "rate-limit-login")
    assert rec["kind"] == "scope-record"
    assert rec["record_type"] == "scope"
    assert rec["schema_version"] == "1"
    assert rec["scope_id"] == "rate-limit-login"
    assert rec["intent"] == "rate-limit POST /api/login"          # Goal → intent
    assert rec["mutation_class"] == "code"                        # Change-type → mutation_class
    assert len(rec["acceptance_criteria"]) == 3                   # Done-when → acceptance_criteria
    assert rec["appetite"] == {"amount": 5, "unit": "$"}          # Budget → appetite
    # filed without a bet → projected as draft / Frame (the conserved machine + skin)
    assert "Frame" in capsys.readouterr().out


def test_scope_artifacts_land_under_neutral_ce_state(tmp_path):
    # the default root is the neutral CE-namespaced .ce/state (never .hermes/.claude)
    assert ver.V3_LOCAL_STATE_ROOT == ".ce/state"
    _file_ready(tmp_path)
    assert (tmp_path / "scopes").is_dir()


def test_invalid_scope_id_refused(tmp_path):
    assert v3_cli.main(["scope", "BAD ID", "--goal", "x", "--change-type", "code", "--root", str(tmp_path)]) == 2


# ---------------------------------------------------------------------------
# the front gate — drive REFUSES unless Ready AND ratified
# ---------------------------------------------------------------------------
def test_drive_refuses_not_ratified(tmp_path, capsys):
    _file_ready(tmp_path)  # DoR-complete but no bet
    code = v3_cli.main(["drive", "rate-limit-login", "--root", str(tmp_path)])
    assert code == 1
    assert "REFUSED (not_ratified)" in capsys.readouterr().out


def test_drive_refuses_not_ready_missing_done_when(tmp_path, capsys):
    # a draft with no Done-when / Budget → not DoR-ready
    v3_cli.main(["scope", "draft-only", "--goal", "explore", "--change-type", "docs", "--root", str(tmp_path)])
    code = v3_cli.main(["drive", "draft-only", "--root", str(tmp_path)])
    assert code == 1
    assert "REFUSED (not_ready)" in capsys.readouterr().out


def test_ratify_refuses_unready_scope(tmp_path, capsys):
    v3_cli.main(["scope", "draft-only", "--goal", "explore", "--change-type", "docs", "--root", str(tmp_path)])
    code = v3_cli.main(["ratify", "draft-only", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    assert code == 1
    assert "not Ready" in capsys.readouterr().out


def test_ratify_refuses_non_hex_approver(tmp_path):
    _file_ready(tmp_path)
    assert v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", "nope", "--root", str(tmp_path)]) == 2


# ---------------------------------------------------------------------------
# the happy path — file → ratify → drive → governed run inputs (G-4/G-5)
# ---------------------------------------------------------------------------
def test_ratify_places_value_free_bet(tmp_path):
    _file_ready(tmp_path)
    assert v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)]) == 0
    rec = _scope_on_disk(tmp_path, "rate-limit-login")
    rat = rec["ratification"]
    assert rat["approver_ref"] == APPROVER
    assert len(rat["ratified_scope_sha"]) == 64 and all(c in "0123456789abcdef" for c in rat["ratified_scope_sha"])
    # value-free: no raw account / secret leaked into the bet
    assert set(rat) == {"approver_ref", "ratified_scope_sha"}


def test_drive_assembles_run_inputs_with_appetite_cap(tmp_path, capsys):
    _file_ready(tmp_path, budget_amount=7, budget_unit="$")
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    capsys.readouterr()  # discard the filing/ratify human output
    code = v3_cli.main(["drive", "rate-limit-login", "--root", str(tmp_path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] == "dispatch_assembled"
    assert payload["mutation_class"] == "code"
    # the G-5 join: the appetite became a run-scope spend envelope, fed unchanged
    envs = payload["runtime_policy"]["spend_envelopes"]
    assert {"scope": "run", "amount": 7, "unit": "$", "window": "per_run"} in envs
    # default drive stays assemble-only (additive --spawn opt-in; no behavior change)
    assert payload["live_spawn"] == "available_via_--spawn"
    assert payload["action"] == "dispatch_assembled"


def test_drive_refuses_missing_policy_file(tmp_path, capsys):
    # fail closed: never dispatch silently dropping an operator's intended policy
    _file_ready(tmp_path)
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    capsys.readouterr()
    code = v3_cli.main(["drive", "rate-limit-login", "--root", str(tmp_path), "--policy", str(tmp_path / "nope.yaml")])
    assert code == 2
    assert "file not found" in capsys.readouterr().out


def test_drive_refuses_malformed_policy(tmp_path, capsys):
    _file_ready(tmp_path)
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a\n- list\n")  # not a mapping
    capsys.readouterr()
    code = v3_cli.main(["drive", "rate-limit-login", "--root", str(tmp_path), "--policy", str(bad)])
    assert code == 2
    assert "must be a YAML mapping" in capsys.readouterr().out


def test_drive_merges_envelope_additively_into_operator_policy(tmp_path, capsys):
    _file_ready(tmp_path, budget_amount=3, budget_unit="$")
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    policy = tmp_path / "policy.yaml"
    policy.write_text(yaml.safe_dump({"spend_envelopes": [{"scope": "global", "amount": 100, "unit": "$"}]}))
    capsys.readouterr()  # discard the filing/ratify human output
    v3_cli.main(["drive", "rate-limit-login", "--root", str(tmp_path), "--policy", str(policy), "--json"])
    payload = json.loads(capsys.readouterr().out)
    envs = payload["runtime_policy"]["spend_envelopes"]
    scopes = sorted(e["scope"] for e in envs)
    assert scopes == ["global", "run"]  # operator global retained + run cap added


# ---------------------------------------------------------------------------
# v3.1-G1 — drive --spawn: assemble → REAL governed seat (subprocess seams faked)
# ---------------------------------------------------------------------------
def _fake_bridge(monkeypatch):
    """Replace the bridge's subprocess legs with in-memory fakes; record calls."""
    calls: dict[str, list] = {"spawn": [], "seed": []}

    def fake_spawn(record):
        record.data["terminal"] = {
            "kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%9",
        }
        record.data["resource_bound"] = {"unit": "ce-seat-x"}
        record.data["spawned_at"] = "20260611T000000Z"
        v3_seat_bridge._write_record(record)
        calls["spawn"].append(record.run_id)
        return v3_seat_bridge.SpawnResult(
            run_id=record.run_id,
            terminal=dict(record.data["terminal"]),
            resource_bound={"unit": "ce-seat-x"},
        )

    def fake_seed(record):
        calls["seed"].append(record.run_id)

    monkeypatch.setattr(v3_seat_bridge, "spawn_seat", fake_spawn)
    monkeypatch.setattr(v3_seat_bridge, "seed_brief", fake_seed)
    return calls


def _fake_codex_transcript_locator(monkeypatch):
    monkeypatch.setattr(v3_seat_bridge, "snapshot_codex_transcripts", lambda: set())

    def fake_stamp(record, **_kw):
        record.data["harness_session_id"] = "codex-session-1"
        record.data["transcript_ref"] = str(record.dispatch_dir / "codex.jsonl")
        v3_seat_bridge._write_record(record)
        return record

    monkeypatch.setattr(v3_seat_bridge, "stamp_codex_transcript_locator", fake_stamp)


def test_drive_spawn_refuses_unratified_without_touching_disk(tmp_path, capsys, monkeypatch):
    calls = _fake_bridge(monkeypatch)
    _file_ready(tmp_path)  # filed, NOT ratified → front gate must hold
    capsys.readouterr()
    code = v3_cli.main(["drive", "rate-limit-login", "--spawn", "--root", str(tmp_path)])
    assert code == 1
    assert "front gate held" in capsys.readouterr().out
    assert calls["spawn"] == [] and calls["seed"] == []
    assert not (tmp_path / "dispatches").exists()  # no dispatch materialized


def test_drive_spawn_materializes_and_spawns_governed_seat(tmp_path, capsys, monkeypatch):
    calls = _fake_bridge(monkeypatch)
    _file_ready(tmp_path)
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    capsys.readouterr()
    code = v3_cli.main(["drive", "rate-limit-login", "--spawn", "--root", str(tmp_path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "spawned"
    assert payload["pane_id"] == "%9"
    assert payload["unattended"] is True  # default
    run_id = payload["run_id"]
    assert calls["spawn"] == [run_id] and calls["seed"] == [run_id]
    # the dispatch record + brief landed on disk, terminal stamped
    ddir = tmp_path / "dispatches" / run_id
    assert (ddir / "dispatch.yaml").is_file() and (ddir / "brief.md").is_file()
    data = yaml.safe_load((ddir / "dispatch.yaml").read_text(encoding="utf-8"))
    assert data["terminal"]["pane_id"] == "%9"


def test_drive_spawn_allows_low_risk_codex_harness(tmp_path, capsys, monkeypatch):
    calls = _fake_bridge(monkeypatch)
    _fake_codex_transcript_locator(monkeypatch)
    _file_ready(tmp_path)
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    capsys.readouterr()
    code = v3_cli.main(
        ["drive", "rate-limit-login", "--spawn", "--harness", "codex", "--root", str(tmp_path), "--json"]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["harness"] == "codex"
    assert calls["spawn"] == [payload["run_id"]]
    data = yaml.safe_load((tmp_path / "dispatches" / payload["run_id"] / "dispatch.yaml").read_text(encoding="utf-8"))
    assert data["harness"] == "codex"
    assert data["harness_boundary"] == "codex_managed_pretooluse"
    assert data["transcript_ref"].endswith("codex.jsonl")


def test_drive_spawn_refuses_high_risk_codex_without_override(tmp_path, capsys, monkeypatch):
    calls = _fake_bridge(monkeypatch)
    _file_ready(tmp_path, change_type="schema")
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    capsys.readouterr()
    code = v3_cli.main(
        ["drive", "rate-limit-login", "--spawn", "--harness", "codex", "--root", str(tmp_path), "--json"]
    )
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["reason"] == "codex_risk_refused"
    assert calls["spawn"] == []
    assert not (tmp_path / "dispatches").exists()


def test_drive_spawn_high_risk_codex_override_recorded(tmp_path, capsys, monkeypatch):
    calls = _fake_bridge(monkeypatch)
    _fake_codex_transcript_locator(monkeypatch)
    _file_ready(tmp_path, change_type="schema")
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    override = "c" * 64
    capsys.readouterr()
    code = v3_cli.main([
        "drive", "rate-limit-login", "--spawn", "--harness", "codex",
        "--codex-risk-override", override, "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert calls["spawn"] == [payload["run_id"]]
    data = yaml.safe_load((tmp_path / "dispatches" / payload["run_id"] / "dispatch.yaml").read_text(encoding="utf-8"))
    assert data["codex_risk_override"] == override


def test_drive_spawn_no_unattended_omits_skip_perms(tmp_path, capsys, monkeypatch):
    _fake_bridge(monkeypatch)
    _file_ready(tmp_path)
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    capsys.readouterr()
    code = v3_cli.main(
        ["drive", "rate-limit-login", "--spawn", "--no-unattended", "--root", str(tmp_path), "--json"]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["unattended"] is False
    run_id = payload["run_id"]
    data = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text(encoding="utf-8"))
    assert data["unattended"] is False


def test_drive_spawn_surfaces_launch_refusal(tmp_path, capsys, monkeypatch):
    def boom(record):
        raise v3_seat_bridge.SpawnRefused("CC-D-6 refused: unconfirmed hook-pack")

    monkeypatch.setattr(v3_seat_bridge, "spawn_seat", boom)
    _file_ready(tmp_path)
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    capsys.readouterr()
    code = v3_cli.main(["drive", "rate-limit-login", "--spawn", "--root", str(tmp_path)])
    assert code == 1
    assert "CC-D-6 refused" in capsys.readouterr().out


def test_drive_spawn_refusal_is_not_projected_as_live_build(tmp_path, capsys, monkeypatch):
    # FIX-1 (PR #198 review repro): a refused spawn must NOT leave a dispatch the
    # read-model reports as a live Build/RUN run. The record is failure-stamped and
    # never shaped like a pending/live run.
    def boom(record):
        raise v3_seat_bridge.SpawnRefused("CC-D-6 refused: unconfirmed hook-pack")

    monkeypatch.setattr(v3_seat_bridge, "spawn_seat", boom)
    _file_ready(tmp_path)
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    capsys.readouterr()
    code = v3_cli.main(["drive", "rate-limit-login", "--spawn", "--root", str(tmp_path), "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "spawn_refused"
    run_id = payload["run_id"]
    # the dispatch is failure-stamped (conserved), terminal/spawned_at unset
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"]
    assert "CC-D-6" in drec["spawn_failure_reason"]
    assert drec["terminal"] is None and drec["spawned_at"] is None
    # the read-model does NOT project Build/RUN for the refused spawn
    capsys.readouterr()
    v3_cli.main(["show", "rate-limit-login", "--root", str(tmp_path), "--json"])
    proj = json.loads(capsys.readouterr().out)["projection"]
    assert proj["state"] != "in_progress"
    assert proj["phase"] != "Build"
    assert proj["board"] != "RUN"


# ---------------------------------------------------------------------------
# v3.1-G1b — cev3 collect: run → conserved evidence chain (read-model sees it)
# ---------------------------------------------------------------------------
_RATES_POLICY = {"model_rates": [{"model": "claude-opus-4-8", "input_per_mtok": 15, "output_per_mtok": 75}]}


def _transcript(path: Path, *, n_turns: int = 2) -> Path:
    lines = []
    for i in range(n_turns):
        lines.append(json.dumps({
            "type": "assistant",
            "sessionId": "seat-1",
            "timestamp": f"2026-06-11T09:3{i}:00Z",
            "message": {"model": "claude-opus-4-8",
                        "usage": {"input_tokens": 1000, "output_tokens": 200}},
        }))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _codex_transcript(path: Path, *, session_id: str, cwd: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "type": "session_meta",
            "payload": {
                "id": session_id,
                "cwd": str(cwd.resolve()),
                "timestamp": "2026-06-12T12:00:00Z",
                "cli_version": "0.0.0",
            },
        }) + "\n",
        encoding="utf-8",
    )
    return path


def _owner_only_env(path: Path, content: str = "GITHUB_REVIEWR_TOKEN=ghp_x\n") -> Path:
    """Write an owner-only (0600) env file for the D2 seat-env-file contract."""
    import os
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _session_id(tmp_path, run_id: str) -> str:
    drec = yaml.safe_load(
        (tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text(encoding="utf-8")
    )
    return drec["harness_session_id"]


def _stage_transcript(tmp_path, run_id, monkeypatch, *, n_turns: int = 2) -> Path:
    """D6/F9: stage the run's transcript at its stamped harness-session key under a tmp
    CLAUDE_CONFIG_DIR so ``cev3 collect`` resolves it by id (no ``--transcript`` needed)."""
    sid = _session_id(tmp_path, run_id)
    cfg = tmp_path / ".claude-config"
    proj = cfg / "projects" / "ce-proj"
    proj.mkdir(parents=True, exist_ok=True)
    _transcript(proj / f"{sid}.jsonl", n_turns=n_turns)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cfg))
    return cfg


def _dispatch_a_run(tmp_path, monkeypatch, *, policy: dict | None = None) -> str:
    """file → ratify → drive --spawn (faked) → return the run_id with a dispatch on disk."""
    _fake_bridge(monkeypatch)
    _file_ready(tmp_path)
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    argv = ["drive", "rate-limit-login", "--spawn", "--root", str(tmp_path), "--json"]
    if policy is not None:
        ppath = tmp_path / "op-policy.yaml"
        ppath.write_text(yaml.safe_dump(policy), encoding="utf-8")
        argv += ["--policy", str(ppath)]
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        v3_cli.main(argv)
    return json.loads(buf.getvalue())["run_id"]


def test_collect_folds_transcript_and_outcome_into_chain(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    _stage_transcript(tmp_path, run_id, monkeypatch)
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id,
        "--outcome", "research_delivered", "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "collected"
    assert payload["outcome"] == "research_delivered"
    assert payload["spend_leaves"] == 2
    # D6/F9: the transcript was resolved by the stamped session id, honesty-stamped
    assert payload["transcript_source"] == "stamped"
    # the conserved chain persisted under the neutral runs root + verifies clean
    chain_path = tmp_path / "runs" / f"{run_id}.runtime-evidence.yaml"
    assert chain_path.is_file()
    doc = yaml.safe_load(chain_path.read_text(encoding="utf-8"))
    from creator_engine_validator import runtime_evidence_spine as spine
    assert spine.verify_chain(doc["records"]) == []
    # the dispatch is marked collected (drives the read-model back off Build)
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text(encoding="utf-8"))
    assert drec["collected_at"]


def test_collect_report_renders_outcome_and_spend(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    _stage_transcript(tmp_path, run_id, monkeypatch)
    v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id,
        "--outcome", "research_delivered", "--root", str(tmp_path),
    ])
    capsys.readouterr()
    chain_path = tmp_path / "runs" / f"{run_id}.runtime-evidence.yaml"
    code = v3_cli.main([
        "report", "rate-limit-login", "--evidence", str(chain_path), "--run-id", run_id,
        "--cap", "5", "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "research_delivered"
    # spend folded off the persisted chain (2 turns * (1000*15 + 200*75)/1e6 = 0.06)
    assert "Research delivered" in payload["outcome_label"]


def test_collect_refuses_double_collect(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    _stage_transcript(tmp_path, run_id, monkeypatch)
    args = ["collect", "rate-limit-login", "--run", run_id,
            "--outcome", "no_change", "--root", str(tmp_path)]
    assert v3_cli.main(args) == 0
    capsys.readouterr()
    assert v3_cli.main(args) == 2  # second collect refuses (append-only)
    assert "already collected" in capsys.readouterr().out


def test_collect_refuses_unknown_run(tmp_path, capsys):
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", "run-ghost-x", "--outcome", "no_change",
        "--root", str(tmp_path),
    ])
    assert code == 2
    assert "no dispatch record" in capsys.readouterr().out


def test_collect_refuses_scope_mismatch(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "other-scope", "--run", run_id, "--outcome", "no_change", "--root", str(tmp_path),
    ])
    assert code == 2
    assert "not" in capsys.readouterr().out


def test_uncollected_dispatch_projects_scope_to_build(tmp_path, capsys, monkeypatch):
    # A live (spawned, uncollected) run makes the read-model show Build/in_progress.
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    capsys.readouterr()
    v3_cli.main(["show", "rate-limit-login", "--root", str(tmp_path), "--json"])
    proj = json.loads(capsys.readouterr().out)["projection"]
    assert proj["state"] == "in_progress" and proj["phase"] == "Build"
    # …and once collected, the Scope projects off its own state again (not Build).
    _stage_transcript(tmp_path, run_id, monkeypatch)
    v3_cli.main(["collect", "rate-limit-login", "--run", run_id,
                 "--outcome", "no_change", "--root", str(tmp_path)])
    capsys.readouterr()
    v3_cli.main(["show", "rate-limit-login", "--root", str(tmp_path), "--json"])
    proj2 = json.loads(capsys.readouterr().out)["projection"]
    assert proj2["state"] != "in_progress"


def test_report_defaults_evidence_from_collected_dispatch(tmp_path, capsys, monkeypatch):
    # With a collected dispatch, `report` needs no --evidence — it finds the chain.
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    _stage_transcript(tmp_path, run_id, monkeypatch)
    v3_cli.main(["collect", "rate-limit-login", "--run", run_id,
                 "--outcome", "research_delivered", "--root", str(tmp_path)])
    capsys.readouterr()
    code = v3_cli.main(["report", "rate-limit-login", "--root", str(tmp_path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "research_delivered"
    assert payload["run_id"] == run_id  # defaulted from the collected dispatch


def test_e2e_scope_to_spawn_to_collect_to_report(tmp_path, capsys, monkeypatch):
    # The named keystone: scope → ratify → drive --spawn → collect → report,
    # all subprocess seams faked. Proves the spine end to end.
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    _stage_transcript(tmp_path, run_id, monkeypatch, n_turns=3)
    capsys.readouterr()
    assert v3_cli.main(["collect", "rate-limit-login", "--run", run_id,
                        "--outcome", "research_delivered", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert v3_cli.main(["artifacts", "rate-limit-login", "--cap", "5", "--root", str(tmp_path), "--json"]) == 0
    arts = {a["kind"] for a in json.loads(capsys.readouterr().out)["artifacts"]}
    assert {"scope", "evidence", "spend"} <= arts  # run artifacts surfaced sans --evidence
    assert v3_cli.main(["report", "rate-limit-login", "--root", str(tmp_path)]) == 0
    block = capsys.readouterr().out
    assert "Research delivered" in block


def test_collect_refuses_stamped_run_without_transcript(tmp_path, capsys, monkeypatch):
    """D6/F9: a STAMPED seat that ran must have a transcript at its session key — collecting
    with none present (and no override) is a hard refusal, never a silent zero-spend fold."""
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    # point the config dir at an empty dir so the stamped-key lookup finds nothing
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "empty-config"))
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--outcome", "no_change",
        "--root", str(tmp_path), "--json",
    ])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "stamped_transcript_missing"
    assert payload["harness_session_id"] == _session_id(tmp_path, run_id)


def test_collect_override_folds_and_stamps_operator_override(tmp_path, capsys, monkeypatch):
    """D6/F9: the salvage hatch folds a relocated transcript despite no stamped-key hit and
    loudly stamps transcript_source: operator_override."""
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    salvaged = _transcript(tmp_path / "salvaged-elsewhere.jsonl")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "empty-config"))
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--outcome", "research_delivered",
        "--transcript-override", str(salvaged), "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["transcript_source"] == "operator_override"
    assert payload["spend_leaves"] == 2


def test_collect_refuses_mismatched_explicit_transcript(tmp_path, capsys, monkeypatch):
    """D6/F9: an explicit --transcript whose stem ≠ the stamped id is the #14/#21 mis-fold,
    machine-blocked (use --transcript-override to fold a salvaged one)."""
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    wrong = _transcript(tmp_path / "orchestrator-by-mtime.jsonl")
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--transcript", str(wrong),
        "--outcome", "research_delivered", "--root", str(tmp_path), "--json",
    ])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "transcript_id_mismatch"
    assert payload["stamped_session_id"] == _session_id(tmp_path, run_id)


def test_collect_unstamped_record_conserves_zero_spend(tmp_path, capsys, monkeypatch):
    """D6/F9 backward-compat: a pre-F9 dispatch (no harness_session_id) folds the outcome with
    zero spend (today's behavior) + a transcript_source: unstamped honesty stamp."""
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    # strip the stamped id to simulate a pre-F9 record
    dpath = tmp_path / "dispatches" / run_id / "dispatch.yaml"
    drec = yaml.safe_load(dpath.read_text(encoding="utf-8"))
    drec.pop("harness_session_id", None)
    dpath.write_text(yaml.safe_dump(drec, sort_keys=True), encoding="utf-8")
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--outcome", "no_change",
        "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["spend_leaves"] == 0
    assert payload["outcome"] == "no_change"
    assert payload["transcript_source"] == "unstamped"


def test_collect_codex_uses_spawn_stamped_transcript_ref(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    sid = "codex-session-1"
    tpath = _codex_transcript(tmp_path / "codex" / "session.jsonl", session_id=sid, cwd=tmp_path)
    dpath = tmp_path / "dispatches" / run_id / "dispatch.yaml"
    drec = yaml.safe_load(dpath.read_text(encoding="utf-8"))
    drec["harness"] = "codex"
    drec["harness_session_id"] = sid
    drec["transcript_ref"] = str(tpath)
    dpath.write_text(yaml.safe_dump(drec, sort_keys=True), encoding="utf-8")
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--outcome", "no_change",
        "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["transcript_source"] == "stamped"
    assert payload["spend_leaves"] == 0


def test_collect_codex_falls_back_to_sessions_exact_key(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    sid = "codex-session-2"
    home = tmp_path / "home"
    _codex_transcript(
        home / ".codex" / "sessions" / "2026" / "06" / "12" / "session.jsonl",
        session_id=sid,
        cwd=tmp_path,
    )
    monkeypatch.setenv("HOME", str(home))
    dpath = tmp_path / "dispatches" / run_id / "dispatch.yaml"
    drec = yaml.safe_load(dpath.read_text(encoding="utf-8"))
    drec["harness"] = "codex"
    drec["harness_session_id"] = sid
    drec.pop("transcript_ref", None)
    dpath.write_text(yaml.safe_dump(drec, sort_keys=True), encoding="utf-8")
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--outcome", "no_change",
        "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["transcript_source"] == "stamped"


# ---------------------------------------------------------------------------
# v3.5-B live feeds — escalation open/resolve/sync
# ---------------------------------------------------------------------------
def test_escalation_open_writes_schema_valid_record(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_utc_now_iso", lambda: "2026-07-01T09:00:00+00:00")
    code = v3_cli.main([
        "escalation", "open",
        "--id", "operator-call",
        "--title", "Operator call",
        "--decision", "Raise cap or halt?",
        "--recommend", "Halt and re-scope.",
        "--source-ref", "https://github.com/example/repo/issues/10",
        "--root", str(tmp_path),
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "escalation_opened"
    record = _escalation_on_disk(tmp_path, "operator-call")
    assert record["created_at"] == "2026-07-01T09:00:00+00:00"
    assert record["recommendation"] == "Halt and re-scope."
    _assert_escalation_schema(record)


def test_escalation_open_refuses_duplicate_id(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_utc_now_iso", lambda: "2026-07-01T09:00:00+00:00")
    argv = [
        "escalation", "open",
        "--id", "operator-call",
        "--title", "Operator call",
        "--decision", "Choose",
        "--recommend", "Go",
        "--root", str(tmp_path),
    ]
    assert v3_cli.main(argv) == 0
    capsys.readouterr()
    assert v3_cli.main(argv) == 2
    assert "already exists" in capsys.readouterr().out


def test_escalation_resolve_stamps_resolved_at(tmp_path, capsys, monkeypatch):
    stamps = iter(["2026-07-01T09:00:00+00:00", "2026-07-01T09:05:00+00:00"])
    monkeypatch.setattr(v3_cli, "_utc_now_iso", lambda: next(stamps))
    assert v3_cli.main([
        "escalation", "open", "--id", "operator-call", "--title", "Operator call",
        "--decision", "Choose", "--recommend", "Go", "--root", str(tmp_path),
    ]) == 0
    capsys.readouterr()
    code = v3_cli.main([
        "escalation", "resolve", "operator-call",
        "--resolution", "Operator chose go.",
        "--root", str(tmp_path),
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "escalation_resolved"
    record = _escalation_on_disk(tmp_path, "operator-call")
    assert record["resolved_at"] == "2026-07-01T09:05:00+00:00"
    assert record["resolution"] == "Operator chose go."
    _assert_escalation_schema(record)


class _GhCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _issue(number: int, *, state: str = "OPEN", closed_at: str | None = None) -> dict:
    return {
        "number": number,
        "title": f"Awaiting operator #{number}",
        "url": f"https://github.com/example/repo/issues/{number}",
        "body": "Decision needed: choose path\nRecommendation: choose the safe path\n",
        "createdAt": f"2026-07-01T09:{number:02d}:00Z",
        "closedAt": closed_at,
        "state": state,
    }


def test_escalation_sync_upserts_open_and_resolves_closed_issue(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_utc_now_iso", lambda: "2026-07-01T08:00:00+00:00")
    # Existing open mirror for issue #2 should be updated to resolved when gh says closed.
    v3_cli.main([
        "escalation", "open",
        "--id", "awaiting-operator-2",
        "--title", "old",
        "--decision", "old",
        "--recommend", "old",
        "--source-ref", "https://github.com/example/repo/issues/2",
        "--root", str(tmp_path),
    ])
    capsys.readouterr()

    payload = [_issue(1), _issue(2, state="CLOSED", closed_at="2026-07-01T09:30:00Z")]

    def fake_run(argv, **kw):
        assert argv[:3] == ["gh", "issue", "list"]
        assert "--repo" in argv and "example/repo" in argv
        return _GhCompleted(stdout=json.dumps(payload))

    monkeypatch.setattr(v3_cli.subprocess, "run", fake_run)
    code = v3_cli.main([
        "escalation", "sync",
        "--repo", "example/repo",
        "--root", str(tmp_path),
        "--json",
    ])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "escalation_synced"
    open_record = _escalation_on_disk(tmp_path, "awaiting-operator-1")
    resolved_record = _escalation_on_disk(tmp_path, "awaiting-operator-2")
    assert "resolved_at" not in open_record
    assert resolved_record["resolved_at"] == "2026-07-01T09:30:00Z"
    _assert_escalation_schema(open_record)
    _assert_escalation_schema(resolved_record)


def test_escalation_sync_nonzero_gh_exit_writes_nothing(tmp_path, capsys, monkeypatch):
    def fake_run(argv, **kw):
        return _GhCompleted(returncode=1, stderr="offline")

    monkeypatch.setattr(v3_cli.subprocess, "run", fake_run)
    code = v3_cli.main([
        "escalation", "sync",
        "--repo", "example/repo",
        "--root", str(tmp_path),
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["written"] == 0
    assert not (tmp_path / v3_cli.ESCALATIONS_SUBDIR).exists()


def test_escalation_sync_schema_invalid_payload_writes_nothing(tmp_path, capsys, monkeypatch):
    bad_payload = [_issue(3) | {"body": "Decision needed: choose\n"}]

    def fake_run(argv, **kw):
        return _GhCompleted(stdout=json.dumps(bad_payload))

    monkeypatch.setattr(v3_cli.subprocess, "run", fake_run)
    code = v3_cli.main([
        "escalation", "sync",
        "--repo", "example/repo",
        "--root", str(tmp_path),
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["written"] == 0
    assert not (tmp_path / v3_cli.ESCALATIONS_SUBDIR).exists()


# ---------------------------------------------------------------------------
# the canon skin — stage phase projection (Frame→Shape) over the machine
# ---------------------------------------------------------------------------
def test_status_projects_phase_skin(tmp_path, capsys):
    _file_ready(tmp_path)  # draft → Frame
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])  # → Shape
    capsys.readouterr()  # discard the filing/ratify human output
    v3_cli.main(["status", "--root", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["phase_counts"]["Shape"] == 1
    assert payload["scopes"][0]["projection"]["phase"] == "Shape"
    assert payload["scopes"][0]["projection"]["state"] == "ready"
    assert payload["scopes"][0]["projection"]["board"] == "READY"


def test_show_surfaces_card_labels(tmp_path, capsys):
    _file_ready(tmp_path)
    v3_cli.main(["show", "rate-limit-login", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    for label in ("Goal", "Done-when", "Budget", "Change-type", "Ready"):
        assert label in out


def test_artifacts_lists_scope(tmp_path, capsys):
    _file_ready(tmp_path)
    code = v3_cli.main(["artifacts", "rate-limit-login", "--root", str(tmp_path)])
    assert code == 0
    assert "scope" in capsys.readouterr().out


def test_session_frame_shows_stage_counts(tmp_path, capsys):
    _file_ready(tmp_path)
    code = v3_cli.main(["session", "--root", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    # banner + the unified status line (stage skin · context · spend)
    assert "Creator Engine" in out and "Frame" in out and "ctx" in out and "spend" in out


def test_no_arg_default_session_uses_session_defaults_and_version(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "V3_LOCAL_STATE_ROOT", str(tmp_path))
    token = v3_cli.version.ce_version()

    code = v3_cli.main([])
    assert code == 0
    default_out = capsys.readouterr().out

    code = v3_cli.main(["session", "--root", str(tmp_path)])
    assert code == 0
    explicit_out = capsys.readouterr().out

    assert default_out == explicit_out
    assert token in default_out

    code = v3_cli.main(["session", "--root", str(tmp_path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ce_version"] == token


def test_session_unified_meters_from_inputs(tmp_path, capsys):
    _file_ready(tmp_path)
    spine = tmp_path / "spine.yaml"
    # one run spend-ledger leaf: $4 of a $5 run cap → 80% → soft
    spine.write_text(yaml.safe_dump({"records": [
        {"record_type": "runtime_spend_ledger", "unit": "$", "amount": 4, "run_id": "r-1"},
    ]}))
    capsys.readouterr()
    v3_cli.main(["session", "--root", str(tmp_path), "--context-pct", "62",
                 "--spine", str(spine), "--cap", "5", "--run-id", "r-1", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["context"] == {"pct": 62.0, "state": "urgent"}
    assert payload["spend"]["state"] == "soft"
    assert payload["spend"]["spent"] == "4" and payload["spend"]["cap"] == "5"


def test_show_missing_scope_returns_2(tmp_path):
    assert v3_cli.main(["show", "ghost", "--root", str(tmp_path)]) == 2


# ---------------------------------------------------------------------------
# report — the ◆ CE Completion Report (canon Outcome/Verdict/Next over evidence)
# ---------------------------------------------------------------------------
def test_report_renders_canon_over_evidence(tmp_path, capsys):
    chain = tmp_path / "chain.yaml"
    chain.write_text(yaml.safe_dump({"records": [
        {"record_type": "runtime_spend_ledger", "unit": "$", "amount": 0.7, "run_id": "r-91a"},
        {"record_type": "runtime_run_outcome", "outcome": "pr_opened", "run_id": "r-91a",
         "change_set": {"branch": "b", "base": "m", "pr_number": 7}},
    ]}))
    code = v3_cli.main(["report", "cs-4f2", "--evidence", str(chain), "--run-id", "r-91a",
                        "--cap", "5", "--change-type", "code", "--done-when-total", "3",
                        "--done-when-met", "3", "--ci", "green", "--in-scope", "--budget-size", "S", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "pr_opened"
    assert payload["outcome_label"] == "PR opened"
    assert "Done-when 3/3 met" in payload["verdict"] and "14% of Budget S" in payload["verdict"]
    assert payload["next"].startswith("→ Review PR #7")
    assert {"pr", "scope", "evidence", "spend"} <= {a["kind"] for a in payload["artifacts"]}


def test_artifacts_enriched_with_evidence(tmp_path, capsys):
    _file_ready(tmp_path)
    chain = tmp_path / "chain.yaml"
    chain.write_text(yaml.safe_dump({"records": [
        {"record_type": "runtime_run_outcome", "outcome": "pr_opened", "run_id": "r-1",
         "change_set": {"branch": "b", "base": "m", "pr_number": 9}},
    ]}))
    capsys.readouterr()
    v3_cli.main(["artifacts", "rate-limit-login", "--root", str(tmp_path),
                 "--evidence", str(chain), "--run-id", "r-1", "--json"])
    payload = json.loads(capsys.readouterr().out)
    kinds = {a["kind"] for a in payload["artifacts"]}
    assert "scope" in kinds and "pr" in kinds and "evidence" in kinds


# ---------------------------------------------------------------------------
# shape — the Frame→Shape grill-me (gaps + minimum questions + the dial)
# ---------------------------------------------------------------------------
def test_shape_flags_gaps_and_budget_is_human_only(tmp_path, capsys):
    code = v3_cli.main(["shape", "rl", "--goal", "rate-limit login", "--change-type", "code", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    fields = {g["field"] for g in payload["gaps"]}
    assert "acceptance_criteria" in fields and "appetite" in fields  # Done-when + Budget still open
    budget_gap = [g for g in payload["gaps"] if g["field"] == "appetite"][0]
    assert budget_gap["human_only"] is True  # the agent never drafts the Budget
    assert payload["ready"] is False


def test_shape_dial_offers_per_persona_risk(capsys):
    # dev + high-risk (deploy) on a "clear" signal → holds (needs explicit)
    v3_cli.main(["shape", "x", "--goal", "g", "--change-type", "deploy",
                 "--persona", "dev", "--signal", "clear", "--json"])
    assert json.loads(capsys.readouterr().out)["offer"] is False
    # ceo + low-risk (docs) on an "actionable" signal → offers
    v3_cli.main(["shape", "x", "--goal", "g", "--change-type", "docs",
                 "--persona", "ceo", "--signal", "actionable", "--json"])
    assert json.loads(capsys.readouterr().out)["offer"] is True


# ---------------------------------------------------------------------------
# classification — v3-classified, additive, distinct entry (no v1 import)
# ---------------------------------------------------------------------------
def test_v3_cli_is_v3_classified():
    assert ver.classify("v3_cli") == ver.V3


def test_v3_cli_imports_no_v1_module():
    src = (Path(v3_cli.__file__)).read_text(encoding="utf-8")
    # imports only stdlib + yaml + v3/shared siblings; never a v1 launcher module.
    for v1_mod in ("ce_cli", "lane_runtime", "launch_runtime", "tmux_adapter", "worker_runtime"):
        assert f"import {v1_mod}" not in src and f"from .{v1_mod}" not in src


def test_onboard_verifies_spec_and_dry_runs(tmp_path, capsys):
    spec = tmp_path / "llms-install.md"
    spec.write_text("# Install CE\n", encoding="utf-8")
    code = v3_cli.main(["install", "--spec", str(spec), "--key-id", "ce-root-v1", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verified"]["ok"] is True
    assert payload["expose_cli"]["command"] == "ce"
    assert payload["profile"]["mode"] == "default"
    assert "the GitHub-App authorization click" in payload["human_approves"]
    # honesty: without a published --sig-value the floor only self-attests integrity
    assert payload["self_attested"] is True


def test_onboard_with_published_sig_is_not_self_attested(tmp_path, capsys):
    from creator_engine_validator import v3_installer
    spec = tmp_path / "spec.md"
    spec.write_text("# spec\n", encoding="utf-8")
    digest = v3_installer.content_digest(spec.read_bytes())
    v3_cli.main(["install", "--spec", str(spec), "--key-id", "ce-root-v1", "--sig-value", digest, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["verified"]["ok"] is True and payload["self_attested"] is False


def test_onboard_refuses_tampered_spec(tmp_path, capsys):
    spec = tmp_path / "spec.md"
    spec.write_text("# real spec\n", encoding="utf-8")
    # a sig value that does not match the spec content → refuse before execute
    code = v3_cli.main(["install", "--spec", str(spec), "--key-id", "ce-root-v1",
                        "--sig-value", "0" * 64])
    assert code == 1
    assert "REFUSED" in capsys.readouterr().out


def test_onboard_optout_requires_ratification_and_educates(tmp_path, capsys):
    spec = tmp_path / "spec.md"
    spec.write_text("# spec\n", encoding="utf-8")
    # opt-out without a valid ratification binding → refused (human-only)
    assert v3_cli.main(["install", "--spec", str(spec), "--opt-out"]) == 1
    capsys.readouterr()
    # with a ratified binding → custom profile + the educate copy surfaces
    code = v3_cli.main(["install", "--spec", str(spec), "--opt-out",
                        "--ratified-prompt-sha", "a" * 64, "--approver-ref", "b" * 64, "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"]["runtime_policy"]["spend_cap_enforcement"] == "off"
    assert "won't speed up your runs" in payload["educate"]


def test_user_facing_command_is_ce_not_cev3(tmp_path, capsys):
    # Operator-ratified directive: users type `ce`; `cev3` is internal-only.
    assert v3_cli.CE_CMD == "ce"
    assert v3_cli._build_parser().prog == "ce"
    # user-facing output never prints the internal `cev3` name
    _file_ready(tmp_path)
    v3_cli.main(["artifacts", "rate-limit-login", "--root", str(tmp_path)])
    v3_cli.main(["shape", "rate-limit-login", "--goal", "g", "--change-type", "code"])
    assert "cev3" not in capsys.readouterr().out


def test_approval_capability_mint_outputs_valid_marker_without_secret(monkeypatch, capsys, tmp_path):
    secret = "mint-command-secret"
    monkeypatch.setenv("CE_APPROVAL_CAPABILITY_SECRET", secret)
    monkeypatch.setattr(v3_cli.time, "time", lambda: 1_800_000_000)

    code = v3_cli.main([
        "approval-capability",
        "mint",
        "--repo", "owner/repo",
        "--pr", "440",
        "--head-sha", "a" * 40,
        "--approved-by", "ce-dev-2",
        "--policy-sha", "policy-v1",
        "--ttl-seconds", "600",
        "--root", str(tmp_path),
    ])

    assert code == 0
    marker = capsys.readouterr().out.strip()
    assert marker.startswith("ce-approval-capability: v1.")
    assert secret not in marker
    verifier = ApprovalCapabilityVerifier(lambda: secret, now=lambda: 1_800_000_001, policy_sha="policy-v1")
    result = verifier.verify(
        marker,
        repo="owner/repo",
        pr_number=440,
        head_sha="a" * 40,
        approved_by_candidates=("ce-dev-2",),
    )
    assert result.valid is True


def _approval_wall_daemon_args(**overrides) -> Namespace:
    values = {
        "repo": "owner/repo",
        "approval_wall_policy_sha": "policy-v1",
        "approval_wall_marker_ttl_seconds": 77,
        "approval_wall_secret_backend": v3_cli.secret_identity.DEFAULT_APPROVAL_WALL_SECRET_BACKEND,
        "approval_wall_secret_mount": v3_cli.secret_identity.DEFAULT_APPROVAL_WALL_SECRET_MOUNT,
        "approval_wall_secret_path": v3_cli.secret_identity.DEFAULT_APPROVAL_WALL_SECRET_PATH,
        "approval_wall_secret_field": v3_cli.secret_identity.DEFAULT_APPROVAL_WALL_SECRET_FIELD,
        "approval_wall_secret_version": None,
        "approval_wall_secret_purpose": v3_cli.secret_identity.DEFAULT_APPROVAL_WALL_SECRET_PURPOSE,
        "approval_wall_secret_owner_ref": v3_cli.secret_identity.DEFAULT_APPROVAL_WALL_SECRET_OWNER_REF,
        "approval_wall_secret_ref_policy_sha": "a" * 64,
        "approval_wall_secret_target_ref": "file:/tmp/ce-approval-wall-secret",
        "approval_wall_secret_repo": None,
        "approval_wall_secret_run_id": "approval-wall-daemon",
        "approval_wall_secret_seat_id": "dev-1",
        "approval_wall_secret_ttl_seconds": 600,
        "approval_wall_secret_env": "CE_APPROVAL_CAPABILITY_SECRET",
    }
    values.update(overrides)
    return Namespace(**values)


def _daemon_pr() -> v3_cli.integrator_belt.DaemonPullRequest:
    return v3_cli.integrator_belt.DaemonPullRequest(
        repo="owner/repo",
        pr_number=440,
        title="approval wall",
        url="https://github.example/owner/repo/pull/440",
        body="",
        head_ref="feature",
        head_sha="a" * 40,
        base_ref="main",
        review_decision="APPROVED",
        approving_review_commits=("a" * 40,),
        approving_reviewers=("ce-dev-2",),
        approval_capability_present=False,
        approval_capability_marker=None,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        rollup_state="SUCCESS",
        checks=(),
        changed_paths=("validators/creator_engine_validator/v3_cli.py",),
        files_complete=True,
        checks_complete=True,
        is_draft=False,
    )


class _RecordingApprovalWallBackend:
    backend_key = "openbao"

    def __init__(self) -> None:
        self.requests = []
        self.materialized_targets = []
        self.revoked = []

    def validate_config(self) -> None:
        return None

    def resolve_identity(self, seat_id):
        raise AssertionError("resolve_identity is not used by approval wall minting")

    def issue(self, request):
        self.requests.append(request)
        return v3_cli.secret_identity.SecretGrant(
            grant_id="grant-approval-wall-001",
            run_id=request.run_id,
            seat_id=request.seat_id,
            secret_ref=request.secret_ref,
            lease_id=None,
            token_accessor_ref="accessor:approval-wall",
            issued_at="2026-06-25T00:00:00Z",
            expires_at="2026-06-25T00:10:00Z",
            delivery_ref=None,
            audit_ref="audit:approval-wall",
        )

    def issue_secret_zero(self, request):
        raise AssertionError("issue_secret_zero is not used by approval wall minting")

    def materialize(self, grant, target_ref):
        self.materialized_targets.append(target_ref)
        return replace(grant, delivery_ref=target_ref)

    def revoke(self, grant):
        self.revoked.append(grant.grant_id)
        return replace(grant, revoked_at="2026-06-25T00:01:00Z")

    def collect_audit(self, grant):
        return {"grant_id": grant.grant_id, "audit_ref": grant.audit_ref}


def _pickup_secret_args(**overrides) -> Namespace:
    values = {
        "repo": "owner/repo",
        "org": None,
        "pickup_token_secret_backend": None,
        "pickup_token_secret_mount": None,
        "pickup_token_secret_path": None,
        "pickup_token_secret_field": None,
        "pickup_token_secret_version": None,
        "pickup_token_secret_purpose": None,
        "pickup_token_secret_owner_ref": None,
        "pickup_token_secret_ref_policy_sha": None,
        "pickup_token_secret_target_ref": None,
        "pickup_token_secret_run_id": "review-pickup-daemon",
        "pickup_token_secret_seat_id": "dev-2",
        "pickup_token_secret_ttl_seconds": (
            v3_cli.secret_identity.DEFAULT_REVIEW_PICKUP_TOKEN_SECRET_TTL_SECONDS
        ),
    }
    values.update(overrides)
    return Namespace(**values)


class _RecordingPickupTokenBackend:
    backend_key = "openbao"

    def __init__(self) -> None:
        self.requests = []
        self.materialized_targets = []
        self.revoked = []

    def validate_config(self) -> None:
        return None

    def resolve_identity(self, seat_id):
        raise AssertionError("resolve_identity is not used by review-pickup token supply")

    def issue(self, request):
        self.requests.append(request)
        return v3_cli.secret_identity.SecretGrant(
            grant_id="grant-review-pickup-token-001",
            run_id=request.run_id,
            seat_id=request.seat_id,
            secret_ref=request.secret_ref,
            lease_id=None,
            token_accessor_ref="accessor:review-pickup",
            issued_at="2026-07-05T00:00:00Z",
            expires_at="2026-07-05T00:05:00Z",
            delivery_ref=None,
            audit_ref="audit:review-pickup",
        )

    def issue_secret_zero(self, request):
        raise AssertionError("issue_secret_zero is not used by review-pickup token supply")

    def materialize(self, grant, target_ref):
        self.materialized_targets.append(target_ref)
        return replace(grant, delivery_ref=target_ref)

    def revoke(self, grant):
        self.revoked.append(grant.grant_id)
        return replace(grant, revoked_at="2026-07-05T00:00:01Z")

    def collect_audit(self, grant):
        return {"grant_id": grant.grant_id, "audit_ref": grant.audit_ref}


def test_review_pickup_token_supplier_unconfigured_preserves_static_path() -> None:
    assert v3_cli._review_pickup_token_supplier_from_args(_pickup_secret_args()) is None


def test_review_pickup_token_supplier_uses_recording_backend(monkeypatch) -> None:
    backend = _RecordingPickupTokenBackend()
    monkeypatch.setattr(v3_cli.secret_identity, "get_backend", lambda key: backend)
    monkeypatch.setattr(
        v3_cli,
        "_approval_wall_materialized_value_reader",
        lambda target_ref: "ghp_backend_review_token",
    )

    supplier = v3_cli._review_pickup_token_supplier_from_args(
        _pickup_secret_args(
            pickup_token_secret_ref_policy_sha="a" * 64,
            pickup_token_secret_target_ref="file:/run/ce/review-pickup-token",
        )
    )

    assert supplier is not None
    assert supplier() == "ghp_backend_review_token"
    assert backend.materialized_targets == ["file:/run/ce/review-pickup-token"]
    assert backend.revoked == ["grant-review-pickup-token-001"]
    request = backend.requests[0]
    assert request.run_id == "review-pickup-daemon"
    assert request.seat_id == "dev-2"
    assert request.ttl_seconds == 300
    assert request.secret_ref.backend == "openbao"
    assert request.secret_ref.mount == "ce-kv"
    assert request.secret_ref.path == "forge/ce-dev-2/gh-token"
    assert request.secret_ref.field == "token"
    assert request.secret_ref.purpose == "review-pickup-token"
    assert request.secret_ref.owner_ref == "controller:reviewer"


def test_review_pickup_token_supplier_rejects_env_target_ref() -> None:
    args = _pickup_secret_args(
        pickup_token_secret_ref_policy_sha="a" * 64,
        pickup_token_secret_target_ref="env:CE_PICKUP_TOKEN",
    )

    with pytest.raises(pickup_search.PickupError, match="env: targets are fork-unsafe"):
        v3_cli._review_pickup_token_supplier_from_args(args)


def test_approval_capability_marker_issuer_uses_backend_supplier(monkeypatch):
    backend = _RecordingApprovalWallBackend()
    monkeypatch.setenv("CE_APPROVAL_CAPABILITY_SECRET", "env-fallback-secret")
    monkeypatch.setattr(v3_cli.secret_identity, "get_backend", lambda key: backend)
    monkeypatch.setattr(
        v3_cli,
        "_approval_wall_materialized_value_reader",
        lambda target_ref: "backend-approval-wall-secret",
    )
    monkeypatch.setattr(v3_cli.time, "time", lambda: 1_800_000_000)

    issuer = v3_cli._approval_capability_marker_issuer_from_args(_approval_wall_daemon_args())
    marker = issuer(
        _daemon_pr(),
        v3_cli.integrator_belt.DaemonApprovalWitness(
            reviewer_login="ce-dev-2",
            commit_oid="a" * 40,
        ),
    )

    assert backend.materialized_targets == ["file:/tmp/ce-approval-wall-secret"]
    assert backend.revoked == ["grant-approval-wall-001"]
    request = backend.requests[0]
    assert request.secret_ref.backend == "openbao"
    assert request.secret_ref.mount == "ce-kv"
    assert request.secret_ref.path == "forge/approval-capability/wall"
    assert request.secret_ref.field == "signing_secret"
    assert request.secret_ref.purpose == "approval-capability-wall"
    assert request.secret_ref.owner_ref == "controller:integrator"

    verifier = ApprovalCapabilityVerifier(
        lambda: "backend-approval-wall-secret",
        now=lambda: 1_800_000_001,
        policy_sha="policy-v1",
    )
    result = verifier.verify(
        marker,
        repo="owner/repo",
        pr_number=440,
        head_sha="a" * 40,
        approved_by_candidates=("ce-dev-2",),
    )
    assert result.valid is True
    assert result.claims is not None
    assert result.claims.expires_at - result.claims.issued_at == 77
    assert ApprovalCapabilityVerifier(
        lambda: "env-fallback-secret",
        now=lambda: 1_800_000_001,
        policy_sha="policy-v1",
    ).verify(marker, repo="owner/repo", pr_number=440, head_sha="a" * 40).valid is False


def test_approval_capability_marker_issuer_refuses_without_backend_supplier(monkeypatch):
    monkeypatch.setenv("CE_APPROVAL_CAPABILITY_SECRET", "env-fallback-secret")
    args = _approval_wall_daemon_args(
        approval_wall_secret_backend=None,
        approval_wall_secret_mount=None,
        approval_wall_secret_path=None,
        approval_wall_secret_field=None,
        approval_wall_secret_purpose=None,
        approval_wall_secret_owner_ref=None,
        approval_wall_secret_ref_policy_sha=None,
        approval_wall_secret_target_ref=None,
    )

    with pytest.raises(v3_cli.integrator_belt.IntegratorBeltError, match="not configured"):
        v3_cli._approval_capability_marker_issuer_from_args(args)


def test_approval_capability_marker_issuer_refuses_backend_without_secret_and_ignores_env(monkeypatch):
    backend = _RecordingApprovalWallBackend()
    monkeypatch.setenv("CE_APPROVAL_CAPABILITY_SECRET", "env-fallback-secret")
    monkeypatch.setattr(v3_cli.secret_identity, "get_backend", lambda key: backend)
    monkeypatch.setattr(v3_cli, "_approval_wall_materialized_value_reader", lambda target_ref: None)
    monkeypatch.setattr(v3_cli.time, "time", lambda: 1_800_000_000)

    issuer = v3_cli._approval_capability_marker_issuer_from_args(_approval_wall_daemon_args())

    with pytest.raises(v3_cli.integrator_belt.IntegratorBeltError, match="secret unavailable"):
        issuer(
            _daemon_pr(),
            v3_cli.integrator_belt.DaemonApprovalWitness(
                reviewer_login="ce-dev-2",
                commit_oid="a" * 40,
            ),
        )


def test_guide_prints_in_product_help(capsys):
    code = v3_cli.main(["guide"])
    assert code == 0
    out = capsys.readouterr().out
    # the seed surfaces what CE is + the five canon stages + the Scope card labels
    assert "Creator Engine" in out
    for stage in ("Frame", "Shape", "Build", "Review", "Ship"):
        assert stage in out
    for label in ("Goal", "Done-when", "Budget", "Change-type", "Ready"):
        assert label in out
    assert "cev3" not in out  # user-facing → speaks `ce`


def test_help_reachable():
    with pytest.raises(SystemExit) as exc:
        v3_cli.main(["--help"])
    assert exc.value.code == 0



# ---------------------------------------------------------------------------
# v3.5-E.3 E3-G3 — onboard: --answers / --inventory / --plan / --non-interactive
# ---------------------------------------------------------------------------
_GOOD_ANSWERS_YAML = """\
answers_version: 1
profile: solo-pilot
host:
  sudo_grant: [git, python, runsc, proxy]
cost:
  profile: default
provider:
  harness: claude-code
  anthropic_api_key: env://ANTHROPIC_API_KEY
github:
  mode: existing
  repo: chmod735/creator-engine-canonical
  bootstrap_token: prompt://github-bootstrap-token
  app:
    kind: shared
    installation_id: 12345678
  protections: reference
  reviewer: chmod735
"""

_GREENFIELD_ANSWERS_YAML = """\
answers_version: 1
profile: solo-pilot
host:
  sudo_grant: [git, python, runsc, proxy]
cost:
  profile: default
provider:
  harness: claude-code
  anthropic_api_key: env://ANTHROPIC_API_KEY
github:
  mode: new
  repo: chmod735/greenfield-first
  new_repo:
    visibility: private
    default_branch: main
  bootstrap_token: prompt://github-bootstrap-token
  app:
    kind: shared
    installation_id: 12345678
  protections: reference
  reviewer: chmod735
project:
  name: greenfield-first
  scaffold:
    kind: minimal
"""


def _spec(tmp_path):
    spec = tmp_path / "llms-install.md"
    spec.write_text("# Install CE\n", encoding="utf-8")
    return spec


def _signed_spec(tmp_path):
    canonical = """\
kind: ce-install-spec
signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: <published-with-this-spec>
  content_sha256: <published-with-this-spec>
"""
    digest = v3_installer.content_digest(v3_installer.canonical_spec_bytes(canonical))
    spec = tmp_path / "signed-install.md"
    spec.write_text(
        canonical.replace("  value: <published-with-this-spec>", "  value: c2ln").replace(
            "  content_sha256: <published-with-this-spec>",
            f"  content_sha256: {digest}",
        ),
        encoding="utf-8",
    )
    return spec


def _trust_root(tmp_path, key_material="ce-root-v1 ssh-ed25519 TESTKEY"):
    trust = tmp_path / "ce-root-v1"
    trust.write_text(key_material + "\n", encoding="utf-8")
    return trust


def _trust_anchor(tmp_path, text="ce-root-v1=SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ"):
    anchor = tmp_path / "ce-root-v1.anchor"
    anchor.write_text(text + "\n", encoding="utf-8")
    return anchor


def _answers_file(tmp_path, content=_GOOD_ANSWERS_YAML):
    path = tmp_path / "ce-install.answers.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def _brownfield_cli_probe(origin_remote="chmod735/creator-engine-canonical", *, dirty=False):
    return {
        "enabled": True,
        "project_root": ".",
        "history": {
            "mode": "git_history_present",
            "head_sha": "a" * 40,
            "default_branch": "main",
            "commit_count": 1,
            "dirty": dirty,
        },
        "github": {"origin_remote": origin_remote},
        "ci": {"workflows": [], "current_required_checks": [], "workflow_present": False},
        "tests": {"commands": []},
        "conventions": {"branch_patterns": [], "commit_styles": []},
        "secrets": {"preflight": "required", "status": "not_run", "scanner_available": None, "findings": []},
    }


def _init_brownfield_project(tmp_path: Path) -> Path:
    import subprocess

    root = tmp_path / "project"
    root.mkdir()
    workflow_dir = root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        """\
name: CI
on: [push, pull_request]
jobs:
  test:
    name: Unit tests
    runs-on: ubuntu-latest
    steps:
      - run: python -m pytest
""",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        """\
[project]
dependencies = ["pytest"]
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ce@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "CE Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "feat: initial project"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/acme/app.git"], cwd=root, check=True)
    return root


def test_detect_brownfield_project_empty_non_git_dir_disables_brownfield(tmp_path):
    probe = v3_cli._detect_brownfield_project(tmp_path)

    assert probe["enabled"] is False
    assert probe["history"]["present"] is False
    assert probe["history"]["mode"] == "absent"
    assert probe["ci"]["workflows"] == []
    assert probe["tests"]["commands"] == []


def test_detect_brownfield_project_enables_for_git_history_without_ci_or_tests(tmp_path):
    import subprocess

    (tmp_path / "README.md").write_text("# Existing project\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ce@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "CE Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "feat: initial project"], cwd=tmp_path, check=True, capture_output=True)

    probe = v3_cli._detect_brownfield_project(tmp_path)

    assert probe["enabled"] is True
    assert probe["history"]["present"] is True
    assert probe["history"]["mode"] == "git_history_present"
    assert probe["ci"]["workflows"] == []
    assert probe["tests"]["commands"] == []


def test_detect_brownfield_project_enables_brownfield_for_real_signals(tmp_path):
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        """\
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: python -m pytest
""",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        """\
[project]
dependencies = ["pytest"]
""",
        encoding="utf-8",
    )

    probe = v3_cli._detect_brownfield_project(tmp_path)

    assert probe["enabled"] is True
    assert [workflow["path"] for workflow in probe["ci"]["workflows"]] == [".github/workflows/ci.yml"]
    assert [item["command"] for item in probe["tests"]["commands"]] == ["python -m pytest"]


def _source_files(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def _brownfield_answers_for(repo: str) -> str:
    return _GOOD_ANSWERS_YAML.replace(
        "repo: chmod735/creator-engine-canonical",
        f"repo: {repo}",
    ).replace(
        "target_repo: chmod735/creator-engine-canonical",
        f"target_repo: {repo}",
    ).replace(
        "reviewer: chmod735",
        "reviewer: operator",
    )


def _assert_brownfield_refusal_copy_is_tenant_lens(text: str) -> None:
    assert "E3" not in text
    assert "onboard_apply" not in text
    assert "e2_brownfield_seam_unavailable" not in text
    assert "adoption write escalation" not in text


def test_onboard_inventory_emits_the_awareness_artifact(tmp_path, capsys):
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)), "--inventory", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "onboard_inventory"
    assert payload["verified"]["ok"] is True   # verify stays first, even for awareness
    rows = {row["key"]: row for row in payload["inventory"]}
    assert rows["github.bootstrap_token"]["status"] == "secret (ref required)"
    assert rows["cost.profile"]["status"] == "default:default"


def test_onboard_inventory_warns_for_missing_selected_backend_dependency(
    tmp_path,
    capsys,
    monkeypatch,
):
    monkeypatch.setattr(
        v3_cli,
        "_which",
        lambda tool: tool in ("python", "uv", "claude"),
    )
    code = v3_cli.main([
        "install",
        "--spec", str(_spec(tmp_path)),
        "--answers", str(_answers_file(tmp_path)),
        "--inventory",
        "--json",
    ])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    rows = {row["key"]: row for row in payload["inventory"]}
    assert rows["dependencies.git"]["status"] == "WARN MISSING (needed for first-value)"
    assert rows["dependencies.git"]["dependency"] is True
    assert rows["dependencies.git"]["tool"] == "git"
    assert "dependencies.runsc" not in rows
    assert "dependencies.proxy" not in rows


def test_onboard_inventory_human_output_shows_missing_git_warn(
    tmp_path,
    capsys,
    monkeypatch,
):
    monkeypatch.setattr(
        v3_cli,
        "_which",
        lambda tool: tool in ("python", "uv", "claude"),
    )
    code = v3_cli.main([
        "install",
        "--spec", str(_spec(tmp_path)),
        "--answers", str(_answers_file(tmp_path)),
        "--inventory",
    ])

    assert code == 0
    out = capsys.readouterr().out
    assert "dependencies.git" in out
    assert "WARN MISSING (needed for first-value)" in out
    assert "REFUSED" not in out


def test_git_read_refuses_missing_git(monkeypatch, tmp_path):
    monkeypatch.setattr(v3_cli, "_which", lambda tool: False if tool == "git" else True)
    with pytest.raises(v3_installer.InstallRefused) as exc:
        v3_cli._git_read(tmp_path, "status")
    detail = str(exc.value)
    assert "missing_bootstrap_dependency" in detail
    assert "required command missing: git" in detail
    assert "Remediation:" in detail


def test_onboard_inventory_warns_when_brownfield_probe_misses_dependency(tmp_path, capsys, monkeypatch):
    # ce-ops#191 (N1×N5 reconciliation): brownfield detection shells out to git,
    # which N5 fail-closes on a missing dependency. But ``--inventory`` is the
    # read-only AWARENESS artifact (N1) — a missing dependency must surface as a
    # WARN row (exit 0), NOT a refusal. Only ``_which`` controls presence, so a
    # genuinely-missing git is reproduced by masking it (the brownfield probe then
    # raises the missing-dependency refusal internally, which inventory degrades).
    monkeypatch.setattr(
        v3_cli,
        "_which",
        lambda tool: tool in ("python", "uv", "claude"),
    )
    code = v3_cli.main([
        "install",
        "--spec", str(_spec(tmp_path)),
        "--answers", str(_answers_file(tmp_path)),
        "--inventory",
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "onboard_inventory"
    rows = {row["key"]: row for row in payload["inventory"]}
    assert rows["dependencies.git"]["status"] == "WARN MISSING (needed for first-value)"


def test_onboard_inventory_refuses_on_non_dependency_brownfield_fault(tmp_path, capsys, monkeypatch):
    # N5 stays fail-closed for NON-dependency faults even on the read-only path:
    # only the ``missing_bootstrap_dependency`` class degrades to a WARN row.
    def refused(_root):
        raise v3_installer.InstallRefused(
            "artifact_hash_mismatch: brownfield baseline attestation tampered"
        )

    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", refused)
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)), "--inventory", "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    assert "artifact_hash_mismatch" in payload["detail"]


def test_onboard_plan_fails_closed_on_missing_git_dependency(tmp_path, capsys, monkeypatch):
    # The reconciliation is scoped to ``--inventory``: ``--plan`` (the apply/bootstrap
    # path) keeps N5's clean fail-closed refusal on a missing bootstrap dependency.
    def refused(_root):
        raise v3_installer.InstallRefused(
            "missing_bootstrap_dependency: required command missing: git. "
            "Remediation: install Git with your OS package manager, then re-run this installer."
        )

    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", refused)
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)), "--plan", "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    assert "missing_bootstrap_dependency" in payload["detail"]
    assert "required command missing: git" in payload["detail"]


def test_onboard_authentic_inventory_uses_fetched_trust_root(tmp_path, capsys, monkeypatch):
    calls = []

    def fake_runner(**kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", fake_runner)
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--trust-root", str(_trust_root(tmp_path, v3_installer.PINNED_KEYS["ce-root-v1"])),
        "--trust-anchor", f"dns-txt={_trust_anchor(tmp_path)}",
        "--inventory",
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "onboard_inventory"
    assert payload["self_attested"] is False
    assert payload["verified"]["ok"] is True
    assert payload["verified"]["key_id"] == "ce-root-v1"
    assert payload["verified"]["trust_anchors"]["agreed"] == ["dns-txt"]
    assert "fingerprint" not in payload["verified"]["trust_anchors"]
    assert calls and calls[0]["signature"] == b"sig"
    assert calls[0]["allowed_signers"].startswith("ce-root-v1 ssh-ed25519")
    assert calls[0]["namespace"] == v3_installer.SSH_SIG_NAMESPACE


def test_onboard_authentic_reports_actionable_missing_ssh_keygen(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli.shutil, "which", lambda _name: None)

    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--trust-root", str(_trust_root(tmp_path, v3_installer.PINNED_KEYS["ce-root-v1"])),
        "--trust-anchor", f"dns-txt={_trust_anchor(tmp_path)}",
        "--inventory",
        "--json",
    ])

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    assert "missing_dependency_ssh_keygen" in payload["detail"]
    assert "required command missing: ssh-keygen" in payload["detail"]
    assert "sudo apt-get install -y openssh-client" in payload["detail"]
    assert "sudo dnf install -y openssh-clients" in payload["detail"]
    assert "brew install openssh" in payload["detail"]


def test_onboard_refuses_self_attested_when_authentic_required(tmp_path, capsys):
    code = v3_cli.main([
        "install",
        "--spec", str(_spec(tmp_path)),
        "--trust-root", str(_trust_root(tmp_path)),
        "--inventory",
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    assert "signature block missing" in payload["detail"]


def test_onboard_authentic_refuses_same_origin_only_trust_root(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--trust-root", str(_trust_root(tmp_path, v3_installer.PINNED_KEYS["ce-root-v1"])),
        "--inventory",
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    assert "same_origin_only" in payload["detail"]


def test_onboard_authentic_refuses_same_origin_url_trust_anchor(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--trust-root", str(_trust_root(tmp_path, v3_installer.PINNED_KEYS["ce-root-v1"])),
        "--trust-anchor", f"https://creator-engine.dev/trust/ce-root-v1.txt={_trust_anchor(tmp_path)}",
        "--inventory",
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    assert "same_origin_anchor" in payload["detail"]
    assert "shares origin" in payload["detail"]
    assert "SHA256:" not in payload["detail"]


def test_onboard_authentic_refuses_mismatched_trust_anchor(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--trust-root", str(_trust_root(tmp_path, v3_installer.PINNED_KEYS["ce-root-v1"])),
        "--trust-anchor", f"github-org-profile={_trust_anchor(tmp_path, 'ce-root-v1=SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')}",
        "--inventory",
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    assert "mismatch" in payload["detail"]


def test_onboard_authentic_refuses_tampered_spec_before_inventory(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    spec = _signed_spec(tmp_path)
    spec.write_text(spec.read_text(encoding="utf-8") + "\ntamper\n", encoding="utf-8")
    code = v3_cli.main([
        "install",
        "--spec", str(spec),
        "--trust-root", str(_trust_root(tmp_path, v3_installer.PINNED_KEYS["ce-root-v1"])),
        "--trust-anchor", f"dns-txt={_trust_anchor(tmp_path)}",
        "--inventory",
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert "content_sha256 does not match" in payload["detail"]


def test_onboard_inventory_derives_greenfield_inputs(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe(origin_remote=None))
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)), "--inventory", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    rows = {row["key"]: row for row in payload["inventory"]}
    assert rows["project.name"]["step"] == 5
    assert rows["project.name"]["sensitivity"] == "plain"
    assert rows["project.name"]["modes"] == ["F", "I"]
    assert rows["project.name"]["status"] == "not-applicable"
    assert rows["project.scaffold.kind"]["status"] == "not-applicable"


def test_onboard_answers_file_resolves_the_asks(tmp_path, capsys, monkeypatch):
    # pin the live probe (host-independent): claude present, codex absent
    monkeypatch.setattr(
        v3_cli, "_which",
        lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"),
    )
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe())
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)),
                        "--answers", str(_answers_file(tmp_path)), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["answers"]["missing"] == []
    assert payload["answers"]["sha256"] and len(payload["answers"]["sha256"]) == 64
    assert payload["answers"]["sources"]["github.repo"] == "answers"


def test_onboard_refuses_typo_key_fail_closed(tmp_path, capsys):
    bad = _answers_file(tmp_path, _GOOD_ANSWERS_YAML + "workspce_root: typo\n")
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)), "--answers", str(bad)])
    assert code == 1
    assert "REFUSED" in capsys.readouterr().out


def test_onboard_refuses_raw_secret_in_answers(tmp_path, capsys):
    bad = _answers_file(tmp_path, _GOOD_ANSWERS_YAML.replace(
        "prompt://github-bootstrap-token", "ghp_rawsecret123"))
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)), "--answers", str(bad)])
    assert code == 1
    out = capsys.readouterr().out
    assert "REFUSED" in out and "SecretRef" in out


def test_onboard_non_interactive_refuses_with_exact_missing_list(tmp_path, capsys, monkeypatch):
    # no origin remote detected here, so github.mode/repo remain real missing inputs
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe(origin_remote=None))
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)), "--non-interactive", "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    missing_keys = {m["key"] for m in payload["missing"]}
    assert "github.mode" in missing_keys and "github.bootstrap_token" in missing_keys


def test_onboard_non_interactive_succeeds_on_complete_answers(tmp_path, capsys, monkeypatch):
    # pin the live probe (host-independent): claude present, codex absent; the
    # grant covers every privileged tool, so even a host missing runsc/proxy
    # stays inside the operator's written upfront approval
    monkeypatch.setattr(
        v3_cli, "_which",
        lambda tool: tool in ("git", "python", "uv", "claude"),
    )
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe())
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)),
                        "--answers", str(_answers_file(tmp_path)),
                        "--non-interactive", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["non_interactive"] is True
    assert payload["answers"]["missing"] == []
    assert payload["answers"]["sudo_grant"]["uncovered"] == []


def test_onboard_non_interactive_refuses_sudo_outside_the_grant(tmp_path, capsys, monkeypatch):
    # ce-ops#71 MAJOR-1: the privileged runsc/proxy pairing only enters the plan for
    # a gvisor-proxy backend, so this refusal-path test pins a `team` profile (→
    # gvisor-proxy). force a privileged install the grant does not cover.
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv"))
    narrow = _answers_file(tmp_path, _GOOD_ANSWERS_YAML.replace(
        "profile: solo-pilot", "profile: team").replace(
        "sudo_grant: [git, python, runsc, proxy]", "sudo_grant: [runsc]"))
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)),
                        "--answers", str(narrow), "--non-interactive", "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["sudo_uncovered"] == ["proxy"]


def test_onboard_answers_custom_cost_profile_flows_to_the_g5_fragment(tmp_path, capsys):
    custom = _answers_file(tmp_path, _GOOD_ANSWERS_YAML.replace(
        "cost:\n  profile: default",
        "cost:\n  profile: custom\n  optout:\n"
        f"    ratified_prompt_sha: {'a' * 64}\n"
        f"    approver_ref: {'b' * 64}\n"
        "    educate_acknowledged: true",
    ))
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)),
                        "--answers", str(custom), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"]["runtime_policy"]["spend_cap_enforcement"] == "off"
    # the answers-file ack is stripped — the fragment matches the G-5 schema
    assert "educate_acknowledged" not in payload["profile"]["runtime_policy"]["spend_cap_optout"]
    assert "won't speed up your runs" in payload["educate"]


def test_onboard_plan_composes_the_github_leg(tmp_path, capsys):
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)),
                        "--answers", str(_answers_file(tmp_path)), "--plan", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    leg = payload["github_leg"]
    assert leg["app"]["click_required"] is False          # installation declared → no click
    assert leg["human_approves"] == []
    # unprobed live facts stay fail-closed in the dry run (the E.4 drive probes them)
    assert leg["bootstrap_token_scopes"]["probed"] is False
    assert payload["first_project"] is None


def test_onboard_plan_without_profile_defaults_to_os_native_no_sudo(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv", "claude"))
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe(origin_remote=None))

    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)), "--plan", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0, payload
    assert payload["dependencies"]["install"] == []
    assert payload["dependencies"]["needs_sudo"] is False
    assert payload["dependencies"]["isolation_backend"] == "os-native"
    assert payload["dependencies"]["isolation_tier"] == 1
    assert payload["profile"]["isolation_tier"] == 1
    assert "sudo (privileged dependency installs)" not in payload["human_approves"]

    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)), "--plan"])
    text = capsys.readouterr().out
    assert code == 0
    assert "dependencies · backend os-native · install —" in text
    assert "sudo no" in text


def test_onboard_authentic_plan_trust_anchor_evidence_is_value_free(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--trust-root", str(_trust_root(tmp_path, v3_installer.PINNED_KEYS["ce-root-v1"])),
        "--trust-anchor", f"dns-txt={_trust_anchor(tmp_path)}",
        "--answers", str(_answers_file(tmp_path)),
        "--plan",
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    trust_anchors = payload["verified"]["trust_anchors"]
    assert trust_anchors["agreed"] == ["dns-txt"]
    assert "fingerprint" not in trust_anchors


def test_onboard_plan_emits_greenfield_first_project(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe(origin_remote=None))
    answers = _answers_file(tmp_path, _GREENFIELD_ANSWERS_YAML)
    code = v3_cli.main([
        "install",
        "--spec", str(_spec(tmp_path)),
        "--answers", str(answers),
        "--plan",
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    first = payload["first_project"]
    assert first["mode"] == "greenfield"
    assert first["project_root"].endswith("/greenfield-first")
    assert first["scaffold_input"]["supplied_to_e2_leg"] == "workspace_checkout"
    assert first["e2_apply_required"] is True
    assert first["frame_to_ship"]["first_scope_filed"] is False
    assert first["first_ship_not_yet_counted"] is True


def test_onboard_apply_rejects_read_only_modes(tmp_path, capsys):
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)), "--plan", "--apply", "--json"])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "invalid_onboard_mode"


def test_onboard_inventory_and_plan_do_not_create_apply_state(tmp_path, capsys):
    root = tmp_path / "state"
    assert v3_cli.main([
        "install", "--spec", str(_spec(tmp_path)), "--inventory", "--root", str(root), "--json",
    ]) == 0
    capsys.readouterr()
    assert v3_cli.main([
        "install", "--spec", str(_spec(tmp_path)), "--answers", str(_answers_file(tmp_path)),
        "--plan", "--root", str(root), "--json",
    ]) == 0
    capsys.readouterr()
    assert not (root / "onboard" / "ledger.ndjson").exists()
    assert not (root / "onboard" / "apply.lock").exists()


def test_onboard_brownfield_inventory_is_read_only(tmp_path, capsys, monkeypatch):
    project = _init_brownfield_project(tmp_path)
    before = _source_files(project)
    monkeypatch.chdir(project)

    def should_not_apply(*_args, **_kwargs):
        raise AssertionError("inventory must not invoke the E2 executor")

    monkeypatch.setattr(onboard_apply, "apply_onboard", should_not_apply)
    code = v3_cli.main([
        "install",
        "--spec", str(_spec(tmp_path)),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--inventory",
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["brownfield"]["history"]["mode"] == "git_history_present"
    assert payload["brownfield"]["tests"] == ["python -m pytest"]
    assert _source_files(project) == before
    assert not (project / ".ce" / "state" / "onboard").exists()


def test_onboard_plan_emits_brownfield_adoption_payload(tmp_path, capsys, monkeypatch):
    project = _init_brownfield_project(tmp_path)
    monkeypatch.chdir(project)
    answers = _answers_file(tmp_path, _brownfield_answers_for("acme/app"))
    code = v3_cli.main([
        "install",
        "--spec", str(_spec(tmp_path)),
        "--answers", str(answers),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--plan",
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    plan = payload["brownfield_adoption"]
    assert plan["inventory_sha256"] and len(plan["inventory_sha256"]) == 64
    assert plan["tests"]["required_commands"] == ["python -m pytest"]
    assert "Unit tests" in " ".join(plan["ci"]["checks_to_preserve"])
    assert plan["ci"]["checks_to_add"] == ["Validate governance artifacts"]
    assert [step["id"] for step in plan["apply_steps"]] == list(v3_installer.BROWNFIELD_APPLY_STEP_IDS)
    scrub_step = next(step for step in plan["apply_steps"] if step["id"] == "brownfield_secret_preflight")
    assert ".github/workflows/ce-validate.yml" in scrub_step["scan_paths"]
    build_step = next(step for step in plan["apply_steps"] if step["id"] == "brownfield_build_scaffold")
    assert "secrets_preflight_clean_or_waived" in build_step["requires"]
    pr_step = next(step for step in plan["apply_steps"] if step["id"] == "brownfield_open_join_pr")
    assert pr_step["plan_ref"] == plan["inventory_sha256"]


def test_onboard_apply_existing_brownfield_refuses_without_e2_extension(tmp_path, capsys, monkeypatch):
    project = _init_brownfield_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"))
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)

    def should_not_apply(*_args, **_kwargs):
        raise AssertionError("brownfield apply must refuse before the greenfield E2 executor runs")

    monkeypatch.setattr(onboard_apply, "apply_onboard", should_not_apply)
    answers = _answers_file(tmp_path, _brownfield_answers_for("acme/app"))
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(answers),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--apply",
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == "e2_brownfield_seam_unavailable"
    assert payload["detail"] == (
        "Brownfield adoption needs explicit write authorization "
        "(CE_FORGE_ADOPTION_WRITE=1); without it, CE only emits the handoff plan."
    )
    _assert_brownfield_refusal_copy_is_tenant_lens(payload["detail"])
    assert payload["brownfield_adoption"]["apply_steps"]
    assert payload["brownfield_blockers"] == []


def test_onboard_apply_existing_brownfield_human_refusal_uses_tenant_lens_copy(
    tmp_path, capsys, monkeypatch
):
    project = _init_brownfield_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"))
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)

    def should_not_apply(*_args, **_kwargs):
        raise AssertionError("brownfield apply must refuse before the greenfield E2 executor runs")

    monkeypatch.setattr(onboard_apply, "apply_onboard", should_not_apply)
    answers = _answers_file(tmp_path, _brownfield_answers_for("acme/app"))
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(answers),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--apply",
    ])
    assert code == 1
    out = capsys.readouterr().out
    assert "Brownfield adoption is ready, but this command was started without write authorization." in out
    assert "CE_FORGE_LIVE_FORGE=1 and CE_FORGE_ADOPTION_WRITE=1" in out
    _assert_brownfield_refusal_copy_is_tenant_lens(out)


def test_onboard_apply_existing_brownfield_credential_refusal_is_tenant_lens(
    tmp_path, capsys, monkeypatch
):
    project = _init_brownfield_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"))
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    monkeypatch.setenv("CE_FORGE_LIVE_FORGE", "1")
    monkeypatch.setenv("CE_FORGE_ADOPTION_WRITE", "1")

    def should_not_apply(*_args, **_kwargs):
        raise AssertionError("brownfield apply must refuse before the greenfield E2 executor runs")

    monkeypatch.setattr(onboard_apply, "apply_onboard", should_not_apply)
    answers = _answers_file(tmp_path, _brownfield_answers_for("acme/app"))
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(answers),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--apply",
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == "e2_brownfield_seam_unavailable"
    assert payload["detail"] == (
        "Brownfield adoption needs a GitHub App credential before CE can open "
        "the governance PR; configure a local PEM for kind: own, or a broker "
        "for kind: shared."
    )
    _assert_brownfield_refusal_copy_is_tenant_lens(payload["detail"])


def test_onboard_apply_authorized_brownfield_routes_to_adoption(tmp_path, capsys, monkeypatch):
    # ce-ops#85 — with the DUAL escalation authorized (CE_FORGE_LIVE_FORGE +
    # CE_FORGE_ADOPTION_WRITE) and the repo genuine-brownfield (NOT already-CE) + adoptable, the
    # CLI routes to the adoption-apply legs: it hands the adoption driver to apply_onboard and
    # sets adoption_apply=True + the brownfield plan/probe. (The leg loop itself is covered by
    # the onboard_apply unit/integration tests; here we pin the CLI ROUTING decision.)
    from creator_engine_validator import onboard_apply_live

    project = _init_brownfield_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"))
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)

    # an adoption driver instance (its forge legs never run — apply_onboard is stubbed).
    adoption_driver = onboard_apply_live.LiveForgeAdoptionDriver(
        onboard_apply_live.LiveForgeConfig(
            repo="acme/app", installation_id=1, app_client_id="x",
            signer=lambda _b: b"", policy_sha="a" * 64, run_id="t",
        )
    )
    monkeypatch.setattr(
        v3_cli.onboard_apply_live, "adoption_forge_select",
        lambda *a, **k: adoption_driver,
    )
    # genuine brownfield: NOT already-CE.
    monkeypatch.setattr(v3_cli.onboard_apply, "repo_is_already_ce_governed", lambda *a, **k: False)

    captured = {}

    def fake_apply(request, **kwargs):
        captured["adoption_apply"] = request.adoption_apply
        captured["has_plan"] = request.brownfield_plan is not None
        captured["driver_is_adoption"] = kwargs.get("driver") is adoption_driver
        return {
            "action": "onboard_apply", "mode": request.mode, "target_repo": "acme/app",
            "verified_count": 12, "legs_total": 19, "greenfield_repos_created": 0,
            "repos_already_satisfied": 0, "brownfield_deferred": 0, "applied": 5,
            "already_satisfied": 7, "refused": 0, "failed": 0, "skipped": 7,
            "manual_rollback_required": 0, "brownfield_adopted": 1,
            "brownfield_adoption_pr": {"repo": "acme/app", "branch": "ce/adopt-governance",
                                       "base": "main", "pr_number": 11},
            "brownfield_scrub_findings": 0, "brownfield_scrub_findings_waived": 0, "legs": [],
        }

    monkeypatch.setattr(onboard_apply, "apply_onboard", fake_apply)
    monkeypatch.setenv("CE_FORGE_LIVE_FORGE", "1")
    monkeypatch.setenv("CE_FORGE_ADOPTION_WRITE", "1")

    answers = _answers_file(tmp_path, _brownfield_answers_for("acme/app"))
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(answers),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--apply",
        "--json",
    ])
    assert code == 0
    assert captured == {"adoption_apply": True, "has_plan": True, "driver_is_adoption": True}
    payload = json.loads(capsys.readouterr().out)
    assert payload["brownfield_adopted"] == 1
    assert payload["brownfield_adoption_pr"]["pr_number"] == 11


def test_onboard_apply_authorized_brownfield_gets_driver_from_onboard_apply_seam(
    tmp_path, capsys, monkeypatch
):
    # ce-ops#88 — production apply-driver selection belongs in _onboard_apply_driver().
    # The existing-repo apply path must ask that seam for an adoption-capable driver with
    # the merged install answers and verified policy digest, not bypass it through a
    # call-site selector.
    from creator_engine_validator import onboard_apply_live

    project = _init_brownfield_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"))
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)

    adoption_driver = onboard_apply_live.LiveForgeAdoptionDriver(
        onboard_apply_live.LiveForgeConfig(
            repo="acme/app", installation_id=1, app_client_id="x",
            signer=lambda _b: b"", policy_sha="a" * 64, run_id="t",
        )
    )
    captured: dict[str, object] = {}

    def driver_factory(*, merged, policy_sha, adoption):
        captured["repo"] = merged.value("github.repo")
        captured["policy_sha_len"] = len(policy_sha)
        captured["adoption"] = adoption
        return adoption_driver

    monkeypatch.setattr(v3_cli, "_onboard_apply_driver", driver_factory)
    monkeypatch.setattr(v3_cli.onboard_apply, "repo_is_already_ce_governed", lambda *a, **k: False)

    def fake_apply(request, **kwargs):
        captured["adoption_apply"] = request.adoption_apply
        captured["driver_is_adoption"] = kwargs.get("driver") is adoption_driver
        return {
            "action": "onboard_apply", "mode": request.mode, "target_repo": "acme/app",
            "verified_count": 12, "legs_total": 19, "greenfield_repos_created": 0,
            "repos_already_satisfied": 0, "brownfield_deferred": 0, "applied": 5,
            "already_satisfied": 7, "refused": 0, "failed": 0, "skipped": 7,
            "manual_rollback_required": 0, "brownfield_adopted": 1,
            "brownfield_adoption_pr": {"repo": "acme/app", "branch": "ce/adopt-governance",
                                       "base": "main", "pr_number": 12},
            "brownfield_scrub_findings": 0, "brownfield_scrub_findings_waived": 0, "legs": [],
        }

    monkeypatch.setattr(onboard_apply, "apply_onboard", fake_apply)

    answers = _answers_file(tmp_path, _brownfield_answers_for("acme/app"))
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(answers),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--apply",
        "--json",
    ])
    assert code == 0
    assert captured == {
        "repo": "acme/app",
        "policy_sha_len": 64,
        "adoption": True,
        "adoption_apply": True,
        "driver_is_adoption": True,
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["brownfield_adoption_pr"]["pr_number"] == 12


def test_onboard_apply_driver_selects_live_adoption_driver_when_authorized(
    tmp_path, monkeypatch
):
    from creator_engine_validator import onboard_apply_live

    pem = tmp_path / "ce-app.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nx\n-----END PRIVATE KEY-----\n", encoding="utf-8")
    monkeypatch.setenv("CE_FORGE_LIVE_FORGE", "1")
    monkeypatch.setenv("CE_FORGE_ADOPTION_WRITE", "1")
    monkeypatch.setenv("CE_FORGE_APP_CLIENT_ID", "Iv1.testclient")
    monkeypatch.setenv("CE_FORGE_APP_PEM", str(pem))

    answers = yaml.safe_load(_brownfield_answers_for("acme/app"))
    answers["github"]["app"] = {"installation_id": 140271364}
    schema = yaml.safe_load((_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH).read_text())
    merged = v3_installer.merge_answers(schema, answers=answers, detected={})

    driver = v3_cli._onboard_apply_driver(
        merged=merged, policy_sha="a" * 64, adoption=True
    )
    try:
        assert isinstance(driver, onboard_apply_live.LiveForgeAdoptionDriver)
    finally:
        v3_cli._close_apply_driver(driver)


def test_onboard_apply_existing_already_ce_repo_routes_to_plain_join(tmp_path, capsys, monkeypatch):
    # ce-ops#85 — an existing ALREADY-CE repo is NOT refused as brownfield: the gate
    # detects already-CE (fail-closed) and routes to the plain-join apply, handing the
    # SAME detection driver to the executor. Genuine brownfield stays E3-deferred
    # (covered by test_onboard_apply_existing_brownfield_refuses_without_e2_extension).
    from validators.tests.unit.test_onboard_apply import FakeDriver

    project = _init_brownfield_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"))
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    # inject a driver that reports the repo is already CE-governed
    monkeypatch.setattr(v3_cli, "_onboard_apply_driver", lambda: FakeDriver(repo_exists=True))

    captured: dict[str, object] = {}

    def fake_apply(request, *, verifier, driver):
        captured["request"] = request
        captured["driver"] = driver
        return {
            "action": "onboard_apply", "root": str(request.state_root), "mode": request.mode,
            "verified": {"ok": True, "key_id": "ce-root-v1", "algo": v3_installer.SSH_ED25519_ALGO},
            "target_repo": request.answers["github"]["repo"],
            "greenfield_repos_created": 0, "repos_already_satisfied": 12, "brownfield_deferred": 0,
            "legs_total": 12, "applied": 0, "already_satisfied": 12, "verified_count": 12,
            "skipped": 0, "refused": 0, "failed": 0, "rolled_back": 0, "manual_rollback_required": 0,
            "legs": [],
        }

    monkeypatch.setattr(onboard_apply, "apply_onboard", fake_apply)
    answers = _answers_file(tmp_path, _brownfield_answers_for("acme/app"))
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(answers),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--apply",
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "onboard_apply"
    assert payload.get("code") != "e2_brownfield_seam_unavailable"
    # the gate routed to plain-join and handed its already-CE driver to the executor
    assert isinstance(captured["driver"], FakeDriver)
    assert captured["request"].answers["github"]["mode"] == "existing"


def test_onboard_plan_surfaces_plain_join_route_for_already_ce_repo(tmp_path, capsys, monkeypatch):
    # ce-ops#85 --plan/--apply PARITY — --plan surfaces the plain-join route (kills the
    # "plan-level only" honesty gap) when the injected driver reports already-CE.
    from validators.tests.unit.test_onboard_apply import FakeDriver

    project = _init_brownfield_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.setattr(v3_cli, "_onboard_apply_driver", lambda: FakeDriver(repo_exists=True))
    answers = _answers_file(tmp_path, _brownfield_answers_for("acme/app"))
    code = v3_cli.main([
        "install",
        "--spec", str(_spec(tmp_path)),
        "--answers", str(answers),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--plan",
        "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plain_join"]["route"] == "plain-join"
    assert payload["plain_join"]["already_ce_detected"] is True
    assert payload["plain_join"]["enforcement"]["state"] == "verified_classic"


def test_onboard_plan_refuses_when_protection_floor_unenforceable(tmp_path, capsys, monkeypatch):
    from validators.tests.unit.test_onboard_apply import FakeDriver

    class UnenforceableDriver(FakeDriver):
        def verify_branch_protection(self, *, repo, branch, policy):
            self.calls.append("verify_branch_protection")
            return {
                "ok": False,
                "reason": onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE,
                "message": "Upgrade to GitHub Pro or make this repository public to enable this feature.",
                "remediation": onboard_apply.PROTECTION_FLOOR_REMEDIATION,
            }

    project = _init_brownfield_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.setattr(v3_cli, "_onboard_apply_driver", lambda: UnenforceableDriver(repo_exists=True))
    answers = _answers_file(tmp_path, _brownfield_answers_for("acme/app"))
    code = v3_cli.main([
        "install",
        "--spec", str(_spec(tmp_path)),
        "--answers", str(answers),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--plan",
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE
    assert payload["enforcement"]["state"] == "unenforceable"
    assert payload["plain_join"]["enforcement"]["state"] == "unenforceable"
    assert "GitHub Team/Pro" in payload["remediation"]


def test_onboard_apply_preflight_refuses_when_protection_floor_unenforceable(
    tmp_path, capsys, monkeypatch
):
    from validators.tests.unit.test_onboard_apply import FakeDriver

    class UnenforceableDriver(FakeDriver):
        def verify_branch_protection(self, *, repo, branch, policy):
            self.calls.append("verify_branch_protection")
            return {
                "ok": False,
                "reason": onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE,
                "message": "Upgrade to GitHub Pro or make this repository public to enable this feature.",
                "remediation": onboard_apply.PROTECTION_FLOOR_REMEDIATION,
            }

    project = _init_brownfield_project(tmp_path)
    monkeypatch.chdir(project)
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"))
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    monkeypatch.setattr(v3_cli, "_onboard_apply_driver", lambda: UnenforceableDriver(repo_exists=True))

    def should_not_apply(*_args, **_kwargs):
        raise AssertionError("unenforceable protection floor must refuse before apply_onboard")

    monkeypatch.setattr(onboard_apply, "apply_onboard", should_not_apply)
    answers = _answers_file(tmp_path, _brownfield_answers_for("acme/app"))
    code = v3_cli.main([
        "install",
        "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(answers),
        "--answers-schema", str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
        "--apply",
        "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE
    assert payload["enforcement"]["state"] == "unenforceable"
    assert "make the repository public" in payload["detail"]


def test_onboard_apply_refuses_self_attested_signature(tmp_path, capsys):
    spec = _spec(tmp_path)
    digest = v3_installer.content_digest(spec.read_bytes())
    code = v3_cli.main([
        "install", "--spec", str(spec), "--apply", "--sig-algo", v3_installer.CONTENT_ALGO,
        "--sig-value", digest, "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    assert "ssh-ed25519" in payload["detail"]


def test_onboard_apply_requires_complete_answers_before_executor(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe(origin_remote=None))

    def should_not_apply(*_args, **_kwargs):
        raise AssertionError("apply_onboard must not run with missing answers")

    monkeypatch.setattr(onboard_apply, "apply_onboard", should_not_apply)
    code = v3_cli.main(["install", "--spec", str(_signed_spec(tmp_path)), "--apply", "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    assert "github.mode" in {item["key"] for item in payload["missing"]}


def test_onboard_apply_hands_verified_request_to_executor(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        v3_cli,
        "_which",
        lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"),
    )
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe(origin_remote=None))
    captured: dict[str, object] = {}

    def fake_apply(request, *, verifier):
        captured["request"] = request
        captured["verifier"] = verifier
        return {
            "action": "onboard_apply",
            "root": str(request.state_root),
            "mode": request.mode,
            "verified": {"ok": True, "key_id": "ce-root-v1", "algo": v3_installer.SSH_ED25519_ALGO},
            "target_repo": request.answers["github"]["repo"],
            "greenfield_repos_created": 0,
            "repos_already_satisfied": 1,
            "brownfield_deferred": 0,
            "legs_total": 12,
            "applied": 1,
            "already_satisfied": 11,
            "verified_count": 12,
            "skipped": 0,
            "refused": 0,
            "failed": 0,
            "rolled_back": 0,
            "manual_rollback_required": 0,
            "legs": [],
        }

    monkeypatch.setattr(onboard_apply, "apply_onboard", fake_apply)
    root = tmp_path / "state"
    greenfield_answers = _answers_file(tmp_path, _GREENFIELD_ANSWERS_YAML)
    code = v3_cli.main([
        "install", "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(greenfield_answers),
        "--apply", "--root", str(root), "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "onboard_apply"
    assert payload["first_project"]["e2_apply_required"] is False
    assert payload["first_project"]["e2_convergence"]["counts"]["verified_count"] == 12
    request = captured["request"]
    assert isinstance(request, onboard_apply.ApplyRequest)
    assert request.state_root == root
    assert request.explicit_signature is None
    assert request.answers["github"]["repo"] == "chmod735/greenfield-first"
    assert captured["verifier"] is not None


def _fake_apply_success_summary(request):
    return {
        "action": "onboard_apply",
        "root": str(request.state_root),
        "mode": request.mode,
        "verified": {"ok": True, "key_id": "ce-root-v1", "algo": v3_installer.SSH_ED25519_ALGO},
        "target_repo": request.answers["github"]["repo"],
        "greenfield_repos_created": 1,
        "repos_already_satisfied": 0,
        "brownfield_deferred": 0,
        "legs_total": 12,
        "applied": 12,
        "already_satisfied": 0,
        "verified_count": 12,
        "skipped": 0,
        "refused": 0,
        "failed": 0,
        "rolled_back": 0,
        "manual_rollback_required": 0,
        "legs": [],
    }


def test_onboard_apply_solo_pilot_os_native_not_refused_without_runsc_or_proxy(tmp_path, capsys, monkeypatch):
    # ce-ops#71 MAJOR-1 (the headline bug) — driven through the REAL CLI entrypoint
    # (`ce install --apply` → ``_cmd_onboard``), NOT apply_onboard/_prepare directly.
    # A solo-pilot install resolves the os-native backend BEFORE the preflight, so on
    # a host WITHOUT runsc/proxy and with an EMPTY sudo grant the command does NOT
    # falsely refuse (the old flat-Tier-2 preflight planned runsc/proxy and tripped
    # ``sudo_grant_uncovered``). It must reach the executor with an os-native probe.
    monkeypatch.setattr(
        v3_cli, "_which",
        lambda tool: tool in ("git", "python", "uv", "claude"),  # NO runsc / NO proxy
    )
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe(origin_remote=None))
    captured: dict[str, object] = {}

    def fake_apply(request, *, verifier):
        captured["request"] = request
        return _fake_apply_success_summary(request)

    monkeypatch.setattr(onboard_apply, "apply_onboard", fake_apply)
    # solo-pilot, EMPTY sudo grant — governance-only, zero privileged installs.
    answers = _answers_file(tmp_path, _GREENFIELD_ANSWERS_YAML.replace(
        "sudo_grant: [git, python, runsc, proxy]", "sudo_grant: []"))
    code = v3_cli.main([
        "install", "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(answers), "--apply", "--root", str(tmp_path / "state"), "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    # NOT refused at the CLI preflight gate.
    assert code == 0, payload
    assert payload.get("error") != "refused"
    # Resolved os-native: the probe handed to the executor carries ONLY the
    # backend-aware deps — no privileged runsc/proxy the old flat-Tier-2 gate planned.
    request = captured["request"]
    assert set(request.dependency_probe) == {"git", "python", "uv"}


def test_onboard_apply_team_gvisor_still_refuses_when_runsc_proxy_missing(tmp_path, capsys, monkeypatch):
    # ce-ops#71 MAJOR-1 back-compat: a `team` profile (→ gvisor-proxy) on a host
    # genuinely missing runsc/proxy, with a grant that does NOT cover them, STILL
    # refuses at the CLI preflight (the privileged pairing is real for gvisor-proxy).
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv", "claude"))
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe(origin_remote=None))

    def should_not_apply(*_args, **_kwargs):
        raise AssertionError("apply_onboard must not run when the gvisor-proxy preflight refuses")

    monkeypatch.setattr(onboard_apply, "apply_onboard", should_not_apply)
    answers = _answers_file(tmp_path, _GREENFIELD_ANSWERS_YAML.replace(
        "profile: solo-pilot", "profile: team").replace(
        "sudo_grant: [git, python, runsc, proxy]", "sudo_grant: []"))
    code = v3_cli.main([
        "install", "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(answers), "--apply", "--root", str(tmp_path / "state"), "--json",
    ])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "refused"
    assert set(payload["sudo_uncovered"]) == {"runsc", "proxy"}


def test_onboard_apply_solo_pilot_os_native_real_e2e_succeeds_with_held_runtime(tmp_path, capsys, monkeypatch):
    # ce-ops#71 round 2 / ITEM 3 — REAL end-to-end CLI→apply (NO apply_onboard
    # monkeypatch). The full ``apply_onboard`` pipeline executes (legs, ledger,
    # ``_run_leg``, ``verify_runtime``, ``_fold_counters``); only the environment-I/O
    # seam — the driver, designed-injectable for CI — is faked so the GitHub legs need
    # no live forge. Proves the no-root solo-pilot ``--apply`` SUCCEEDS while the
    # os-native runtime is HONESTLY recorded as HELD (item-1 shape), not verified.
    from validators.tests.unit.test_onboard_apply import FakeDriver

    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv", "claude"))  # NO runsc/proxy
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe(origin_remote=None))
    # Inject the CI driver through apply_onboard's OWN seam (``ApplyDriver()``), NOT by
    # replacing apply_onboard — the real apply runs in full.
    monkeypatch.setattr(onboard_apply, "ApplyDriver", FakeDriver)

    root = tmp_path / "state"
    answers = _answers_file(tmp_path, _GREENFIELD_ANSWERS_YAML)
    code = v3_cli.main([
        "install", "--spec", str(_signed_spec(tmp_path)),
        "--answers", str(answers), "--apply", "--non-interactive",
        "--root", str(root), "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    # the apply SUCCEEDS end-to-end (exit 0; nothing failed or refused) — the #71 headline.
    assert code == 0, payload
    assert payload["failed"] == 0 and payload["refused"] == 0
    # the runtime_posture leg ran under os-native and is HONESTLY held (NOT verified).
    legs = {leg["id"]: leg for leg in payload["legs"]}
    posture = legs["runtime_posture"]
    assert posture["status"] == "held"
    assert payload["held"] == 1
    v = posture["verification"]
    assert v["backend"] == "os-native"
    assert v["ok"] is False and v["held"] is True
    assert v["runtime_available"] is False and v["runtime_held_reason"]
    # the run was actually recorded — the append-only ledger exists on disk.
    assert (root / "onboard" / "ledger.ndjson").is_file()


def test_onboard_answers_conflict_with_detected_fact_is_surfaced(tmp_path, capsys, monkeypatch):
    # detected harness contradicts the file's harness → surfaced, never silent
    monkeypatch.setattr(
        v3_cli, "_which",
        lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "codex"),
    )
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe())
    code = v3_cli.main(["install", "--spec", str(_spec(tmp_path)),
                        "--answers", str(_answers_file(tmp_path)), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["answers"]["conflicts"] == [
        {"key": "provider.harness", "file": "claude-code", "detected": "codex"}
    ]


def test_shipped_llms_install_spec_verifies_through_the_real_path(capsys):
    """The served spec re-signs with the in-tree mechanism: its published
    content digest must verify through the actual CLI gate (design §2.4 —
    the installer's verify step still passes after the E.3 regeneration)."""
    from creator_engine_validator import v3_installer

    spec = Path(__file__).resolve().parents[3] / "docs" / "llms-install.md"
    digest = v3_installer.content_digest(spec.read_bytes())
    code = v3_cli.main(["install", "--spec", str(spec), "--sig-value", digest, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["verified"]["ok"] is True and payload["self_attested"] is False


def test_install_inventory_help_names_the_loop():
    # the agent loop is discoverable from --help (inventory → answers → plan)
    parser = v3_cli._build_parser()
    help_text = parser.format_help()
    assert "install" in help_text


# ---------------------------------------------------------------------------
# v3.1-G2a — cev3 pr (push + open through the v3 forge; plan-by-default)
# ---------------------------------------------------------------------------
_G2_REPO = "creator-engine/creator-engine"


@pytest.fixture()
def _fake_forge_join(monkeypatch):
    """Stub the forge-join seam so the CLI wiring is tested with zero live git/gh/openssl.

    The real mint→push→open→stamp behavior is covered by test_v3_forge_join; here we record the
    kwargs the CLI forwards and shape the ChangeRef by the apply flag.
    """
    from creator_engine_validator import v3_forge_join as fj
    from creator_engine_validator.forge.change import ChangeRef

    calls: dict = {}

    def fake_load(path):
        calls["app_config_path"] = path
        return fj.AppConfig(client_id="x", installation_id=1, pem_path="/k.pem",
                            repo=_G2_REPO, permissions=())

    def fake_open(root, run_id, *, app_config, branch, manifest_paths, base="main",
                  source_dir=".", apply=False, **kw):
        calls["open"] = {
            "run_id": run_id, "branch": branch, "manifest_paths": list(manifest_paths),
            "base": base, "source_dir": source_dir, "apply": apply, "repo": app_config.repo,
        }
        if calls.get("raise"):
            raise fj.ForgeJoinRefused(calls["raise"])
        pr = 7 if apply else None
        return ChangeRef(
            repo=app_config.repo, branch=branch, base=base, pr_number=pr,
            head_sha=("d" * 40 if apply else None), manifest_paths=tuple(manifest_paths),
            plan_ref="e" * 64, changed=True, applied=apply, verified=apply,
        )

    monkeypatch.setattr(v3_cli.v3_forge_join, "load_app_config", fake_load)
    monkeypatch.setattr(v3_cli.v3_forge_join, "open_change_for_run", fake_open)
    return calls


def _pr_argv(tmp_path, run_id, *, apply=False, scope="rate-limit-login"):
    argv = [
        "pr", scope, "--run", run_id, "--branch", "v31-g2-forge-join",
        "--manifest-path", "validators/x.py", "--manifest-path", "validators/y.py",
        "--app-config", str(tmp_path / "app.json"), "--root", str(tmp_path), "--json",
    ]
    if apply:
        argv.append("--apply")
    return argv


def test_pr_plan_by_default_mutates_nothing(tmp_path, capsys, monkeypatch, _fake_forge_join):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    capsys.readouterr()
    code = v3_cli.main(_pr_argv(tmp_path, run_id))
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "pr_planned"
    assert payload["pr_number"] is None and payload["apply"] is False
    assert _fake_forge_join["open"]["apply"] is False


def test_pr_apply_opens_and_reports_pr(tmp_path, capsys, monkeypatch, _fake_forge_join):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    capsys.readouterr()
    code = v3_cli.main(_pr_argv(tmp_path, run_id, apply=True))
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "pr_opened" and payload["pr_number"] == 7
    assert payload["repo"] == _G2_REPO


def test_pr_forwards_app_config_manifest_and_base(tmp_path, capsys, monkeypatch, _fake_forge_join):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    v3_cli.main(_pr_argv(tmp_path, run_id, apply=True))
    opened = _fake_forge_join["open"]
    assert _fake_forge_join["app_config_path"] == str(tmp_path / "app.json")
    assert opened["manifest_paths"] == ["validators/x.py", "validators/y.py"]
    assert opened["base"] == "main" and opened["run_id"] == run_id


def test_pr_refuses_scope_mismatch_before_forge(tmp_path, capsys, monkeypatch, _fake_forge_join):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    capsys.readouterr()
    code = v3_cli.main(_pr_argv(tmp_path, run_id, scope="other-scope"))
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "scope_mismatch"
    assert "open" not in _fake_forge_join  # the forge was never reached


def test_pr_refuses_unknown_run(tmp_path, capsys, _fake_forge_join):
    capsys.readouterr()
    code = v3_cli.main(_pr_argv(tmp_path, "run-ghost-x"))
    assert code == 2
    assert "open" not in _fake_forge_join


def test_pr_surfaces_forge_refusal(tmp_path, capsys, monkeypatch, _fake_forge_join):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _fake_forge_join["raise"] = "App config not found"
    capsys.readouterr()
    code = v3_cli.main(_pr_argv(tmp_path, run_id, apply=True))
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "pr_refused"


def test_pr_app_config_is_required():
    # The Operator amendment: --app-config has NO default — argparse refuses without it.
    with pytest.raises(SystemExit):
        v3_cli.main(["pr", "s", "--run", "r", "--branch", "b", "--manifest-path", "x"])


# ---------------------------------------------------------------------------
# v3.1-G2a — collect derives change_set from the stamped change block
# ---------------------------------------------------------------------------
def _stamp_change_block(tmp_path, run_id, *, pr_number=7, head_sha="d" * 40):
    path = tmp_path / "dispatches" / run_id / "dispatch.yaml"
    drec = yaml.safe_load(path.read_text(encoding="utf-8"))
    drec["change"] = {
        "branch": "v31-g2-forge-join", "base": "main", "pr_number": pr_number,
        "head_sha": head_sha, "manifest_paths": ["validators/x.py"],
        "opened_at": "2026-06-11T09:30:00Z",
    }
    path.write_text(yaml.safe_dump(drec, sort_keys=True), encoding="utf-8")


def _outcome_change_set(chain_path: Path) -> dict:
    from creator_engine_validator import runtime_evidence_spine as spine
    doc = yaml.safe_load(chain_path.read_text(encoding="utf-8"))
    for r in doc["records"]:
        if r.get("record_type") == spine.RUN_OUTCOME_RECORD_TYPE:
            return r["change_set"]
    raise AssertionError("no run-outcome record")  # pragma: no cover


def test_collect_derives_change_set_and_pr_opened_from_block(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    _stamp_change_block(tmp_path, run_id, pr_number=7, head_sha="d" * 40)
    _stage_transcript(tmp_path, run_id, monkeypatch)
    capsys.readouterr()
    # no --outcome, no --branch/--head-sha: all derived from the stamped change block
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "pr_opened" and payload["pr"] == 7
    cs = _outcome_change_set(tmp_path / "runs" / f"{run_id}.runtime-evidence.yaml")
    assert cs["pr_number"] == 7 and cs["head_sha"] == "d" * 40  # NOT the run id (honesty gap closed)
    assert cs["branch"] == "v31-g2-forge-join"


def test_collect_explicit_outcome_wins_over_block(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stamp_change_block(tmp_path, run_id)
    _stage_transcript(tmp_path, run_id, monkeypatch)
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--outcome", "no_change",
        "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["outcome"] == "no_change"


def test_collect_refuses_missing_outcome_without_block(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)  # no change block stamped
    capsys.readouterr()
    code = v3_cli.main(["collect", "rate-limit-login", "--run", run_id, "--root", str(tmp_path), "--json"])
    assert code == 2
    assert json.loads(capsys.readouterr().out)["error"] == "outcome_required"


def test_collect_no_pr_fallback_is_byte_conserved(tmp_path, capsys, monkeypatch):
    # the operator-typed path for a run that opened no PR: head_sha defaults to the run id (G1).
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stage_transcript(tmp_path, run_id, monkeypatch)
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--outcome", "research_delivered",
        "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    cs = _outcome_change_set(tmp_path / "runs" / f"{run_id}.runtime-evidence.yaml")
    assert cs["head_sha"] == run_id and cs["base"] == "main"


# ---------------------------------------------------------------------------
# v3.1-G2b — cev3 review (dispatch a distinct CE-governed reviewer venue)
# ---------------------------------------------------------------------------
def _review_argv(tmp_path, author_run_id, *, spawn=False, scope="rate-limit-login", **extra):
    argv = [
        "review", scope, "--run", author_run_id,
        "--reviewer-actor", "ubuntuaws745-cmyk", "--root", str(tmp_path), "--json",
    ]
    if spawn:
        argv.append("--spawn")
    for k, v in extra.items():
        argv += ["--" + k.replace("_", "-"), str(v)]
    return argv


def test_review_refuses_without_stamped_pr(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)  # no change block → no PR
    capsys.readouterr()
    code = v3_cli.main(_review_argv(tmp_path, run_id))
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "no_pr"


def test_review_refuses_scope_mismatch(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stamp_change_block(tmp_path, run_id)
    capsys.readouterr()
    code = v3_cli.main(_review_argv(tmp_path, run_id, scope="other-scope"))
    assert code == 2
    assert json.loads(capsys.readouterr().out)["error"] == "scope_mismatch"


def test_review_codex_harness_is_deferred(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stamp_change_block(tmp_path, run_id, pr_number=7)
    capsys.readouterr()
    code = v3_cli.main(_review_argv(tmp_path, run_id, harness="codex", spawn=True))
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "codex_review_deferred"


def test_review_assemble_only_materializes_envelope_and_dispatch(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stamp_change_block(tmp_path, run_id, pr_number=7)
    capsys.readouterr()
    code = v3_cli.main(_review_argv(tmp_path, run_id))
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "review_assembled" and payload["pr_number"] == 7
    review_run_id = payload["review_run_id"]
    assert (tmp_path / "dispatches" / review_run_id / "dispatch.yaml").is_file()
    assert Path(payload["envelope_ref"]).is_file()


def test_review_spawn_requires_venue_root_and_ledger(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stamp_change_block(tmp_path, run_id)
    capsys.readouterr()
    code = v3_cli.main(_review_argv(tmp_path, run_id, spawn=True))  # no --venue-root/--ledger-root
    assert code == 2
    assert json.loads(capsys.readouterr().out)["error"] == "spawn_inputs_missing"


def test_review_spawn_launches_venue(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stamp_change_block(tmp_path, run_id, pr_number=7)

    seen = {}

    def fake_spawn(rec, *, controller_id, venue_root, ledger_root, seat_env_file=None):
        seen["controller_id"] = controller_id
        seen["venue_root"] = venue_root
        seen["seat_env_file"] = seat_env_file
        return v3_seat_bridge.SpawnResult(
            run_id=rec.run_id,
            terminal={"kind": "tmux", "session_id": "$5", "window_id": "@6", "pane_id": "%7"},
        )

    monkeypatch.setattr(v3_cli.v3_seat_bridge, "spawn_review_venue", fake_spawn)
    capsys.readouterr()
    code = v3_cli.main(_review_argv(
        tmp_path, run_id, spawn=True, venue_root=str(tmp_path / "venues"),
        ledger_root=str(tmp_path / "ledger"), controller_id="ctrl-x",
        seat_env_file=str(_owner_only_env(tmp_path / "rev.env"))))
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "spawned_review" and payload["pane_id"] == "%7"
    assert seen["controller_id"] == "ctrl-x"
    # D1: the review dispatch defaults UNATTENDED; D2: the seat-env-file is threaded through
    review_run_id = payload["review_run_id"]
    drec = yaml.safe_load(
        (tmp_path / "dispatches" / review_run_id / "dispatch.yaml").read_text(encoding="utf-8"))
    assert drec["unattended"] is True
    assert seen["seat_env_file"] == str(tmp_path / "rev.env")


def test_review_no_unattended_recorded_on_dispatch(tmp_path, capsys, monkeypatch):
    """D1/F3: --no-unattended threads through to the review dispatch record."""
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stamp_change_block(tmp_path, run_id, pr_number=7)
    capsys.readouterr()
    code = v3_cli.main(_review_argv(tmp_path, run_id) + ["--no-unattended"])
    assert code == 0
    review_run_id = json.loads(capsys.readouterr().out)["review_run_id"]
    drec = yaml.safe_load(
        (tmp_path / "dispatches" / review_run_id / "dispatch.yaml").read_text(encoding="utf-8"))
    assert drec["unattended"] is False


def test_review_spawn_fail_closed(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stamp_change_block(tmp_path, run_id)

    def boom(rec, **kw):
        raise v3_seat_bridge.SpawnRefused("pco-allocate refused")

    monkeypatch.setattr(v3_cli.v3_seat_bridge, "spawn_review_venue", boom)
    capsys.readouterr()
    code = v3_cli.main(_review_argv(
        tmp_path, run_id, spawn=True, venue_root=str(tmp_path / "v"), ledger_root=str(tmp_path / "l")))
    assert code == 1
    assert json.loads(capsys.readouterr().out)["action"] == "spawn_refused"


# ---------------------------------------------------------------------------
# v3.1-G2c — cev3 merge (gated squash; plan-by-default; --apply is the gated act)
# ---------------------------------------------------------------------------
def _merge_result(*, merged=False, would_merge=True, commit=None, head_status="unchanged",
                  restamp_recorded=False, audit_tree_equivalence=None,
                  old_head="d" * 40, new_head=None):
    from creator_engine_validator.v3_forge_join import RestampMergeResult
    return RestampMergeResult(
        pr_number=7, head_status=head_status, old_head_sha=old_head, new_head_sha=new_head,
        old_base_sha="a" * 40, new_base_sha=None, eligible=would_merge, would_merge=would_merge,
        merged=merged, merge_commit_sha=commit, review_decision="APPROVED",
        rollup_state="SUCCESS", merge_state_status="CLEAN", mergeable="MERGEABLE",
        applied=merged, restamp_recorded=restamp_recorded,
        audit_tree_equivalence=audit_tree_equivalence,
    )


@pytest.fixture()
def _fake_merge(monkeypatch):
    calls = {}

    def fake_merge_for_run(root, run_id, *, merge_gh_runner, apply=False, **kw):
        calls["apply"] = apply
        calls["run_id"] = run_id
        if calls.get("raise"):
            raise v3_cli.v3_forge_join.ForgeJoinRefused(calls["raise"])
        return _merge_result(merged=apply, would_merge=True,
                             commit=("f" * 40 if apply else None))

    monkeypatch.setattr(v3_cli.v3_forge_join, "merge_for_run", fake_merge_for_run)
    monkeypatch.setattr(v3_cli.v3_forge_join, "ambient_gh_runner", lambda **k: (lambda *a, **kw: None))
    return calls


def test_merge_plan_reports_gate_snapshot(tmp_path, capsys, monkeypatch, _fake_merge):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    capsys.readouterr()
    code = v3_cli.main(["merge", "rate-limit-login", "--run", run_id, "--root", str(tmp_path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "merge_planned" and payload["would_merge"] is True
    assert payload["merged"] is False and _fake_merge["apply"] is False


def test_merge_apply_reports_merged(tmp_path, capsys, monkeypatch, _fake_merge):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    capsys.readouterr()
    code = v3_cli.main(["merge", "rate-limit-login", "--run", run_id, "--apply",
                        "--root", str(tmp_path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "merged" and payload["merge_commit_sha"] == "f" * 40
    assert _fake_merge["apply"] is True


def test_merge_refuses_scope_mismatch(tmp_path, capsys, monkeypatch, _fake_merge):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    capsys.readouterr()
    code = v3_cli.main(["merge", "other-scope", "--run", run_id, "--root", str(tmp_path), "--json"])
    assert code == 2
    assert json.loads(capsys.readouterr().out)["error"] == "scope_mismatch"
    assert "run_id" not in _fake_merge  # merge_for_run never reached


def test_merge_surfaces_forge_refusal(tmp_path, capsys, monkeypatch, _fake_merge):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _fake_merge["raise"] = "not collected"
    capsys.readouterr()
    code = v3_cli.main(["merge", "rate-limit-login", "--run", run_id, "--apply",
                        "--root", str(tmp_path), "--json"])
    assert code == 1
    assert json.loads(capsys.readouterr().out)["action"] == "merge_refused"


def _patch_merge(monkeypatch, result):
    monkeypatch.setattr(v3_cli.v3_forge_join, "merge_for_run",
                        lambda *a, **k: result)
    monkeypatch.setattr(v3_cli.v3_forge_join, "ambient_gh_runner", lambda **k: (lambda *a, **kw: None))


def test_merge_plan_surfaces_base_only_restamp_available(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _patch_merge(monkeypatch, _merge_result(
        head_status="base_only_restamp_available", new_head="c" * 40))
    capsys.readouterr()
    code = v3_cli.main(["merge", "rate-limit-login", "--run", run_id, "--root", str(tmp_path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["head_status"] == "base_only_restamp_available"
    assert payload["new_head_sha"] == "c" * 40


def test_merge_apply_reports_restamped_and_audit(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _patch_merge(monkeypatch, _merge_result(
        merged=True, commit="f" * 40, head_status="base_only_restamped",
        restamp_recorded=True, audit_tree_equivalence=True, new_head="c" * 40))
    capsys.readouterr()
    code = v3_cli.main(["merge", "rate-limit-login", "--run", run_id, "--apply",
                        "--root", str(tmp_path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "merged" and payload["restamp_recorded"] is True
    assert payload["head_status"] == "base_only_restamped"


def test_merge_apply_audit_tree_mismatch_is_loud_nonzero(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _patch_merge(monkeypatch, _merge_result(
        merged=True, commit="f" * 40, head_status="unchanged", audit_tree_equivalence=False))
    capsys.readouterr()
    code = v3_cli.main(["merge", "rate-limit-login", "--run", run_id, "--apply",
                        "--root", str(tmp_path), "--json"])
    assert code == 1
    assert json.loads(capsys.readouterr().out)["action"] == "merge_audit_tree_mismatch"


# ---------------------------------------------------------------------------
# v3.1-G2c — read-model: show/status surface the PR + a live reviewer venue
# ---------------------------------------------------------------------------
def _seed_review_dispatch(tmp_path, author_run_id, *, pr_number=7):
    author = yaml.safe_load((tmp_path / "dispatches" / author_run_id / "dispatch.yaml").read_text())
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor="ubuntuaws745-cmyk", pr_number=pr_number, head_sha="d" * 40)
    rec.data["terminal"] = {"kind": "tmux", "session_id": "$5", "window_id": "@6", "pane_id": "%7"}
    rec.data["spawned_at"] = "20260611T093500Z"
    v3_seat_bridge._write_record(rec)
    return rec.run_id


def test_show_surfaces_pr_and_review_venue(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stamp_change_block(tmp_path, run_id, pr_number=7)
    review_run_id = _seed_review_dispatch(tmp_path, run_id, pr_number=7)
    capsys.readouterr()
    v3_cli.main(["show", "rate-limit-login", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "PR: #7" in out and "Review venue:" in out and review_run_id in out


def test_status_surfaces_pr_in_payload(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    _stamp_change_block(tmp_path, run_id, pr_number=7)
    capsys.readouterr()
    v3_cli.main(["status", "--root", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    scope = next(s for s in payload["scopes"] if s["scope_id"] == "rate-limit-login")
    assert scope["pr"] == 7


# ---------------------------------------------------------------------------
# v3.1-G2 keystone — end-to-end faked drive: scope→pr→review→collect→merge→report
# ---------------------------------------------------------------------------
class _E2EMergeGh:
    """Routes the gated-merge gh calls for the e2e (review/checks/conflict reads + squash PUT)."""

    def __call__(self, argv, input_text=None):
        argv = list(argv)
        joined = " ".join(argv)
        if "-X" in argv and "PUT" in argv:
            return _cp(argv, json.dumps({"merged": True, "sha": "f" * 40}))
        if "headRefName" in joined:  # F6 combined pr_state read (unchanged head "d"*40)
            return _cp(argv, json.dumps({"data": {"repository": {"pullRequest": {
                "number": 7, "headRefName": "v31-g2-forge-join", "baseRefName": "main",
                "headRefOid": "d" * 40, "baseRefOid": "a" * 40, "reviewDecision": "APPROVED",
                "mergeStateStatus": "CLEAN", "mergeable": "MERGEABLE",
                "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": "SUCCESS"}}}]}}}}}))
        if "reviewDecision" in joined:
            return _cp(argv, json.dumps({"data": {"repository": {"pullRequest": {"reviewDecision": "APPROVED"}}}}))
        if "statusCheckRollup" in joined:
            return _cp(argv, json.dumps({"data": {"repository": {"pullRequest": {
                "headRefOid": "d" * 40,
                "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": "SUCCESS"}}}]}}}}}))
        if "mergeStateStatus" in joined:
            return _cp(argv, json.dumps({"data": {"repository": {"pullRequest": {
                "mergeStateStatus": "CLEAN", "mergeable": "MERGEABLE"}}}}))
        raise AssertionError(joined)  # pragma: no cover


def _cp(argv, stdout):
    import subprocess
    return subprocess.CompletedProcess(list(argv), 0, stdout=stdout, stderr="")


def test_e2e_scope_to_pr_to_review_to_merge_to_report(tmp_path, capsys, monkeypatch):
    # 1) scope → ratify → drive --spawn (faked seat bridge) with a rates policy for the spend fold.
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)

    # 2) cev3 pr --apply (faked forge join: stamps the change block like the real open does).
    from creator_engine_validator.forge.change import ChangeRef

    def fake_open(root, rid, *, app_config, branch, manifest_paths, base="main",
                  source_dir=".", apply=False, **kw):
        if apply:
            dpath = Path(root) / "dispatches" / rid / "dispatch.yaml"
            drec = yaml.safe_load(dpath.read_text())
            drec["change"] = {"branch": branch, "base": base, "pr_number": 7, "head_sha": "d" * 40,
                              "manifest_paths": list(manifest_paths), "opened_at": "2026-06-11T09:30:00Z"}
            dpath.write_text(yaml.safe_dump(drec))
        return ChangeRef(repo=app_config.repo, branch=branch, base=base,
                         pr_number=(7 if apply else None), head_sha=("d" * 40 if apply else None),
                         manifest_paths=tuple(manifest_paths), plan_ref="e" * 64,
                         changed=True, applied=apply, verified=apply)

    monkeypatch.setattr(v3_cli.v3_forge_join, "load_app_config",
                        lambda p: v3_cli.v3_forge_join.AppConfig("x", 1, "/k.pem", _G2_REPO, ()))
    monkeypatch.setattr(v3_cli.v3_forge_join, "open_change_for_run", fake_open)
    assert v3_cli.main([
        "pr", "rate-limit-login", "--run", run_id, "--branch", "v31-g2-forge-join",
        "--manifest-path", "validators/x.py", "--app-config", str(tmp_path / "app.json"),
        "--apply", "--root", str(tmp_path), "--json"]) == 0

    # 3) cev3 review --spawn (faked venue launch).
    monkeypatch.setattr(v3_cli.v3_seat_bridge, "spawn_review_venue",
                        lambda rec, **kw: v3_seat_bridge.SpawnResult(
                            run_id=rec.run_id,
                            terminal={"kind": "tmux", "session_id": "$5", "window_id": "@6", "pane_id": "%7"}))
    capsys.readouterr()
    assert v3_cli.main([
        "review", "rate-limit-login", "--run", run_id, "--reviewer-actor", "ubuntuaws745-cmyk",
        "--spawn", "--venue-root", str(tmp_path / "venues"), "--ledger-root", str(tmp_path / "ledger"),
        "--root", str(tmp_path), "--json"]) == 0
    review_run_id = json.loads(capsys.readouterr().out)["review_run_id"]

    # 4) cev3 collect the REVIEW venue run (its own run, its own chain) — D6/F9 resolves the
    #    transcript by the venue's stamped harness session id (no --transcript guess).
    _stage_transcript(tmp_path, review_run_id, monkeypatch)
    assert v3_cli.main([
        "collect", "rate-limit-login", "--run", review_run_id,
        "--outcome", "review_submitted", "--pr", "7", "--root", str(tmp_path)]) == 0

    # 5) cev3 collect the AUTHOR run — derives change_set + pr_opened FROM the stamped change block.
    _stage_transcript(tmp_path, run_id, monkeypatch)
    assert v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id,
        "--root", str(tmp_path)]) == 0

    # 6) cev3 merge --apply (REAL merge_for_run; ambient gh faked) → appends pr_merged.
    monkeypatch.setattr(v3_cli.v3_forge_join, "ambient_gh_runner", lambda **k: _E2EMergeGh())
    capsys.readouterr()
    assert v3_cli.main([
        "merge", "rate-limit-login", "--run", run_id, "--apply", "--root", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["action"] == "merged"

    # 7) cev3 report the AUTHOR run → ◆ renders outcome pr_merged + PR #7 + the spend fold.
    capsys.readouterr()
    chain = tmp_path / "runs" / f"{run_id}.runtime-evidence.yaml"
    assert v3_cli.main([
        "report", "rate-limit-login", "--evidence", str(chain), "--run-id", run_id,
        "--cap", "5", "--root", str(tmp_path), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["outcome"] == "pr_merged"
    assert report["action"] == "report"


# ===========================================================================
# ce-ops#43 — `cev3 reap once|watch|status` (the seat/venue retirement reaper)
# ===========================================================================
import json as _json
import signal as _signal

from creator_engine_validator import seat_reaper as _seat_reaper


def _write_reap_seat(root: Path, run_id: str, *, events, **disp_over) -> Path:
    """A minimal dispatch + events surface under <root>/dispatches/<run_id>/."""
    d = root / "dispatches" / run_id
    d.mkdir(parents=True, exist_ok=True)
    rec = {
        "kind": "dispatch-record", "record_type": "dispatch", "schema_version": "1",
        "scope_id": "demo-scope", "run_id": run_id, "mutation_class": "code",
        "harness": "claude", "unattended": True, "session": "ce", "window": "drive",
        "terminal": {"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%3"},
        "spawned_at": "20260613T115500Z",
    }
    rec.update(disp_over)
    (d / "dispatch.yaml").write_text(yaml.safe_dump(rec, sort_keys=True), encoding="utf-8")
    (d / "events.jsonl").write_text(
        "\n".join(_json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )
    return d


def _ev(kind: str, run_id: str, *, ts: str, **extra) -> dict:
    e = {"v": 1, "event": kind, "ts": ts, "seat_id": run_id, "run_id": run_id,
         "writer": "launcher_wrapper"}
    e.update(extra)
    return e


def test_reap_status_required_json_shape(tmp_path, capsys):
    root = tmp_path / "state"
    (root / "dispatches").mkdir(parents=True)
    assert v3_cli.main(["reap", "status", "--root", str(root), "--json"]) == 0
    payload = _json.loads(capsys.readouterr().out)
    for key in ("action", "root", "observed_dispatches", "eligible", "conserved",
                "would_escalate", "already_retired", "active_or_unknown", "seats"):
        assert key in payload, key
    assert payload["action"] == "reap_status"


def test_11_status_is_read_only(tmp_path, capsys):
    """`reap status` writes nothing and leaves events.jsonl byte-identical; the same
    byte-identical pin holds across a `reap once` evaluation pass that does not retire."""
    root = tmp_path / "state"
    run_id = "run-unclean-20200101T000000Z"
    # an OLD launched-no-exited seat with a dead pid → always classifies unclean-stop,
    # independent of the wall clock (the CLI uses real now()).
    d = _write_reap_seat(
        root, run_id, events=[_ev("launched", run_id, ts="2020-01-01T00:00:00Z", pid=999999,
                                  command_sha256="ab" * 32)],
    )
    events_path = d / "events.jsonl"
    before = events_path.read_bytes()

    # (a) status: read-only — writes no escalation/reaper/archive, events byte-identical
    assert v3_cli.main(["reap", "status", "--root", str(root),
                        "--ledger-root", str(tmp_path / "ledger"), "--json"]) == 0
    st = _json.loads(capsys.readouterr().out)
    assert st["would_escalate"] == 1
    assert events_path.read_bytes() == before
    assert not (root / "escalations").exists()
    assert not (root / "reaper").exists()

    # (b) a `reap once` evaluation pass that does NOT retire still leaves events identical
    assert v3_cli.main(["reap", "once", "--root", str(root),
                        "--ledger-root", str(tmp_path / "ledger"), "--repo-root", str(tmp_path),
                        "--json"]) == 0
    once = _json.loads(capsys.readouterr().out)
    assert once["reaped"] == 0 and once["escalated"] == 1
    assert events_path.read_bytes() == before          # NEVER appends to events.jsonl
    assert not (root / "reaper").exists()               # no retirement ledger written
    # the escalation landed in the existing queue (B.8 can banner it)
    esc = list((root / "escalations").glob("*.yaml"))
    assert len(esc) == 1
    _assert_escalation_schema(yaml.safe_load(esc[0].read_text()))


def test_reap_once_required_json_shape(tmp_path, capsys):
    root = tmp_path / "state"
    run_id = "run-conserved-20260613T110000Z"
    _write_reap_seat(
        root, run_id, conserve=True, conserve_reason="evidence", conserved_at="2026-06-13T11:00:00Z",
        events=[_ev("launched", run_id, ts="2026-06-13T11:00:00Z", pid=1, command_sha256="ab" * 32),
                _ev("exited", run_id, ts="2026-06-13T11:01:00Z", exit_code=0)],
    )
    assert v3_cli.main(["reap", "once", "--root", str(root),
                        "--ledger-root", str(tmp_path / "l"), "--repo-root", str(tmp_path),
                        "--json"]) == 0
    payload = _json.loads(capsys.readouterr().out)
    for key in ("action", "root", "observed_dispatches", "eligible", "reaped", "conserved",
                "escalated", "skipped_active_or_unknown", "already_retired", "failed",
                "step_counts", "retirements", "escalations"):
        assert key in payload, key
    assert payload["action"] == "reap_once"
    assert payload["conserved"] == 1 and payload["reaped"] == 0


def test_reap_watch_invalid_interval_refuses_before_loop(tmp_path, capsys):
    root = tmp_path / "state"
    (root / "dispatches").mkdir(parents=True)
    assert v3_cli.main(["reap", "watch", "--root", str(root), "--interval", "0", "--json"]) == 2
    payload = _json.loads(capsys.readouterr().out)
    assert payload["error"] == "reap_invalid_interval"


@pytest.mark.parametrize("sig", [_signal.SIGINT, _signal.SIGTERM])
def test_12_watch_tick_shape_and_clean_signal_stop(tmp_path, monkeypatch, capsys, sig):
    """Each watch tick emits the `reap_watch_tick` action/counter shape; SIGINT and
    SIGTERM stop the loop cleanly after the current pass (exit 0)."""
    import os as _os

    root = tmp_path / "state"
    (root / "dispatches").mkdir(parents=True)
    seen: list[str] = []

    def _stub(root_arg, **kw):
        seen.append(kw.get("action"))
        # deliver the stop signal mid-tick; the installed handler flips the stop flag
        _os.kill(_os.getpid(), sig)
        return {
            "action": kw.get("action"), "root": str(root_arg), "observed_dispatches": 0,
            "eligible": 0, "reaped": 0, "conserved": 0, "escalated": 0,
            "skipped_active_or_unknown": 0, "already_retired": 0, "failed": 0,
            "step_counts": {}, "retirements": [], "escalations": [],
        }

    monkeypatch.setattr(v3_cli.seat_reaper, "reap_once", _stub)
    rc = v3_cli.main(["reap", "watch", "--root", str(root), "--interval", "5",
                      "--ledger-root", str(tmp_path / "l"), "--repo-root", str(tmp_path)])
    assert rc == 0
    assert seen == ["reap_watch_tick"]  # exactly one pass, then a clean stop
    assert "reap watch tick" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# install — the "onboard" legacy alias (ce-ops#440 S1: docs/install.sh still
# invokes ``cev3 onboard`` and is release-signed; kept for one release cycle)
# ---------------------------------------------------------------------------
def test_install_subparser_accepts_legacy_onboard_alias():
    parser = v3_cli._build_parser()
    args = parser.parse_args(["onboard", "--spec", "some/spec.yaml"])
    # argparse stores the literal alias string in the subparsers dest, not the
    # canonical subparser name — so the dispatch table must key it explicitly.
    assert args.command == "onboard"
    assert args.spec == "some/spec.yaml"
    handler = v3_cli._DISPATCH.get(args.command)
    assert handler is v3_cli._cmd_onboard
    # and the canonical spelling still resolves to the very same handler
    canonical_args = parser.parse_args(["install", "--spec", "some/spec.yaml"])
    assert v3_cli._DISPATCH.get(canonical_args.command) is handler
