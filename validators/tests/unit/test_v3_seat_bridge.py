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
from creator_engine_validator import claude_launch_spec as v3_launch_spec
from creator_engine_validator import coordination, v3_seat_bridge


# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------

_FIXED_NOW = datetime(2026, 6, 11, 9, 30, 0, tzinfo=timezone.utc)

_FIXED_SESSION_ID = "00000000-0000-4000-8000-000000000000"


@pytest.fixture(autouse=True)
def _drive_posture_cwd(tmp_path, monkeypatch):
    """Default cwd = ``tmp_path`` (an ancestor of the dispatch dir) — the drive posture.

    ``cev3 drive --spawn`` runs from the state-root's repo, an ancestor of the dispatch
    dir, so ``spawn_seat`` composes a CE-owned RELATIVE ``--mcp-config`` (CC-D-7, D3-fix).
    Tests that probe the escape refusal chdir elsewhere in their body (last write wins).
    """
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _spawn_binaries_present(monkeypatch):
    """Default: the spawn-preflight binaries (``tmux`` + the harness) resolve on PATH.

    The G2f PATH preflight calls the real ``shutil.which``; in the CI envelope the
    harness binary is absent, so without this the spawn-path tests would all trip the
    preflight. Tests that exercise the refusal override ``which`` to return ``None``.
    """
    monkeypatch.setattr(
        v3_seat_bridge.shutil, "which", lambda name: f"/usr/bin/{name}"
    )


class _StubClock:
    """A monotonic clock + sleep stub: each ``sleep`` advances the clock deterministically."""

    def __init__(self, *, step: float = 0.5):
        self.t = 0.0
        self.step = step

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds if seconds else self.step


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


def _launch_json(*, spawned=True, pane="%3", resource_bound=None, events_ref=None):
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
            "events_ref": events_ref,
        }
    )


class _RecordingRunner:
    """Captures argv; returns a scripted result (default: a clean spawn).

    The seed readiness-poll (``tmux display-message``) is routed to a ready
    foreground command (``pane_command``, default ``claude``) so seed tests don't
    spin; everything else returns the scripted ``_result``.
    """

    def __init__(self, result: _FakeCompleted | None = None, *, pane_command: str = "claude"):
        self.calls: list[list[str]] = []
        self._result = result or _FakeCompleted(stdout=_launch_json())
        self._pane_command = pane_command

    def __call__(self, argv, **kw):
        argv = list(argv)
        self.calls.append(argv)
        if "display-message" in argv:
            return _FakeCompleted(stdout=self._pane_command)
        if "capture-pane" in argv:
            # input box empty → the seed line submitted on the first Enter
            return _FakeCompleted(stdout="(harness ready)\n")
        return self._result

    @property
    def send_keys_calls(self) -> list[list[str]]:
        return [c for c in self.calls if "send-keys" in c]


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


def test_spawn_seat_stamps_events_ref(tmp_path):
    # ce-ops#26: the bridge stamps the seat's lifecycle events surface (a value-free
    # path ref) from the v1 LaunchResult into dispatch.yaml; absent ⇒ key omitted.
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    ev = str(rec.dispatch_dir / "events.jsonl")
    runner = _RecordingRunner(_FakeCompleted(stdout=_launch_json(events_ref=ev)))
    v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce", now=_FIXED_NOW)
    data = yaml.safe_load((rec.dispatch_dir / "dispatch.yaml").read_text(encoding="utf-8"))
    assert data["events_ref"] == ev
    # and the record still conforms to the (additive-optional) dispatch schema
    import jsonschema

    schema = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "schemas" / "dispatch-record.schema.yaml")
        .read_text(encoding="utf-8")
    )
    jsonschema.validate(data, schema)


