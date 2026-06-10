"""Unit tests for the Cockpit L2 read-model (v3.5-B.1, = harness-paper F1).

The principle-6 law in testable form (design §3.0.6 / cluster §0.4):

* importing the L2 module never imports ``textual``/``watchfiles``;
* the snapshot is JSON-round-trippable (the future-GUI seam is real);
* the demo seed folds to the expected board (five canon columns, the blocked
  refused-``git push`` seat present);
* the seed chains verify clean (``verify_chain() == []``);
* the stage column derives via ``coordination.PHASE_BY_STATE`` — never a third
  vocabulary;
* absent live sources degrade honestly (``unavailable``, never fabricated).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from creator_engine_validator import coordination
from creator_engine_validator.runner import cockpit_demo_seed, cockpit_readmodel
from creator_engine_validator.runtime_evidence_spine import verify_chain
from creator_engine_validator.schema import validate_with_schema

VALIDATORS_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = VALIDATORS_DIR.parent


def _demo_snapshot() -> dict:
    return cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())


# --- principle 6.2: the L2 import is textual/watchfiles-free -----------------

def test_importing_readmodel_leaves_textual_and_watchfiles_unimported():
    code = (
        "import sys\n"
        "import creator_engine_validator.runner.cockpit_readmodel\n"
        "import creator_engine_validator.runner.cockpit_demo_seed\n"
        "assert 'textual' not in sys.modules, 'L2 must not import textual'\n"
        "assert 'watchfiles' not in sys.modules, 'L2 must not import watchfiles'\n"
    )
    env = {**os.environ, "PYTHONPATH": str(VALIDATORS_DIR)}
    proc = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr


# --- principle 6.3: JSON round-trip identity ---------------------------------

def test_demo_snapshot_json_round_trips():
    snapshot = _demo_snapshot()
    assert json.loads(json.dumps(snapshot, sort_keys=True)) == snapshot


def test_live_snapshot_json_round_trips(tmp_path):
    snapshot = cockpit_readmodel.snapshot_from_roots(tmp_path, environ={})
    assert json.loads(json.dumps(snapshot, sort_keys=True)) == snapshot


# --- the demo seed folds to the expected board -------------------------------

def test_demo_board_populates_all_five_canon_columns():
    snapshot = _demo_snapshot()
    board = snapshot["board"]
    assert board["columns"] == list(coordination.COGNITIVE_PHASES)
    phases = {card["phase"] for card in board["cards"]}
    assert phases == set(coordination.COGNITIVE_PHASES)
    for phase in coordination.COGNITIVE_PHASES:
        assert board["phase_counts"][phase] >= 1


def test_demo_seats_tell_the_grader_outside_story():
    snapshot = _demo_snapshot()
    seats = snapshot["seats"]
    assert len(seats) >= 6
    blocked = [s for s in seats if s["status"] == "blocked"]
    assert blocked, "the demo must include a blocked seat (the refused git push)"
    push_seat = [s for s in seats if s["lane_id"] == "gate-push-refusal"]
    assert push_seat and push_seat[0]["status"] == "blocked"
    roles = {s["role"] for s in seats}
    assert "reviewer" in roles and "implementer" in roles


def test_demo_source_carries_the_persistent_watermark():
    snapshot = _demo_snapshot()
    assert snapshot["source"]["demo"] is True
    assert snapshot["source"]["mode"] == "demo"
    assert snapshot["source"]["watermark"] == cockpit_readmodel.DEMO_WATERMARK
    assert "DEMO" in cockpit_readmodel.DEMO_WATERMARK
    assert "not a live fleet" in cockpit_readmodel.DEMO_WATERMARK


def test_live_source_has_no_watermark(tmp_path):
    snapshot = cockpit_readmodel.snapshot_from_roots(tmp_path, environ={})
    assert snapshot["source"]["demo"] is False
    assert snapshot["source"]["watermark"] is None


# --- the seed chains verify clean (tamper-evident, not invented) -------------

def test_every_seed_chain_verifies_clean():
    seed = cockpit_demo_seed.seed()
    assert seed["chains"], "the seed must carry at least one evidence chain"
    for run_id, chain in seed["chains"].items():
        assert verify_chain(chain) == [], f"seed chain {run_id!r} must verify clean"


def test_seed_chain_carries_the_denied_git_push_record():
    seed = cockpit_demo_seed.seed()
    chain = seed["chains"]["gate-push-refusal"]
    denied = [r for r in chain if r.get("classification") == "denied"]
    assert denied, "the push-refusal chain must carry a denied runtime_agent_action"
    record = denied[0]
    assert record["record_type"] == "runtime_agent_action"
    assert record["mutation_class"] == "deploy"
    assert "git push" in record["tool"] or "git push" in record["target"]
    assert "G2.007.2" in record["decision_reason"]


def test_snapshot_evidence_section_reports_verified_chains():
    snapshot = _demo_snapshot()
    evidence = snapshot["evidence"]
    assert "gate-push-refusal" in evidence
    for run_id, summary in evidence.items():
        assert summary["verified"] is True, f"demo chain {run_id!r} must verify"
        assert summary["record_count"] >= 1


# --- the seed is schema-true (panes + scopes validate against L1 schemas) ----

def test_seed_panes_are_schema_true():
    seed = cockpit_demo_seed.seed()
    assert len(seed["panes"]) >= 6
    for pane in seed["panes"]:
        errors = validate_with_schema(
            pane,
            "schemas/pane-registry.schema.yaml",
            Path("cockpit-demo-seed"),
            code="test_pane_schema",
            contract="docs/operations/PANE_REGISTRY_PROTOCOL.md",
        )
        assert not errors, [e.format() for e in errors]


def test_seed_scopes_are_schema_true():
    seed = cockpit_demo_seed.seed()
    for scope in seed["scopes"]:
        errors = validate_with_schema(
            scope,
            "schemas/scope.schema.yaml",
            Path("cockpit-demo-seed"),
            code="test_scope_schema",
            contract="docs/contracts/scope.md",
        )
        assert not errors, [e.format() for e in errors]


# --- the stage column is the canon skin (no third vocabulary) ----------------

def test_stage_column_derives_via_phase_by_state():
    snapshot = _demo_snapshot()
    for card in snapshot["board"]["cards"]:
        assert card["phase"] == coordination.PHASE_BY_STATE[card["state"]]
        assert card["board_label"] == coordination.BOARD_BY_STATE[card["state"]]


# --- live loaders: narrow seams over real fixture roots ----------------------

def _write_live_fixtures(tmp_path: Path) -> tuple[Path, Path, Path]:
    state_root = tmp_path / "state"
    (state_root / "scopes").mkdir(parents=True)
    scope = {
        "kind": "scope-record",
        "record_type": "scope",
        "schema_version": "1",
        "scope_id": "live-probe",
        "intent": "probe the live loaders",
        "mutation_class": "docs",
    }
    (state_root / "scopes" / "live-probe.scope.yaml").write_text(
        yaml.safe_dump(scope, sort_keys=True), encoding="utf-8"
    )
    seed = cockpit_demo_seed.seed()
    chain_doc = {
        "kind": "runtime-evidence-chain",
        "record_type": "runtime_evidence_chain",
        "schema_version": "1",
        "records": seed["chains"]["gate-push-refusal"],
    }
    (state_root / "gate-push-refusal.runtime-evidence.yaml").write_text(
        yaml.safe_dump(chain_doc, sort_keys=True), encoding="utf-8"
    )
    ledger_root = tmp_path / "ledger"
    panes_dir = ledger_root / "panes" / "ce-live-seat"
    panes_dir.mkdir(parents=True)
    (panes_dir / "live-lane.yaml").write_text(
        yaml.safe_dump(seed["panes"][0], sort_keys=True), encoding="utf-8"
    )
    obs_dir = tmp_path / "observations"
    obs_dir.mkdir()
    (obs_dir / "observations.ndjson").write_text(
        '{"hookEventName":"Stop","observedAt":"2026-07-01T09:00:00Z",'
        '"advisory":true,"blocking":false}\n',
        encoding="utf-8",
    )
    return state_root, ledger_root, obs_dir


def test_snapshot_from_roots_loads_live_fixtures(tmp_path):
    state_root, ledger_root, obs_dir = _write_live_fixtures(tmp_path)
    snapshot = cockpit_readmodel.snapshot_from_roots(
        state_root,
        ledger_root=ledger_root,
        observations_dir=obs_dir,
        environ={},
    )
    assert snapshot["availability"]["seats"] == "ok"
    assert snapshot["availability"]["board"] == "ok"
    assert snapshot["availability"]["refusals"] == "ok"
    assert [c["scope_id"] for c in snapshot["board"]["cards"]] == ["live-probe"]
    assert len(snapshot["seats"]) == 1
    assert snapshot["evidence"]["gate-push-refusal"]["verified"] is True
    assert len(snapshot["refusals"]["entries"]) == 1


def test_ledger_root_resolves_from_environment(tmp_path):
    state_root, ledger_root, _obs = _write_live_fixtures(tmp_path)
    snapshot = cockpit_readmodel.snapshot_from_roots(
        state_root,
        environ={cockpit_readmodel.LEDGER_ROOT_ENV: str(ledger_root)},
    )
    assert snapshot["availability"]["seats"] == "ok"
    assert len(snapshot["seats"]) == 1


def test_absent_sources_degrade_honestly_never_fabricate(tmp_path):
    snapshot = cockpit_readmodel.snapshot_from_roots(tmp_path / "nowhere", environ={})
    assert snapshot["availability"]["seats"] == "unavailable"
    assert snapshot["availability"]["refusals"] == "unavailable"
    assert snapshot["seats"] == []
    assert snapshot["board"]["cards"] == []
    assert snapshot["refusals"]["entries"] == []


def test_watch_paths_lists_only_existing_roots(tmp_path):
    state_root, ledger_root, obs_dir = _write_live_fixtures(tmp_path)
    paths = cockpit_readmodel.watch_paths(
        state_root, ledger_root=ledger_root, observations_dir=obs_dir, environ={}
    )
    assert str(state_root) in paths
    assert str(ledger_root) in paths
    assert str(obs_dir) in paths
    assert cockpit_readmodel.watch_paths(tmp_path / "missing", environ={}) == []
