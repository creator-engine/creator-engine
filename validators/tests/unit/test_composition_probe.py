from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from creator_engine_validator import composition_probe as probe
from creator_engine_validator.composition_probe import (
    CLEANUP_ABORT,
    GREEN,
    MERGE_ABORT,
    MERGE_CONFLICT,
    RED_DETERMINISTIC,
    RED_FLAKE,
    VALIDATOR_ABORT,
    MergeSimulation,
    ValidationAttempt,
    probe_composition,
)


MAIN = "a" * 40
HEAD = "b" * 40
TREE = "d" * 40
BASE = "c" * 40
PR = {"number": 42, "head_sha": HEAD}


@pytest.fixture
def fresh_merge():
    paths: list[Path] = []

    def merge(_repo_path: str, _main: str, _head: str, tmp_dir: str) -> MergeSimulation:
        path = Path(tmp_dir)
        path.mkdir()
        paths.append(path)
        return MergeSimulation("clean", merge_base=BASE, tree_ref=TREE, repo_path="/ignored")

    merge.paths = paths  # type: ignore[attr-defined]
    return merge


def test_green_composition_validates_once_from_owned_child(fresh_merge, tmp_path):
    seen: list[tuple[str, str]] = []
    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=fresh_merge,
        validator_fn=lambda repo, tree: seen.append((repo, tree)) or ValidationAttempt(True, "green"),
        tmp_dir=tmp_path,
    )

    assert result.outcome == GREEN
    assert result.validation_attempt_count == 1
    assert result.validation_output == "green"
    assert seen == [(str(fresh_merge.paths[0]), TREE)]
    assert not fresh_merge.paths[0].parent.exists()
    assert tmp_path.exists()


def test_merge_conflict_never_validates(tmp_path):
    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=lambda *_: MergeSimulation("conflict", merge_base=BASE),
        validator_fn=lambda *_: pytest.fail("validation must not run"),
        tmp_dir=tmp_path,
    )
    assert result.outcome == MERGE_CONFLICT
    assert result.validation_attempt_count == 0


def test_merge_abort_never_validates(tmp_path):
    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=lambda *_: MergeSimulation("abort", merge_base=BASE),
        validator_fn=lambda *_: pytest.fail("validation must not run"),
        tmp_dir=tmp_path,
    )
    assert result.outcome == MERGE_ABORT
    assert result.validation_attempt_count == 0
    assert result.error == "composition setup aborted"


def test_retry_uses_fresh_owned_state_and_cannot_inherit_contamination(fresh_merge, tmp_path):
    calls = 0

    def validate(repo: str, _tree: str) -> ValidationAttempt:
        nonlocal calls
        calls += 1
        marker = Path(repo) / "validator-contamination"
        if calls == 1:
            marker.write_text("dirty", encoding="utf-8")
            return ValidationAttempt(False, "first red")
        assert not marker.exists()
        return ValidationAttempt(True, "retry green")

    result = probe_composition(
        MAIN, PR, merge_strategy=fresh_merge, validator_fn=validate, tmp_dir=tmp_path
    )

    assert result.outcome == RED_FLAKE
    assert result.validation_attempt_count == 2
    assert len(fresh_merge.paths) == 2
    assert fresh_merge.paths[0] != fresh_merge.paths[1]
    assert not fresh_merge.paths[0].parent.exists()
    assert not fresh_merge.paths[1].parent.exists()


def test_deterministic_red_returns_bounded_redacted_incident(fresh_merge, tmp_path):
    records: list[object] = []
    secret = "github_pat_" + "z" * 30
    output = "x" * 6000 + f" token={secret} final"
    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=fresh_merge,
        validator_fn=lambda *_: ValidationAttempt(False, output),
        tmp_dir=tmp_path,
        incident_sink=records.append,
    )

    assert result.outcome == RED_DETERMINISTIC
    assert result.validation_attempt_count == 2
    assert len(result.validation_output) <= probe._MAX_OUTPUT + len("[truncated]\n")
    assert secret not in result.validation_output
    assert "[REDACTED]" in result.validation_output
    assert records == [result.incident_record]
    encoded = json.dumps(result.as_dict())
    assert secret not in encoded