def test_spawn_seat_omits_events_ref_when_absent(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    runner = _RecordingRunner(_FakeCompleted(stdout=_launch_json(events_ref=None)))
    v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce", now=_FIXED_NOW)
    data = yaml.safe_load((rec.dispatch_dir / "dispatch.yaml").read_text(encoding="utf-8"))
    assert "events_ref" not in data


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
    assert "--mcp-config" in argv


def test_materialize_codex_dispatch_records_managed_pretooluse_boundary(tmp_path):
    import jsonschema

    rec = v3_seat_bridge.materialize_dispatch(
        _plan(), tmp_path, harness="codex", now=_FIXED_NOW
    )
    assert rec.data["harness"] == "codex"
    assert rec.data["harness_boundary"] == "codex_managed_pretooluse"
    assert "harness_session_id" not in rec.data
    jsonschema.validate(rec.data, _dispatch_schema())


def test_spawn_seat_codex_argv_omits_claude_only_args_and_stamps_bypass(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(
        _plan(), tmp_path, harness="codex", now=_FIXED_NOW
    )
    launch = json.dumps({
        "plan": {"session": "s", "window": "drive", "resource_bound": None, "codex_bypass_mode": "config"},
        "spawned": True,
        "attached": False,
        "terminal": {"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%3"},
    })
    runner = _RecordingRunner(_FakeCompleted(stdout=launch))
    v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce", now=_FIXED_NOW)
    argv = runner.calls[0]
    assert argv[:4] == ["/fake/ce", "launch", "--harness", "codex"]
    assert "--mcp-config" not in argv
    assert not any(arg.startswith("--claude-arg") for arg in argv)
    data = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert data["codex_bypass_mode"] == "config"


def _codex_meta(path: Path, *, session_id: str, cwd: Path) -> Path:
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


def test_codex_transcript_locator_stamps_session_id_and_ref(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(
        _plan(), tmp_path, harness="codex", now=_FIXED_NOW
    )
    sessions = tmp_path / "codex-sessions"
    before = v3_seat_bridge.snapshot_codex_transcripts(sessions)
    path = _codex_meta(
        sessions / "2026" / "06" / "12" / "session.jsonl",
        session_id="codex-session-1",
        cwd=tmp_path,
    )
    v3_seat_bridge.stamp_codex_transcript_locator(
        rec,
        before=before,
        launched_cwd=tmp_path,
        sessions_root=sessions,
        clock=lambda: 0.0,
        sleep=lambda *_: None,
        now=_FIXED_NOW,
    )
    data = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert data["harness_session_id"] == "codex-session-1"
    assert data["transcript_ref"] == str(path.resolve())


def test_codex_transcript_locator_missing_fail_closes(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(
        _plan(), tmp_path, harness="codex", now=_FIXED_NOW
    )
    clk = _StubClock()
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.stamp_codex_transcript_locator(
            rec,
            before=set(),
            launched_cwd=tmp_path,
            sessions_root=tmp_path / "empty-sessions",
            timeout_s=1.0,
            poll_interval_s=0.5,
            clock=clk.now,
            sleep=clk.sleep,
            now=_FIXED_NOW,
        )
    data = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert data["spawn_failed_at"]
    assert data["terminal"] is None and data["spawned_at"] is None


def test_codex_transcript_locator_settles_before_first_poll(tmp_path):
    """ce-ops#56: a bounded settle precedes the FIRST poll, so a codex that writes its
    session file slightly late (the cold-start race) still resolves on the first look —
    no spurious refusal. The settle being the FIRST sleep, with resolution then needing
    NO poll-interval sleep, is the settle-then-resolve contract."""
    rec = v3_seat_bridge.materialize_dispatch(
        _plan(), tmp_path, harness="codex", now=_FIXED_NOW
    )
    sessions = tmp_path / "codex-sessions"
    before = v3_seat_bridge.snapshot_codex_transcripts(sessions)
    target = sessions / "2026" / "06" / "13" / "session.jsonl"
    sleeps: list[float] = []

    def _sleep(seconds: float) -> None:
        # codex finally writes its session file DURING the settle window (the first sleep)
        sleeps.append(seconds)
        if len(sleeps) == 1:
            _codex_meta(target, session_id="codex-late", cwd=tmp_path)

    v3_seat_bridge.stamp_codex_transcript_locator(
        rec,
        before=before,
        launched_cwd=tmp_path,
        sessions_root=sessions,
        clock=lambda: 0.0,  # deadline never trips → isolates the settle behavior
        sleep=_sleep,
        now=_FIXED_NOW,
    )
    data = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert data["harness_session_id"] == "codex-late"
    assert data["transcript_ref"] == str(target.resolve())
    # exactly one sleep — the settle — and it equals the settle window: settle precedes
    # the first poll, which then resolves (without the settle the first poll would miss).
    assert sleeps == [v3_seat_bridge.CODEX_TRANSCRIPT_SETTLE_S]


def test_codex_transcript_locator_settle_capped_at_deadline(tmp_path):
    """ce-ops#56: the settle is bounded by the remaining budget — it never sleeps past the
    deadline, so the total wait stays within ``timeout_s`` even on a tiny budget."""
    rec = v3_seat_bridge.materialize_dispatch(
        _plan(), tmp_path, harness="codex", now=_FIXED_NOW
    )
    clk = _StubClock()
    sleeps: list[float] = []

    def _sleep(s: float) -> None:
        sleeps.append(s)
        clk.sleep(s)  # advance the clock so the bounded loop terminates

    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.stamp_codex_transcript_locator(
            rec,
            before=set(),
            launched_cwd=tmp_path,
            sessions_root=tmp_path / "empty-sessions",
            timeout_s=1.0,
            poll_interval_s=0.5,
            settle_s=5.0,  # larger than the whole budget → must be capped at 1.0
            clock=clk.now,
            sleep=_sleep,
            now=_FIXED_NOW,
        )
    assert sleeps and sleeps[0] == 1.0  # settle capped at the deadline, not 5.0


def test_spawn_argv_mcp_config_is_relative_record_stays_absolute(tmp_path):
    """D3-fix (CC-D-7): in the drive posture (cwd is an ancestor of the dispatch dir),
    the spawn argv's ``--mcp-config`` value is a CE-owned RELATIVE path, while the
    dispatch RECORD keeps the ABSOLUTE ``mcp_config_ref`` (D3 conserved)."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    runner = _RecordingRunner()
    v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce")
    argv = runner.calls[0]
    mcp_arg = argv[argv.index("--mcp-config") + 1]
    # argv value is relative + does not escape — CC-D-7 (_is_ce_owned_mcp_path) accepts it
    assert not Path(mcp_arg).is_absolute()
    assert not mcp_arg.startswith("..")
    assert v3_launch_spec._is_ce_owned_mcp_path(mcp_arg)
    # the RECORD keeps the absolute ref (D3 conserved — the record is for readers)
    assert Path(rec.mcp_config_ref).is_absolute()
    assert rec.mcp_config_ref not in argv
    # and they point at the same file
    assert (Path.cwd() / mcp_arg).resolve() == Path(rec.mcp_config_ref).resolve()


def test_spawn_seat_refuses_when_mcp_relpath_escapes_cwd(tmp_path, monkeypatch):
    """D3-fix: if the launch cwd is NOT an ancestor of the dispatch dir, the relative
    ``--mcp-config`` would escape with ``..`` (CC-D-7 would refuse) → fail-closed
    SpawnRefused with NO spawn side effect (no ``ce launch`` invoked)."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path / "state", now=_FIXED_NOW)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)  # overrides the drive-posture fixture
    runner = _RecordingRunner()
    with pytest.raises(v3_seat_bridge.SpawnRefused) as exc:
        v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce", now=_FIXED_NOW)
    assert "CC-D-7" in str(exc.value)
    # fail-closed: no `ce launch` ran (refused before the spawn side effect)
    assert runner.calls == []
    # the refusal is stamped value-free; the record is NOT shaped like a live run
    data = yaml.safe_load((rec.dispatch_dir / "dispatch.yaml").read_text(encoding="utf-8"))
    assert data["terminal"] is None and data["spawned_at"] is None
    assert data["spawn_failed_at"] is not None


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
    v3_seat_bridge.seed_brief(rec, runner=seed, sleep=lambda *_: None, clock=lambda: 0.0)
    sends = seed.send_keys_calls
    assert len(sends) == 2
    literal, enter = sends
    assert literal[:5] == ["tmux", "send-keys", "-t", rec.pane_id, "-l"]
    assert literal[5] == f"Read {rec.brief_ref} and execute under it."
    assert enter == ["tmux", "send-keys", "-t", rec.pane_id, "Enter"]
    # The brief BODY / markers never leak into the seed text (the monitor lesson).
    assert "Goal" not in literal[5] and "Done-when" not in literal[5]


def test_seed_brief_refuses_without_pane(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.seed_brief(rec, runner=_RecordingRunner())


# ---------------------------------------------------------------------------
# D5 (G1-followups) — PATH preflight + Seed-Enter readiness poll + send-keys rc
# ---------------------------------------------------------------------------


def test_spawn_refuses_when_tmux_or_claude_absent(tmp_path, monkeypatch):
    """PATH preflight: a missing spawn-critical binary fail-closes BEFORE the launch
    leg, and the refused attempt is conserved (mark_spawn_failed), never half-spawned."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    monkeypatch.setattr(
        v3_seat_bridge.shutil, "which",
        lambda name: None if name == "claude" else f"/usr/bin/{name}",
    )
    runner = _RecordingRunner()
    with pytest.raises(v3_seat_bridge.SpawnRefused) as exc:
        v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce", now=_FIXED_NOW)
    assert "claude" in str(exc.value)
    assert runner.calls == []  # never reached the launch leg
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"] and drec["terminal"] is None


def test_seed_brief_polls_until_harness_ready(tmp_path):
    """Readiness poll: the pointer line is held until the pane foreground leaves the
    shell (the harness REPL is up) — a fake runner returns shell, then claude."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    v3_seat_bridge.spawn_seat(rec, runner=_RecordingRunner(), ce_exe="/fake/ce")

    foreground = iter(["bash", "bash", "claude"])

    class _PollRunner:
        def __init__(self):
            self.calls = []

        def __call__(self, argv, **kw):
            argv = list(argv)
            self.calls.append(argv)
            if "display-message" in argv:
                return _FakeCompleted(stdout=next(foreground))
            return _FakeCompleted()

    runner = _PollRunner()
    clk = _StubClock()
    v3_seat_bridge.seed_brief(
        rec, runner=runner, clock=clk.now, sleep=clk.sleep, poll_interval_s=0.5,
    )
    polls = [c for c in runner.calls if "display-message" in c]
    sends = [c for c in runner.calls if "send-keys" in c]
    assert len(polls) == 3  # shell, shell, then ready
    assert len(sends) == 2  # only seeded AFTER ready


def test_seed_brief_fail_closed_on_readiness_timeout(tmp_path):
    """Readiness timeout: never-ready pane → mark_spawn_failed, pane CONSERVED, no seed."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    v3_seat_bridge.spawn_seat(rec, runner=_RecordingRunner(), ce_exe="/fake/ce")

    class _StuckRunner:
        def __init__(self):
            self.calls = []

        def __call__(self, argv, **kw):
            argv = list(argv)
            self.calls.append(argv)
            if "display-message" in argv:
                return _FakeCompleted(stdout="bash")  # never leaves the shell
            return _FakeCompleted()

    runner = _StuckRunner()
    clk = _StubClock()
    with pytest.raises(v3_seat_bridge.SpawnRefused) as exc:
        v3_seat_bridge.seed_brief(
            rec, runner=runner, clock=clk.now, sleep=clk.sleep,
            readiness_timeout_s=2.0, poll_interval_s=0.5, now=_FIXED_NOW,
        )
    assert "readiness" in str(exc.value).lower()
    assert not any("send-keys" in c for c in runner.calls)  # never seeded
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"]
    # pane CONSERVED for autopsy (the terminal stamp is not cleared)
    assert drec["terminal"]["pane_id"] == rec.pane_id


def test_seed_brief_fail_closed_on_send_keys_failure(tmp_path):
    """A non-zero send-keys rc (a dead pane that silently absorbs the seed) fail-closes."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    v3_seat_bridge.spawn_seat(rec, runner=_RecordingRunner(), ce_exe="/fake/ce")

    class _SendFailRunner:
        def __call__(self, argv, **kw):
            argv = list(argv)
            if "display-message" in argv:
                return _FakeCompleted(stdout="claude")
            if "send-keys" in argv:
                return _FakeCompleted(returncode=1, stderr="can't find pane")
            return _FakeCompleted()

    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.seed_brief(rec, runner=_SendFailRunner(), now=_FIXED_NOW)
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"]


class _SubmitRunner:
    """display-message ready; ``capture-pane`` reports the seed line as still PENDING in the
    input box for ``pending_captures`` captures, then CLEARED — the S8 submit-lost simulation."""

    def __init__(self, line: str, *, pending_captures: int):
        self.line = line
        self.pending_captures = pending_captures
        self.captures = 0
        self.enters = 0
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kw):
        argv = list(argv)
        self.calls.append(argv)
        if "display-message" in argv:
            return _FakeCompleted(stdout="claude")
        if "capture-pane" in argv:
            self.captures += 1
            if self.captures <= self.pending_captures:
                return _FakeCompleted(stdout=f"prompt> \n{self.line}\n")  # still in the box
            return _FakeCompleted(stdout="prompt> \n(box cleared)\n")  # submitted
        if "send-keys" in argv:
            if "Enter" in argv:
                self.enters += 1
            return _FakeCompleted(returncode=0)
        raise AssertionError(f"unexpected argv: {argv}")  # pragma: no cover


def test_seed_brief_resends_enter_until_submitted(tmp_path):
    """S8 submit-guard: the first Enter leaves the line pending (swallowed); a second Enter
    clears the input box → submitted. A >=1s settle precedes the first Enter."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    v3_seat_bridge.spawn_seat(rec, runner=_RecordingRunner(), ce_exe="/fake/ce")
    runner = _SubmitRunner(v3_seat_bridge._seed_line(rec), pending_captures=1)
    sleeps: list[float] = []
    v3_seat_bridge.seed_brief(
        rec, runner=runner, clock=lambda: 0.0, sleep=sleeps.append,
    )
    assert runner.enters == 2  # first Enter swallowed, second submitted
    # the proven manual cadence: a >=1s settle precedes the first Enter
    assert sleeps and sleeps[0] >= 1.0
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert "spawn_failed_at" not in drec  # a clean submit, not a failure


def test_seed_brief_fail_closed_when_submit_never_clears(tmp_path):
    """S8 submit-guard: the line never leaves the input box → after bounded re-sends, fail
    closed (mark_spawn_failed) with the pane CONSERVED for autopsy."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    v3_seat_bridge.spawn_seat(rec, runner=_RecordingRunner(), ce_exe="/fake/ce")
    runner = _SubmitRunner(v3_seat_bridge._seed_line(rec), pending_captures=999)
    with pytest.raises(v3_seat_bridge.SpawnRefused) as exc:
        v3_seat_bridge.seed_brief(
            rec, runner=runner, clock=lambda: 0.0, sleep=lambda *_: None, now=_FIXED_NOW,
        )
    assert "swallowed the submit" in str(exc.value)
    assert runner.enters == v3_seat_bridge.SEED_SUBMIT_MAX_ATTEMPTS  # bounded re-sends
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"]
    # pane CONSERVED for autopsy (the terminal stamp is not cleared)
    assert drec["terminal"]["pane_id"] == rec.pane_id


# ---------------------------------------------------------------------------
# esc-26 — seat-sentinel wrapper readiness: the #211 wrapper runs the harness as a
# CHILD of `sh`, so the pane foreground stays a shell forever. Readiness must also
# accept a non-shell child probed via `ps -o comm= --ppid <pane_pid>` (same runner seam).
# ---------------------------------------------------------------------------


class _WrapperReadyRunner:
    """The #211 wrapper shape: pane FOREGROUND (``#{pane_current_command}``) stays ``sh``,
    but the pane PID's (``#{pane_pid}``) child tree carries a non-shell harness child
    (``ps`` reports ``claude``). The pane is therefore ready one level down. ``capture-pane``
    reports an empty input box (the seed submits on the first Enter)."""

    def __init__(self, *, child_comm: str = "claude", pane_pid: str = "4242"):
        self.calls: list[list[str]] = []
        self._child_comm = child_comm
        self._pane_pid = pane_pid

    def __call__(self, argv, **kw):
        argv = list(argv)
        self.calls.append(argv)
        if "display-message" in argv:
            if "#{pane_pid}" in argv:
                return _FakeCompleted(stdout=self._pane_pid)
            return _FakeCompleted(stdout="sh")  # foreground never leaves the shell
        if argv and argv[0] == "ps":
            # the wrapper's harness child, exactly one level under the pane pid
            return _FakeCompleted(stdout=f"{self._child_comm}\n")
        if "capture-pane" in argv:
            return _FakeCompleted(stdout="(harness ready)\n")
        return _FakeCompleted()

    @property
    def ps_calls(self) -> list[list[str]]:
        return [c for c in self.calls if c and c[0] == "ps"]


def test_seed_brief_ready_when_wrapper_harness_child_present(tmp_path):
    """Wrapper shape (esc-26): foreground stays ``sh`` but ``ps`` shows a non-shell child
    (``claude``) under the pane pid → ready; the spawn proceeds (the seed is sent)."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    v3_seat_bridge.spawn_seat(rec, runner=_RecordingRunner(), ce_exe="/fake/ce")

    runner = _WrapperReadyRunner()
    clk = _StubClock()
    v3_seat_bridge.seed_brief(
        rec, runner=runner, clock=clk.now, sleep=clk.sleep, poll_interval_s=0.5,
    )
    # the ps probe rode the injectable runner seam against the pane pid
    assert runner.ps_calls, "wrapper readiness must probe the child tree via ps"
    assert runner.ps_calls[0] == ["ps", "-o", "comm=", "--ppid", "4242"]
    # ready was reached → the seed line was delivered (literal + Enter)
    assert any("send-keys" in c for c in runner.calls)


def test_seed_brief_bare_launch_ready_without_ps_probe(tmp_path):
    """Bare-launch shape conserved (esc-26): when the foreground LEAVES the shell set the
    pane is ready immediately — no ``ps`` child probe is needed or issued."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    v3_seat_bridge.spawn_seat(rec, runner=_RecordingRunner(), ce_exe="/fake/ce")

    class _BareLaunchRunner:
        def __init__(self):
            self.calls: list[list[str]] = []

        def __call__(self, argv, **kw):
            argv = list(argv)
            self.calls.append(argv)
            if "display-message" in argv:
                return _FakeCompleted(stdout="claude")  # foreground already left the shell
            if "capture-pane" in argv:
                return _FakeCompleted(stdout="(harness ready)\n")
            return _FakeCompleted()

    runner = _BareLaunchRunner()
    clk = _StubClock()
    v3_seat_bridge.seed_brief(
        rec, runner=runner, clock=clk.now, sleep=clk.sleep, poll_interval_s=0.5,
    )
    assert not any(c and c[0] == "ps" for c in runner.calls), (
        "a non-shell foreground is ready on its own — the ps child probe must not fire"
    )
    # no pane-pid read either: the cheaper foreground check short-circuits readiness
    assert not any("#{pane_pid}" in c for c in runner.calls)


def test_seed_brief_timeout_when_only_shell_children(tmp_path):
    """Foreground ``sh`` AND only shell / no children for the whole window → timeout →
    refusal IDENTICAL to today (mark_spawn_failed by the caller; pane CONSERVED; no seed)."""
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    v3_seat_bridge.spawn_seat(rec, runner=_RecordingRunner(), ce_exe="/fake/ce")

    class _ShellChildrenRunner:
        def __init__(self):
            self.calls: list[list[str]] = []

        def __call__(self, argv, **kw):
            argv = list(argv)
            self.calls.append(argv)
            if "display-message" in argv:
                if "#{pane_pid}" in argv:
                    return _FakeCompleted(stdout="4242")
                return _FakeCompleted(stdout="sh")  # foreground never leaves the shell
            if argv and argv[0] == "ps":
                return _FakeCompleted(stdout="bash\nsh\n")  # children are ALL shells
            return _FakeCompleted()

    runner = _ShellChildrenRunner()
    clk = _StubClock()
    with pytest.raises(v3_seat_bridge.SpawnRefused) as exc:
        v3_seat_bridge.seed_brief(
            rec, runner=runner, clock=clk.now, sleep=clk.sleep,
            readiness_timeout_s=2.0, poll_interval_s=0.5, now=_FIXED_NOW,
        )
    assert "readiness" in str(exc.value).lower()
    assert any(c and c[0] == "ps" for c in runner.calls)  # the child tree was probed
    assert not any("send-keys" in c for c in runner.calls)  # never seeded
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"]
    # pane CONSERVED for autopsy (the terminal stamp is not cleared) — no spawn side effect
    assert drec["terminal"]["pane_id"] == rec.pane_id


def test_pane_has_nonshell_child_rides_runner_seam_no_live_subprocess(tmp_path):
    """The child probe issues ``ps -o comm= --ppid <pane_pid>`` through the injectable
    runner ONLY — CI exercises a fake, never a live subprocess; an empty pid short-circuits."""
    calls: list[list[str]] = []

    def runner(argv, **kw):
        calls.append(list(argv))
        if "display-message" in argv and "#{pane_pid}" in argv:
            return _FakeCompleted(stdout="7777")
        if list(argv)[:1] == ["ps"]:
            return _FakeCompleted(stdout="node\n")
        return _FakeCompleted()

    assert v3_seat_bridge._pane_has_nonshell_child("%9", runner) is True
    assert ["ps", "-o", "comm=", "--ppid", "7777"] in calls

    # an empty pane pid never reaches ps (fail-closed, no spurious probe)
    calls.clear()
    assert v3_seat_bridge._pane_has_nonshell_child(
        "%9", lambda argv, **kw: _FakeCompleted(stdout="")
    ) is False


# ---------------------------------------------------------------------------
# D6 (F9) — harness_session_id minted at materialize, stamped onto the spawn argv
# ---------------------------------------------------------------------------


def test_harness_session_id_minted_and_schema_valid(tmp_path):
    import jsonschema

    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    sid = rec.data["harness_session_id"]
    assert sid and rec.harness_session_id == sid
    jsonschema.validate(rec.data, _dispatch_schema())


def test_spawn_seat_stamps_session_id_on_claude_arg(tmp_path):
    rec = v3_seat_bridge.materialize_dispatch(
        _plan(), tmp_path, now=_FIXED_NOW, harness_session_id=_FIXED_SESSION_ID
    )
    runner = _RecordingRunner()
    v3_seat_bridge.spawn_seat(rec, runner=runner, ce_exe="/fake/ce")
    assert f"--claude-arg=--session-id={_FIXED_SESSION_ID}" in runner.calls[0]


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

    def __init__(self, *, pco_rc=0, launch_rc=0, pane="%7", launch_stdout=None,
                 gh_login=_REVIEWER_LOGIN, gh_rc=0,
                 repo_root="/repo/secondary-wt", repo_root_rc=0):
        self.calls = []
        self.pco_rc = pco_rc
        self.launch_rc = launch_rc
        self.pane = pane
        self.launch_stdout = launch_stdout
        # ce-ops#89: the step-0.5 `git -C <ledger> rev-parse --show-toplevel` probe that
        # resolves the (non-root) repo_root pco-allocate runs `git worktree add` from.
        self.repo_root = repo_root
        self.repo_root_rc = repo_root_rc
        # ce-ops#58: the step-2.5 gh-identity probe. Default = the envelope actor (the
        # happy path: venue login == actor); override to simulate the #218 wrong-login.
        self.gh_login = gh_login
        self.gh_rc = gh_rc

    def __call__(self, argv, **kw):
        argv = list(argv)
        self.calls.append({"argv": argv, "kw": kw})
        if "rev-parse" in argv:  # ce-ops#89: repo-root resolution probe
            return _FakeCompleted(
                returncode=self.repo_root_rc,
                stdout="" if self.repo_root_rc else f"{self.repo_root}\n",
                stderr="not a git repository" if self.repo_root_rc else "",
            )
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
        if "api" in argv and "user" in argv:  # ce-ops#58: `gh api user --jq .login`
            return _FakeCompleted(
                returncode=self.gh_rc,
                stdout="" if self.gh_rc else self.gh_login,
                stderr="gh boom" if self.gh_rc else "",
            )
        if "display-message" in argv:
            return _FakeCompleted(returncode=0, stdout="claude")  # ready immediately
        if "capture-pane" in argv:
            return _FakeCompleted(returncode=0, stdout="(box empty)\n")  # submit cleared
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


def test_review_run_id_satisfies_ledger_lane_and_lease_patterns(tmp_path):
    """Regression for the L7 live-drive HALT (esc-14-l7-venue-id-defect): the minted review
    run_id is fed to ``pco-allocate`` as the ledger lane id, and the derived lease id is
    ``lease-<lane>-<14-digit stamp>``. Both patterns are READ FROM the schemas (not hardcoded)
    so this guards the exact contract that fail-closed refused twice in the live drive."""
    import re

    schemas_dir = Path(__file__).resolve().parents[3] / "schemas"
    ledger = yaml.safe_load((schemas_dir / "active-work-ledger.schema.yaml").read_text(encoding="utf-8"))
    lane_pattern = ledger["properties"]["lane_id"]["pattern"]
    lease = yaml.safe_load((schemas_dir / "worktree-lease.schema.yaml").read_text(encoding="utf-8"))
    lease_pattern = lease["properties"]["lease_id"]["pattern"]

    # a representatively long scope id — the shape that overflowed the lease length bound before
    author = _author_dispatch(tmp_path, scope_id="b7-fleet-cost-meter")
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD,
        now=_FIXED_NOW,
    )
    run_id = rec.run_id
    assert re.match(lane_pattern, run_id), f"{run_id!r} violates lane pattern {lane_pattern!r}"
    lease_id = f"lease-{run_id}-{'0' * 14}"
    assert re.match(lease_pattern, lease_id), f"{lease_id!r} violates lease pattern {lease_pattern!r}"


def test_review_run_id_clamps_long_scope_id_within_lease_bound(tmp_path):
    """ce-ops#89 (PCO-020): for a scope_id long enough to overflow the naive
    ``rev-<scope>-<stamp>`` → ``lease-<lane>-<14>`` derivation past 64 chars, the
    minted run_id is clamped (hash-suffixed) so BOTH the lane and lease ids stay
    schema-valid — and the clamp is read from the live schema patterns."""
    import re

    schemas_dir = Path(__file__).resolve().parents[3] / "schemas"
    ledger = yaml.safe_load((schemas_dir / "active-work-ledger.schema.yaml").read_text(encoding="utf-8"))
    lane_pattern = ledger["properties"]["lane_id"]["pattern"]
    lease = yaml.safe_load((schemas_dir / "worktree-lease.schema.yaml").read_text(encoding="utf-8"))
    lease_pattern = lease["properties"]["lease_id"]["pattern"]

    # 40-char scope_id ⇒ naive lease_id would be 82 chars (overflow). The clamp MUST
    # bring it back inside the bound. pco derives lease_id with a 14-digit stamp, so
    # construct the worst case here too.
    long_scope = "b7-fleet-cost-meter-with-a-very-long-tail"  # 41 chars
    assert len(long_scope) > 22  # i.e. it genuinely overflows the naive form
    author = _author_dispatch(tmp_path, scope_id=long_scope)
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD,
        now=_FIXED_NOW,
    )
    run_id = rec.run_id
    lease_id = f"lease-{run_id}-{'9' * 14}"
    assert len(lease_id) <= 64, f"lease_id overflowed: {len(lease_id)} chars ({lease_id!r})"
    assert re.match(lane_pattern, run_id), f"{run_id!r} violates lane pattern {lane_pattern!r}"
    assert re.match(lease_pattern, lease_id), f"{lease_id!r} violates lease pattern {lease_pattern!r}"


def test_review_run_id_clamp_is_collision_free_for_distinct_long_scopes(tmp_path):
    """ce-ops#89: two DISTINCT long scope_ids that share a clipped prefix must still
    mint DISTINCT run_ids (the hash-suffix preserves uniqueness), and a given
    scope_id is deterministic for a fixed stamp."""
    stamp = "20260615T120000Z"
    shared_prefix = "scope-shared-prefix-aaaaaaaaaaaaaaaa"
    a = v3_seat_bridge._derive_review_run_id(shared_prefix + "-alpha-tail-distinct-A", stamp)
    b = v3_seat_bridge._derive_review_run_id(shared_prefix + "-alpha-tail-distinct-B", stamp)
    assert a != b, "clipped long scope_ids collided into the same lane id"
    # deterministic for a fixed (scope_id, stamp)
    again = v3_seat_bridge._derive_review_run_id(shared_prefix + "-alpha-tail-distinct-A", stamp)
    assert a == again
    # both stay within the lease budget
    for run_id in (a, b):
        assert len(f"lease-{run_id}-{'0' * 14}") <= 64
    # short scope_ids keep the readable, lossless form (no needless hashing)
    assert v3_seat_bridge._derive_review_run_id("short-scope", stamp) == f"rev-short-scope-{stamp.lower()}"


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
        sleep=lambda *_: None, clock=lambda: 0.0,
    )
    assert result.terminal["pane_id"] == "%7"
    # pco-allocate ran with cwd OUTSIDE the repo (the venue zone)
    pco = runner.argv_for("pco-allocate")
    assert pco is not None and "--no-write-authority" in pco
    pco_call = next(c for c in runner.calls if "pco-allocate" in c["argv"])
    assert pco_call["kw"].get("cwd") == str(venue_root)
    # ce-ops#89: pco carries an explicit, resolved --repo-root (the ledger's git
    # toplevel) so `git worktree add` targets a real repo and no longer exits 128
    # against the non-git venue zone.
    assert "--repo-root" in pco and pco[pco.index("--repo-root") + 1] == "/repo/secondary-wt"
    # lane launch bound the reviewer envelope on a distinct reviewer venue, JSON-mode
    launch = runner.argv_for("launch")
    assert "--role" in launch and launch[launch.index("--role") + 1] == "reviewer"
    assert "--lane-kind" in launch and launch[launch.index("--lane-kind") + 1] == "review"
    assert "--reviewer-authority-ref" in launch and "--json" in launch
    # the venue pane is cwd'd IN its allocated worktree — without --worktree-path the relative
    # --mcp-config fails under --strict-mcp-config and the venue claude dies at birth (L7 cwd defect)
    venue_worktree = str(venue_root / rec.run_id)
    assert "--repo-root" in launch and launch[launch.index("--repo-root") + 1] == venue_worktree
    assert "--worktree-path" in launch and launch[launch.index("--worktree-path") + 1] == venue_worktree
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


def test_spawn_review_venue_fail_closed_on_unresolved_repo_root(tmp_path):
    """ce-ops#89: if the ledger-root is not inside a git worktree, repo-root cannot
    be resolved — the venue MUST fail closed BEFORE pco-allocate (no half-venue),
    stamping the dispatch, rather than letting `git worktree add` exit 128 downstream."""
    author = _author_dispatch(tmp_path)
    venue_root = tmp_path / "venues"; venue_root.mkdir()
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD, now=_FIXED_NOW)
    runner = _ReviewRunner(repo_root_rc=1)  # `git rev-parse --show-toplevel` fails
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.spawn_review_venue(
            rec, controller_id="ctrl-x", venue_root=venue_root, ledger_root=tmp_path / "l",
            runner=runner, validator_exe="creator-engine-validator", ce_exe="ce", now=_FIXED_NOW)
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"] and drec["terminal"] is None
    assert runner.argv_for("pco-allocate") is None  # refused before any pco side effect


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


