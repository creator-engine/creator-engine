"""Unit tests for the F2 ``work_sizing_floor`` check."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import work_sizing_floor as chk
from creator_engine_validator.cli import main


def _record(declared_work_class="story", change_stats=None, **overrides):
    stats = change_stats if change_stats is not None else [
        {"path": "validators/creator_engine_validator/checks/work_sizing_floor.py", "additions": 180, "deletions": 20},
    ]
    floor = overrides.pop("sizing_floor", None)
    record = {
        "kind": "work-sizing-floor-record",
        "schema_version": "1",
        "intent_ref": "ce-ops#164",
        "declared_work_class": declared_work_class,
        "change_stats": stats,
        "sizing_floor": floor if floor is not None else chk.sizing_floor_projection(declared_work_class, stats),
    }
    record.update(overrides)
    return record


def _codes(record):
    return sorted({e.code for e in chk.validate_work_sizing_floor(record, Path("floor.yml"))})


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _init_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "seed.txt").write_text("seed\n")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "base")
    return repo, _head(repo)


def _write_repo_file(repo: Path, rel: str, lines: int = 1) -> None:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(f"line {i}\n" for i in range(lines)))


def _commit_all(repo: Path, message: str = "change") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def test_registered_in_check_surface():
    reg = registered_checks()
    assert chk.CHECK_NAME in reg and reg[chk.CHECK_NAME].frs


def test_parse_numstat_parses_text_and_binary_entries():
    stats = chk.parse_numstat(
        "10\t2\tvalidators/a.py\n"
        "-\t-\tassets/logo.png\n"
    )
    assert stats == [
        chk.ChangeStat(path="validators/a.py", additions=10, deletions=2, binary=False),
        chk.ChangeStat(path="assets/logo.png", additions=0, deletions=0, binary=True),
    ]


def test_parse_numstat_rejects_malformed_lines_with_value_free_error():
    try:
        chk.parse_numstat("not-a-numstat-line")
    except ValueError as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("malformed numstat should fail closed")
    assert "not-a-numstat-line" not in message
    assert message == "invalid numstat line"


def test_thresholds_are_grounded_at_200_400_and_800_to_1000():
    assert chk.classify_change_size([{"path": "a.py", "additions": 200, "deletions": 0}]) == {
        "included_files": 1,
        "included_lines": 200,
        "excluded_files": 0,
        "excluded_lines": 0,
        "excluded_path_categories": [],
        "size_band": "target_advisory",
        "minimum_work_class": "tiny",
    }
    assert chk.classify_change_size([{"path": "a.py", "additions": 400, "deletions": 0}])["size_band"] == "warn"
    assert chk.classify_change_size([{"path": "a.py", "additions": 799, "deletions": 0}])["minimum_work_class"] == "story"
    assert chk.classify_change_size([{"path": "a.py", "additions": 800, "deletions": 0}]) == {
        "included_files": 1,
        "included_lines": 800,
        "excluded_files": 0,
        "excluded_lines": 0,
        "excluded_path_categories": [],
        "size_band": "explain_or_split",
        "minimum_work_class": "feature",
    }
    assert chk.classify_change_size([{"path": "a.py", "additions": 1000, "deletions": 0}])["size_band"] == "explain_or_split"
    assert chk.classify_change_size([{"path": "a.py", "additions": 1001, "deletions": 0}]) == {
        "included_files": 1,
        "included_lines": 1001,
        "excluded_files": 0,
        "excluded_lines": 0,
        "excluded_path_categories": [],
        "size_band": "split_required",
        "minimum_work_class": "epic",
    }


def test_generated_lockfile_and_vendored_lines_are_excluded_from_floor():
    stats = [
        {"path": "src/app.py", "additions": 150, "deletions": 50},
        {"path": "src/generated/client.py", "additions": 900, "deletions": 10},
        {"path": "assets/app.min.js", "additions": 500, "deletions": 500},
        {"path": "pnpm-lock.yaml", "additions": 2000, "deletions": 0},
        {"path": "third_party/lib/file.c", "additions": 1000, "deletions": 1},
    ]

    assert chk.excluded_path_category("src/generated/client.py") == "generated"
    assert chk.excluded_path_category("pnpm-lock.yaml") == "lockfile"
    assert chk.excluded_path_category("third_party/lib/file.c") == "vendored"
    assert chk.classify_change_size(stats) == {
        "included_files": 1,
        "included_lines": 200,
        "excluded_files": 4,
        "excluded_lines": 4911,
        "excluded_path_categories": ["generated", "lockfile", "vendored"],
        "size_band": "target_advisory",
        "minimum_work_class": "tiny",
    }


def test_valid_floor_record_passes():
    assert _codes(_record()) == []


def test_schema_error_fires_on_bad_declared_class():
    assert chk.CODE_SCHEMA in _codes(_record(declared_work_class="bogus", sizing_floor={
        "included_files": 0,
        "included_lines": 0,
        "excluded_files": 0,
        "excluded_lines": 0,
        "excluded_path_categories": [],
        "size_band": "target_advisory",
        "minimum_work_class": "tiny",
        "floor_met": True,
    }))


def test_projection_drift_fires_on_schema_valid_mismatched_floor():
    record = _record(sizing_floor={
        "included_files": 1,
        "included_lines": 1,
        "excluded_files": 0,
        "excluded_lines": 0,
        "excluded_path_categories": [],
        "size_band": "target_advisory",
        "minimum_work_class": "tiny",
        "floor_met": True,
    })
    assert chk.CODE_INVALID in _codes(record)


def test_underdeclared_work_class_fails_floor_check():
    record = _record(
        declared_work_class="story",
        change_stats=[{"path": "feature.py", "additions": 800, "deletions": 0}],
    )
    assert record["sizing_floor"]["floor_met"] is False
    assert chk.CODE_INVALID in _codes(record)


def test_run_green_on_valid_floor_record_dir(tmp_path):
    (tmp_path / "floor.yml").write_text(yaml.safe_dump(_record()))
    result = chk.run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]


def test_run_ignores_f1_records_and_schema_paths(tmp_path):
    (tmp_path / "sizing.yml").write_text(yaml.safe_dump({"kind": "sizing-record"}))
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "floor.yml").write_text(yaml.safe_dump(_record()))
    assert chk.run([tmp_path]).ok


def test_run_with_base_uses_actual_diff_when_persisted_records_are_omitted(tmp_path):
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "src/large_feature.py", lines=801)
    _commit_all(repo)

    result = chk.run_with_base([repo], base, declared_work_class="story")

    assert not result.ok
    assert {e.code for e in result.errors} == {chk.CODE_INVALID}
    rendered = "\n".join(e.format() for e in result.errors)
    assert "801" not in rendered
    assert "large_feature.py" not in rendered


def test_run_with_base_uses_actual_diff_when_persisted_records_understate_stats(tmp_path):
    repo, _base = _init_repo(tmp_path)
    (repo / "floor.yml").write_text(yaml.safe_dump(_record()))
    _commit_all(repo, "persist understated record")
    base = _head(repo)
    assert chk.run([repo]).ok

    _write_repo_file(repo, "src/large_feature.py", lines=801)
    _commit_all(repo)

    result = chk.run_with_base([repo], base, declared_work_class="story")

    assert not result.ok
    assert {e.code for e in result.errors} == {chk.CODE_INVALID}


def test_run_with_base_excludes_generated_lockfile_and_vendored_actual_diff(tmp_path):
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "src/app.py", lines=20)
    _write_repo_file(repo, "src/generated/client.py", lines=900)
    _write_repo_file(repo, "pnpm-lock.yaml", lines=2000)
    _write_repo_file(repo, "vendor/lib.c", lines=1200)
    _commit_all(repo)

    result = chk.run_with_base([repo], base, declared_work_class="tiny")

    assert result.ok, [e.format() for e in result.errors]


def test_cli_verify_work_sizing_floor_exits_nonzero_on_underfloor(capsys, tmp_path):
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "src/large_feature.py", lines=801)
    _commit_all(repo)

    exit_code = main([
        "verify-work-sizing-floor",
        "--base",
        base,
        "--declared-work-class",
        "story",
        str(repo),
    ])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL work_sizing_floor" in out
    assert chk.CODE_INVALID in out


def test_cli_verify_work_sizing_floor_exits_zero_when_declared_class_satisfies_floor(
    capsys,
    tmp_path,
):
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "src/large_feature.py", lines=801)
    _commit_all(repo)

    exit_code = main([
        "verify-work-sizing-floor",
        "--base",
        base,
        "--declared-work-class",
        "feature",
        str(repo),
    ])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "PASS work_sizing_floor" in out
