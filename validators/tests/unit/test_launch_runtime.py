"""RV1-063 — ``ce launch`` / ``ce hud`` launcher runtime (strict TDD).

The launcher is the canonical deterministic Controller-seat launcher (DP-2 = B).
``ce hud`` is an alias/seam label for the *same* launcher — not a CE-native TUI.
tmux is replaced by a test double so dry-run planning, attach/resume, and the
hidden-continuation refusal can be exercised without a real tmux process or a
live provider login.
"""
from __future__ import annotations

import hashlib
import json
import shlex
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_bootstrap, brain_runtime, launch_runtime
from creator_engine_validator.tmux_adapter import TmuxPane


def _write_brain_ledger(state_root: Path, *, object_value: str = "ready") -> None:
    result = brain_runtime.assert_claim(
        assertion_id="brain-assertion-launch-runtime-0001",
        claim={"subject": "controller", "predicate": "bootstrap", "object": object_value},
        scope="global",
        evidence_ref="validators/tests/unit/test_launch_runtime.py#brain-ledger",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    path = brain_runtime.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brain_runtime.serialize_ledger([result.record]), encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolate_seat_state(tmp_path, monkeypatch):
    """Per-test isolation of the seat-state surface (ce-ops#53 xdist flake fix).

    A ``launch`` without an explicit ``repo_root`` defaults the state root to the
    CWD and writes ``sentinel-wrapper.sh`` to ``./.ce/state/dispatches/<seat_id>/``
    — a path keyed only by session/window. The many ``session="s"`` tests here
    therefore all target the *same* shared path; under xdist (`-n auto`) two run
    concurrently on different workers and one overwrites the other's wrapper
    mid-read → flaky ``StopIteration`` on the ``code=$?`` scan. chdir each test
    into its own unique ``tmp_path`` so the default state root is per-test unique.
    Tests that pass an explicit absolute ``repo_root=tmp_path`` are unaffected.
    """
    monkeypatch.chdir(tmp_path)
    _write_brain_ledger(tmp_path / ".ce" / "state")


def _inner_argv(result):
    """Recover the EXACT governed/bounded argv embedded in the ce-ops#26 wrapper.

    The pane command is now ``["/bin/sh", <wrapper>]``; the seat command runs
    FOREGROUND inside the wrapper (the line just before ``code=$?``).
    """
    wrapper = Path(result.events_ref).parent / "sentinel-wrapper.sh"
    lines = wrapper.read_text().splitlines()
    idx = next(i for i, line in enumerate(lines) if line == "code=$?")
    return shlex.split(lines[idx - 1])


def _brain_payload(result):
    ref = Path(result.plan.brain_bootstrap_ref)
    assert ref.is_file()
    return json.loads(ref.read_text(encoding="utf-8"))


def _assert_foreman_charter_and_worker_spawn(payload):
    operating_mode = payload["operating_mode"]
    charter = operating_mode["foreman_charter"]
    worker_spawn = operating_mode["capabilities"]["worker_spawn"]
    assert charter["id"] == brain_bootstrap.FOREMAN_CHARTER_ID
    assert charter["mandatory"] is True
    assert charter["enforcement"] == "launcher-injected-non-optional"
    assert "delegate-substantive-implementation-review-and-build-work" in charter["directives"]
    assert worker_spawn["id"] == brain_bootstrap.WORKER_SPAWN_CAPABILITY_ID
    assert worker_spawn["mandatory"] is True
    assert worker_spawn["enforcement"] == "launcher-injected-non-optional"
    assert worker_spawn["surface"]["cli"] == "ce worker spawn"
    assert worker_spawn["surface"]["module"] == "creator_engine_validator.worker_spawn"


def _fake_codex(tmp_path: Path, monkeypatch) -> Path:
    codex = tmp_path / "bin" / "codex"
    codex.parent.mkdir()
    codex.write_text("#!/bin/sh\n", encoding="utf-8")
    codex.chmod(0o755)
    monkeypatch.setenv(launch_runtime.codex_launch_spec.CODEX_HARNESS_ENV, str(codex))
    return codex


class FakeAdapter:
    kind = "tmux"

    def __init__(self, *, available: bool = True, sessions: set[str] | None = None):
        self._available = available
        self._sessions = set(sessions or set())
        self.spawned: list[tuple[str, str, list[str]]] = []

    def is_available(self) -> bool:
        return self._available

    def session_exists(self, session: str) -> bool:
        return session in self._sessions

    def ensure_pane(self, *, session, window, command):
        self.spawned.append((session, window, list(command)))
        self._sessions.add(session)
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3", pane_tty="/dev/pts/7", pane_pid=999)


class PinningAdapter(FakeAdapter):
    def __init__(self, *, pane_cwd: str | None = None):
        super().__init__()
        self.pane_cwd = pane_cwd
        self.pinned: dict | None = None

    def ensure_pane(self, *, session, window, command, cwd=None, env=None):
        self.pinned = {
            "session": session,
            "window": window,
            "command": list(command),
            "cwd": cwd,
            "env": dict(env or {}),
        }
        self._sessions.add(session)
        return TmuxPane(
            session_id="$1",
            window_id="@2",
            pane_id="%3",
            pane_tty="/dev/pts/7",
            pane_pid=999,
            pane_cwd=self.pane_cwd,
        )


class Exit127Adapter(FakeAdapter):
    def ensure_pane(self, *, session, window, command):
        pane = super().ensure_pane(session=session, window=window, command=command)
        events = Path(command[1]).parent / "events.jsonl"
        events.write_text(
            json.dumps({"event": "launched", "seat_id": "exec-fail--controller"}) + "\n"
            + json.dumps({"event": "exited", "seat_id": "exec-fail--controller", "exit_code": 127}) + "\n",
            encoding="utf-8",
        )
        return pane


# ---------------------------------------------------------------------------
# Deterministic planning + hud alias
# ---------------------------------------------------------------------------


def test_plan_launch_is_deterministic_and_visible():
    plan = launch_runtime.plan_launch(harness="claude")
    assert plan.mode == "launch"
    assert plan.visibility == "operator_visible"
    assert plan.harness == "claude"
    assert plan.command[0] == "claude"


def test_hud_is_an_alias_of_launch_not_a_native_tui():
    launch_plan = launch_runtime.plan_launch(harness="claude", session="s", window="w")
    hud_plan = launch_runtime.plan_launch(harness="claude", session="s", window="w", invoked_as="hud")
    assert hud_plan.invoked_as == "hud"
    assert hud_plan.alias_of == "launch"
    # Same launcher: identical session/window/command/visibility.
    assert hud_plan.session == launch_plan.session
    assert hud_plan.command == launch_plan.command
    assert hud_plan.visibility == "operator_visible"


def test_default_mcp_config_path_uses_ce_state_root():
    assert (
        launch_runtime._default_mcp_config_path("ce-controller")
        == ".ce/state/launch/ce-controller/mcp/ce-mcp.json"
    )


# ---------------------------------------------------------------------------
# Dry-run: no side effects, proves alias without a provider login
# ---------------------------------------------------------------------------


def test_dry_run_does_not_spawn():
    adapter = FakeAdapter()
    result = launch_runtime.launch(harness="claude", dry_run=True, tmux_adapter=adapter)
    assert result.plan.dry_run is True
    assert result.spawned is False
    assert adapter.spawned == []


def test_dry_run_writes_no_seat_lifecycle_record(tmp_path):
    adapter = FakeAdapter()
    ledger = tmp_path / ".hermes" / "active-work-ledger"
    result = launch_runtime.launch(
        harness="claude",
        dry_run=True,
        repo_root=tmp_path,
        ledger_root=ledger,
        tmux_adapter=adapter,
    )
    assert result.seat_record_ref is None
    assert result.seat_lifecycle_state is None
    assert not (ledger / "seats").exists()
    assert not (ledger / "seat-events").exists()


def test_dry_run_works_without_tmux_available():
    # Planning must not require a live tmux (or provider) — dry-run is pure.
    adapter = FakeAdapter(available=False)
    result = launch_runtime.launch(harness="claude", dry_run=True, tmux_adapter=adapter)
    assert result.plan.dry_run is True
    assert adapter.spawned == []


# ---------------------------------------------------------------------------
# Hidden-continuation refusal (no hidden fallback)
# ---------------------------------------------------------------------------


def test_launch_refuses_hidden_continuation():
    adapter = FakeAdapter()
    with pytest.raises(launch_runtime.HiddenContinuationRefused):
        launch_runtime.launch(harness="claude", allow_hidden=True, tmux_adapter=adapter)
    assert adapter.spawned == []


def test_launch_refuses_non_visible_terminal():
    adapter = FakeAdapter()
    with pytest.raises(launch_runtime.HiddenContinuationRefused):
        launch_runtime.launch(harness="claude", visible=False, tmux_adapter=adapter)
    assert adapter.spawned == []


# ---------------------------------------------------------------------------
# tmux availability + resume semantics
# ---------------------------------------------------------------------------


def test_launch_refuses_when_tmux_unavailable():
    adapter = FakeAdapter(available=False)
    with pytest.raises(launch_runtime.TmuxUnavailableError):
        launch_runtime.launch(harness="claude", tmux_adapter=adapter)
    assert adapter.spawned == []


def test_resume_refuses_missing_session():
    adapter = FakeAdapter(sessions=set())  # nothing to resume
    with pytest.raises(launch_runtime.ResumeTargetMissing):
        launch_runtime.launch(harness="claude", session="ce-controller", resume=True, tmux_adapter=adapter)
    assert adapter.spawned == []


def test_resume_attaches_existing_session():
    adapter = FakeAdapter(sessions={"ce-controller"})
    result = launch_runtime.launch(
        harness="claude", session="ce-controller", resume=True, tmux_adapter=adapter
    )
    assert result.plan.mode == "resume"
    assert result.attached is True
    assert result.spawned is False
    assert adapter.spawned == []


def test_launch_spawns_visible_controller_seat():
    adapter = FakeAdapter()
    result = launch_runtime.launch(harness="claude", session="ce-controller", tmux_adapter=adapter)
    assert result.spawned is True
    assert adapter.spawned, "controller seat should be spawned in a visible tmux pane"
    assert result.plan.visibility == "operator_visible"


def test_launch_pins_cwd_and_env_at_tmux_boundary(tmp_path):
    adapter = PinningAdapter(pane_cwd=str(tmp_path))
    result = launch_runtime.launch(
        harness="claude",
        session="pinned-seat",
        repo_root=tmp_path,
        tmux_adapter=adapter,
        launch_cwd=tmp_path,
        launch_env={"HOME": str(tmp_path / ".ce/state/workers/w/home"), "PATH": "/bin"},
    )

    assert result.spawned is True
    assert adapter.pinned is not None
    assert adapter.pinned["cwd"] == tmp_path
    assert adapter.pinned["env"] == {
        "HOME": str(tmp_path / ".ce/state/workers/w/home"),
        "PATH": "/bin",
    }


def test_launch_refuses_when_pinned_cwd_is_not_verified(tmp_path):
    adapter = PinningAdapter(pane_cwd=None)

    with pytest.raises(launch_runtime.TmuxPanePinningRefused):
        launch_runtime.launch(
            harness="claude",
            session="unpinned-seat",
            repo_root=tmp_path,
            tmux_adapter=adapter,
            launch_cwd=tmp_path,
            launch_env={"HOME": str(tmp_path / ".ce/state/workers/w/home")},
        )


def test_launch_refuses_missing_brain_ledger_before_spawn(tmp_path):
    repo = tmp_path / "missing-brain-repo"
    repo.mkdir()
    adapter = FakeAdapter()

    with pytest.raises(launch_runtime.BrainBootstrapLaunchRefused):
        launch_runtime.launch(harness="claude", repo_root=repo, tmux_adapter=adapter)

    assert adapter.spawned == []
    assert not (repo / ".ce" / "state" / "dispatches").exists()


def test_launch_refuses_tampered_brain_ledger_before_spawn(tmp_path):
    repo = tmp_path / "tampered-brain-repo"
    state_root = repo / ".ce" / "state"
    _write_brain_ledger(state_root)
    ledger = brain_runtime.ledger_path(state_root)
    ledger.write_text(ledger.read_text(encoding="utf-8").replace("ready", "tampered"), encoding="utf-8")
    adapter = FakeAdapter()

    with pytest.raises(launch_runtime.BrainBootstrapLaunchRefused):
        launch_runtime.launch(harness="claude", repo_root=repo, tmux_adapter=adapter)

    assert adapter.spawned == []
    assert not (repo / ".ce" / "state" / "dispatches").exists()


def test_launch_refuses_missing_foreman_dispatch_contract_before_spawn(monkeypatch, tmp_path):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime.brain_bootstrap, "FOREMAN_DISPATCH_CONTRACT", None)

    with pytest.raises(launch_runtime.BrainBootstrapLaunchRefused) as ei:
        launch_runtime.launch(
            harness="claude",
            session="missing-foreman-contract",
            repo_root=tmp_path,
            tmux_adapter=adapter,
        )

    assert "foreman_dispatch_contract must be a mapping" in str(ei.value)
    assert adapter.spawned == []
    assert not (tmp_path / ".ce" / "state" / "dispatches").exists()