# ---------------------------------------------------------------------------
# D1 (F3) — unattended reviewer venues + D3 (F5) absolute refs + D6 + D2 pass-through
# ---------------------------------------------------------------------------


def _spawn_venue(tmp_path, *, unattended=True, seat_env_file=None, runner=None):
    author = _author_dispatch(tmp_path)
    venue_root = tmp_path / "venues"
    venue_root.mkdir(exist_ok=True)
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD,
        unattended=unattended, now=_FIXED_NOW, harness_session_id=_FIXED_SESSION_ID,
    )
    runner = runner or _ReviewRunner(pane="%7")
    v3_seat_bridge.spawn_review_venue(
        rec, controller_id="ctrl-x", venue_root=venue_root, ledger_root=tmp_path / "ledger",
        seat_env_file=seat_env_file, runner=runner,
        validator_exe="creator-engine-validator", ce_exe="ce", now=_FIXED_NOW,
        sleep=lambda *_: None, clock=lambda: 0.0,
    )
    return rec, runner


def test_unattended_venue_appends_skip_permissions(tmp_path):
    rec, runner = _spawn_venue(tmp_path, unattended=True)
    assert rec.data["unattended"] is True
    launch = runner.argv_for("launch")
    assert "--claude-arg=--dangerously-skip-permissions" in launch


