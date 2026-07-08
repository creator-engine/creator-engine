from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime
from creator_engine_validator.brain_intent_materializer import (
    ARMING_ENABLED,
    ARMING_DISABLED_MESSAGE,
    Materializer,
    MaterializerConfig,
    RecordBuilder,
    construct_materialization_commit,
    event_sha256_for_line,
)


FIXED_NOW = lambda: datetime(2026, 7, 8, 13, 0, tzinfo=UTC)


class Capture:
    text = ""

    def __call__(self, _path: Path, text: str) -> None:
        self.text = text


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


def _intent() -> dict:
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


def _write_intent(tmp_path: Path) -> Path:
    path = tmp_path / "ce-491-optiona-slice1.yaml"
    path.write_text(yaml.safe_dump(_intent(), sort_keys=True), encoding="utf-8")
    return path


def _config(tmp_path: Path) -> MaterializerConfig:
    return MaterializerConfig(
        state_root=tmp_path / ".ce" / "state" / "brain-intent-materializer",
        quarantine_root=tmp_path / ".ce" / "state" / "brain-intent-quarantine",
        repo_root=tmp_path,
        private_key_env="CE_MATERIALIZER_APP_PRIVATE_KEY",
    )


def _runner(ledger_text: str):
    def run(args, _cwd):
        if args == ["rev-parse", "main"]:
            return 0, "a" * 40 + "\n", ""
        if args == ["show", f"{'a' * 40}:.ce/brain/assertions.yaml"]:
            return 0, ledger_text, ""
        return 1, "", f"unexpected args: {args}"

    return run


def test_run_dry_writes_json_artifact_and_event(tmp_path: Path):
    config = _config(tmp_path)
    intent_path = _write_intent(tmp_path)

    output = Materializer.run_dry(
        merge_commit_sha="b" * 40,
        intent_path=intent_path,
        branch_slug="ce-491-optiona-slice1",
        pr_number=491,
        config=config,
        git_runner=_runner(_ledger_text()),
        now=FIXED_NOW,
    )

    artifact = config.state_root / "dry-run" / f"{output.materialization_key}.json"
    assert output.mode == "dry_run"
    assert output.status == "would_materialize"
    assert output.generated_patch_sha256
    assert artifact.is_file()
    assert json.loads(artifact.read_text(encoding="utf-8"))["status"] == "would_materialize"

    lines = (config.state_root / "materializer.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["started_at"] == "2026-07-08T13:00:00Z"
    assert event["event_sha256"] == event_sha256_for_line(lines[0])


def test_run_dry_would_append_records_match_record_builder(tmp_path: Path):
    config = _config(tmp_path)
    intent_path = _write_intent(tmp_path)
    ledger = _ledger_text()
    records = brain_runtime.load_ledger_text(ledger)

    output = Materializer.run_dry(
        merge_commit_sha="b" * 40,
        intent_path=intent_path,
        branch_slug="ce-491-optiona-slice1",
        pr_number=491,
        config=config,
        git_runner=_runner(ledger),
        now=FIXED_NOW,
    )
    expected = RecordBuilder().build(
        intent_data=_intent(),
        live_records=records,
        live_tail_content_hash=records[-1]["content_hash"],
        repo_root=tmp_path,
        merge_commit_sha="b" * 40,
        pr_number=491,
        branch_slug="ce-491-optiona-slice1",
        intent_path=str(intent_path),
        intent_sha256=output.intent_sha256,
        materialization_key=output.materialization_key,
    )

    assert output.would_append_records == expected.appended_records


def test_malformed_intent_is_held_not_refused_and_writes_quarantine(tmp_path: Path):
    config = _config(tmp_path)
    intent_path = tmp_path / "ce-491-optiona-slice1.yaml"
    intent_path.write_text("kind: [unclosed", encoding="utf-8")

    output = Materializer.run_dry(
        merge_commit_sha="b" * 40,
        intent_path=intent_path,
        branch_slug="ce-491-optiona-slice1",
        pr_number=491,
        config=config,
        git_runner=_runner(_ledger_text()),
        now=FIXED_NOW,
    )

    assert output.status == "held"
    assert "brain_append_intent_schema" in str(output.refusal_reason)
    assert (config.quarantine_root / f"{output.materialization_key}.json").is_file()
    held = json.loads((config.state_root / "held" / f"{output.materialization_key}.json").read_text(encoding="utf-8"))
    assert held["held_reason"] == "brain_intent_materialization_failed"


def test_tail_unprovable_is_held_with_event(tmp_path: Path):
    config = _config(tmp_path)
    intent_path = _write_intent(tmp_path)

    def bad_runner(args, _cwd):
        if args == ["rev-parse", "main"]:
            return 0, "a" * 40 + "\n", ""
        return 1, "", "missing ledger"

    output = Materializer.run_dry(
        merge_commit_sha="b" * 40,
        intent_path=intent_path,
        branch_slug="ce-491-optiona-slice1",
        pr_number=491,
        config=config,
        git_runner=bad_runner,
        now=FIXED_NOW,
    )

    assert output.status == "held"
    assert output.refusal_reason == "brain_ledger_tail_unprovable"
    lines = (config.state_root / "materializer.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["result_status"] == "held"


def test_arming_is_disabled_and_commit_path_raises():
    assert ARMING_ENABLED is False
    with pytest.raises(RuntimeError, match=ARMING_DISABLED_MESSAGE):
        construct_materialization_commit()


def test_jsonl_log_is_append_only_between_calls(tmp_path: Path):
    config = _config(tmp_path)
    first_intent = _write_intent(tmp_path)
    second_intent = tmp_path / "ce-491-optiona-slice1-second.yaml"
    second_intent.write_text(first_intent.read_text(encoding="utf-8"), encoding="utf-8")

    Materializer.run_dry(
        merge_commit_sha="b" * 40,
        intent_path=first_intent,
        branch_slug="ce-491-optiona-slice1",
        pr_number=491,
        config=config,
        git_runner=_runner(_ledger_text()),
        now=FIXED_NOW,
    )
    Materializer.run_dry(
        merge_commit_sha="c" * 40,
        intent_path=second_intent,
        branch_slug="ce-491-optiona-slice1-second",
        pr_number=492,
        config=config,
        git_runner=_runner(_ledger_text()),
        now=FIXED_NOW,
    )

    assert len((config.state_root / "materializer.jsonl").read_text(encoding="utf-8").splitlines()) == 2