def test_launch_refuses_malformed_foreman_dispatch_contract_before_spawn(monkeypatch, tmp_path):
    adapter = FakeAdapter()
    malformed = json.loads(json.dumps(launch_runtime.brain_bootstrap.FOREMAN_DISPATCH_CONTRACT))
    malformed["roles"]["reviewer"]["dispatch_surface"] = []
    monkeypatch.setattr(launch_runtime.brain_bootstrap, "FOREMAN_DISPATCH_CONTRACT", malformed)

    with pytest.raises(launch_runtime.BrainBootstrapLaunchRefused) as ei:
        launch_runtime.launch(
            harness="claude",
            session="malformed-foreman-contract",
            repo_root=tmp_path,
            tmux_adapter=adapter,
        )

    assert "roles.reviewer.dispatch_surface" in str(ei.value)
    assert adapter.spawned == []
    assert not (tmp_path / ".ce" / "state" / "dispatches").exists()


def test_launch_injects_brain_bootstrap_payload_ref(tmp_path):
    adapter = FakeAdapter()
    result = launch_runtime.launch(
        harness="claude",
        session="brain-seat",
        repo_root=tmp_path,
        tmux_adapter=adapter,
    )

    ref = Path(result.plan.brain_bootstrap_ref)
    assert ref.is_file()
    assert result.plan.brain_bootstrap_sha256 == hashlib.sha256(ref.read_bytes()).hexdigest()
    payload = _brain_payload(result)
    assert payload["kind"] == "brain-bootstrap-context"
    assert payload["context"]["role"] == "controller"
    assert payload["context"]["seat_class"] == "foreman"
    dispatch_contract = payload["operating_mode"]["foreman_dispatch_contract"]
    assert dispatch_contract["launch_pinned"] is True
    assert set(dispatch_contract["roles"]) == {
        "researcher",
        "implementer",
        "reviewer",
    }
    wrapper = (Path(result.events_ref).parent / "sentinel-wrapper.sh").read_text(encoding="utf-8")
    assert f"export CE_BRAIN_BOOTSTRAP_REF={shlex.quote(str(ref))}" in wrapper
    assert f"export CE_BRAIN_BOOTSTRAP_SHA256={result.plan.brain_bootstrap_sha256}" in wrapper