def test_incident_sink_failure_preserves_deterministic_red(fresh_merge, tmp_path):
    def broken_sink(_record):
        raise RuntimeError("password=hunter2")

    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=fresh_merge,
        validator_fn=lambda *_: False,
        tmp_dir=tmp_path,
        incident_sink=broken_sink,
    )
    assert result.outcome == RED_DETERMINISTIC
    assert result.validation_attempt_count == 2
    assert result.incident_record is not None
    assert "hunter2" not in (result.incident_sink_error or "")
    assert "[REDACTED]" in (result.incident_sink_error or "")


def test_validator_exception_is_not_merge_abort(fresh_merge, tmp_path):
    def broken_validator(*_args):
        raise RuntimeError("api_key=supersecret")

    result = probe_composition(
        MAIN, PR, merge_strategy=fresh_merge, validator_fn=broken_validator, tmp_dir=tmp_path
    )
    assert result.outcome == VALIDATOR_ABORT
    assert result.validation_attempt_count == 1
    assert "supersecret" not in (result.error or "")


def test_second_validator_exception_preserves_first_attempt_evidence(fresh_merge, tmp_path):
    calls = iter([ValidationAttempt(False, "first evidence"), RuntimeError("boom")])

    def validator(*_args):
        value = next(calls)
        if isinstance(value, Exception):
            raise value
        return value

    result = probe_composition(
        MAIN, PR, merge_strategy=fresh_merge, validator_fn=validator, tmp_dir=tmp_path
    )
    assert result.outcome == VALIDATOR_ABORT
    assert result.validation_attempt_count == 2
    assert result.validation_output == "first evidence"
    assert "validator failed" in (result.error or "")


@pytest.mark.parametrize(
    ("main", "pr"),
    [
        ("main", PR),
        ("-" + "a" * 39, PR),
        ("a" * 41, PR),
        (MAIN, {"number": 0, "head_sha": HEAD}),
        (MAIN, {"number": True, "head_sha": HEAD}),
        (MAIN, {"number": 1, "head_sha": "HEAD"}),
        (MAIN, {"number": 1, "head_sha": "-" + "b" * 39}),
        (MAIN, {"number": 1, "head_sha": HEAD, "tmp_dir": "/tmp"}),
    ],
)
def test_invalid_inputs_fail_before_strategy_side_effect(main, pr, tmp_path):
    called = False

    def merge(*_args):
        nonlocal called
        called = True

    with pytest.raises(ValueError):
        probe_composition(main, pr, merge_strategy=merge, tmp_dir=tmp_path)
    assert called is False
    assert list(tmp_path.iterdir()) == []


def test_uppercase_shas_are_normalized_before_strategy(fresh_merge, tmp_path):
    seen = []

    def merge(_repo, main, head, temp):
        seen.append((main, head))
        return fresh_merge(_repo, main, head, temp)

    result = probe_composition(
        MAIN.upper(),
        {"number": 1, "head_sha": "B" * 40},
        merge_strategy=merge,
        validator_fn=lambda *_: True,
        tmp_dir=tmp_path,
    )
    assert result.outcome == GREEN
    assert seen == [(MAIN, HEAD)]