def test_attended_venue_omits_skip_permissions(tmp_path):
    rec, runner = _spawn_venue(tmp_path, unattended=False)
    assert rec.data["unattended"] is False
    launch = runner.argv_for("launch")
    assert "--claude-arg=--dangerously-skip-permissions" not in launch


def test_venue_spawn_stamps_session_id_on_claude_arg(tmp_path):
    _rec, runner = _spawn_venue(tmp_path)
    launch = runner.argv_for("launch")
    assert f"--claude-arg=--session-id={_FIXED_SESSION_ID}" in launch


def test_review_refs_are_absolute_from_relative_root(tmp_path, monkeypatch):
    """D3: a RELATIVE --root yields ABSOLUTE envelope_ref / brief_ref / seeded line, so
    the in-venue Ring-1 hook (resolving from the venue worktree cwd) can find them."""
    monkeypatch.chdir(tmp_path)
    author = _author_dispatch(Path("state"))
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, "state", reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD,
        now=_FIXED_NOW,
    )
    envelope_ref = rec.data["review_of"]["envelope_ref"]
    assert Path(envelope_ref).is_absolute(), envelope_ref
    assert Path(rec.brief_ref).is_absolute(), rec.brief_ref
    # the seeded pointer line names the absolute brief path
    assert v3_seat_bridge._seed_line(rec).endswith("and execute under it.")
    assert str(Path(rec.brief_ref)) in v3_seat_bridge._seed_line(rec)


