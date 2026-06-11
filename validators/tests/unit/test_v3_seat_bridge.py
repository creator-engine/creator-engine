"""v3.1-G1 — unit tests for the assemble→spawn bridge (``v3_seat_bridge``).

Every subprocess edge (``ce launch``, ``tmux send-keys``) is faked through the
``runner=`` seam: zero live tmux / claude / systemd. The headline invariant — the
bridge imports NO v1 module — is asserted directly off the module AST, making the
subprocess+DATA design choice a tested contract rather than a convention.
"""
from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import _versions as ver
from creator_engine_validator import coordination, v3_seat_bridge


# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------

_FIXED_NOW = datetime(2026, 6, 11, 9, 30, 0, tzinfo=timezone.utc)


def _plan(scope_id: str = "demo-scope") -> coordination.DispatchPlan:
    return coordination.DispatchPlan(
        scope_id=scope_id,
        runtime_policy={"spend_envelopes": [{"scope": "run", "cap_usd": 5}]},
        mutation_class="docs",
        scope_ratification={"approver_ref": "a" * 64, "ratified_scope_sha": "b" * 64},
    )


class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _launch_json(*, spawned=True, pane="%3", resource_bound=None):
    return json.dumps(
        {
            "plan": {"session": "s", "window": "drive", "resource_bound": resource_bound},
            "spawned": spawned,
            "attached": False,
            "terminal": (
                {"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": pane}
                if pane
                else None
            ),
            "resource_confirm": None,
        }
    )


class _RecordingRunner:
    """Captures argv; returns a scripted result (default: a clean spawn)."""

    def __init__(self, result: _FakeCompleted | None = None):
        self.calls: list[list[str]] = []
        self._result = result or _FakeCompleted(stdout=_launch_json())

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        return self._result


# ---------------------------------------------------------------------------
# The boundary invariant — AST proves zero v1 imports
# ---------------------------------------------------------------------------