def test_explicit_temp_parent_must_exist_before_any_strategy_call(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(ValueError, match="existing directory"):
        probe_composition(MAIN, PR, merge_strategy=lambda *_: pytest.fail(), tmp_dir=missing)
    assert not missing.exists()


def test_non_callable_seams_fail_before_owned_child_creation(tmp_path):
    with pytest.raises(ValueError, match="incident_sink must be callable"):
        probe_composition(MAIN, PR, incident_sink="/tmp/events", tmp_dir=tmp_path)  # type: ignore[arg-type]
    assert list(tmp_path.iterdir()) == []


def test_cli_rejects_json_controlled_paths_before_probe(monkeypatch):
    payload = {"main_tip_sha": MAIN, "representative_pr": PR, "incident_path": "/tmp/x"}
    monkeypatch.setattr(probe.sys, "stdin", io.StringIO(json.dumps(payload)))
    with pytest.raises(ValueError, match="unsupported fields"):
        probe.main([])


def test_cli_prints_only_bounded_redacted_result(monkeypatch, capsys, tmp_path):
    secret = "ghp_" + "q" * 30
    fresh = tmp_path / "fresh"
    fresh.mkdir()

    def merge(_repo, _main, _head, target):
        Path(target).mkdir()
        return MergeSimulation("clean", merge_base=BASE, tree_ref=TREE)

    monkeypatch.setattr(probe, "_default_merge_strategy", merge)
    monkeypatch.setattr(
        probe, "_default_validator", lambda *_: ValidationAttempt(True, "z" * 6000 + secret)
    )
    monkeypatch.setattr(probe.tempfile, "gettempdir", lambda: str(fresh))
    monkeypatch.setattr(
        probe.sys,
        "stdin",
        io.StringIO(json.dumps({"main_tip_sha": MAIN, "representative_pr": PR})),
    )
    assert probe.main([]) == 0
    rendered = capsys.readouterr().out
    assert secret not in rendered
    result = json.loads(rendered)
    assert len(result["validation_output"]) <= probe._MAX_OUTPUT + len("[truncated]\n")
    assert len(rendered.splitlines()) == 1


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=cwd, check=True, text=True, capture_output=True
    )
    return completed.stdout.strip()


def _two_commit_repo(tmp_path: Path) -> tuple[Path, Path, str, str]:
    repo = tmp_path / "source"
    parent = tmp_path / "attempts"
    repo.mkdir()
    parent.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "base.txt")
    _git(repo, "commit", "-m", "base")
    main_sha = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "-c", "feature")
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "feature")
    head_sha = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "main")
    return repo, parent, main_sha, head_sha


def test_production_default_validates_real_composed_commit_against_exact_main(
    monkeypatch, tmp_path
):
    repo, parent, main_sha, head_sha = _two_commit_repo(tmp_path)
    observed: dict[str, object] = {}

    def fake_run(argv, cwd):
        worktree = Path(cwd)
        composed = _git(worktree, "rev-parse", "HEAD")
        observed.update(
            argv=list(argv),
            composed=composed,
            parents=_git(worktree, "show", "-s", "--format=%P", "HEAD").split(),
            status=_git(worktree, "status", "--porcelain"),
            feature=(worktree / "feature.txt").read_text(encoding="utf-8"),
        )
        return ValidationAttempt(True, "green")

    monkeypatch.chdir(repo)
    monkeypatch.setattr(probe, "_run_validator_bounded", fake_run)
    result = probe_composition(
        main_sha,
        {"number": 7, "head_sha": head_sha},
        tmp_dir=parent,
    )

    assert result.outcome == GREEN
    assert observed["composed"] != main_sha
    assert observed["composed"] != head_sha
    assert observed["parents"] == [main_sha, head_sha]
    assert observed["status"] == ""
    assert observed["feature"] == "feature\n"
    argv = observed["argv"]
    assert argv[0] == probe.sys.executable
    assert argv[1:5] == ["-I", "-m", "creator_engine_validator.ce_cli", "validate-pr"]
    assert argv[5:7] == ["--base", main_sha]
    assert list(parent.iterdir()) == []


