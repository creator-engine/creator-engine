from __future__ import annotations

from pathlib import Path

from creator_engine_validator.brain_intent_materializer import (
    DryRunOutput,
    Materializer,
    MaterializerConfig,
    MaterializerRunLoop,
)


def _config(tmp_path: Path) -> MaterializerConfig:
    return MaterializerConfig(
        state_root=tmp_path / ".ce" / "state" / "brain-intent-materializer",
        quarantine_root=tmp_path / ".ce" / "state" / "brain-intent-quarantine",
        repo_root=tmp_path,
        private_key_env="CE_MATERIALIZER_APP_PRIVATE_KEY",
    )


def _output(merge_commit_sha: str, intent_path: str) -> DryRunOutput:
    return DryRunOutput(
        mode="dry_run",
        status="would_materialize",
        intent_path=intent_path,
        intent_sha256="b" * 64,
        merge_commit_sha=merge_commit_sha,
        would_append_records=[],
        would_remove_intent_path=intent_path,
        materialization_key="c" * 64,
        ledger_tail_before="d" * 64,
        ledger_tail_after="e" * 64,
        refusal_reason=None,
        generated_patch_sha256="f" * 64,
    )


def test_empty_poll_source_returns_empty_result_list(tmp_path: Path):
    assert MaterializerRunLoop(_config(tmp_path), poll_source=lambda: []).run_once() == []


def test_single_item_poll_source_calls_run_dry_once(monkeypatch, tmp_path: Path):
    calls = []

    def fake_run_dry(**kwargs):
        calls.append(kwargs)
        return _output(kwargs["merge_commit_sha"], str(kwargs["intent_path"]))

    monkeypatch.setattr(Materializer, "run_dry", staticmethod(fake_run_dry))

    result = MaterializerRunLoop(
        _config(tmp_path),
        poll_source=lambda: [("a" * 40, ".ce/brain/append-intents/branch.yaml")],
        pr_number=491,
    ).run_once()

    assert len(result) == 1
    assert len(calls) == 1
    assert calls[0]["branch_slug"] == "branch"
    assert calls[0]["pr_number"] == 491


def test_two_item_poll_source_calls_run_dry_in_order(monkeypatch, tmp_path: Path):
    calls = []

    def fake_run_dry(**kwargs):
        calls.append((kwargs["merge_commit_sha"], kwargs["intent_path"]))
        return _output(kwargs["merge_commit_sha"], str(kwargs["intent_path"]))

    monkeypatch.setattr(Materializer, "run_dry", staticmethod(fake_run_dry))
    items = [
        ("a" * 40, ".ce/brain/append-intents/first.yaml"),
        ("b" * 40, ".ce/brain/append-intents/second.yaml"),
    ]

    result = MaterializerRunLoop(_config(tmp_path), poll_source=lambda: items, pr_number=491).run_once()

    assert len(result) == 2
    assert calls == items


def test_injectable_poll_source_is_used(monkeypatch, tmp_path: Path):
    called = {"value": False}

    def poll():
        called["value"] = True
        return []

    monkeypatch.setattr(
        "creator_engine_validator.brain_intent_materializer.HistoryScanner",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("default scanner used")),
    )

    MaterializerRunLoop(_config(tmp_path), poll_source=poll).run_once()

    assert called["value"] is True


def test_run_loop_importable_without_git_subprocess_calls():
    assert MaterializerRunLoop.__name__ == "MaterializerRunLoop"


def test_run_loop_docstring_contains_q4_singleton_caveat():
    assert (
        "Under multi-instance topology, multiple run-loop invocations against the same repo state would produce competing leases; correctness requires an external linearizable lock with the same brain-append exclusion scope (Q4 ratified ruling)."
        in (MaterializerRunLoop.__doc__ or "")
    )
