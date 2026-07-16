"""Unit tests for the ``ce worker`` CLI surface (allocate / terminate / gc).

The container-engine runner and credential broker are injected through the
``ce_cli._make_worker_runner`` / ``ce_cli._make_worker_broker`` factories, which
tests monkeypatch with fakes. The default factories return the real
fail-closed seams (Podman unavailable on this host).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from creator_engine_validator import ce_cli, worker_runtime
from creator_engine_validator import worker_spawn
from creator_engine_validator import worker_run


_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64
CONTROLLER = "hermes-primary"
LANE = "pco-slice2ir-worker"


@dataclass
class FakeRunner:
    available_flag: bool = True
    egress_primitive_value: str | None = None
    calls: list[str] = field(default_factory=list)

    def available(self) -> bool:
        return self.available_flag

    def egress_primitive(self, allowlist):
        return self.egress_primitive_value

    def run_detached(self, argv):
        self.calls.append("run_detached")
        return worker_runtime.RunResult(0, "container-x\n", "", "container-x")

    def stop(self, container_ref, *, signal="SIGTERM"):
        self.calls.append("stop")
        return worker_runtime.RunResult(0, "", "", container_ref)


class FakeBroker:
    def __init__(self):
        self.revoked = []

    def grant(self, secret_name, ttl_seconds):
        return worker_runtime.BrokerGrant(
            broker_grant_id=f"grant-{secret_name}",
            secret_name=secret_name, mode="env",
            granted_at="2026-05-25T05:33:05Z", ttl_seconds=ttl_seconds,
        )

    def revoke(self, broker_grant_id):
        self.revoked.append(broker_grant_id)
        return "2026-05-25T06:00:00Z"


class FakeSpawnLauncher:
    def __init__(self):
        self.calls = []

    def launch(self, plan):
        self.calls.append(plan)
        return worker_spawn.WorkerLaunchOutcome(
            spawned=True,
            attached=False,
            terminal={
                "kind": "tmux",
                "session_id": plan.worker_id,
                "window_id": "worker",
                "pane_id": "%99",
            },
            events_ref=f"{plan.worktree_path}/.ce/state/workers/{plan.worker_id}/events.jsonl",
            seat_record_ref=f"{plan.worktree_path}/.ce/state/active-work-ledger/seats/{plan.worker_id}.yaml",
            seat_lifecycle_state="active",
        )


class FakeRunSeeder:
    def __init__(self):
        self.calls = []

    def seed(self, **kwargs):
        self.calls.append(kwargs)
        return worker_run.render_seed_instruction(
            prompt_path=kwargs["prompt_path"],
            findings_path=kwargs["findings_path"],
        )


class FakeRunCollector:
    def __init__(self):
        self.calls = []

    def collect(self, **kwargs):
        self.calls.append(kwargs)
        kwargs["findings_path"].write_text(
            yaml.safe_dump(
                {
                    "status": "completed",
                    "summary": "cli round trip",
                    "findings": [{"kind": "cli", "message": "ok"}],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return worker_run.normalize_findings(kwargs["findings_path"])


def _write(path: Path, record: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _setup(tmp_path: Path) -> dict[str, Any]:
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _write(awl / "claims" / CONTROLLER / f"{LANE}.yaml", {
        "kind": "active-work-ledger-record", "record_type": "claim", "schema_version": "1",
        "controller_id": CONTROLLER, "lane_id": LANE, "record_timestamp": "2026-05-25T05:00:00Z",
        "worktree_path": f"/worktrees/{LANE}", "envelope_ref": f".hermes/envelopes/{LANE}.md",
        "lease_seconds": 3600, "claimed_at": "2026-05-25T05:00:00Z",
        "last_heartbeat_at": "9999-01-01T00:00:00Z",
    })
    _write(awl / "leases" / CONTROLLER / f"{LANE}.yaml", {
        "kind": "worktree-lease-record", "record_type": "worktree_lease", "schema_version": "1",
        "controller_id": CONTROLLER, "lane_id": LANE, "record_timestamp": "2026-05-25T05:00:00Z",
        "lease_id": "lease-001", "worktree_path": f"/worktrees/{LANE}",
        "acquired_at": "2026-05-25T05:00:00Z", "lease_seconds": 3600,
        "expires_at": "9999-01-01T00:00:00Z",
    })
    policy = _write(tmp_path / "governance" / "policies" / "worker-container" / "p.yaml", {
        "kind": "worker-container-policy-record", "record_type": "worker_container_policy",
        "schema_version": "1", "policy_id": "podman-verification-v1", "policy_sha": _POLICY_SHA,
        "role": "verification", "runtime_engine": "podman-rootless",
        "image_ref": {"name": "ghcr.io/example/verification:latest", "sha": _IMAGE_SHA},
        "mount_manifest": [{"path": "governance", "mode": "ro"}],
        "egress_allowlist": [], "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False, "grant_authority": "controller",
    })
    return {"awl": awl, "policy": policy, "cir": tmp_path / "container-instances"}


def _allocate_argv(env, instance_id="inst-cli-001") -> list[str]:
    return [
        "worker", "allocate",
        "--policy", str(env["policy"]),
        "--controller-id", CONTROLLER, "--lane-id", LANE,
        "--claim-ref", f"claims/{CONTROLLER}/{LANE}.yaml",
        "--lease-ref", f"leases/{CONTROLLER}/{LANE}.yaml",
        "--active-work-ledger-root", str(env["awl"]),
        "--container-instance-root", str(env["cir"]),
        "--instance-id", instance_id,
    ]


def test_worker_allocate_happy_path(tmp_path, monkeypatch, capsys):
    env = _setup(tmp_path)
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    monkeypatch.setattr(ce_cli, "_make_worker_runner", lambda: runner)
    monkeypatch.setattr(ce_cli, "_make_worker_broker", lambda: broker)

    assert ce_cli.main(_allocate_argv(env)) == 0
    instance_path = env["cir"] / LANE / "inst-cli-001.yaml"
    assert instance_path.is_file()
    assert "run_detached" in runner.calls


def test_worker_allocate_fails_closed_without_podman(tmp_path, monkeypatch, capsys):
    env = _setup(tmp_path)
    # Force the Podman-unavailable condition test-side so this assertion does not
    # depend on the ambient host/CI runner lacking Podman (GitHub runners ship it).
    # We keep the real PodmanCommandRunner and the real allocate code path via the
    # default factories: only the command resolver it consults (`shutil.which`) is
    # forced to report podman absent — exactly the seam that
    # ``PodmanCommandRunner.available()`` gates the fail-closed refusal on.
    real_which = worker_runtime.shutil.which
    monkeypatch.setattr(
        worker_runtime.shutil,
        "which",
        lambda cmd, *args, **kwargs: (
            None if cmd == "podman" else real_which(cmd, *args, **kwargs)
        ),
    )

    rc = ce_cli.main(_allocate_argv(env))
    assert rc == 1
    err = capsys.readouterr().err
    assert "G5-PODMAN-UNAVAILABLE" in err
    assert not (env["cir"] / LANE / "inst-cli-001.yaml").exists()


def test_worker_terminate_happy_path(tmp_path, monkeypatch, capsys):
    env = _setup(tmp_path)
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    monkeypatch.setattr(ce_cli, "_make_worker_runner", lambda: runner)
    monkeypatch.setattr(ce_cli, "_make_worker_broker", lambda: broker)
    assert ce_cli.main(_allocate_argv(env)) == 0

    rc = ce_cli.main([
        "worker", "terminate",
        "--instance-id", "inst-cli-001", "--claim-id", LANE,
        "--container-instance-root", str(env["cir"]),
        "--reason", "normal_release",
    ])
    assert rc == 0
    record = yaml.safe_load((env["cir"] / LANE / "inst-cli-001.yaml").read_text())
    assert record["stopped_at"] is not None
    assert "grant-model-provider-key" in broker.revoked


def test_worker_gc_happy_path(tmp_path, monkeypatch, capsys):
    env = _setup(tmp_path)
    runner, broker = FakeRunner(available_flag=True), FakeBroker()
    monkeypatch.setattr(ce_cli, "_make_worker_runner", lambda: runner)
    monkeypatch.setattr(ce_cli, "_make_worker_broker", lambda: broker)
    # An orphan: released claim, still running.
    _write(env["cir"] / "pco-released" / "inst-orphan.yaml", {
        "kind": "container-instance-record", "record_type": "container_instance",
        "schema_version": "1", "instance_id": "inst-orphan",
        "policy_ref": {"policy_id": "podman-implementer-v1", "policy_sha": _POLICY_SHA,
                       "image_sha": _IMAGE_SHA},
        "image_sha": _IMAGE_SHA, "claim_id": "pco-released", "lease_id": "lease-001",
        "started_at": "2026-05-25T05:33:05Z", "stopped_at": None, "exit_code": None,
        "mount_manifest_applied": [{"path": "governance", "mode": "ro", "source": "policy"}],
        "secret_grants": [], "egress_allowlist_applied": [], "enforcement_primitive": "none",
        "policy_sha": _POLICY_SHA, "claim_released_at": "2026-05-25T07:00:00Z",
    })
    rc = ce_cli.main(["worker", "gc", "--container-instance-root", str(env["cir"])])
    assert rc == 0
    reaped = yaml.safe_load((env["cir"] / "pco-released" / "inst-orphan.yaml").read_text())
    assert reaped["stopped_at"] is not None


def test_worker_help_is_reachable():
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(["worker"])
    assert exc.value.code == 0


def test_worker_run_help_is_discoverable(capsys):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(["worker", "--help"])
    assert exc.value.code == 0
    assert "run" in capsys.readouterr().out


def _one_shot_worktree(tmp_path: Path) -> tuple[Path, Path, str]:
    worktree = tmp_path / "worker"
    (worktree / "governance" / "policies").mkdir(parents=True)
    source_policy = Path(__file__).resolve().parents[3] / "governance" / "policies" / "codex-one-shot-launch-v1.yaml"
    (worktree / "governance" / "policies" / source_policy.name).write_bytes(source_policy.read_bytes())
    (worktree / "governance").mkdir(exist_ok=True)
    (worktree / "validators").mkdir()
    (worktree / ".claude" / "agents").mkdir(parents=True)
    for role in ("architect_research", "implementer"):
        (worktree / ".claude" / "agents" / f"{role}.md").write_text(
            f"# governed {role}\n", encoding="utf-8"
        )
    brief = worktree / ".ce" / "briefs" / "task.md"
    brief.parent.mkdir(parents=True)
    brief.write_text("bounded cli brief\n", encoding="utf-8")
    (worktree / ".ce" / "state").mkdir()
    return worktree, brief, hashlib.sha256(brief.read_bytes()).hexdigest()


def test_worker_launch_dry_run_is_json_and_never_constructs_a_runner(tmp_path, monkeypatch, capsys):
    worktree, brief, digest = _one_shot_worktree(tmp_path)
    called = []
    monkeypatch.setattr(ce_cli, "_make_codex_one_shot_runner", lambda: called.append(True))
    monkeypatch.setattr(
        ce_cli, "_make_codex_launcher_filesystem", lambda: __import__(
            "validators.tests.unit.test_codex_worker_launcher", fromlist=["HermeticFilesystem"]
        ).HermeticFilesystem()
    )
    monkeypatch.setattr(
        ce_cli, "_make_codex_version_probe", lambda: __import__(
            "validators.tests.unit.test_codex_worker_launcher", fromlist=["FixedVersionProbe"]
        ).FixedVersionProbe()
    )
    assert ce_cli.main([
        "worker", "launch", "--dry-run", "--json",
        "--role", "architect_research", "--venue", "dev1-local", "--worktree", str(worktree),
        "--brief", str(brief), "--brief-sha256", digest,
        "--run-id", "cli-test",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["run_id"] == "cli-test"
    assert payload["argv"][-1] == "-"
    assert called == []


def test_worker_launch_refuses_removed_policy_binary_and_stdin_overrides(tmp_path, monkeypatch, capsys):
    worktree, brief, digest = _one_shot_worktree(tmp_path)
    monkeypatch.setattr(ce_cli, "_make_codex_one_shot_runner", lambda: pytest.fail("runner invoked"))
    for removed in ("--policy", "--codex-binary", "--stdin", "--sandbox"):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main([
                "worker", "launch", "--role", "architect_research", "--venue", "dev1-local",
                "--worktree", str(worktree), "--brief", str(brief),
                "--brief-sha256", digest, removed, "untrusted",
            ])
        assert exc.value.code == 2
        capsys.readouterr()


class FakeOneShotRunner:
    def __init__(self, *, returncode: int = 0, error: Exception | None = None) -> None:
        self.returncode = returncode
        self.error = error

    def run(self, argv, *, stdin: bytes, provider_credential_env_names) -> int:
        if self.error is not None:
            raise self.error
        return self.returncode


def _patch_one_shot_preflight(monkeypatch, runner: FakeOneShotRunner) -> None:
    support = __import__(
        "validators.tests.unit.test_codex_worker_launcher",
        fromlist=["HermeticFilesystem", "FixedVersionProbe"],
    )
    monkeypatch.setattr(ce_cli, "_make_codex_one_shot_runner", lambda: runner)
    monkeypatch.setattr(
        ce_cli, "_make_codex_launcher_filesystem", lambda: support.HermeticFilesystem()
    )
    monkeypatch.setattr(
        ce_cli, "_make_codex_version_probe", lambda: support.FixedVersionProbe()
    )


def _worker_launch_argv(worktree: Path, brief: Path, digest: str) -> list[str]:
    return [
        "worker", "launch", "--role", "architect_research", "--venue", "dev1-local",
        "--worktree", str(worktree), "--brief", str(brief),
        "--brief-sha256", digest, "--run-id", "cli-reporting-test",
    ]


@pytest.mark.parametrize("venue", ["dgx-relay", "dev1-local"])
def test_worker_launch_refuses_implementer_native_venues_before_runner_construction(
    tmp_path, monkeypatch, capsys, venue
) -> None:
    worktree, brief, digest = _one_shot_worktree(tmp_path)
    support = __import__(
        "validators.tests.unit.test_codex_worker_launcher",
        fromlist=["HermeticFilesystem", "FixedVersionProbe"],
    )
    monkeypatch.setattr(
        ce_cli, "_make_codex_launcher_filesystem", lambda: support.HermeticFilesystem()
    )
    monkeypatch.setattr(
        ce_cli, "_make_codex_version_probe", lambda: support.FixedVersionProbe()
    )
    monkeypatch.setattr(
        ce_cli, "_make_codex_one_shot_runner", lambda: pytest.fail("runner constructed")
    )
    assert ce_cli.main([
        "worker", "launch", "--role", "implementer", "--venue", venue,
        "--worktree", str(worktree), "--brief", str(brief),
        "--brief-sha256", digest, "--run-id", "cli-refusal-test",
    ]) == 1
    assert "not attested for required isolation" in capsys.readouterr().err


def test_worker_launch_oserror_is_governed_refusal_without_traceback(
    tmp_path, monkeypatch, capsys
) -> None:
    worktree, brief, digest = _one_shot_worktree(tmp_path)
    _patch_one_shot_preflight(monkeypatch, FakeOneShotRunner(error=OSError("exec failed")))
    assert ce_cli.main(_worker_launch_argv(worktree, brief, digest)) == 1
    captured = capsys.readouterr()
    assert "ce worker launch refused" in captured.err
    assert "Traceback" not in captured.err
    assert "completed" not in captured.out + captured.err


def test_worker_launch_nonzero_reports_failed_refused_and_returns_child_status(
    tmp_path, monkeypatch, capsys
) -> None:
    worktree, brief, digest = _one_shot_worktree(tmp_path)
    _patch_one_shot_preflight(monkeypatch, FakeOneShotRunner(returncode=23))
    assert ce_cli.main(_worker_launch_argv(worktree, brief, digest)) == 23
    captured = capsys.readouterr()
    assert "failed/refused" in captured.err
    assert "status 23" in captured.err
    assert "completed" not in captured.out + captured.err


def test_worker_launch_zero_reports_completion(tmp_path, monkeypatch, capsys) -> None:
    worktree, brief, digest = _one_shot_worktree(tmp_path)
    _patch_one_shot_preflight(monkeypatch, FakeOneShotRunner())
    assert ce_cli.main(_worker_launch_argv(worktree, brief, digest)) == 0
    captured = capsys.readouterr()
    assert "ce worker launch: completed cli-reporting-test" in captured.out
    assert captured.err == ""


def test_worker_spawn_dry_run_json_has_no_side_effect(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    worktree = tmp_path / "worker"
    worktree.mkdir()

    rc = ce_cli.main([
        "worker", "spawn",
        "--role", "researcher",
        "--harness", "claude",
        "--worktree", str(worktree),
        "--scope-id", "ce-ops#163",
        "--brief", "research without recording this body",
        "--dry-run",
        "--json",
    ])

    assert rc == 0
    payload = yaml.safe_load(capsys.readouterr().out)
    assert payload["written"] is False
    assert payload["record"]["role"] == "researcher"
    assert payload["record"]["lane_kind"] == "read-only"
    assert "research without recording this body" not in str(payload)
    assert not (worktree / ".ce/state/workers").exists()


def test_worker_spawn_live_uses_injected_launcher_and_scrubs_tokens(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    worktree = tmp_path / "worker"
    worktree.mkdir()
    controller_home = tmp_path / "controller-home"
    (controller_home / ".config" / "gh").mkdir(parents=True)
    (controller_home / ".ssh").mkdir()
    launcher = FakeSpawnLauncher()
    monkeypatch.setattr(ce_cli, "_make_worker_spawn_launcher", lambda: launcher)
    monkeypatch.setenv("HOME", str(controller_home))
    monkeypatch.setenv("GH_CONFIG_DIR", str(controller_home / ".config" / "gh"))
    monkeypatch.setenv("SSH_AUTH_SOCK", str(controller_home / ".ssh" / "agent.sock"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(controller_home / ".aws" / "config"))
    monkeypatch.setenv("GH_TOKEN", "ghp_super_secret")
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_secret")

    rc = ce_cli.main([
        "worker", "spawn",
        "--role", "implementer",
        "--harness", "claude",
        "--worktree", str(worktree),
        "--scope-id", "ce-ops#163",
        "--brief", "build without recording this body",
        "--parent-id", "ce-dev-4",
        "--json",
    ])

    assert rc == 0
    payload = yaml.safe_load(capsys.readouterr().out)
    assert payload["written"] is True
    assert len(launcher.calls) == 1
    assert "GH_TOKEN" not in launcher.calls[0].child_env
    assert "GITHUB_TOKEN" not in launcher.calls[0].child_env
    assert "GH_CONFIG_DIR" not in launcher.calls[0].child_env
    assert "SSH_AUTH_SOCK" not in launcher.calls[0].child_env
    assert "AWS_CONFIG_FILE" not in launcher.calls[0].child_env
    assert launcher.calls[0].child_env["HOME"] != str(controller_home)
    assert Path(launcher.calls[0].child_env["HOME"]).is_relative_to(worktree)
    record_path = Path(payload["record_path"])
    record_text = record_path.read_text(encoding="utf-8")
    stdout_text = yaml.safe_dump(payload, sort_keys=True)
    assert "ghp_super_secret" not in record_text
    assert "github_pat_secret" not in record_text
    assert str(controller_home / ".config" / "gh") not in record_text
    assert str(controller_home / ".ssh" / "agent.sock") not in record_text
    assert "build without recording this body" not in record_text
    assert "ghp_super_secret" not in stdout_text
    assert "github_pat_secret" not in stdout_text
    assert str(controller_home / ".config" / "gh") not in stdout_text
    assert str(controller_home / ".ssh" / "agent.sock") not in stdout_text


def test_worker_run_cli_round_trip_uses_injected_launch_and_collector(
    tmp_path, monkeypatch, capsys
):
    repo = tmp_path / "repo"
    roles = repo / ".claude" / "agents"
    roles.mkdir(parents=True)
    (roles / "architect_research.md").write_text(
        "---\n"
        "name: architect_research\n"
        "tools: Read, Grep, Glob, WebFetch, WebSearch\n"
        "---\n"
        "# Architect Research\n",
        encoding="utf-8",
    )
    brief = tmp_path / "brief.md"
    brief.write_text("research this\n", encoding="utf-8")
    launcher = FakeSpawnLauncher()
    seeder = FakeRunSeeder()
    collector = FakeRunCollector()
    monkeypatch.setattr(ce_cli, "_make_worker_run_launcher", lambda: launcher)
    monkeypatch.setattr(ce_cli, "_make_worker_run_seeder", lambda: seeder)
    monkeypatch.setattr(ce_cli, "_make_worker_run_collector", lambda timeout: collector)

    rc = ce_cli.main([
        "worker", "run",
        "--role", "architect_research",
        "--brief", str(brief),
        "--repo-root", str(repo),
        "--worktree", str(repo),
        "--run-id", "ce259-cli",
        "--worker-id", "ce259-cli-worker",
        "--json",
    ])

    assert rc == 0
    payload = yaml.safe_load(capsys.readouterr().out)
    assert payload["run_id"] == "ce259-cli"
    assert payload["role"]["name"] == "architect_research"
    assert payload["findings"]["findings"] == [{"kind": "cli", "message": "ok"}]
    assert len(launcher.calls) == 1
    assert launcher.calls[0].role == "architect_research"
    assert len(seeder.calls) == 1
    assert str(seeder.calls[0]["prompt_path"]).endswith("prompt.md")
    assert str(seeder.calls[0]["findings_path"]).endswith("findings.yaml")
    assert len(collector.calls) == 1


def test_worker_run_cli_defaults_worktree_to_repo_root(
    tmp_path, monkeypatch, capsys
):
    repo = tmp_path / "repo"
    roles = repo / ".claude" / "agents"
    roles.mkdir(parents=True)
    (roles / "architect_research.md").write_text(
        "---\n"
        "name: architect_research\n"
        "tools: Read, Grep, Glob, WebFetch, WebSearch\n"
        "---\n"
        "# Architect Research\n",
        encoding="utf-8",
    )
    brief = tmp_path / "brief.md"
    brief.write_text("research this\n", encoding="utf-8")
    launcher = FakeSpawnLauncher()
    seeder = FakeRunSeeder()
    collector = FakeRunCollector()
    monkeypatch.chdir(repo)
    monkeypatch.setattr(ce_cli, "_make_worker_run_launcher", lambda: launcher)
    monkeypatch.setattr(ce_cli, "_make_worker_run_seeder", lambda: seeder)
    monkeypatch.setattr(ce_cli, "_make_worker_run_collector", lambda timeout: collector)

    rc = ce_cli.main([
        "worker", "run",
        "--role", "architect_research",
        "--brief", str(brief),
        "--repo-root", ".",
        "--run-id", "ce259-default-worktree",
        "--worker-id", "ce259-default-worker",
        "--json",
    ])

    assert rc == 0
    payload = yaml.safe_load(capsys.readouterr().out)
    assert payload["run_id"] == "ce259-default-worktree"
    assert len(launcher.calls) == 1
    assert launcher.calls[0].worktree_path == repo.resolve()
    assert launcher.calls[0].role == "architect_research"


def test_worker_run_cli_unknown_role_fails_closed(tmp_path, capsys):
    repo = tmp_path / "repo"
    (repo / ".claude" / "agents").mkdir(parents=True)
    brief = tmp_path / "brief.md"
    brief.write_text("brief\n", encoding="utf-8")

    rc = ce_cli.main([
        "worker", "run",
        "--role", "unknown",
        "--brief", str(brief),
        "--repo-root", str(repo),
    ])

    assert rc == 1
    assert "CE259-WORKER-RUN-ROLE-UNKNOWN" in capsys.readouterr().err
