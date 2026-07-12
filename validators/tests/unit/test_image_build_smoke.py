from __future__ import annotations

import io
from pathlib import Path

import pytest

from creator_engine_validator import image_build_smoke as smoke


class FakeRunner:
    def __init__(self, diff: str, *, failures: dict[tuple[str, ...], smoke.CommandResult] | None = None):
        self.diff = diff
        self.failures = failures or {}
        self.calls: list[tuple[list[str], Path, dict[str, str] | None, float | None]] = []

    def __call__(self, argv, cwd, env=None, *, timeout=None):
        command = list(argv)
        self.calls.append((command, cwd, dict(env) if env is not None else None, timeout))
        if command[:4] == ["git", "diff", "--name-status", "-z"]:
            return smoke.CommandResult(0, self.diff, "")
        return self.failures.get(tuple(command), smoke.CommandResult(0, "ok\n", ""))


def _dockerfile(repo: Path, name: str) -> Path:
    path = repo / "deploy" / name / "Dockerfile"
    path.parent.mkdir(parents=True)
    path.write_text("FROM scratch\n", encoding="utf-8")
    return path


def test_select_changed_dockerfiles_is_sorted_deduplicated_and_skips_deleted(tmp_path: Path):
    _dockerfile(tmp_path, "z")
    first = _dockerfile(tmp_path, "a")
    runner = FakeRunner(
        "M\0deploy/z/Dockerfile\0D\0deploy/deleted/Dockerfile\0M\0deploy/a/Dockerfile\0M\0deploy/a/Dockerfile\0"
    )

    assert smoke.select_changed_dockerfiles("base", tmp_path, runner) == (first, tmp_path / "deploy" / "z" / "Dockerfile")


def test_select_changed_dockerfiles_rejects_unsafe_or_nonregular_paths(tmp_path: Path):
    unsafe = FakeRunner("M\0deploy/../Dockerfile\0")
    with pytest.raises(RuntimeError, match="unsafe Dockerfile path"):
        smoke.select_changed_dockerfiles("base", tmp_path, unsafe)

    link = tmp_path / "deploy" / "linked" / "Dockerfile"
    link.parent.mkdir(parents=True)
    link.symlink_to(tmp_path / "outside")
    with pytest.raises(RuntimeError, match="absent or not a regular file"):
        smoke.select_changed_dockerfiles("base", tmp_path, FakeRunner("M\0deploy/linked/Dockerfile\0"))


def test_no_changed_dockerfile_is_a_fast_noop_without_tool_lookup(tmp_path: Path, monkeypatch):
    runner = FakeRunner("M\0README.md\0")
    monkeypatch.setattr(smoke, "_resolve_hadolint", lambda **_kwargs: pytest.fail("tool lookup must not occur"))

    detail = smoke.run_image_build_smoke("base", tmp_path, runner=runner, out=io.StringIO())

    assert detail.startswith("no-op:")
    assert len(runner.calls) == 1


def test_smoke_uses_exact_hadolint_and_buildx_check_argv_without_publish_flags(tmp_path: Path, monkeypatch):
    first = _dockerfile(tmp_path, "a")
    second = _dockerfile(tmp_path, "b")
    runner = FakeRunner("M\0deploy/b/Dockerfile\0M\0deploy/a/Dockerfile\0")
    monkeypatch.setattr(smoke, "_resolve_hadolint", lambda **_kwargs: Path("/verified/hadolint"))

    detail = smoke.run_image_build_smoke("base", tmp_path, runner=runner, out=io.StringIO())

    assert detail.startswith("passed for 2")
    commands = [call[0] for call in runner.calls]
    assert ["/verified/hadolint", "--failure-threshold", "error", first.relative_to(tmp_path).as_posix()] in commands
    assert ["/verified/hadolint", "--failure-threshold", "error", second.relative_to(tmp_path).as_posix()] in commands
    build_commands = [command for command in commands if command[:3] == ["docker", "buildx", "build"]]
    assert build_commands == [
        ["docker", "buildx", "build", "--check", "--progress=plain", "-f", "deploy/a/Dockerfile", str(tmp_path)],
        ["docker", "buildx", "build", "--check", "--progress=plain", "-f", "deploy/b/Dockerfile", str(tmp_path)],
    ]
    assert all("--push" not in command and "--load" not in command for command in build_commands)
    assert all(call[3] == smoke.DEFAULT_SMOKE_TIMEOUT_SECONDS for call in runner.calls[1:])


