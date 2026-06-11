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


def test_mark_spawn_failed_stamps_value_free_failure(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    out = v3_seat_bridge.mark_spawn_failed(
        rec, v3_seat_bridge.SpawnRefused("CC-D-6 refused: unconfirmed hook-pack"), now=_FIXED_NOW
    )
    assert out is rec
    assert rec.data["spawn_failed_at"] == "20260611T093000Z"
    assert "CC-D-6 refused" in rec.data["spawn_failure_reason"]
    # fail-closed: a refused spawn is NOT shaped like a live run
    assert rec.data["terminal"] is None and rec.data["spawned_at"] is None
    # persisted to disk
    on_disk = yaml.safe_load((rec.dispatch_dir / "dispatch.yaml").read_text(encoding="utf-8"))
    assert on_disk["spawn_failed_at"] == "20260611T093000Z"
    # value-free: no credential/host/account leaked into the stamp
    blob = json.dumps(rec.data).lower()
    for forbidden in ("token", "secret", "password", "credential", "@", "http"):
        assert forbidden not in blob


def test_failure_stamped_record_conforms_to_schema(tmp_path):
    import jsonschema  # vendored dev dep

    schema = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "schemas" / "dispatch-record.schema.yaml")
        .read_text(encoding="utf-8")
    )
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    v3_seat_bridge.mark_spawn_failed(rec, "CC-D-6 refused", now=_FIXED_NOW)
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


# ===========================================================================
# v3.1-G2b — the reviewer-venue leg
# ===========================================================================
import hashlib as _hashlib

_REVIEWER_LOGIN = "ubuntuaws745-cmyk"
_PR_HEAD = "d" * 40