def test_controller_brain_bootstrap_adds_advisory_recall_when_available(tmp_path, monkeypatch):
    calls: dict[str, dict] = {}

    class Hydration:
        def __init__(self, context: str):
            self.context = context

        def to_dict(self):
            return {
                "context": self.context,
                "core_loaded": False,
                "core_path": None,
                "note": "fake recall hydration",
                "recall": [
                    {
                        "tier": "recall",
                        "source_path": "docs/company-brain.md",
                        "chunk_ref": "launch-runtime",
                        "content_hash": "abc123",
                        "as_of": "2026-06-28T00:00:00Z",
                        "verify_against": "docs/company-brain.md",
                    }
                ],
            }

    class Surface:
        def hydrate_session(self, context: str, **kwargs):
            calls["hydrate"] = {"context": context, **kwargs}
            return Hydration(context)

    def open_surface(**kwargs):
        calls["open_surface"] = kwargs
        return Surface()

    monkeypatch.setattr(launch_runtime.brain_recall_surface, "open_surface", open_surface)

    payload = launch_runtime._build_controller_brain_bootstrap(tmp_path)

    assert calls["open_surface"] == {
        "state_root": tmp_path / ".ce" / "state",
        "embedder_name": "vllm-openai",
    }
    assert calls["hydrate"]["top_k"] == 5
    assert calls["hydrate"]["allow_confidential_egress"] is False
    assert "role=controller" in calls["hydrate"]["context"]
    assert "seat_class=foreman" in calls["hydrate"]["context"]
    assert f"repo_root={tmp_path}" in calls["hydrate"]["context"]

    assert payload["knowledge_ssot"]["assertions"][0]["claim"]["object"] == "ready"
    assert payload["recall"]["advisory"] is True
    assert payload["recall"]["embedder"] == "vllm-openai"
    assert payload["recall"]["allow_confidential_egress"] is False
    assert payload["recall"]["recall"][0]["tier"] == "recall"