def test_production_git_commands_ignore_hostile_environment_and_hooks(monkeypatch, tmp_path):
    repo, parent, main_sha, head_sha = _two_commit_repo(tmp_path)
    marker = tmp_path / "hostile-hook-ran"
    hook_dir = tmp_path / "hostile-hooks"
    hook_dir.mkdir()
    hook = hook_dir / "post-checkout"
    hook.write_text(f"#!/bin/sh\nprintf ran > {marker}\n", encoding="utf-8")
    hook.chmod(0o755)
    global_config = tmp_path / "hostile-gitconfig"
    global_config.write_text(f"[core]\n\thooksPath = {hook_dir}\n", encoding="utf-8")
    redirected = tmp_path / "redirected-git-dir"
    redirected.mkdir()
    hostile = {
        "GIT_DIR": str(redirected),
        "GIT_WORK_TREE": str(tmp_path / "redirected-work-tree"),
        "GIT_INDEX_FILE": str(tmp_path / "redirected-index"),
        "GIT_OBJECT_DIRECTORY": str(tmp_path / "redirected-objects"),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(tmp_path / "redirected-alternates"),
        "GIT_CONFIG_GLOBAL": str(global_config),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": str(hook_dir),
    }
    for key, value in hostile.items():
        monkeypatch.setenv(key, value)

    real_run = probe.subprocess.run
    git_environments: list[dict[str, str]] = []

    def observe_run(argv, *args, **kwargs):
        if argv[0] == "git":
            git_environments.append(dict(kwargs["env"]))
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(probe.subprocess, "run", observe_run)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(probe, "_run_validator_bounded", lambda *_: ValidationAttempt(True))
    result = probe_composition(main_sha, {"number": 7, "head_sha": head_sha}, tmp_dir=parent)

    assert result.outcome == GREEN
    assert not marker.exists()
    assert git_environments
    for environment in git_environments:
        assert environment["PATH"] == os.defpath
        assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
        assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
        assert environment["GIT_CONFIG_KEY_0"] == "core.hooksPath"
        assert environment["GIT_CONFIG_VALUE_0"] == os.devnull
        assert set(environment).issubset(set(probe._GIT_ENVIRONMENT) | probe._GIT_IDENTITY_KEYS)
        assert not (set(hostile) - set(probe._GIT_ENVIRONMENT)) & set(environment)