def test_bridge_module_imports_no_v1_module():
    src = Path(v3_seat_bridge.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    referenced: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                referenced.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                referenced.add(node.module.split(".")[0])
            # `from . import coordination` imports sibling modules by alias name.
            if node.level and node.module is None:
                for alias in node.names:
                    referenced.add(alias.name.split(".")[0])
    crossed = referenced & ver.V1_RUNTIME
    assert crossed == set(), f"bridge must import no v1 module, found: {sorted(crossed)}"


def test_bridge_is_classified_v3():
    assert ver.classify("v3_seat_bridge") == ver.V3
    assert "v3_seat_bridge" in ver.V3_RUNTIME


# ---------------------------------------------------------------------------
# materialize_dispatch
# ---------------------------------------------------------------------------


def test_materialize_writes_record_policy_and_brief(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    assert rec.run_id == "run-demo-scope-20260611T093000Z"
    ddir = tmp_path / "dispatches" / rec.run_id
    assert ddir.is_dir()
    assert (ddir / "dispatch.yaml").is_file()
    assert (ddir / "runtime-policy.yaml").is_file()
    assert (ddir / "brief.md").is_file()

    data = yaml.safe_load((ddir / "dispatch.yaml").read_text(encoding="utf-8"))
    assert data["kind"] == "dispatch-record"
    assert data["record_type"] == "dispatch"
    assert data["schema_version"] == "1"
    assert data["scope_id"] == "demo-scope"
    assert data["run_id"] == rec.run_id
    assert data["mutation_class"] == "docs"
    assert data["harness"] == "claude"
    assert data["unattended"] is True
    # Pre-spawn: launch evidence is unstamped.
    assert data["terminal"] is None and data["spawned_at"] is None
    # The merged policy is written for the v1 leg to read AS DATA.
    policy = yaml.safe_load((ddir / "runtime-policy.yaml").read_text(encoding="utf-8"))
    assert policy["spend_envelopes"] == [{"scope": "run", "cap_usd": 5}]


def test_materialize_record_is_value_free(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    blob = json.dumps(rec.data).lower()
    for forbidden in ("token", "secret", "password", "credential", "@", "http"):
        assert forbidden not in blob, f"value-free record leaked {forbidden!r}"
    # Only opaque 64-hex digests carry the ratification.
    assert rec.data["scope_ratification"]["approver_ref"] == "a" * 64


def test_materialized_record_conforms_to_schema(tmp_path):
    import jsonschema  # vendored dev dep

    schema = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "schemas" / "dispatch-record.schema.yaml")
        .read_text(encoding="utf-8")
    )
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    # pre-spawn: terminal/resource_bound/spawned_at are null — must validate
    jsonschema.validate(rec.data, schema)
    # post-spawn: stamped terminal + resource_bound — must still validate
    v3_seat_bridge.spawn_seat(rec, runner=_RecordingRunner(), ce_exe="/fake/ce", now=_FIXED_NOW)
    jsonschema.validate(rec.data, schema)


def test_materialize_unattended_flag_recorded(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(
        _plan(), tmp_path, unattended=False, now=_FIXED_NOW
    )
    assert rec.data["unattended"] is False


def test_brief_names_the_scope_artifact_and_outcome_vocab(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    brief = (rec.dispatch_dir / "brief.md").read_text(encoding="utf-8")
    assert "scopes/demo-scope.scope.yaml" in brief
    assert "cev3 collect demo-scope" in brief
    for outcome in v3_seat_bridge.OUTCOME_VOCABULARY:
        assert outcome in brief


# ---------------------------------------------------------------------------
# spawn_seat — the v1 subprocess leg + stamping
# ---------------------------------------------------------------------------


def test_spawn_seat_stamps_terminal_and_resource_bound(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    runner = _RecordingRunner(
        _FakeCompleted(stdout=_launch_json(pane="%7", resource_bound={"unit": "ce-seat-x"}))
    )
    result = v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce", now=_FIXED_NOW)
    assert result.terminal["pane_id"] == "%7"
    assert result.resource_bound == {"unit": "ce-seat-x"}
    # Stamped back into dispatch.yaml on disk.
    data = yaml.safe_load((rec.dispatch_dir / "dispatch.yaml").read_text(encoding="utf-8"))
    assert data["terminal"]["pane_id"] == "%7"
    assert data["resource_bound"] == {"unit": "ce-seat-x"}
    assert data["spawned_at"] == "20260611T093000Z"


def test_spawn_seat_invokes_ce_launch_json_with_policy(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    runner = _RecordingRunner()
    v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce")
    argv = runner.calls[0]
    assert argv[:2] == ["/fake/ce", "launch"]
    assert "--json" in argv
    assert "--session" in argv and rec.session in argv
    assert "--runtime-policy" in argv
    assert rec.runtime_policy_ref in argv
    assert "--mcp-config" in argv and rec.mcp_config_ref in argv


def test_unattended_spawn_appends_skip_permissions(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    runner = _RecordingRunner()
    v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce")
    assert "--claude-arg=--dangerously-skip-permissions" in runner.calls[0]


def test_attended_spawn_omits_skip_permissions(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(
        _plan(), tmp_path, unattended=False, now=_FIXED_NOW
    )
    runner = _RecordingRunner()
    v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce")
    assert "--claude-arg=--dangerously-skip-permissions" not in runner.calls[0]


def test_spawn_seat_fail_closed_on_nonzero_exit(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    runner = _RecordingRunner(_FakeCompleted(returncode=1, stderr="CC-D-6 refused"))
    with pytest.raises(v3_seat_bridge.SpawnRefused) as exc:
        v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce")
    assert "CC-D-6 refused" in str(exc.value)
    # No half-stamp on refusal.
    data = yaml.safe_load((rec.dispatch_dir / "dispatch.yaml").read_text(encoding="utf-8"))
    assert data["terminal"] is None


def test_spawn_seat_fail_closed_on_unparsable_json(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    runner = _RecordingRunner(_FakeCompleted(stdout="not json"))
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce")


def test_spawn_seat_fail_closed_when_not_spawned(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    runner = _RecordingRunner(_FakeCompleted(stdout=_launch_json(spawned=False, pane=None)))
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce")


def test_resolve_ce_exe_refuses_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(v3_seat_bridge.sys, "executable", str(tmp_path / "py"))
    monkeypatch.setattr(v3_seat_bridge.shutil, "which", lambda _name: None)
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge._resolve_ce_exe(None)


# ---------------------------------------------------------------------------
# seed_brief — pointer-only tmux seed
# ---------------------------------------------------------------------------


def test_seed_brief_sends_pointer_line_then_enter(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    v3_seat_bridge.spawn_seat(rec, runner=_RecordingRunner(), ce_exe="/fake/ce")
    seed = _RecordingRunner()
    v3_seat_bridge.seed_brief(rec, runner=seed)
    assert len(seed.calls) == 2
    literal, enter = seed.calls
    assert literal[:5] == ["tmux", "send-keys", "-t", rec.pane_id, "-l"]
    assert literal[5] == f"Read {rec.brief_ref} and execute under it."
    assert enter == ["tmux", "send-keys", "-t", rec.pane_id, "Enter"]
    # The brief BODY / markers never leak into the seed text (the monitor lesson).
    assert "Goal" not in literal[5] and "Done-when" not in literal[5]


def test_seed_brief_refuses_without_pane(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.seed_brief(rec, runner=_RecordingRunner())