def test_controller_brain_bootstrap_falls_back_to_ssot_when_recall_unavailable(
    tmp_path, monkeypatch, caplog
):
    expected = brain_bootstrap.build_bootstrap_payload(
        state_root=tmp_path / ".ce" / "state",
        role=brain_bootstrap.DEFAULT_ROLE,
        seat_class=brain_bootstrap.DEFAULT_SEAT_CLASS,
    )

    def open_surface(**_kwargs):
        raise RuntimeError("vllm endpoint unavailable")

    monkeypatch.setattr(launch_runtime.brain_recall_surface, "open_surface", open_surface)
    caplog.set_level("WARNING", logger=launch_runtime.__name__)

    payload = launch_runtime._build_controller_brain_bootstrap(tmp_path)

    assert payload == expected
    assert "recall" not in payload
    assert "semantic recall hydration skipped" in caplog.text


@pytest.mark.parametrize("harness", ["claude", "hermes", "openclaw"])
def test_spawned_launch_injects_foreman_charter_and_worker_spawn_for_harnesses(
    tmp_path, harness
):
    result = launch_runtime.launch(
        harness=harness,
        session=f"charter-{harness}",
        repo_root=tmp_path,
        tmux_adapter=FakeAdapter(),
    )

    _assert_foreman_charter_and_worker_spawn(_brain_payload(result))


