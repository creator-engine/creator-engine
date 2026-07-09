from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime
from creator_engine_validator.brain_intent_materializer import (
    AUTHORIZED_WRITE_PATHS,
    HELD_REASONS,
    HeldStateStore,
    MaterializationKey,
    Materializer,
    MaterializerConfig,
    QuarantineWriter,
    _assert_armed_write_target,
    _require_state_subtree,
)


FIXED_NOW = lambda: datetime(2026, 7, 8, 12, 0, tzinfo=UTC)


def _config(tmp_path: Path) -> MaterializerConfig:
    return MaterializerConfig(
        state_root=tmp_path / ".ce" / "state" / "brain-intent-materializer",
        quarantine_root=tmp_path / ".ce" / "state" / "brain-intent-quarantine",
        repo_root=tmp_path,
        private_key_env="CE_MATERIALIZER_APP_PRIVATE_KEY",
    )


def _ledger_text() -> str:
    class Capture:
        text = ""

        def __call__(self, _path: Path, text: str) -> None:
            self.text = text

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


def _runner_unprovable(args, _cwd):
    if args == ["rev-parse", "main"]:
        return 0, "a" * 40 + "\n", ""
    if args == ["show", f"{'a' * 40}:.ce/brain/assertions.yaml"]:
        return 0, "not: [a: ledger", ""
    return 1, "", "unexpected"


def _valid_intent(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "kind": "brain-append-intent",
                "schema_version": "1",
                "intent_kind": "active_assertion_append",
                "active_assertion": {
                    "assertion_id": "brain-assertion-intent-active",
                    "claim": {"subject": "brain", "predicate": "intent", "object": "active"},
                    "scope": "creator-engine",
                    "evidence_ref": "docs/design/ce-491-optiona-merge-intent.md",
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize("reason", sorted(HELD_REASONS))
def test_held_state_store_round_trips_all_reasons(tmp_path: Path, reason: str):
    key = "a" * 64
    store = HeldStateStore(tmp_path / ".ce" / "state" / "brain-intent-materializer", now=FIXED_NOW)

    store.write(
        held_reason=reason,
        materialization_key=key,
        intent_path=".ce/brain/append-intents/branch.yaml",
        intent_sha256="b" * 64,
        merge_commit_sha="c" * 40,
    )

    loaded = store.load(key)
    assert loaded["held_reason"] == reason
    assert loaded["held_at_utc"] == "2026-07-08T12:00:00Z"


def test_quarantine_writer_uses_out_of_band_state_path(tmp_path: Path):
    key = "a" * 64
    path = QuarantineWriter(tmp_path / ".ce" / "state" / "brain-intent-quarantine", now=FIXED_NOW).write(
        materialization_key=key,
        intent_path=".ce/brain/append-intents/branch.yaml",
        intent_sha256="b" * 64,
        merge_commit_sha="c" * 40,
        validation_error="brain_append_intent_schema: malformed",
    )

    assert path == tmp_path / ".ce" / "state" / "brain-intent-quarantine" / f"{key}.json"
    assert ".ce/brain" not in str(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["actor_version"] == "ce-491-prearming"
    assert data["timestamp"] == "2026-07-08T12:00:00Z"


def test_malformed_intent_enters_held_with_quarantine_and_held_record(tmp_path: Path):
    config = _config(tmp_path)
    intent = tmp_path / "ce-491-optiona-slice1.yaml"
    intent.write_text("kind: [unclosed", encoding="utf-8")

    output = Materializer.run_dry(
        merge_commit_sha="d" * 40,
        intent_path=intent,
        branch_slug="ce-491-optiona-slice1",
        pr_number=491,
        config=config,
        git_runner=lambda _args, _cwd: (1, "", "should not reach git"),
        now=FIXED_NOW,
    )

    assert output.status == "held"
    assert "brain_append_intent_schema" in str(output.refusal_reason)
    held = json.loads((config.state_root / "held" / f"{output.materialization_key}.json").read_text(encoding="utf-8"))
    assert held["held_reason"] == "brain_intent_materialization_failed"
    assert (config.quarantine_root / f"{output.materialization_key}.json").is_file()


def test_tail_unprovable_holds_without_dry_run_artifact_or_ledger_bytes(tmp_path: Path):
    config = _config(tmp_path)
    intent = tmp_path / "ce-491-optiona-slice1.yaml"
    _valid_intent(intent)
    key = MaterializationKey.compute(
        "d" * 40,
        str(intent),
        hashlib.sha256(intent.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
    ).key_hex

    output = Materializer.run_dry(
        merge_commit_sha="d" * 40,
        intent_path=intent,
        branch_slug="ce-491-optiona-slice1",
        pr_number=491,
        config=config,
        git_runner=_runner_unprovable,
        now=FIXED_NOW,
    )

    assert output.status == "held"
    assert output.refusal_reason == "brain_ledger_tail_unprovable"
    assert not (config.state_root / "dry-run" / f"{key}.json").exists()
    assert output.would_append_records == []


def test_require_state_subtree_rejects_out_of_subtree_path():
    with pytest.raises(RuntimeError, match="escapes .ce/state"):
        _require_state_subtree(Path("/tmp/evil/key.json"))


def test_require_state_subtree_rejects_dotdot_traversal(tmp_path: Path):
    base = tmp_path / ".ce" / "state"
    base.mkdir(parents=True)
    traversal = base / ".." / ".." / ".." / "outside" / "key.json"

    with pytest.raises(RuntimeError, match="escapes .ce/state"):
        _require_state_subtree(traversal)


def test_authorized_write_paths_are_live_bounded_metadata():
    assert isinstance(AUTHORIZED_WRITE_PATHS, frozenset)
    assert AUTHORIZED_WRITE_PATHS == frozenset({".ce/brain/assertions.yaml", ".ce/brain/append-intents/"})
    assert AUTHORIZED_WRITE_PATHS


def test_armed_write_target_guard_rejects_out_of_bounds_path():
    _assert_armed_write_target(".ce/brain/assertions.yaml")
    _assert_armed_write_target(".ce/brain/append-intents/branch.yaml")
    with pytest.raises(RuntimeError, match="outside authorized paths"):
        _assert_armed_write_target(".ce/changelog/evil.md")