def test_author_refs_are_absolute_from_relative_root(tmp_path, monkeypatch):
    """D3 author-side symmetry: the same absolutization protects any author seat whose
    pane cwd is not the orchestrator's."""
    monkeypatch.chdir(tmp_path)
    rec = v3_seat_bridge.materialize_dispatch(_plan(), "state", now=_FIXED_NOW)
    assert Path(rec.brief_ref).is_absolute()
    assert Path(rec.runtime_policy_ref).is_absolute()
    brief = Path(rec.brief_ref).read_text(encoding="utf-8")
    # the brief's scope/evidence pointers are absolute too
    assert str(tmp_path.resolve()) in brief


def test_venue_seat_env_file_threaded_and_recorded(tmp_path):
    """D2 bridge pass-through: --seat-env-file rides the launch argv; the dispatch records
    only the PATH ref (value-free), never the credential value."""
    env_file = tmp_path / "reviewer.env"
    env_file.write_text("GITHUB_REVIEWR_TOKEN=ghp_secret\n", encoding="utf-8")
    rec, runner = _spawn_venue(tmp_path, seat_env_file=env_file)
    launch = runner.argv_for("launch")
    assert "--seat-env-file" in launch
    assert launch[launch.index("--seat-env-file") + 1] == str(env_file)
    # the dispatch record carries the PATH ref, never the secret value
    record_bytes = rec.dispatch_path.read_text(encoding="utf-8")
    assert rec.data["seat_env_file_ref"] == str(env_file)
    assert "ghp_secret" not in record_bytes