def test_codex_spawned_launch_injects_foreman_charter_and_worker_spawn(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    monkeypatch.setattr(launch_runtime, "_confirm_codex_managed_pack", lambda repo_root: True)
    _fake_codex(tmp_path, monkeypatch)

    result = launch_runtime.launch(
        harness="codex",
        session="charter-codex",
        repo_root=tmp_path,
        tmux_adapter=FakeAdapter(),
    )

    _assert_foreman_charter_and_worker_spawn(_brain_payload(result))


def test_launch_writes_seat_lifecycle_record_and_event(tmp_path):
    adapter = FakeAdapter()
    ledger = tmp_path / ".hermes" / "active-work-ledger"
    result = launch_runtime.launch(
        harness="claude",
        session="ce-controller",
        window="controller",
        repo_root=tmp_path,
        ledger_root=ledger,
        owner_controller_id="chmod735",
        host_id="ce-dev-2",
        purpose="creator-engine/ce-ops#95",
        tmux_adapter=adapter,
    )

    assert result.seat_lifecycle_state == "alive"
    assert result.seat_record_ref is not None
    record_path = Path(result.seat_record_ref)
    assert record_path == ledger / "seats" / "ce-dev-2" / "ce-controller--controller.yaml"
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    assert record["kind"] == "seat-lifecycle-record"
    assert record["seat"]["seat_id"] == "ce-controller--controller"
    assert record["seat"]["owner_controller_id"] == "chmod735"
    assert record["seat"]["host_id"] == "ce-dev-2"
    assert record["seat"]["launch_surface"] == "ce_launch"
    assert record["seat"]["purpose"] == "creator-engine/ce-ops#95"
    assert record["terminal"]["pane_pid"] == 999
    assert record["lifecycle"]["state"] == "alive"
    assert record["policy"]["policy_id"] == "default-governed-seat-v1"
    assert record["policy"]["ttl_seconds"] == 28800
    assert record["policy"]["idle_timeout_seconds"] == 7200

    event_path = ledger / "seat-events" / "ce-dev-2" / "ce-controller--controller.ndjson"
    events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
    assert events == [{
        "event": "registered",
        "host_id": "ce-dev-2",
        "record_ref": str(record_path),
        "seat_id": "ce-controller--controller",
        "state": "alive",
        "ts": events[0]["ts"],
    }]


def test_launch_defaults_lifecycle_ledger_to_ce_state(tmp_path):
    adapter = FakeAdapter()
    result = launch_runtime.launch(
        harness="claude",
        session="ce-controller",
        window="controller",
        repo_root=tmp_path,
        owner_controller_id="ce-dev-1",
        host_id="ce-dev-1",
        purpose="creator-engine/ce-ops#149",
        tmux_adapter=adapter,
    )

    expected = tmp_path / ".ce" / "state" / "active-work-ledger"
    assert result.seat_record_ref is not None
    assert Path(result.seat_record_ref) == (
        expected / "seats" / "ce-dev-1" / "ce-controller--controller.yaml"
    )
    assert (expected / "seat-events" / "ce-dev-1" / "ce-controller--controller.ndjson").is_file()


def test_launch_registration_failure_warns_escalates_and_returns_ungoverned(
    tmp_path, monkeypatch, capsys
):
    adapter = FakeAdapter()

    def _boom(**_kwargs):
        raise launch_runtime.seat_lifecycle.SeatLifecycleError("synthetic write fault")

    monkeypatch.setattr(launch_runtime.seat_lifecycle, "register_spawn", _boom)
    monkeypatch.setattr(launch_runtime.seat_lifecycle, "SEAT_LIFECYCLE_FAIL_CLOSED", False)
    result = launch_runtime.launch(
        harness="claude",
        session="fault-seat",
        window="controller",
        repo_root=tmp_path,
        ledger_root=tmp_path / ".hermes" / "active-work-ledger",
        host_id="ce-dev-2",
        tmux_adapter=adapter,
    )

    assert result.spawned is True
    assert result.seat_record_ref is None
    assert result.seat_lifecycle_state == "ungoverned_registration_failed"
    err = capsys.readouterr().err
    assert "WARNING: seat lifecycle registration failed after pane spawn" in err
    assert "AWAITING-OPERATOR" in err
    escalations = list((tmp_path / ".ce" / "state" / "escalations").glob("*.yaml"))
    assert len(escalations) == 1
    escalation = yaml.safe_load(escalations[0].read_text(encoding="utf-8"))
    assert escalation["record_type"] == "escalation"
    assert "Seat lifecycle registration failed" in escalation["title"]


def test_launch_result_to_dict_is_json_safe():
    import json

    adapter = FakeAdapter()
    result = launch_runtime.launch(harness="claude", dry_run=True, tmux_adapter=adapter)
    json.dumps(result.to_dict())
    assert result.to_dict()["plan"]["mode"] == "launch"


# ---------------------------------------------------------------------------
# CC-G-D — Ring 0 Claude launch refusal + governed command in `ce launch`
# ---------------------------------------------------------------------------


def test_claude_launch_refuses_bare_before_side_effects(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    with pytest.raises(launch_runtime.LaunchRefused) as exc:
        launch_runtime.launch(harness="claude", extra_args=["--bare"], tmux_adapter=adapter)
    assert exc.value.code == "G6-LAUNCH-CLAUDE-REFUSED"
    assert "CC-D-1" in str(exc.value)
    assert adapter.spawned == []


def test_claude_launch_refuses_skip_perms_without_confirmed_pack(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: False)
    with pytest.raises(launch_runtime.LaunchRefused) as exc:
        launch_runtime.launch(
            harness="claude",
            extra_args=["--dangerously-skip-permissions"],
            tmux_adapter=adapter,
        )
    assert "CC-D-6" in str(exc.value)
    assert adapter.spawned == []


def test_claude_launch_pins_setting_sources_and_strict_mcp(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    result = launch_runtime.launch(
        harness="claude",
        session="s",
        tmux_adapter=adapter,
        mcp_config_path=".ce/state/launch/s/mcp/ce-mcp.json",
    )
    (_sess, _win, cmd) = adapter.spawned[-1]
    # ce-ops#26: the pane runs the sentinel wrapper; the governed argv is INSIDE it.
    assert cmd == ["/bin/sh", str(Path(result.events_ref).parent / "sentinel-wrapper.sh")]
    inner = _inner_argv(result)
    assert inner[0] == "claude"
    assert "--setting-sources" in inner and "project" in inner and "--strict-mcp-config" in inner


def test_claude_launch_allows_skip_perms_with_confirmed_pack(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    result = launch_runtime.launch(
        harness="claude",
        session="s",
        extra_args=["--dangerously-skip-permissions"],
        tmux_adapter=adapter,
        mcp_config_path=".ce/state/launch/s/mcp/ce-mcp.json",
    )
    inner = _inner_argv(result)
    assert "--dangerously-skip-permissions" in inner
    assert "--setting-sources" in inner and "project" in inner


def test_codex_launch_builds_governed_env_scrubbed_command(tmp_path, monkeypatch):
    # Codex does not get the Claude MCP command, but it is no longer raw pass-through:
    # CDX-D Ring 0 wraps it with an ambient GitHub credential scrub.
    adapter = FakeAdapter()
    monkeypatch.setattr(
        launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    monkeypatch.setattr(launch_runtime, "_confirm_codex_managed_pack", lambda repo_root: True)
    codex = _fake_codex(tmp_path, monkeypatch)
    result = launch_runtime.launch(
        harness="codex",
        session="s",
        extra_args=["--model", "gpt-5"],
        tmux_adapter=adapter,
    )
    inner = _inner_argv(result)
    assert inner[:2] == ["env", "-u"]
    assert "GH_TOKEN" in inner and "GITHUB_TOKEN" in inner
    assert inner[-3:] == [str(codex), "--model", "gpt-5"]
    assert result.plan.codex_bypass_mode == "config"


def test_codex_launch_refuses_unsafe_surface_before_side_effects(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(
        launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    monkeypatch.setattr(launch_runtime, "_confirm_codex_managed_pack", lambda repo_root: True)
    with pytest.raises(launch_runtime.CodexLaunchRefused) as exc:
        launch_runtime.launch(harness="codex", extra_args=["exec"], tmux_adapter=adapter)
    assert "CDX-D-1" in str(exc.value)
    assert adapter.spawned == []


def test_codex_launch_refuses_unresolved_harness_before_side_effects(tmp_path, monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(
        launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    monkeypatch.setattr(launch_runtime, "_confirm_codex_managed_pack", lambda repo_root: True)
    monkeypatch.setenv(
        launch_runtime.codex_launch_spec.CODEX_HARNESS_ENV,
        str(tmp_path / "missing" / "codex"),
    )

    with pytest.raises(launch_runtime.CodexLaunchRefused) as exc:
        launch_runtime.launch(
            harness="codex",
            session="missing-codex",
            repo_root=tmp_path,
            ledger_root=tmp_path / ".ce" / "state" / "active-work-ledger",
            tmux_adapter=adapter,
        )

    assert "cannot resolve Codex harness" in str(exc.value)
    assert adapter.spawned == []
    assert not (tmp_path / ".ce" / "state" / "dispatches" / "missing-codex--controller").exists()
    assert not (tmp_path / ".ce" / "state" / "active-work-ledger" / "seats").exists()


def test_codex_launch_refuses_unconfirmed_managed_hook_pack_before_side_effects(tmp_path, monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_codex_managed_pack", lambda repo_root: False)
    monkeypatch.setattr(
        launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    _fake_codex(tmp_path, monkeypatch)

    with pytest.raises(launch_runtime.CodexLaunchRefused) as exc:
        launch_runtime.launch(harness="codex", session="s", repo_root=tmp_path, tmux_adapter=adapter)

    assert launch_runtime.codex_launch_spec.CLAUSE_MANAGED_HOOK_PACK in str(exc.value)
    assert adapter.spawned == []


def test_launch_reconciles_exit_127_sentinel_to_dead_record(tmp_path, monkeypatch):
    monkeypatch.setattr(
        launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    monkeypatch.setattr(launch_runtime, "_confirm_codex_managed_pack", lambda repo_root: True)
    _fake_codex(tmp_path, monkeypatch)

    result = launch_runtime.launch(
        harness="codex",
        session="exec-fail",
        repo_root=tmp_path,
        ledger_root=tmp_path / ".ce" / "state" / "active-work-ledger",
        tmux_adapter=Exit127Adapter(),
    )

    record = yaml.safe_load(Path(result.seat_record_ref).read_text(encoding="utf-8"))
    assert result.seat_lifecycle_state == "dead"
    assert record["lifecycle"]["state"] == "dead"
    assert record["lifecycle"]["terminal_exit_code"] == 127


def test_launch_refuses_existing_launched_events_before_reuse(tmp_path, monkeypatch):
    adapter = FakeAdapter()
    seat_dir = tmp_path / ".ce" / "state" / "dispatches" / "reuse--controller"
    seat_dir.mkdir(parents=True)
    (seat_dir / "events.jsonl").write_text(
        json.dumps({"event": "launched", "seat_id": "reuse--controller"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)

    with pytest.raises(launch_runtime.SeatSurfaceReuseRefused):
        launch_runtime.launch(
            harness="claude",
            session="reuse",
            repo_root=tmp_path,
            tmux_adapter=adapter,
        )

    assert adapter.spawned == []
    assert not (seat_dir / "sentinel-wrapper.sh").exists()


def test_claude_args_do_not_affect_codex_cli_route(tmp_path, monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(
        launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    monkeypatch.setattr(launch_runtime, "_confirm_codex_managed_pack", lambda repo_root: True)
    _fake_codex(tmp_path, monkeypatch)
    result = launch_runtime.launch(harness="codex", session="s", tmux_adapter=adapter)
    assert "--dangerously-skip-permissions" not in _inner_argv(result)


def test_seat_surface_dispatch_driven_seat_id_is_run_id(tmp_path):
    # ce-ops#26: --runtime-policy <state>/dispatches/<run_id>/runtime-policy.yaml ⇒
    # seat_id = run_id and events land NEXT TO dispatch.yaml.
    dispatch_dir = tmp_path / ".ce" / "state" / "dispatches" / "run-x-1"
    dispatch_dir.mkdir(parents=True)
    seat_dir, seat_id, run_id = launch_runtime._resolve_seat_surface(
        repo_root=tmp_path, session="s", window="w",
        runtime_policy=dispatch_dir / "runtime-policy.yaml",
    )
    assert (seat_dir, seat_id, run_id) == (dispatch_dir, "run-x-1", "run-x-1")


def test_seat_surface_bare_seat_id_is_session_window_slug(tmp_path):
    seat_dir, seat_id, run_id = launch_runtime._resolve_seat_surface(
        repo_root=tmp_path, session="Ctrl Seat", window="main", runtime_policy=None,
    )
    assert seat_id == "ctrl-seat--main"
    assert run_id is None
    assert seat_dir == tmp_path / ".ce" / "state" / "dispatches" / "ctrl-seat--main"


def test_claude_launch_refuses_uncontrolled_mcp_config_flag(monkeypatch):
    # An operator-supplied --mcp-config outside the governed roots must refuse
    # (LaunchRefused), never crash with a raw GovernedCommandError.
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    with pytest.raises(launch_runtime.LaunchRefused) as exc:
        launch_runtime.launch(
            harness="claude",
            session="s",
            tmux_adapter=adapter,
            mcp_config_path="/etc/global/mcp.json",
        )
    assert "CC-D-7" in str(exc.value)
    assert adapter.spawned == []


# ---------------------------------------------------------------------------
# v3.1-G1 defect-a — plain `ce launch` must provision the strict MCP config
# (claude was pinned at a path that was never created -> silent exit 1).
# ---------------------------------------------------------------------------


class _McpProbingAdapter(FakeAdapter):
    """FakeAdapter that records whether ``mcp_path`` existed at spawn time."""

    def __init__(self, mcp_path, **kw):
        super().__init__(**kw)
        self._mcp_path = mcp_path
        self.mcp_existed_at_spawn: bool | None = None

    def ensure_pane(self, *, session, window, command):
        self.mcp_existed_at_spawn = self._mcp_path.is_file()
        return super().ensure_pane(session=session, window=window, command=command)


def test_claude_launch_provisions_mcp_config_before_spawn(tmp_path, monkeypatch):
    # defect-a: a non-dry-run claude launch writes the strict MCP config into the
    # seat cwd (repo_root) BEFORE ensure_pane, so the governed seat can bind.
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    mcp_rel = ".ce/state/launch/ce-controller/mcp/ce-mcp.json"
    mcp_abs = tmp_path / mcp_rel
    adapter = _McpProbingAdapter(mcp_abs)
    assert not mcp_abs.exists()
    launch_runtime.launch(
        harness="claude",
        session="ce-controller",
        tmux_adapter=adapter,
        repo_root=str(tmp_path),
    )
    assert adapter.spawned, "the governed seat must spawn"
    assert adapter.mcp_existed_at_spawn is True, "MCP config must exist before ensure_pane"
    assert mcp_abs.read_text(encoding="utf-8") == (
        json.dumps({"mcpServers": {}}, indent=2, sort_keys=True) + "\n"
    )


def test_claude_launch_does_not_overwrite_existing_mcp_config(tmp_path, monkeypatch):
    # An Operator/launcher-supplied MCP config is never clobbered by provisioning.
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    mcp_rel = ".ce/state/launch/s/mcp/ce-mcp.json"
    mcp_abs = tmp_path / mcp_rel
    mcp_abs.parent.mkdir(parents=True)
    preexisting = '{"mcpServers": {"keep": {"command": "x"}}}\n'
    mcp_abs.write_text(preexisting, encoding="utf-8")
    launch_runtime.launch(
        harness="claude",
        session="s",
        tmux_adapter=FakeAdapter(),
        mcp_config_path=mcp_rel,
        repo_root=str(tmp_path),
    )
    assert mcp_abs.read_text(encoding="utf-8") == preexisting


def test_claude_launch_refuses_nonfile_mcp_target_before_spawn(tmp_path, monkeypatch):
    # A non-regular-file at the MCP target is a fail-closed LaunchRefused (no spawn).
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    mcp_rel = ".ce/state/launch/s/mcp/ce-mcp.json"
    (tmp_path / mcp_rel).mkdir(parents=True)  # a DIRECTORY where the file must go
    adapter = FakeAdapter()
    with pytest.raises(launch_runtime.LaunchRefused):
        launch_runtime.launch(
            harness="claude",
            session="s",
            tmux_adapter=adapter,
            mcp_config_path=mcp_rel,
            repo_root=str(tmp_path),
        )
    assert adapter.spawned == []


# ---------------------------------------------------------------------------
# v3.1-G1 defect-b — CC-D-6 gates the bridge's unattended skip-permissions flag.
# The bridge passes `--claude-arg=--dangerously-skip-permissions`; the governance
# already exists (CC-D-6), so launch_runtime is the enforced boundary.
# ---------------------------------------------------------------------------


def test_unattended_skip_perms_refuses_when_hook_pack_unconfirmed(tmp_path, monkeypatch):
    # CC-D-6 fail-closed: an unattended (skip-perms) seat with an unconfirmed
    # hook-pack is refused before any side effect.
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: False)
    adapter = FakeAdapter()
    with pytest.raises(launch_runtime.LaunchRefused) as exc:
        launch_runtime.launch(
            harness="claude",
            session="drive-seat",
            extra_args=["--dangerously-skip-permissions"],
            tmux_adapter=adapter,
            repo_root=str(tmp_path),
        )
    assert "CC-D-6" in str(exc.value)
    assert adapter.spawned == []


def test_unattended_skip_perms_carries_flag_when_hook_pack_confirmed(tmp_path, monkeypatch):
    # CC-D-6 confirmed: the governed argv carries --dangerously-skip-permissions.
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    adapter = FakeAdapter()
    result = launch_runtime.launch(
        harness="claude",
        session="drive-seat",
        extra_args=["--dangerously-skip-permissions"],
        tmux_adapter=adapter,
        repo_root=str(tmp_path),
    )
    inner = _inner_argv(result)
    assert "--dangerously-skip-permissions" in inner
    assert "--setting-sources" in inner and "project" in inner


def test_claude_dry_run_does_not_confirm_pack_when_no_skip_perms(monkeypatch):
    # Dry-run with no skip-perms must not invoke the (possibly impure) pack probe.
    adapter = FakeAdapter()

    def _boom(repo_root):
        raise AssertionError("_confirm_pack must not be called without skip-permissions")

    monkeypatch.setattr(launch_runtime, "_confirm_pack", _boom)
    result = launch_runtime.launch(harness="claude", dry_run=True, tmux_adapter=adapter)
    assert result.plan.dry_run is True
    assert adapter.spawned == []


# --- CE Ring 0 Hermes harness governance (round: Hermes governance TDD) ---


def test_hermes_dry_run_emits_governed_profile_pinned_command():
    result = launch_runtime.launch(harness="hermes", dry_run=True)
    # no longer a bare ["hermes"]; profile is pinned and visible in the plan
    assert result.plan.command == ["hermes", "--profile", "creator-engine"]
    assert result.plan.dry_run is True


def test_hermes_launch_refuses_yolo_before_side_effect():
    adapter = FakeAdapter(available=True)
    with pytest.raises(launch_runtime.LaunchRefused):
        launch_runtime.launch(harness="hermes", extra_args=["--yolo"], tmux_adapter=adapter)


def test_hermes_launch_refuses_profile_override_before_side_effect():
    adapter = FakeAdapter(available=True)
    with pytest.raises(launch_runtime.LaunchRefused):
        launch_runtime.launch(
            harness="hermes", extra_args=["--profile", "mythos"], tmux_adapter=adapter
        )


def test_hermes_launch_refuses_resume_continue_before_side_effect():
    adapter = FakeAdapter(available=True)
    for argv in (["--resume", "s"], ["-c"]):
        with pytest.raises(launch_runtime.LaunchRefused):
            launch_runtime.launch(harness="hermes", extra_args=argv, tmux_adapter=adapter)


def test_claude_governance_not_regressed_by_hermes_branch():
    # the Claude harness still pins --setting-sources project + --strict-mcp-config
    result = launch_runtime.launch(harness="claude", dry_run=True)
    cmd = result.plan.command
    assert cmd[0] == "claude"
    assert "--setting-sources" in cmd and "project" in cmd
    assert "--strict-mcp-config" in cmd


class _SpawnTrackingAdapter:
    kind = "tmux"
    def __init__(self): self.spawned = []
    def is_available(self): return True
    def ensure_pane(self, *, session, window, command, cwd=None):
        self.spawned.append((session, window, list(command), cwd))
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3")


@pytest.mark.parametrize("argv", [["--res"], ["-rabc"], ["--cont"], ["-cabc"], ["--yol"], ["--acc"], ["--ignore-r"], ["--prof", "mythos"]])
def test_hermes_refuses_abbreviated_bypass_with_no_spawn(argv):
    adapter = _SpawnTrackingAdapter()
    with pytest.raises(launch_runtime.LaunchRefused):
        launch_runtime.launch(harness="hermes", extra_args=argv, tmux_adapter=adapter)
    assert adapter.spawned == []


def test_hermes_refusal_uses_hermes_code_not_claude():
    adapter = _SpawnTrackingAdapter()
    try:
        launch_runtime.launch(harness="hermes", extra_args=["--yolo"], tmux_adapter=adapter)
        assert False, "expected refusal"
    except launch_runtime.LaunchRefused as exc:
        assert getattr(exc, "code", "") == "G6-LAUNCH-HERMES-REFUSED"
    assert adapter.spawned == []