def _author_dispatch(tmp_path, scope_id="rate-limit-login"):
    """Materialize a spawned author dispatch dict (the input to the review leg)."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(scope_id), tmp_path, now=_FIXED_NOW)
    rec.data["terminal"] = {"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%3"}
    rec.data["spawned_at"] = "20260611T093000Z"
    v3_seat_bridge._write_record(rec)
    return rec.data


class _ReviewRunner:
    """Routes the venue subprocess chain (pco-allocate / lane launch --json / tmux seed)."""

    def __init__(self, *, pco_rc=0, launch_rc=0, pane="%7", launch_stdout=None):
        self.calls = []
        self.pco_rc = pco_rc
        self.launch_rc = launch_rc
        self.pane = pane
        self.launch_stdout = launch_stdout

    def __call__(self, argv, **kw):
        argv = list(argv)
        self.calls.append({"argv": argv, "kw": kw})
        if "pco-allocate" in argv:
            return _FakeCompleted(returncode=self.pco_rc, stderr="pco boom" if self.pco_rc else "")
        if "launch" in argv and "lane" in argv:
            if self.launch_rc:
                return _FakeCompleted(returncode=self.launch_rc, stderr="lane boom")
            stdout = self.launch_stdout if self.launch_stdout is not None else json.dumps({
                "pane_path": "/venue/panes/x.yaml",
                "record": {"terminal": {
                    "kind": "tmux", "session_id": "$5", "window_id": "@6", "pane_id": self.pane}},
            })
            return _FakeCompleted(returncode=0, stdout=stdout)
        if "send-keys" in argv:
            return _FakeCompleted(returncode=0)
        raise AssertionError(f"unexpected argv: {argv}")  # pragma: no cover

    def argv_for(self, needle):
        for c in self.calls:
            if needle in c["argv"]:
                return c["argv"]
        return None


def _envelope_schema():
    return yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "schemas" / "reviewer-authority-envelope.schema.yaml")
        .read_text(encoding="utf-8")
    )


def _dispatch_schema():
    return yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "schemas" / "dispatch-record.schema.yaml")
        .read_text(encoding="utf-8")
    )


def test_compose_reviewer_envelope_is_schema_valid(tmp_path):
    import jsonschema
    path = v3_seat_bridge.compose_reviewer_envelope(
        tmp_path, scope_id="rate-limit-login", pr_number=7, head_sha=_PR_HEAD,
        actor=_REVIEWER_LOGIN, ratified_prompt_sha="b" * 64, now=_FIXED_NOW,
    )
    env = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    jsonschema.validate(env, _envelope_schema())
    rae = env["reviewer_authority_envelope"]
    assert rae["mechanic"] == "pr_review" and rae["pr_number"] == 7
    assert rae["actor"] == _REVIEWER_LOGIN and rae["ratified_prompt_sha"] == "b" * 64
    assert rae["envelope_id"].startswith("rva-rev-rate-limit-login-")


def test_materialize_review_dispatch_role_and_review_of(tmp_path):
    import jsonschema
    author = _author_dispatch(tmp_path)
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD,
        now=_FIXED_NOW,
    )
    assert rec.data["role"] == "reviewer"
    assert rec.data["review_of"]["author_run_id"] == author["run_id"]
    assert rec.data["review_of"]["pr_number"] == 7
    assert Path(rec.data["review_of"]["envelope_ref"]).is_file()
    # the review dispatch record validates against the (additively-extended) schema
    jsonschema.validate(rec.data, _dispatch_schema())


def test_review_dispatch_record_is_value_free(tmp_path):
    author = _author_dispatch(tmp_path)
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD,
        now=_FIXED_NOW,
    )
    # the reviewer LOGIN lives in the envelope FILE, never in the dispatch RECORD bytes
    record_bytes = rec.dispatch_path.read_text(encoding="utf-8")
    assert _REVIEWER_LOGIN not in record_bytes
    envelope_bytes = Path(rec.data["review_of"]["envelope_ref"]).read_text(encoding="utf-8")
    assert _REVIEWER_LOGIN in envelope_bytes  # the schema requires the login here


def test_reviewer_brief_names_pr_and_collect_handoff(tmp_path):
    author = _author_dispatch(tmp_path)
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD,
        now=_FIXED_NOW,
    )
    brief = Path(rec.brief_ref).read_text(encoding="utf-8")
    assert "PR #7" in brief
    assert "gh pr review 7" in brief
    assert "--outcome review_submitted" in brief


def test_spawn_review_venue_runs_pco_then_lane_launch_then_seed(tmp_path):
    author = _author_dispatch(tmp_path)
    venue_root = tmp_path / "venues"
    venue_root.mkdir()
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD,
        now=_FIXED_NOW,
    )
    runner = _ReviewRunner(pane="%7")
    result = v3_seat_bridge.spawn_review_venue(
        rec, controller_id="ctrl-x", venue_root=venue_root, ledger_root=tmp_path / "ledger",
        runner=runner, validator_exe="creator-engine-validator", ce_exe="ce", now=_FIXED_NOW,
    )
    assert result.terminal["pane_id"] == "%7"
    # pco-allocate ran with cwd OUTSIDE the repo (the venue zone)
    pco = runner.argv_for("pco-allocate")
    assert pco is not None and "--no-write-authority" in pco
    pco_call = next(c for c in runner.calls if "pco-allocate" in c["argv"])
    assert pco_call["kw"].get("cwd") == str(venue_root)
    # lane launch bound the reviewer envelope on a distinct reviewer venue, JSON-mode
    launch = runner.argv_for("launch")
    assert "--role" in launch and launch[launch.index("--role") + 1] == "reviewer"
    assert "--lane-kind" in launch and launch[launch.index("--lane-kind") + 1] == "review"
    assert "--reviewer-authority-ref" in launch and "--json" in launch
    # the terminal got stamped + the brief got seeded
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["terminal"]["pane_id"] == "%7" and drec["spawned_at"]
    assert runner.argv_for("send-keys") is not None


def test_spawn_review_venue_fail_closed_on_pco_refusal(tmp_path):
    author = _author_dispatch(tmp_path)
    venue_root = tmp_path / "venues"; venue_root.mkdir()
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD, now=_FIXED_NOW)
    runner = _ReviewRunner(pco_rc=1)
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.spawn_review_venue(
            rec, controller_id="ctrl-x", venue_root=venue_root, ledger_root=tmp_path / "l",
            runner=runner, validator_exe="creator-engine-validator", ce_exe="ce", now=_FIXED_NOW)
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"] and drec["terminal"] is None
    assert runner.argv_for("launch") is None  # never reached lane launch


def test_spawn_review_venue_fail_closed_on_lane_launch_refusal(tmp_path):
    author = _author_dispatch(tmp_path)
    venue_root = tmp_path / "venues"; venue_root.mkdir()
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD, now=_FIXED_NOW)
    runner = _ReviewRunner(launch_rc=1)
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.spawn_review_venue(
            rec, controller_id="ctrl-x", venue_root=venue_root, ledger_root=tmp_path / "l",
            runner=runner, validator_exe="creator-engine-validator", ce_exe="ce", now=_FIXED_NOW)
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"] and drec["terminal"] is None
    assert runner.argv_for("send-keys") is None  # never seeded a half-venue


def test_spawn_review_venue_fail_closed_on_no_pane(tmp_path):
    author = _author_dispatch(tmp_path)
    venue_root = tmp_path / "venues"; venue_root.mkdir()
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD, now=_FIXED_NOW)
    runner = _ReviewRunner(launch_stdout=json.dumps({"pane_path": "x", "record": {"terminal": {}}}))
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.spawn_review_venue(
            rec, controller_id="ctrl-x", venue_root=venue_root, ledger_root=tmp_path / "l",
            runner=runner, validator_exe="creator-engine-validator", ce_exe="ce", now=_FIXED_NOW)
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"]