def test_production_validator_subprocess_ignores_hostile_git_environment_and_hooks(
    monkeypatch, tmp_path
):
    repo, _parent, main_sha, _head_sha = _two_commit_repo(tmp_path)
    (repo / "main-second.txt").write_text("main second\n", encoding="utf-8")
    _git(repo, "add", "main-second.txt")
    _git(repo, "commit", "-m", "second main")
    main_sha = _git(repo, "rev-parse", "HEAD")
    marker = tmp_path / "hostile-hook-ran"
    observed = tmp_path / "validator-environment"
    hook_dir = tmp_path / "hostile-hooks"
    hook_dir.mkdir()
    hook = hook_dir / "post-checkout"
    hook.write_text(f"#!/bin/sh\nprintf ran > {marker}\n", encoding="utf-8")
    hook.chmod(0o755)
    global_config = tmp_path / "hostile-gitconfig"
    global_config.write_text(f"[core]\n\thooksPath = {hook_dir}\n", encoding="utf-8")
    redirected = tmp_path / "redirected-git-dir"
    redirected.mkdir()
    hostile = {
        "GIT_DIR": str(redirected),
        "GIT_WORK_TREE": str(tmp_path / "redirected-work-tree"),
        "GIT_INDEX_FILE": str(tmp_path / "redirected-index"),
        "GIT_OBJECT_DIRECTORY": str(tmp_path / "redirected-objects"),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(tmp_path / "redirected-alternates"),
        "GIT_CONFIG_GLOBAL": str(global_config),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": str(hook_dir),
    }
    for key, value in hostile.items():
        monkeypatch.setenv(key, value)

    venv_root = tmp_path / "venv"
    venv_bin = venv_root / "bin"
    venv_bin.mkdir(parents=True)
    git = shutil.which("git")
    assert git is not None
    interpreter = venv_bin / "python"
    interpreter.symlink_to(Path(probe.sys.executable).resolve())
    (venv_root / "pyvenv.cfg").write_text(
        "home = /usr/bin\ninclude-system-site-packages = false\n",
        encoding="utf-8",
    )
    site_packages = (
        venv_root
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    package = site_packages / "creator_engine_validator"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    absent = (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    )
    (package / "ce_cli.py").write_text(
        "import os\n"
        "import subprocess\n"
        "import sys\n"
        f"absent = {absent!r}\n"
        "if any(key in os.environ for key in absent):\n"
        "    raise SystemExit(17)\n"
        "if sys.argv[1:2] != ['validate-pr']:\n"
        "    raise SystemExit(21)\n"
        "if sys.prefix == sys.base_prefix:\n"
        "    raise SystemExit(22)\n"
        f"with open({str(observed)!r}, 'w', encoding='utf-8') as output:\n"
        "    for key in ('PATH', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL', "
        "'GIT_CONFIG_KEY_0', 'GIT_CONFIG_VALUE_0'):\n"
        "        output.write(f'{key}={os.environ[key]}\\n')\n"
        "    output.write(f'PREFIX={sys.prefix}\\n')\n"
        f"subprocess.run([{git!r}, 'checkout', '--detach', 'HEAD'], check=True)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(probe.sys, "executable", str(interpreter))

    result = probe._default_validator(str(repo), main_sha)

    assert result.green
    assert not marker.exists()
    received = dict(line.split("=", 1) for line in observed.read_text(encoding="utf-8").splitlines())
    assert received["PATH"] == os.defpath
    assert received["GIT_CONFIG_NOSYSTEM"] == "1"
    assert received["GIT_CONFIG_GLOBAL"] == os.devnull
    assert received["GIT_CONFIG_KEY_0"] == "core.hooksPath"
    assert received["GIT_CONFIG_VALUE_0"] == os.devnull
    assert received["PREFIX"] == str(venv_root)


def test_validator_entrypoint_preserves_absolute_venv_symlink(monkeypatch, tmp_path):
    venv_root = tmp_path / "venv"
    interpreter = venv_root / "bin" / "python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(Path(probe.sys.executable).resolve())
    (venv_root / "pyvenv.cfg").write_text(
        "home = /usr/bin\ninclude-system-site-packages = false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(probe.sys, "executable", str(interpreter))

    assert probe._trusted_validator_argv()[:1] == [str(interpreter)]


def test_validator_entrypoint_fails_closed_without_absolute_executable(monkeypatch):
    monkeypatch.setattr(probe.sys, "executable", "python")

    with pytest.raises(RuntimeError, match="not an absolute path"):
        probe._trusted_validator_argv()


def test_production_retry_has_independent_common_repo_config_refs_index_and_hooks(
    monkeypatch, tmp_path
):
    repo, parent, main_sha, head_sha = _two_commit_repo(tmp_path)
    common_dirs: list[Path] = []
    calls = 0

    def fake_run(_argv, cwd):
        nonlocal calls
        calls += 1
        clone = Path(cwd)
        common = (clone / _git(clone, "rev-parse", "--git-common-dir")).resolve()
        common_dirs.append(common)
        if calls == 1:
            _git(clone, "config", "composition-probe.contaminated", "yes")
            _git(clone, "update-ref", "refs/heads/attempt-one-only", "HEAD")
            hooks = common / "hooks"
            hooks.mkdir(exist_ok=True)
            (hooks / "pre-commit").write_text("attempt one\n", encoding="utf-8")
            metadata = common / "worktrees" / "attempt-one-only"
            metadata.mkdir(parents=True)
            (metadata / "gitdir").write_text("/nonexistent\n", encoding="utf-8")
            _git(clone, "rm", "--cached", "feature.txt")
            return ValidationAttempt(False, "first red")

        config = subprocess.run(
            ["git", "config", "--get", "composition-probe.contaminated"],
            cwd=clone,
            text=True,
            capture_output=True,
            check=False,
        )
        ref = subprocess.run(
            ["git", "show-ref", "--verify", "refs/heads/attempt-one-only"],
            cwd=clone,
            text=True,
            capture_output=True,
            check=False,
        )
        assert config.returncode != 0
        assert ref.returncode != 0
        assert not (common / "hooks" / "pre-commit").exists()
        assert not (common / "worktrees" / "attempt-one-only").exists()
        assert _git(clone, "status", "--porcelain") == ""
        return ValidationAttempt(True, "retry green")

    monkeypatch.chdir(repo)
    monkeypatch.setattr(probe, "_run_validator_bounded", fake_run)
    result = probe_composition(
        main_sha, {"number": 7, "head_sha": head_sha}, tmp_dir=parent
    )

    assert result.outcome == RED_FLAKE
    assert result.validation_attempt_count == 2
    assert len(common_dirs) == 2
    assert common_dirs[0] != common_dirs[1]
    assert all(repo / ".git" != common for common in common_dirs)
    assert list(parent.iterdir()) == []


def test_production_retry_merge_conflict_remains_distinct(monkeypatch, tmp_path):
    repo, parent, main_sha, head_sha = _two_commit_repo(tmp_path)
    real_merge = probe._default_merge_strategy
    calls = 0

    def conflict_on_retry(source, main, head, target):
        nonlocal calls
        calls += 1
        simulation = real_merge(source, main, head, target)
        if calls == 2:
            return MergeSimulation("conflict", merge_base=simulation.merge_base)
        return simulation

    monkeypatch.chdir(repo)
    result = probe_composition(
        main_sha,
        {"number": 7, "head_sha": head_sha},
        merge_strategy=conflict_on_retry,
        validator_fn=lambda *_: ValidationAttempt(False, "first red"),
        tmp_dir=parent,
    )

    assert calls == 2
    assert result.outcome == MERGE_CONFLICT
    assert result.validation_attempt_count == 1
    assert result.validation_output == "first red"
    assert result.error is None
    assert list(parent.iterdir()) == []


def _custom_clone_merge(_repo, _main, _head, target):
    clone = Path(target)
    (clone / ".git").mkdir(parents=True)
    return MergeSimulation("clean", merge_base=BASE, tree_ref=TREE)


def test_nonzero_git_cleanup_fails_closed_after_green(monkeypatch, tmp_path):
    real_git = probe._git

    def failing_git(repo_path, *args, **kwargs):
        if args[:2] == ("worktree", "prune"):
            return subprocess.CompletedProcess(
                ["git", *args], 9, "", "token=cleanup-secret " + "x" * 6000
            )
        return real_git(repo_path, *args, **kwargs)

    monkeypatch.setattr(probe, "_git", failing_git)
    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=_custom_clone_merge,
        validator_fn=lambda *_: True,
        tmp_dir=tmp_path,
    )

    assert result.outcome == CLEANUP_ABORT
    assert result.primary_outcome == GREEN
    assert "cleanup-secret" not in (result.cleanup_error or "")
    assert len(result.cleanup_error or "") <= probe._MAX_OUTPUT + len("[truncated]\n")
    assert list(tmp_path.iterdir()) == []


def test_raising_git_cleanup_continues_deletion_and_verification(monkeypatch, tmp_path):
    real_git = probe._git
    verified: list[Path] = []
    real_verify = probe._verify_owned_root_removed

    def raising_git(repo_path, *args, **kwargs):
        if args[:2] == ("worktree", "prune"):
            raise OSError("secret=git-cleanup")
        return real_git(repo_path, *args, **kwargs)

    def verify(path):
        verified.append(path)
        real_verify(path)

    monkeypatch.setattr(probe, "_git", raising_git)
    monkeypatch.setattr(probe, "_verify_owned_root_removed", verify)
    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=_custom_clone_merge,
        validator_fn=lambda *_: True,
        tmp_dir=tmp_path,
    )

    assert result.outcome == CLEANUP_ABORT
    assert result.primary_outcome == GREEN
    assert verified
    assert not verified[0].exists()
    assert "git-cleanup" not in (result.cleanup_error or "")


def test_filesystem_deletion_failure_blocks_retry_and_incident(monkeypatch, tmp_path):
    real_rmtree = probe.shutil.rmtree
    incidents: list[object] = []

    def broken_rmtree(_path):
        raise OSError("password=delete-secret")

    monkeypatch.setattr(probe.shutil, "rmtree", broken_rmtree)
    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=_custom_clone_merge,
        validator_fn=lambda *_: False,
        tmp_dir=tmp_path,
        incident_sink=incidents.append,
    )

    assert result.outcome == CLEANUP_ABORT
    assert result.primary_outcome == "RETRY_PENDING"
    assert result.validation_attempt_count == 1
    assert result.incident_record is None
    assert incidents == []
    assert "delete-secret" not in (result.cleanup_error or "")
    for path in tmp_path.iterdir():
        real_rmtree(path)


