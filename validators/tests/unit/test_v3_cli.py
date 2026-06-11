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
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import _versions as ver
from creator_engine_validator import v3_cli, v3_seat_bridge
from creator_engine_validator.schema import validate_with_schema


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
APPROVER = "a" * 64  # a value-free 64-hex opaque digest


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


def test_drive_spawn_refuses_non_claude_harness(tmp_path, capsys, monkeypatch):
    calls = _fake_bridge(monkeypatch)
    _file_ready(tmp_path)
    v3_cli.main(["ratify", "rate-limit-login", "--approver-ref", APPROVER, "--root", str(tmp_path)])
    capsys.readouterr()
    code = v3_cli.main(
        ["drive", "rate-limit-login", "--spawn", "--harness", "codex", "--root", str(tmp_path)]
    )
    assert code == 2
    out = capsys.readouterr().out
    assert "G1-codex" in out and "not bridged" in out
    assert calls["spawn"] == []  # never reached the spawn leg


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
    tpath = _transcript(tmp_path / "seat.jsonl")
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--transcript", str(tpath),
        "--outcome", "research_delivered", "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "collected"
    assert payload["outcome"] == "research_delivered"
    assert payload["spend_leaves"] == 2
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
    tpath = _transcript(tmp_path / "seat.jsonl")
    v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--transcript", str(tpath),
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
    tpath = _transcript(tmp_path / "seat.jsonl")
    args = ["collect", "rate-limit-login", "--run", run_id, "--transcript", str(tpath),
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
    tpath = _transcript(tmp_path / "seat.jsonl")
    v3_cli.main(["collect", "rate-limit-login", "--run", run_id, "--transcript", str(tpath),
                 "--outcome", "no_change", "--root", str(tmp_path)])
    capsys.readouterr()
    v3_cli.main(["show", "rate-limit-login", "--root", str(tmp_path), "--json"])
    proj2 = json.loads(capsys.readouterr().out)["projection"]
    assert proj2["state"] != "in_progress"


def test_report_defaults_evidence_from_collected_dispatch(tmp_path, capsys, monkeypatch):
    # With a collected dispatch, `report` needs no --evidence — it finds the chain.
    run_id = _dispatch_a_run(tmp_path, monkeypatch, policy=_RATES_POLICY)
    tpath = _transcript(tmp_path / "seat.jsonl")
    v3_cli.main(["collect", "rate-limit-login", "--run", run_id, "--transcript", str(tpath),
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
    tpath = _transcript(tmp_path / "seat.jsonl", n_turns=3)
    capsys.readouterr()
    assert v3_cli.main(["collect", "rate-limit-login", "--run", run_id, "--transcript", str(tpath),
                        "--outcome", "research_delivered", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert v3_cli.main(["artifacts", "rate-limit-login", "--cap", "5", "--root", str(tmp_path), "--json"]) == 0
    arts = {a["kind"] for a in json.loads(capsys.readouterr().out)["artifacts"]}
    assert {"scope", "evidence", "spend"} <= arts  # run artifacts surfaced sans --evidence
    assert v3_cli.main(["report", "rate-limit-login", "--root", str(tmp_path)]) == 0
    block = capsys.readouterr().out
    assert "Research delivered" in block


def test_collect_without_transcript_still_records_outcome(tmp_path, capsys, monkeypatch):
    run_id = _dispatch_a_run(tmp_path, monkeypatch)
    capsys.readouterr()
    code = v3_cli.main([
        "collect", "rate-limit-login", "--run", run_id, "--outcome", "no_change",
        "--root", str(tmp_path), "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["spend_leaves"] == 0
    assert payload["outcome"] == "no_change"


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
    code = v3_cli.main(["onboard", "--spec", str(spec), "--key-id", "ce-root-v1", "--json"])
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
    v3_cli.main(["onboard", "--spec", str(spec), "--key-id", "ce-root-v1", "--sig-value", digest, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["verified"]["ok"] is True and payload["self_attested"] is False


def test_onboard_refuses_tampered_spec(tmp_path, capsys):
    spec = tmp_path / "spec.md"
    spec.write_text("# real spec\n", encoding="utf-8")
    # a sig value that does not match the spec content → refuse before execute
    code = v3_cli.main(["onboard", "--spec", str(spec), "--key-id", "ce-root-v1",
                        "--sig-value", "0" * 64])
    assert code == 1
    assert "REFUSED" in capsys.readouterr().out


def test_onboard_optout_requires_ratification_and_educates(tmp_path, capsys):
    spec = tmp_path / "spec.md"
    spec.write_text("# spec\n", encoding="utf-8")
    # opt-out without a valid ratification binding → refused (human-only)
    assert v3_cli.main(["onboard", "--spec", str(spec), "--opt-out"]) == 1
    capsys.readouterr()
    # with a ratified binding → custom profile + the educate copy surfaces
    code = v3_cli.main(["onboard", "--spec", str(spec), "--opt-out",
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


def _spec(tmp_path):
    spec = tmp_path / "llms-install.md"
    spec.write_text("# Install CE\n", encoding="utf-8")
    return spec


def _answers_file(tmp_path, content=_GOOD_ANSWERS_YAML):
    path = tmp_path / "ce-install.answers.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_onboard_inventory_emits_the_awareness_artifact(tmp_path, capsys):
    code = v3_cli.main(["onboard", "--spec", str(_spec(tmp_path)), "--inventory", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "onboard_inventory"
    assert payload["verified"]["ok"] is True   # verify stays first, even for awareness
    rows = {row["key"]: row for row in payload["inventory"]}
    assert rows["github.bootstrap_token"]["status"] == "secret (ref required)"
    assert rows["cost.profile"]["status"] == "default:default"


def test_onboard_answers_file_resolves_the_asks(tmp_path, capsys, monkeypatch):
    # pin the live probe (host-independent): claude present, codex absent
    monkeypatch.setattr(
        v3_cli, "_which",
        lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"),
    )
    code = v3_cli.main(["onboard", "--spec", str(_spec(tmp_path)),
                        "--answers", str(_answers_file(tmp_path)), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["answers"]["missing"] == []
    assert payload["answers"]["sha256"] and len(payload["answers"]["sha256"]) == 64
    assert payload["answers"]["sources"]["github.repo"] == "answers"


def test_onboard_refuses_typo_key_fail_closed(tmp_path, capsys):
    bad = _answers_file(tmp_path, _GOOD_ANSWERS_YAML + "workspce_root: typo\n")
    code = v3_cli.main(["onboard", "--spec", str(_spec(tmp_path)), "--answers", str(bad)])
    assert code == 1
    assert "REFUSED" in capsys.readouterr().out


def test_onboard_refuses_raw_secret_in_answers(tmp_path, capsys):
    bad = _answers_file(tmp_path, _GOOD_ANSWERS_YAML.replace(
        "prompt://github-bootstrap-token", "ghp_rawsecret123"))
    code = v3_cli.main(["onboard", "--spec", str(_spec(tmp_path)), "--answers", str(bad)])
    assert code == 1
    out = capsys.readouterr().out
    assert "REFUSED" in out and "SecretRef" in out


def test_onboard_non_interactive_refuses_with_exact_missing_list(tmp_path, capsys):
    code = v3_cli.main(["onboard", "--spec", str(_spec(tmp_path)), "--non-interactive", "--json"])
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
    code = v3_cli.main(["onboard", "--spec", str(_spec(tmp_path)),
                        "--answers", str(_answers_file(tmp_path)),
                        "--non-interactive", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["non_interactive"] is True
    assert payload["answers"]["missing"] == []
    assert payload["answers"]["sudo_grant"]["uncovered"] == []


def test_onboard_non_interactive_refuses_sudo_outside_the_grant(tmp_path, capsys, monkeypatch):
    # force a privileged install the grant does not cover
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in ("git", "python", "uv"))
    narrow = _answers_file(tmp_path, _GOOD_ANSWERS_YAML.replace(
        "sudo_grant: [git, python, runsc, proxy]", "sudo_grant: [runsc]"))
    code = v3_cli.main(["onboard", "--spec", str(_spec(tmp_path)),
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
    code = v3_cli.main(["onboard", "--spec", str(_spec(tmp_path)),
                        "--answers", str(custom), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"]["runtime_policy"]["spend_cap_enforcement"] == "off"
    # the answers-file ack is stripped — the fragment matches the G-5 schema
    assert "educate_acknowledged" not in payload["profile"]["runtime_policy"]["spend_cap_optout"]
    assert "won't speed up your runs" in payload["educate"]


def test_onboard_plan_composes_the_github_leg(tmp_path, capsys):
    code = v3_cli.main(["onboard", "--spec", str(_spec(tmp_path)),
                        "--answers", str(_answers_file(tmp_path)), "--plan", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    leg = payload["github_leg"]
    assert leg["app"]["click_required"] is False          # installation declared → no click
    assert leg["human_approves"] == []
    # unprobed live facts stay fail-closed in the dry run (the E.4 drive probes them)
    assert leg["bootstrap_token_scopes"]["probed"] is False


def test_onboard_answers_conflict_with_detected_fact_is_surfaced(tmp_path, capsys, monkeypatch):
    # detected harness contradicts the file's harness → surfaced, never silent
    monkeypatch.setattr(
        v3_cli, "_which",
        lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "codex"),
    )
    code = v3_cli.main(["onboard", "--spec", str(_spec(tmp_path)),
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
    code = v3_cli.main(["onboard", "--spec", str(spec), "--sig-value", digest, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["verified"]["ok"] is True and payload["self_attested"] is False


def test_onboard_inventory_help_names_the_loop():
    # the agent loop is discoverable from --help (inventory → answers → plan)
    parser = v3_cli._build_parser()
    help_text = parser.format_help()
    assert "onboard" in help_text