def test_venue_without_seat_env_file_omits_flag(tmp_path):
    _rec, runner = _spawn_venue(tmp_path, seat_env_file=None)
    launch = runner.argv_for("launch")
    assert "--seat-env-file" not in launch


# ===========================================================================
# ce-ops#43 — the conserved-evidence marker on the dispatch record (§3.2). The
# reaper treats `conserve: true` as an absolute teardown stop; the additive
# OPTIONAL fields must validate against the (closed) dispatch schema, and a
# record WITHOUT them must still validate (old records unaffected).
# ===========================================================================


def test_conserve_marker_fields_validate_against_dispatch_schema(tmp_path):
    import jsonschema

    schema = _dispatch_schema()
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    # additive-optional: a record without the marker still validates (unchanged)
    jsonschema.validate(rec.data, schema)
    # with the conserved-evidence marker it also validates
    rec.data["conserve"] = True
    rec.data["conserve_reason"] = "refused dispatch — conserved as evidence"
    rec.data["conserved_at"] = "2026-06-13T12:00:00Z"
    jsonschema.validate(rec.data, schema)


def test_conserve_marker_unknown_field_still_rejected(tmp_path):
    import jsonschema

    schema = _dispatch_schema()
    rec = v3_seat_bridge.materialize_dispatch(_plan(), tmp_path, now=_FIXED_NOW)
    rec.data["conserve"] = True
    rec.data["conserve_typo_field"] = "x"  # the schema stays closed (unevaluatedProperties:false)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(rec.data, schema)


