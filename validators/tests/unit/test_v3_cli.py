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
from creator_engine_validator import v3_cli


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
    assert payload["live_spawn"] == "deferred"


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


def test_user_facing_command_is_ce_not_cev3(tmp_path, capsys):
    # Operator-ratified directive: users type `ce`; `cev3` is internal-only.
    assert v3_cli.CE_CMD == "ce"
    assert v3_cli._build_parser().prog == "ce"
    # user-facing output never prints the internal `cev3` name
    _file_ready(tmp_path)
    v3_cli.main(["artifacts", "rate-limit-login", "--root", str(tmp_path)])
    v3_cli.main(["shape", "rate-limit-login", "--goal", "g", "--change-type", "code"])
    assert "cev3" not in capsys.readouterr().out


def test_help_reachable():
    with pytest.raises(SystemExit) as exc:
        v3_cli.main(["--help"])
    assert exc.value.code == 0
