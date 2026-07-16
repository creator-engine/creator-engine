"""Hermetic contracts for the policy-bound Codex one-shot launcher."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from creator_engine_validator import codex_worker_launcher as launcher


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "governance" / "policies" / "codex-one-shot-launch-v1.yaml"
PINNED_BINARY = "/opt/creator-engine/codex/0.145.0-alpha.9/bin/codex"


class HermeticFilesystem(launcher.RealLauncherFilesystem):
    def __init__(
        self,
        *,
        binary_exists: bool = True,
        binary_executable: bool = True,
        binary_realpath: str = PINNED_BINARY,
    ) -> None:
        self.binary_exists = binary_exists
        self.binary_executable = binary_executable
        self.binary_realpath = binary_realpath

    def realpath(self, path: str) -> str:
        if os.path.normpath(path) == PINNED_BINARY:
            return self.binary_realpath
        return super().realpath(path)

    def is_file(self, path: str) -> bool:
        if os.path.normpath(path) in {PINNED_BINARY, self.binary_realpath}:
            return self.binary_exists
        return super().is_file(path)

    def is_executable(self, path: str) -> bool:
        if os.path.normpath(path) in {PINNED_BINARY, self.binary_realpath}:
            return self.binary_executable
        return super().is_executable(path)


class FixedVersionProbe:
    def __init__(self, version: str = "0.145.0-alpha.9") -> None:
        self.version = version
        self.calls: list[str] = []

    def probe(self, binary: str) -> str:
        self.calls.append(binary)
        return self.version


class RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], bytes]] = []

    def run(self, argv, *, stdin: bytes, provider_credential_env_names) -> int:
        self.calls.append((tuple(argv), stdin))
        assert tuple(provider_credential_env_names) == ("OPENAI_API_KEY",)
        return 0


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    root = tmp_path / "allocated-worker"
    (root / "governance" / "policies").mkdir(parents=True)
    shutil.copy2(POLICY_PATH, root / "governance" / "policies" / POLICY_PATH.name)
    (root / "validators").mkdir()
    (root / ".claude" / "agents").mkdir(parents=True)
    for role in ("architect_research", "implementer", "reviewer", "verification"):
        (root / ".claude" / "agents" / f"{role}.md").write_bytes(
            f"# Canonical {role}\nexact policy bytes\n".encode()
        )
    (root / ".ce" / "briefs").mkdir(parents=True)
    (root / ".ce" / "state").mkdir()
    return root


def policy(worktree: Path) -> launcher.CodexOneShotPolicy:
    return launcher.load_canonical_policy(worktree, filesystem=HermeticFilesystem())


def governed_input(
    worktree: Path,
    *,
    role: str = "implementer",
    brief_path: Path | None = None,
    brief_sha256: str | None = None,
) -> launcher.GovernedWorkerInput:
    brief = brief_path or (worktree / ".ce" / "briefs" / "task.md")
    if brief_path is None:
        brief.write_bytes(b"perform the bounded task\n")
    digest = brief_sha256 or hashlib.sha256(brief.read_bytes()).hexdigest()
    return launcher.load_governed_worker_input(
        worktree=str(worktree),
        role=role,
        brief_path=str(brief),
        brief_sha256=digest,
        filesystem=HermeticFilesystem(),
    )


def plan(worktree: Path, **overrides) -> launcher.CodexWorkerLaunchPlan:
    values = {
        "policy": policy(worktree),
        "governed_input": governed_input(worktree),
        "role": "implementer",
        "venue": "dev1-local",
        "worktree": str(worktree),
        "run_id": "test-run",
        "filesystem": HermeticFilesystem(),
        "version_probe": FixedVersionProbe(),
    }
    values.update(overrides)
    return launcher.build_launch_plan(**values)


def test_canonical_policy_pins_deployment_version_and_actual_venues(worktree: Path) -> None:
    loaded = policy(worktree)
    assert loaded.version == "0.145.0-alpha.9"
    assert set(loaded.venue_names) == {"dgx-relay", "vps-tmux", "dev1-local", "in-seat"}
    assert loaded.provider_credentials_for("architect_research") == ("OPENAI_API_KEY",)
    assert loaded.provider_credentials_for("implementer") == ("OPENAI_API_KEY",)
    assert loaded.provider_credentials_for("reviewer") == ()
    assert loaded.provider_credentials_for("verification") == ()


@pytest.mark.parametrize(
    ("venue", "role", "sandbox"),
    [
        (venue, role, sandbox)
        for venue, values in {
            "dgx-relay": {
                "architect_research": "read-only",
                "implementer": "workspace-write",
                "reviewer": "read-only",
                "verification": "read-only",
            },
            "dev1-local": {
                "architect_research": "read-only",
                "implementer": "workspace-write",
                "reviewer": "read-only",
                "verification": "read-only",
            },
            "vps-tmux": {
                "architect_research": None,
                "implementer": None,
                "reviewer": None,
                "verification": None,
            },
            "in-seat": {
                "architect_research": None,
                "implementer": None,
                "reviewer": None,
                "verification": None,
            },
        }.items()
        for role, sandbox in values.items()
    ],
)
def test_role_venue_matrix_is_complete_and_fail_closed(
    worktree: Path, venue: str, role: str, sandbox: str | None
) -> None:
    loaded = policy(worktree)
    if sandbox is None:
        with pytest.raises(launcher.CodexWorkerLaunchError, match="not attested"):
            loaded.sandbox_for(role=role, venue=venue)
    else:
        assert loaded.sandbox_for(role=role, venue=venue) == sandbox


def test_plan_has_exact_real_codex_argv_and_digest_only_metadata(worktree: Path) -> None:
    built = plan(worktree)
    assert built.model == "gpt-5.6-terra"
    assert built.effort == "high"
    assert built.argv == (
        PINNED_BINARY,
        "exec",
        "--ephemeral",
        "-m",
        "gpt-5.6-terra",
        "-c",
        "model_reasoning_effort=high",
        "-c",
        "features.multi_agent=false",
        "-c",
        "features.multi_agent_v2=false",
        "-s",
        "workspace-write",
        "-C",
        str(worktree),
        "--add-dir",
        f"{worktree}/governance",
        "--add-dir",
        f"{worktree}/validators",
        "-o",
        f"{worktree}/.ce/state/test-run.json",
        "-",
    )
    serialized = str(built.to_dict())
    assert "perform the bounded task" not in serialized
    assert built.brief_sha256 in serialized
    assert built.role_policy_sha256 in serialized


def test_governed_input_frames_exact_canonical_role_and_verified_brief_bytes(worktree: Path) -> None:
    loaded = governed_input(worktree)
    role_bytes = (worktree / ".claude" / "agents" / "implementer.md").read_bytes()
    brief_bytes = (worktree / ".ce" / "briefs" / "task.md").read_bytes()
    assert loaded.stdin.endswith(role_bytes + brief_bytes)
    header = loaded.stdin[: -(len(role_bytes) + len(brief_bytes))]
    assert header.startswith(b"CE-GOVERNED-CODEX-WORKER-PROMPT-V1\n")
    assert f"ROLE-SHA256 {hashlib.sha256(role_bytes).hexdigest()}\n".encode() in header
    assert f"ROLE-BYTES {len(role_bytes)}\n".encode() in header
    assert f"BRIEF-SHA256 {hashlib.sha256(brief_bytes).hexdigest()}\n".encode() in header
    assert f"BRIEF-BYTES {len(brief_bytes)}\n\n".encode() in header


@pytest.mark.parametrize("digest", ["A" * 64, "f" * 63, "0" * 64])
def test_governed_input_refuses_noncanonical_or_mismatched_digest(worktree: Path, digest: str) -> None:
    with pytest.raises(launcher.CodexWorkerLaunchError, match="brief SHA-256"):
        governed_input(worktree, brief_sha256=digest)


def test_governed_input_refuses_brief_escape_symlink_and_nonregular(worktree: Path) -> None:
    outside = worktree.parent / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    link = worktree / ".ce" / "briefs" / "link.md"
    link.symlink_to(outside)
    directory = worktree / ".ce" / "briefs" / "directory"
    directory.mkdir()
    missing = worktree / ".ce" / "briefs" / "missing.md"
    for candidate, message in [
        (outside, "canonical area"),
        (link, "symlink"),
        (directory, "regular readable file"),
        (missing, "regular readable file"),
    ]:
        with pytest.raises(launcher.CodexWorkerLaunchError, match=message):
            governed_input(worktree, brief_path=candidate, brief_sha256="0" * 64)


def test_governed_input_refuses_replaced_canonical_role_policy(worktree: Path) -> None:
    role_path = worktree / ".claude" / "agents" / "implementer.md"
    role_path.unlink()
    role_path.symlink_to(worktree / ".claude" / "agents" / "reviewer.md")
    with pytest.raises(launcher.CodexWorkerLaunchError, match="role policy.*symlink"):
        governed_input(worktree)


def test_canonical_policy_rejects_symlink_replacement(worktree: Path) -> None:
    canonical = worktree / "governance" / "policies" / POLICY_PATH.name
    replacement = worktree / "replacement.yaml"
    replacement.write_bytes(POLICY_PATH.read_bytes())
    canonical.unlink()
    canonical.symlink_to(replacement)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="launcher policy.*symlink"):
        launcher.load_canonical_policy(worktree, filesystem=HermeticFilesystem())


def test_worktree_and_canonical_directories_are_real_existing_directories(worktree: Path) -> None:
    missing = worktree / "validators"
    missing.rmdir()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="canonical add-dir.*directory"):
        plan(worktree)
    missing.write_text("not a directory\n", encoding="utf-8")
    with pytest.raises(launcher.CodexWorkerLaunchError, match="canonical add-dir.*directory"):
        plan(worktree)


def test_canonical_add_dir_symlink_is_refused(worktree: Path) -> None:
    validators = worktree / "validators"
    validators.rmdir()
    outside = worktree.parent / "outside-validators"
    outside.mkdir()
    validators.symlink_to(outside, target_is_directory=True)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="canonical add-dir.*symlink"):
        plan(worktree)


def test_worktree_symlink_is_refused(worktree: Path) -> None:
    link = worktree.parent / "linked-worker"
    link.symlink_to(worktree, target_is_directory=True)
    loaded = policy(worktree)
    worker_input = governed_input(worktree)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="worktree.*symlink"):
        launcher.build_launch_plan(
            policy=loaded,
            governed_input=worker_input,
            role="implementer",
            venue="dev1-local",
            worktree=str(link),
            filesystem=HermeticFilesystem(),
            version_probe=FixedVersionProbe(),
        )


def test_existing_output_symlink_or_nonregular_node_is_refused(worktree: Path) -> None:
    output = worktree / ".ce" / "state" / "test-run.json"
    outside = worktree.parent / "outside-output.json"
    outside.write_text("do not overwrite\n", encoding="utf-8")
    output.symlink_to(outside)
    with pytest.raises(launcher.CodexWorkerLaunchError, match="output.*symlink"):
        plan(worktree)
    output.unlink()
    output.mkdir()
    with pytest.raises(launcher.CodexWorkerLaunchError, match="output.*regular file"):
        plan(worktree)


@pytest.mark.parametrize(
    ("filesystem", "probe", "message"),
    [
        (HermeticFilesystem(binary_exists=False), FixedVersionProbe(), "regular executable"),
        (HermeticFilesystem(binary_executable=False), FixedVersionProbe(), "regular executable"),
        (
            HermeticFilesystem(binary_realpath="/opt/creator-engine/codex/other/bin/codex"),
            FixedVersionProbe(),
            "version root",
        ),
        (HermeticFilesystem(), FixedVersionProbe("0.144.1"), "version probe"),
    ],
)
def test_binary_preflight_refuses_missing_nonexecutable_escape_or_version_mismatch(
    worktree: Path,
    filesystem: HermeticFilesystem,
    probe: FixedVersionProbe,
    message: str,
) -> None:
    with pytest.raises(launcher.CodexWorkerLaunchError, match=message):
        plan(worktree, filesystem=filesystem, version_probe=probe)


def test_only_explicit_launch_calls_injected_runner_with_verified_bytes(worktree: Path) -> None:
    runner = RecordingRunner()
    worker_input = governed_input(worktree)
    built = plan(worktree, governed_input=worker_input)
    assert runner.calls == []
    assert launcher.launch(built, governed_input=worker_input, runner=runner) == 0
    assert runner.calls == [(built.argv, worker_input.stdin)]


def test_production_runner_uses_isolated_homes_and_scrubs_hostile_ambient_env(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}
    hostile = {
        "PATH": "/runtime/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TERM": "xterm-256color",
        "HOME": str(tmp_path / "host-home"),
        "CODEX_HOME": str(tmp_path / "host-codex"),
        "XDG_CONFIG_HOME": str(tmp_path / "host-config"),
        "GH_TOKEN": "host-gh-secret",
        "GITHUB_TOKEN": "host-github-secret",
        "AWS_ACCESS_KEY_ID": "host-aws-secret",
        "AWS_SECRET_ACCESS_KEY": "host-aws-secret",
        "SSH_AUTH_SOCK": str(tmp_path / "ssh-agent.sock"),
        "GPG_AGENT_INFO": str(tmp_path / "gpg-agent.sock"),
        "CE_CONTROLLER_SOCKET": str(tmp_path / "controller.sock"),
        "CE_SEAT_SOCKET": str(tmp_path / "seat.sock"),
        "GIT_CONFIG_GLOBAL": str(tmp_path / "host-gitconfig"),
        "AWS_CONFIG_FILE": str(tmp_path / "host-aws-config"),
        "OPENAI_API_KEY": "allowed-provider-secret",
        "ANTHROPIC_API_KEY": "unlisted-provider-secret",
        "HOSTILE_AMBIENT": "must-not-survive",
    }

    def fake_run(argv, **kwargs):
        env = kwargs["env"]
        captured.update({"argv": argv, "env": dict(env)})
        for name in (
            "HOME",
            "CODEX_HOME",
            "TMPDIR",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "XDG_DATA_HOME",
        ):
            assert Path(env[name]).is_dir()
            assert Path(env[name]).is_relative_to(Path(env["HOME"]).parent)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    runner = launcher.SubprocessCodexOneShotRunner(environ=hostile)
    assert runner.run(
        ["/pinned/codex", "exec"],
        stdin=b"verified",
        provider_credential_env_names=("OPENAI_API_KEY",),
    ) == 0

    child_env = captured["env"]
    assert isinstance(child_env, dict)
    assert child_env["OPENAI_API_KEY"] == "allowed-provider-secret"
    assert child_env["PATH"] == "/runtime/bin"
    assert child_env["LANG"] == "C.UTF-8"
    assert child_env["LC_ALL"] == "C.UTF-8"
    assert child_env["TERM"] == "xterm-256color"
    invocation_owned = {"HOME", "CODEX_HOME", "XDG_CONFIG_HOME"}
    for name in hostile:
        if name not in {
            "PATH",
            "LANG",
            "LC_ALL",
            "TERM",
            "OPENAI_API_KEY",
            *invocation_owned,
        }:
            assert name not in child_env
    for name in invocation_owned:
        assert name in child_env
        assert child_env[name] != hostile[name]
    assert not Path(child_env["HOME"]).exists()
    assert not Path(child_env["CODEX_HOME"]).exists()


def test_production_runner_refuses_untracked_provider_credential_name() -> None:
    runner = launcher.SubprocessCodexOneShotRunner(environ={"GITHUB_TOKEN": "secret"})
    with pytest.raises(launcher.CodexWorkerLaunchError, match="non-provider credential"):
        runner.run(
            ["/pinned/codex", "exec"],
            stdin=b"verified",
            provider_credential_env_names=("GITHUB_TOKEN",),
        )
