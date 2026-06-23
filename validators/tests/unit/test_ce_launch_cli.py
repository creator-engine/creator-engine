"""RV1-063 — unit tests for ``ce launch`` / ``ce hud`` CLI surfaces.

Drives ``creator_engine_validator.ce_cli.main`` directly with the tmux adapter
replaced by a test double, so the deterministic dry-run, hud alias, and the
hidden-continuation / resume refusals are exercised without a real tmux process
or a live provider login.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest
import yaml

from creator_engine_validator import brain_runtime, ce_cli
from creator_engine_validator.tmux_adapter import TmuxPane


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

    def ensure_pane(self, *, session, window, command, cwd=None, env=None):
        self.spawned.append((session, window, list(command)))
        self._sessions.add(session)
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3")


class FakeGhRunner:
    """Tiny `gh api` double that supports the work-claim acquire reread loop."""

    def __init__(self):
        self.comments: list[dict] = []
        self.next_id = 100

    def __call__(self, argv, input_text=None):
        method = None
        if "--method" in argv:
            method = argv[argv.index("--method") + 1]
        if method == "GET":
            return subprocess.CompletedProcess(
                list(argv), 0, stdout=json.dumps(self.comments), stderr=""
            )
        if method == "POST":
            payload = json.loads(input_text or "{}")
            comment = {
                "id": self.next_id,
                "body": payload["body"],
                "created_at": "2026-06-16T00:00:00Z",
                "user": {"login": "chmod735"},
                "html_url": (
                    "https://github.com/creator-engine/ce-ops/issues/95"
                    f"#issuecomment-{self.next_id}"
                ),
            }
            self.next_id += 1
            self.comments.append(comment)
            return subprocess.CompletedProcess(
                list(argv), 0, stdout=json.dumps({"html_url": comment["html_url"]}), stderr=""
            )
        raise AssertionError(f"unexpected gh invocation: {argv!r}")


def _write_brain_ledger(state_root: Path) -> None:
    result = brain_runtime.assert_claim(
        assertion_id="brain-assertion-ce-launch-cli-0001",
        claim={"subject": "controller", "predicate": "bootstrap", "object": "ready"},
        scope="global",
        evidence_ref="validators/tests/unit/test_ce_launch_cli.py#brain-ledger",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    path = brain_runtime.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brain_runtime.serialize_ledger([result.record]), encoding="utf-8")


def _fake_codex(tmp_path: Path, monkeypatch) -> Path:
    codex = tmp_path / "bin" / "codex"
    codex.parent.mkdir()
    codex.write_text("#!/bin/sh\n", encoding="utf-8")
    codex.chmod(0o755)
    monkeypatch.setenv(ce_cli.launch_runtime.codex_launch_spec.CODEX_HARNESS_ENV, str(codex))
    return codex


def _write_runtime_policy(
    tmp_path: Path, *, backend: str | None = "gvisor-proxy"
) -> Path:
    policy = {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "gvisor-implementer-v1",
        "policy_sha": "a" * 64,
        "role": "implementer",
        "image_ref": {
            "name": "registry.example/creator-engine/implementer",
            "sha": "sha256:" + "b" * 64,
        },
        "mount_manifest": [
            {
                "path": "/runtime/worktree",
                "mode": "rw",
                "write_justification": "allocated worktree for this seat",
            },
            {"path": "/runtime/governance", "mode": "ro"},
        ],
        "egress_allowlist": [
            {"host": "model-provider.example", "protocol": "https", "assurance": ["l4"]},
        ],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }
    if backend is not None:
        policy["isolation_backend"] = backend
    path = tmp_path / "runtime-policy.yaml"
    path.write_text(yaml.safe_dump(policy, sort_keys=True), encoding="utf-8")
    return path


class FakeContainerRunner:
    def __init__(self, *, available: bool = True, egress_enforceable: bool = True):
        self._available = available
        self._egress = egress_enforceable

    def available(self) -> bool:
        return self._available

    def egress_enforceable(self) -> bool:
        return self._egress

    def run(self, argv, input_text=None):  # pragma: no cover - bridge must not call it
        raise AssertionError("visible bridge should route runsc argv through tmux")


def _gvisor_plan_kwargs() -> dict:
    return {
        "uid": 1001,
        "gid": 1002,
        "host_codex_home": "/host/codex-home",
        "host_codex_bin": "/host/codex-bin/codex",
        "container_workdir": "/runtime/worktree",
    }


@pytest.fixture(autouse=True)
def _isolate_brain_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_brain_ledger(tmp_path / ".ce" / "state")


@pytest.fixture()
def use_fake_tmux(monkeypatch):
    adapter = FakeAdapter()

    def _install(a: FakeAdapter):
        monkeypatch.setattr(ce_cli, "_make_tmux_adapter", lambda: a)

    _install(adapter)
    return _install


@pytest.mark.parametrize("argv", [["launch", "--help"], ["hud", "--help"]])
def test_launch_and_hud_help_reachable(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


def test_launch_help_names_ce_state_not_hermes(capsys):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(["launch", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert ".ce/state" in out
    assert ".hermes" not in out


def test_launch_dry_run_json(use_fake_tmux, capsys):
    ret = ce_cli.main(["launch", "--dry-run", "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"]["mode"] == "launch"
    assert payload["plan"]["invoked_as"] == "launch"
    assert payload["plan"]["visibility"] == "operator_visible"
    assert payload["spawned"] is False


def test_launch_backend_dry_run_json_carries_runtime_policy(use_fake_tmux, tmp_path, capsys):
    policy = _write_runtime_policy(tmp_path)
    ret = ce_cli.main([
        "launch",
        "--dry-run",
        "--json",
        "--backend",
        "gvisor",
        "--runtime-policy",
        str(policy),
    ])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    stamp = payload["plan"]["runtime_policy"]
    assert stamp["requested_backend"] == "gvisor"
    assert stamp["resolved_backend"] == "gvisor-proxy"
    assert stamp["image_ref"]["digest"].endswith("@sha256:" + "b" * 64)
    assert stamp["mount_manifest"][0]["path"] == "/runtime/worktree"
    assert stamp["egress_allowlist"] == [
        {"host": "model-provider.example", "protocol": "https", "assurance": ["l4"]}
    ]


def test_launch_backend_refuses_without_runtime_policy(use_fake_tmux, capsys):
    ret = ce_cli.main(["launch", "--dry-run", "--backend", "gvisor"])
    assert ret != 0
    err = capsys.readouterr().err
    assert "--backend requires --runtime-policy" in err


def test_launch_backend_live_refuses_before_raw_tmux(use_fake_tmux, tmp_path, capsys, monkeypatch):
    from creator_engine_validator import runner

    monkeypatch.setattr(
        ce_cli.launch_runtime.runtime_backend_bridge,
        "_default_gvisor_plan_kwargs",
        _gvisor_plan_kwargs,
    )
    monkeypatch.setattr(
        runner,
        "SubprocessContainerRunner",
        lambda: FakeContainerRunner(available=False),
    )
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    policy = _write_runtime_policy(tmp_path)
    ret = ce_cli.main([
        "launch",
        "--backend",
        "gvisor",
        "--runtime-policy",
        str(policy),
    ])
    assert ret != 0
    assert adapter.spawned == []
    err = capsys.readouterr().err
    assert "not available" in err


def test_launch_backend_gvisor_spawns_visible_docker_runsc_path(tmp_path):
    adapter = FakeAdapter()
    policy = _write_runtime_policy(tmp_path)
    result = ce_cli.launch_runtime.launch(
        harness="hermes",
        runtime_policy=policy,
        backend="gvisor",
        repo_root=tmp_path,
        tmux_adapter=adapter,
        container_runner=FakeContainerRunner(),
        gvisor_plan_kwargs=_gvisor_plan_kwargs(),
    )

    assert result.spawned is True
    assert result.plan.runtime_policy["resolved_backend"] == "gvisor-proxy"
    assert result.runner_runtime["backend_key"] == "gvisor-proxy"
    argv = result.runner_runtime["argv"]
    assert argv[:3] == ["docker", "run", "--rm"]
    assert "--runtime=runsc-gvproxy-ptrace" in argv
    assert "registry.example/creator-engine/implementer@sha256:" + "b" * 64 in argv
    assert adapter.spawned
    assert adapter.spawned[0][2] == argv


def test_launch_backend_unavailable_refuses_without_raw_tmux(tmp_path):
    adapter = FakeAdapter()
    policy = _write_runtime_policy(tmp_path)

    with pytest.raises(ce_cli.launch_runtime.RuntimePolicyRefused, match="not available"):
        ce_cli.launch_runtime.launch(
            harness="hermes",
            runtime_policy=policy,
            backend="gvisor",
            repo_root=tmp_path,
            tmux_adapter=adapter,
            container_runner=FakeContainerRunner(available=False),
            gvisor_plan_kwargs=_gvisor_plan_kwargs(),
        )

    assert adapter.spawned == []


def test_launch_default_backend_live_refuses_before_raw_tmux(
    use_fake_tmux, tmp_path, capsys
):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    policy = _write_runtime_policy(tmp_path, backend=None)
    ret = ce_cli.main(["launch", "--runtime-policy", str(policy)])
    assert ret != 0
    assert adapter.spawned == []
    err = capsys.readouterr().err
    assert "default runtime-policy backend 'gvisor-proxy'" in err
    assert "raw tmux fallback" in err


def test_launch_backend_mismatch_refuses(use_fake_tmux, tmp_path, capsys):
    policy = _write_runtime_policy(tmp_path, backend="openshell")
    ret = ce_cli.main([
        "launch",
        "--dry-run",
        "--backend",
        "gvisor",
        "--runtime-policy",
        str(policy),
    ])
    assert ret != 0
    err = capsys.readouterr().err
    assert "runtime policy declares 'openshell'" in err


def test_lane_launch_default_backend_refuses_before_raw_tmux(
    use_fake_tmux, tmp_path, capsys
):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    policy = _write_runtime_policy(tmp_path, backend=None)
    prompt = tmp_path / "prompt.md"
    prompt.write_text("lane prompt\n", encoding="utf-8")
    ret = ce_cli.main([
        "lane",
        "launch",
        "--controller-id",
        "ctrl",
        "--lane-id",
        "lane",
        "--role",
        "implementer",
        "--prompt",
        str(prompt),
        "--prompt-sha",
        "0" * 64,
        "--repo-root",
        str(tmp_path),
        "--ledger-root",
        str(tmp_path / ".hermes" / "active-work-ledger"),
        "--runtime-policy",
        str(policy),
    ])
    assert ret != 0
    assert adapter.spawned == []
    err = capsys.readouterr().err
    assert "default runtime-policy backend 'gvisor-proxy'" in err
    assert "raw tmux fallback" in err


def test_hud_dry_run_json_is_alias_of_launch(use_fake_tmux, capsys):
    ce_cli.main(["launch", "--dry-run", "--json", "--session", "s", "--window", "w"])
    launch_payload = json.loads(capsys.readouterr().out)
    ce_cli.main(["hud", "--dry-run", "--json", "--session", "s", "--window", "w"])
    hud_payload = json.loads(capsys.readouterr().out)
    assert hud_payload["plan"]["invoked_as"] == "hud"
    assert hud_payload["plan"]["alias_of"] == "launch"
    assert hud_payload["plan"]["command"] == launch_payload["plan"]["command"]


def test_launch_refuses_no_tmux_flag(use_fake_tmux, capsys):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    ret = ce_cli.main(["launch", "--no-tmux"])
    assert ret != 0
    assert adapter.spawned == []


def test_launch_spawns_visible_seat(use_fake_tmux):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    ret = ce_cli.main(["launch", "--session", "ce-controller"])
    assert ret == 0
    assert adapter.spawned


def test_launch_claim_ticket_binding_is_persisted_in_seat_lifecycle(
    tmp_path, use_fake_tmux, monkeypatch
):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    gh = FakeGhRunner()
    ledger = tmp_path / ".hermes" / "active-work-ledger"
    monkeypatch.setattr(ce_cli, "_make_gh_runner", lambda: gh)
    monkeypatch.setattr(ce_cli.work_claims, "resolve_holder", lambda holder=None, environ=None: "chmod735")
    monkeypatch.setattr(ce_cli.work_claims, "resolve_host", lambda host=None: "ce-dev-2")
    monkeypatch.setattr(ce_cli.work_claims.time, "sleep", lambda _seconds: None)

    ret = ce_cli.main([
        "launch",
        "--session", "ce95",
        "--repo-root", str(tmp_path),
        "--ledger-root", str(ledger),
        "--controller-id", "chmod735",
        "--host-id", "ce-dev-2",
        "--claim-ticket", "creator-engine/ce-ops#95",
    ])

    assert ret == 0
    record_path = ledger / "seats" / "ce-dev-2" / "ce95--controller.yaml"
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    assert record["work"]["ticket"] == "creator-engine/ce-ops#95"
    claim = record["work"]["work_claim"]
    assert claim["work_key"] == "creator-engine/ce-ops:issue:95"
    assert claim["claim_id"].startswith("wclaim-")
    assert claim["claim_comment_url"] == (
        "https://github.com/creator-engine/ce-ops/issues/95#issuecomment-100"
    )
    assert claim["holder"] == "chmod735"
    assert claim["host"] == "ce-dev-2"
    assert claim["stale_after_seconds"] == 14400
    assert adapter.spawned


def test_launch_claim_ticket_refuses_tampered_brain_before_work_claim_acquire(
    tmp_path, use_fake_tmux, monkeypatch, capsys
):
    brain_runtime.ledger_path(tmp_path / ".ce" / "state").write_text(
        "not a valid brain ledger\n",
        encoding="utf-8",
    )
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    calls = []

    def _acquire(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("work claim acquire must not run before brain bootstrap preflight")

    monkeypatch.setattr(ce_cli.work_claims, "acquire", _acquire)

    ret = ce_cli.main([
        "launch",
        "--session", "ce305",
        "--repo-root", str(tmp_path),
        "--claim-ticket", "creator-engine/ce-ops#305",
    ])

    assert ret != 0
    assert calls == []
    assert adapter.spawned == []
    assert "G6-LAUNCH-BRAIN-BOOTSTRAP-REFUSED" in capsys.readouterr().err


def test_launch_resume_refuses_missing_session(use_fake_tmux):
    adapter = FakeAdapter(sessions=set())
    use_fake_tmux(adapter)
    ret = ce_cli.main(["launch", "--resume", "--session", "ce-controller"])
    assert ret != 0
    assert adapter.spawned == []


def test_launch_resume_attaches_existing(use_fake_tmux, capsys):
    adapter = FakeAdapter(sessions={"ce-controller"})
    use_fake_tmux(adapter)
    ret = ce_cli.main(["launch", "--resume", "--session", "ce-controller", "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"]["mode"] == "resume"
    assert payload["attached"] is True


# ---------------------------------------------------------------------------
# CC-G-D — Ring 0 governed Claude surfaces via the CLI
# ---------------------------------------------------------------------------


def test_cli_launch_refuses_claude_bare(use_fake_tmux, monkeypatch, capsys):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    monkeypatch.setattr(ce_cli.launch_runtime, "_confirm_pack", lambda r: True)
    ret = ce_cli.main(["launch", "--harness", "claude", "--claude-arg=--bare"])
    assert ret != 0
    assert adapter.spawned == []
    err = capsys.readouterr().err
    assert "G6-LAUNCH-CLAUDE-REFUSED" in err
    assert "CC-D-1" in err


def test_cli_launch_refuses_claude_skip_perms_without_pack(use_fake_tmux, monkeypatch, capsys):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    monkeypatch.setattr(ce_cli.launch_runtime, "_confirm_pack", lambda r: False)
    ret = ce_cli.main(
        ["launch", "--harness", "claude", "--claude-arg=--dangerously-skip-permissions"]
    )
    assert ret != 0
    assert adapter.spawned == []
    assert "CC-D-6" in capsys.readouterr().err


def test_cli_launch_pins_governed_command(use_fake_tmux, monkeypatch):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    monkeypatch.setattr(ce_cli.launch_runtime, "_confirm_pack", lambda r: True)
    ret = ce_cli.main(
        ["launch", "--harness", "claude", "--mcp-config", ".ce/state/launch/s/mcp/ce-mcp.json"]
    )
    assert ret == 0
    (_sess, _win, cmd) = adapter.spawned[-1]
    # ce-ops#26: the pane runs the sentinel wrapper; the governed argv is INSIDE it.
    import shlex
    from pathlib import Path

    assert cmd[0] == "/bin/sh"
    lines = Path(cmd[1]).read_text().splitlines()
    idx = next(i for i, line in enumerate(lines) if line == "code=$?")
    inner = shlex.split(lines[idx - 1])
    assert "--setting-sources" in inner and "project" in inner and "--strict-mcp-config" in inner


def test_cli_launch_dry_run_still_pure(use_fake_tmux):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    assert ce_cli.main(["launch", "--harness", "claude", "--dry-run", "--json"]) == 0
    assert adapter.spawned == []


def test_cli_codex_dry_run_json_uses_governed_command(use_fake_tmux, tmp_path, monkeypatch, capsys):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    monkeypatch.setattr(
        ce_cli.launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    monkeypatch.setattr(
        ce_cli.launch_runtime, "_confirm_codex_managed_pack", lambda repo_root: True
    )
    codex = _fake_codex(tmp_path, monkeypatch)
    ret = ce_cli.main([
        "launch", "--harness", "codex", "--codex-arg=--model", "--codex-arg", "gpt-5",
        "--claude-arg=--bare", "--dry-run", "--json",
    ])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    command = payload["plan"]["command"]
    assert command[:2] == ["env", "-u"]
    assert command[-3:] == [str(codex), "--model", "gpt-5"]
    assert "--bare" not in command
    assert payload["plan"]["codex_bypass_mode"] == "config"


def test_cli_codex_refuses_non_allowlisted_arg(use_fake_tmux, monkeypatch, capsys):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    monkeypatch.setattr(
        ce_cli.launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    monkeypatch.setattr(
        ce_cli.launch_runtime, "_confirm_codex_managed_pack", lambda repo_root: True
    )
    ret = ce_cli.main(["launch", "--harness", "codex", "--codex-arg=--foo"])
    assert ret != 0
    assert adapter.spawned == []
    assert "CDX-D-7" in capsys.readouterr().err
