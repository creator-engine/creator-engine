from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.brain_intent_materializer import HistoryScanner


class FakeGitRunner:
    def __init__(self, *, log: list[str], trees: dict[str, list[str]], fail_log: bool = False):
        self.log = log
        self.trees = trees
        self.fail_log = fail_log
        self.calls: list[list[str]] = []

    def __call__(self, args, _cwd: Path):
        args = list(args)
        self.calls.append(args)
        if args == ["log", "--first-parent", "--format=%H", "origin/main"]:
            if self.fail_log:
                return 1, "", "fatal: log failed"
            return 0, "\n".join(self.log) + ("\n" if self.log else ""), ""
        if args[:3] == ["ls-tree", "-r", "--name-only"] and args[4:] == [".ce/brain/append-intents/"]:
            return 0, "\n".join(self.trees.get(args[3], [])) + ("\n" if self.trees.get(args[3], []) else ""), ""
        return 1, "", f"unexpected args: {args}"


def test_empty_history_returns_no_intents(tmp_path: Path):
    runner = FakeGitRunner(log=[], trees={"origin/main": []})

    assert HistoryScanner(tmp_path, git_runner=runner).scan() == []


def test_one_pending_intent_found_in_newest_commit(tmp_path: Path):
    path = ".ce/brain/append-intents/ce-491.yaml"
    runner = FakeGitRunner(log=["a" * 40], trees={"origin/main": [path], "a" * 40: [path]})

    assert HistoryScanner(tmp_path, git_runner=runner).scan() == [("a" * 40, path)]


def test_two_commits_yield_oldest_first(tmp_path: Path):
    old_path = ".ce/brain/append-intents/old.yaml"
    new_path = ".ce/brain/append-intents/new.yaml"
    old_sha = "a" * 40
    new_sha = "b" * 40
    runner = FakeGitRunner(
        log=[new_sha, old_sha],
        trees={
            "origin/main": [old_path, new_path],
            old_sha: [old_path],
            new_sha: [old_path, new_path],
        },
    )

    assert HistoryScanner(tmp_path, git_runner=runner).scan() == [(old_sha, old_path), (new_sha, new_path)]


def test_intent_absent_from_current_origin_main_is_not_yielded(tmp_path: Path):
    consumed = ".ce/brain/append-intents/consumed.yaml"
    sha = "c" * 40
    runner = FakeGitRunner(log=[sha], trees={"origin/main": [], sha: [consumed]})

    assert HistoryScanner(tmp_path, git_runner=runner).scan() == []


def test_multiple_intents_in_one_commit_are_path_sorted(tmp_path: Path):
    first = ".ce/brain/append-intents/a.yaml"
    second = ".ce/brain/append-intents/b.yaml"
    sha = "d" * 40
    runner = FakeGitRunner(log=[sha], trees={"origin/main": [second, first], sha: [second, first]})

    assert HistoryScanner(tmp_path, git_runner=runner).scan() == [(sha, first), (sha, second)]


def test_git_log_failure_raises_fail_closed(tmp_path: Path):
    runner = FakeGitRunner(log=[], trees={}, fail_log=True)

    with pytest.raises(RuntimeError, match="log failed"):
        HistoryScanner(tmp_path, git_runner=runner).scan()
