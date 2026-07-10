from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import composition_probe as probe
from creator_engine_validator.composition_probe import (
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


def test_production_default_validates_real_composed_commit_against_exact_main(
    monkeypatch, tmp_path
):
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
    assert argv[:4] == ["ce", "validate-pr", "--base", main_sha]
    assert list(parent.iterdir()) == []