def test_existing_hadolint_must_be_an_executable_with_exact_pinned_bytes(tmp_path: Path, monkeypatch):
    binary = tmp_path / "hadolint"
    binary.write_bytes(b"pinned")
    binary.chmod(0o755)
    # Stub the arch guard so the hash-verification logic is exercised hermetically
    # on every host (including aarch64 CI seats); the arch guard itself is tested
    # separately in test_selected_tier_refuses_missing_or_wrong_architecture_tools.
    monkeypatch.setattr(smoke, "_require_linux_x86_64", lambda: None)
    monkeypatch.setattr(smoke, "_sha256", lambda _path: smoke.HADOLINT_SHA256)
    assert smoke.verify_hadolint(binary) == binary

    monkeypatch.setattr(smoke, "_sha256", lambda _path: "wrong")
    with pytest.raises(RuntimeError, match="required pinned artifact"):
        smoke.verify_hadolint(binary)


def test_download_refuses_hash_mismatch_before_creating_executable(tmp_path: Path, monkeypatch):
    # Stub the arch guard so the hash-check-before-write logic is exercised
    # hermetically on every host; production refuses aarch64 binaries correctly.
    monkeypatch.setattr(smoke, "_require_linux_x86_64", lambda: None)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"wrong bytes"

    destination = tmp_path / "hadolint"
    with pytest.raises(RuntimeError, match="wrong SHA-256"):
        smoke.provision_hadolint(destination, opener=lambda *_args, **_kwargs: Response())
    assert not destination.exists()


def test_selected_tier_refuses_missing_or_wrong_architecture_tools(tmp_path: Path, monkeypatch):
    _dockerfile(tmp_path, "app")
    runner = FakeRunner("M\0deploy/app/Dockerfile\0")
    monkeypatch.setattr(smoke.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="hadolint is required"):
        smoke.run_image_build_smoke("base", tmp_path, runner=runner, out=io.StringIO())

    monkeypatch.setattr(smoke.platform, "system", lambda: "Darwin")
    with pytest.raises(RuntimeError, match="wrong-architecture"):
        smoke._require_linux_x86_64()


@pytest.mark.parametrize(
    ("failing_command", "expected"),
    [
        (("/verified/hadolint", "--failure-threshold", "error", "deploy/app/Dockerfile"), "hadolint deploy/app/Dockerfile failed"),
        (("docker", "buildx", "build", "--check", "--progress=plain", "-f", "deploy/app/Dockerfile", "{repo_root}"), "Docker Buildx --check deploy/app/Dockerfile failed"),
    ],
)
def test_lint_and_build_failures_are_file_scoped(tmp_path: Path, monkeypatch, failing_command, expected):
    _dockerfile(tmp_path, "app")
    runner = FakeRunner("M\0deploy/app/Dockerfile\0")
    monkeypatch.setattr(smoke, "_resolve_hadolint", lambda **_kwargs: Path("/verified/hadolint"))
    runner.failures[tuple(part.format(repo_root=tmp_path) for part in failing_command)] = smoke.CommandResult(1, "", "bad input")

    with pytest.raises(RuntimeError, match=expected):
        smoke.run_image_build_smoke("base", tmp_path, runner=runner, out=io.StringIO())


def test_timeout_is_a_hard_failure(tmp_path: Path, monkeypatch):
    _dockerfile(tmp_path, "app")
    runner = FakeRunner(
        "M\0deploy/app/Dockerfile\0",
        failures={("docker", "buildx", "version"): smoke.CommandResult(124, "", "timed out")},
    )
    monkeypatch.setattr(smoke, "_resolve_hadolint", lambda **_kwargs: Path("/verified/hadolint"))

    with pytest.raises(RuntimeError, match="Docker Buildx availability timed out"):
        smoke.run_image_build_smoke("base", tmp_path, runner=runner, out=io.StringIO())
