from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

import creator_engine_validator.brain_intent_materializer as materializer
from creator_engine_validator import brain_runtime
from creator_engine_validator.brain_intent_materializer import (
    ArmedMaterializationOutput,
    MaterializationCommit,
    Materializer,
    MaterializerConfig,
    MaterializerRunLoop,
    RecordBuilder,
    construct_materialization_commit,
    push_materialization_commit,
)


class Capture:
    text = ""

    def __call__(self, _path: Path, text: str) -> None:
        self.text = text


def _git(repo: Path, *args: str, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        input=input_text,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result


def _ledger_text() -> str:
    sink = Capture()
    brain_runtime.assert_claim(
        claim={"subject": "brain", "predicate": "intent", "object": "base"},
        scope="creator-engine",
        evidence_ref="docs/design/ce-491-optiona-merge-intent.md",
        assertion_id="brain-assertion-intent-base",
        records=[],
        state_root=Path(".ce/state"),
        write=sink,
    )
    return sink.text


def _intent() -> dict[str, Any]:
    return {
        "kind": "brain-append-intent",
        "schema_version": "1",
        "intent_kind": "active_assertion_append",
        "active_assertion": {
            "assertion_id": "brain-assertion-intent-active",
            "claim": {"subject": "brain", "predicate": "intent", "object": "active"},
            "scope": "creator-engine",
            "evidence_ref": "docs/design/ce-491-optiona-merge-intent.md",
        },
    }


def _config(tmp_path: Path) -> MaterializerConfig:
    return MaterializerConfig(
        state_root=tmp_path / ".ce" / "state" / "brain-intent-materializer",
        quarantine_root=tmp_path / ".ce" / "state" / "brain-intent-quarantine",
        repo_root=tmp_path,
        private_key_env="CE_MATERIALIZER_APP_PRIVATE_KEY",
    )


def test_construct_materialization_commit_is_deterministic_while_disarmed(tmp_path: Path):
    repo = tmp_path
    _git(repo, "init")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    ledger_path = repo / ".ce" / "brain" / "assertions.yaml"
    intent_path = repo / ".ce" / "brain" / "append-intents" / "branch.yaml"
    ledger_path.parent.mkdir(parents=True)
    intent_path.parent.mkdir(parents=True)
    ledger_path.write_text(_ledger_text(), encoding="utf-8")
    intent_path.write_text(yaml.safe_dump(_intent(), sort_keys=True), encoding="utf-8")
    _git(repo, "add", ".ce/brain/assertions.yaml", ".ce/brain/append-intents/branch.yaml")
    _git(repo, "commit", "-m", "seed")
    parent_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    records = brain_runtime.load_ledger_text(ledger_path.read_text(encoding="utf-8"))
    built = RecordBuilder().build(
        intent_data=_intent(),
        live_records=records,
        live_tail_content_hash=records[-1]["content_hash"],
        repo_root=repo,
        merge_commit_sha=parent_sha,
        pr_number=491,
        branch_slug="branch",
        intent_path=".ce/brain/append-intents/branch.yaml",
        intent_sha256="b" * 64,
        materialization_key="c" * 64,
    )

    first = construct_materialization_commit(
        repo_root=repo,
        parent_sha=parent_sha,
        built=built,
        intent_path=".ce/brain/append-intents/branch.yaml",
        merge_commit_sha=parent_sha,
        materialization_key="c" * 64,
    )
    second = construct_materialization_commit(
        repo_root=repo,
        parent_sha=parent_sha,
        built=built,
        intent_path=".ce/brain/append-intents/branch.yaml",
        merge_commit_sha=parent_sha,
        materialization_key="c" * 64,
    )

    assert materializer.ARMING_ENABLED is False
    assert first.tree_sha == second.tree_sha
    assert first.commit_sha == second.commit_sha
    assert first.message == second.message
    assert "CE-Materialization-Key: " + "c" * 64 in first.message
    assert _git(repo, "cat-file", "-e", f"{first.commit_sha}:.ce/brain/append-intents/branch.yaml", check=False).returncode != 0
    assert built.ledger_tail_after in _git(repo, "show", f"{first.commit_sha}:.ce/brain/assertions.yaml").stdout


def test_cas_push_uses_expected_parent_and_reports_remote_movement(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(materializer, "ARMING_ENABLED", True)
    calls = []
    commit = MaterializationCommit(
        parent_sha="a" * 40,
        tree_sha="b" * 40,
        commit_sha="c" * 40,
        message="Materialize brain append intent\n\nCE-Materialization-Key: " + "d" * 64 + "\n",
        intent_path=".ce/brain/append-intents/branch.yaml",
        materialization_key="d" * 64,
        ledger_tail_after="e" * 64,
    )

    def runner(args, cwd):
        calls.append((list(args), cwd))
        return 1, "", "! [rejected] main -> main (stale info)"

    assert push_materialization_commit(repo_root=tmp_path, commit=commit, git_runner=runner) is False
    assert calls == [
        (
            [
                "push",
                "--force-with-lease=refs/heads/main:" + "a" * 40,
                "origin",
                "c" * 40 + ":refs/heads/main",
            ],
            tmp_path,
        )
    ]


def test_armed_run_loop_rescans_after_cas_failure(monkeypatch, tmp_path: Path):
    scans = [
        [("a" * 40, ".ce/brain/append-intents/stale.yaml"), ("b" * 40, ".ce/brain/append-intents/not-yet.yaml")],
        [("c" * 40, ".ce/brain/append-intents/fresh.yaml")],
    ]
    run_calls = []

    def poll():
        return scans.pop(0)

    def fake_run_armed(**kwargs):
        run_calls.append((kwargs["merge_commit_sha"], kwargs["intent_path"]))
        status = "cas_failed" if kwargs["merge_commit_sha"] == "a" * 40 else "materialized"
        return ArmedMaterializationOutput(
            status=status,
            intent_path=str(kwargs["intent_path"]),
            intent_sha256="b" * 64,
            merge_commit_sha=kwargs["merge_commit_sha"],
            materialization_key="c" * 64,
            main_parent_sha="d" * 40,
            materialization_commit_sha="e" * 40,
            ledger_tail_after="f" * 64,
            refusal_reason=None,
        )

    monkeypatch.setattr(Materializer, "run_armed", staticmethod(fake_run_armed))

    outputs = MaterializerRunLoop(_config(tmp_path), poll_source=poll, pr_number=491).run_armed_until_idle()

    assert [output.status for output in outputs] == ["cas_failed", "materialized"]
    assert run_calls == [
        ("a" * 40, ".ce/brain/append-intents/stale.yaml"),
        ("c" * 40, ".ce/brain/append-intents/fresh.yaml"),
    ]