# ---------------------------------------------------------------------------
# ce-ops#58 (F-class, #218 lineage) — fail-closed step-2.5 gh-identity guard
# ---------------------------------------------------------------------------


def _review_rec(tmp_path):
    author = _author_dispatch(tmp_path)
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, tmp_path, reviewer_actor=_REVIEWER_LOGIN, pr_number=7, head_sha=_PR_HEAD,
        now=_FIXED_NOW,
    )
    venue_root = tmp_path / "venues"; venue_root.mkdir(exist_ok=True)
    return rec, venue_root


def test_gh_identity_probe_runs_between_launch_and_seed(tmp_path):
    """The matching-identity path probes `gh api user --jq .login`, finds the envelope
    actor, and proceeds to seed — the probe sits between lane launch and the seed."""
    rec, venue_root = _review_rec(tmp_path)
    runner = _ReviewRunner(pane="%7")  # default gh_login == _REVIEWER_LOGIN (the actor)
    v3_seat_bridge.spawn_review_venue(
        rec, controller_id="ctrl-x", venue_root=venue_root, ledger_root=tmp_path / "ledger",
        runner=runner, validator_exe="creator-engine-validator", ce_exe="ce", now=_FIXED_NOW,
        sleep=lambda *_: None, clock=lambda: 0.0,
    )
    gh = runner.argv_for("api")
    assert gh is not None and gh[:5] == ["gh", "api", "user", "--jq", ".login"]
    # identity matched → the venue seeded (send-keys reached)
    assert runner.argv_for("send-keys") is not None