@pytest.mark.parametrize(
    ("status", "primary_outcome"),
    [("abort", MERGE_ABORT), ("conflict", MERGE_CONFLICT)],
)
def test_cleanup_failure_preserves_pre_validation_attempt_count(
    monkeypatch, tmp_path, status, primary_outcome
):
    real_rmtree = probe.shutil.rmtree

    def broken_rmtree(_path):
        raise OSError("secret=pre-validation-cleanup")

    monkeypatch.setattr(probe.shutil, "rmtree", broken_rmtree)
    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=lambda *_: MergeSimulation(status, merge_base=BASE),
        validator_fn=lambda *_: pytest.fail("validation must not run"),
        tmp_dir=tmp_path,
    )

    assert result.outcome == CLEANUP_ABORT
    assert result.primary_outcome == primary_outcome
    assert result.validation_attempt_count == 0
    assert "pre-validation-cleanup" not in (result.cleanup_error or "")
    for path in tmp_path.iterdir():
        real_rmtree(path)


def test_second_red_cleanup_failure_suppresses_deterministic_incident(monkeypatch, tmp_path):
    real_rmtree = probe.shutil.rmtree
    deletions = 0
    incidents: list[object] = []

    def fail_second_deletion(path):
        nonlocal deletions
        deletions += 1
        if deletions == 2:
            raise OSError("secret=second-cleanup")
        real_rmtree(path)

    monkeypatch.setattr(probe.shutil, "rmtree", fail_second_deletion)

    def clean_merge(_repo, _main, _head, target):
        Path(target).mkdir()
        return MergeSimulation("clean", merge_base=BASE, tree_ref=TREE)

    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=clean_merge,
        validator_fn=lambda *_: ValidationAttempt(False, "red"),
        tmp_dir=tmp_path,
        incident_sink=incidents.append,
    )

    assert result.outcome == CLEANUP_ABORT
    assert result.primary_outcome == RED_DETERMINISTIC
    assert result.validation_attempt_count == 2
    assert result.incident_record is None
    assert incidents == []
    assert "second-cleanup" not in (result.cleanup_error or "")
    for path in tmp_path.iterdir():
        real_rmtree(path)


def test_filesystem_verification_failure_overrides_green(monkeypatch, tmp_path):
    def broken_verify(_path):
        raise RuntimeError("api_key=verification-secret")

    monkeypatch.setattr(probe, "_verify_owned_root_removed", broken_verify)
    result = probe_composition(
        MAIN,
        PR,
        merge_strategy=_custom_clone_merge,
        validator_fn=lambda *_: True,
        tmp_dir=tmp_path,
    )

    assert result.outcome == CLEANUP_ABORT
    assert result.primary_outcome == GREEN
    assert "verification-secret" not in (result.cleanup_error or "")
    assert list(tmp_path.iterdir()) == []