def test_gh_identity_probe_sources_seat_env_when_present(tmp_path):
    """ce-ops#58: when a seat-env file is supplied the probe sources it the SAME way the
    review will (`sh -c '<seat-env wrap>' … <file> gh api user …`), so the probe sees the
    review's identity by construction — the secret never transits the probe argv."""
    rec, venue_root = _review_rec(tmp_path)
    env_file = tmp_path / "reviewer.env"
    env_file.write_text("GH_TOKEN=ghp_secret\nGITHUB_TOKEN=ghp_secret\n", encoding="utf-8")
    runner = _ReviewRunner(pane="%7")
    v3_seat_bridge.spawn_review_venue(
        rec, controller_id="ctrl-x", venue_root=venue_root, ledger_root=tmp_path / "ledger",
        seat_env_file=env_file, runner=runner, validator_exe="creator-engine-validator",
        ce_exe="ce", now=_FIXED_NOW, sleep=lambda *_: None, clock=lambda: 0.0,
    )
    gh = runner.argv_for("api")
    assert gh[:2] == ["sh", "-c"]
    assert gh[2] == v3_seat_bridge._SEAT_ENV_WRAP_SCRIPT
    assert str(env_file) in gh
    assert gh[-5:] == ["gh", "api", "user", "--jq", ".login"]
    # the secret value never lands in the probe argv (only the file PATH does)
    assert "ghp_secret" not in " ".join(gh)


def test_spawn_review_venue_fail_closed_on_gh_identity_mismatch(tmp_path):
    """The #218 leak: venue gh-login != envelope actor (ambient wrong identity) → fail
    closed BEFORE seeding; the failure is conserved and value-free (no login in record)."""
    rec, venue_root = _review_rec(tmp_path)
    runner = _ReviewRunner(pane="%7", gh_login="chmod735")  # the author, NOT the reviewer
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.spawn_review_venue(
            rec, controller_id="ctrl-x", venue_root=venue_root, ledger_root=tmp_path / "l",
            runner=runner, validator_exe="creator-engine-validator", ce_exe="ce", now=_FIXED_NOW,
            sleep=lambda *_: None, clock=lambda: 0.0,
        )
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"]
    assert runner.argv_for("send-keys") is None  # never seeded a wrong-identity venue
    # value-free: neither the wrong login nor the reviewer login lands in the record bytes
    record_bytes = rec.dispatch_path.read_text(encoding="utf-8")
    assert "chmod735" not in record_bytes and _REVIEWER_LOGIN not in record_bytes


def test_spawn_review_venue_fail_closed_on_gh_probe_error(tmp_path):
    """A failed identity probe (gh non-zero) is fail-closed — never an unverified seed."""
    rec, venue_root = _review_rec(tmp_path)
    runner = _ReviewRunner(pane="%7", gh_rc=1)
    with pytest.raises(v3_seat_bridge.SpawnRefused):
        v3_seat_bridge.spawn_review_venue(
            rec, controller_id="ctrl-x", venue_root=venue_root, ledger_root=tmp_path / "l",
            runner=runner, validator_exe="creator-engine-validator", ce_exe="ce", now=_FIXED_NOW,
            sleep=lambda *_: None, clock=lambda: 0.0,
        )
    drec = yaml.safe_load(rec.dispatch_path.read_text(encoding="utf-8"))
    assert drec["spawn_failed_at"]
    assert runner.argv_for("send-keys") is None
