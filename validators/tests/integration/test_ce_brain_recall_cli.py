from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import brain_runtime, ce_cli
import pytest

pytestmark = pytest.mark.slow



def _ingest(tmp_path: Path) -> tuple[Path, Path]:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "merge.md").write_text(
        "# Merge throughput\n\nReviewed-vs-merged head merge queue prior art.\n",
        encoding="utf-8",
    )
    (corpus / "topology.md").write_text(
        "# Seat topology\n\nDGX spark host controller seat map.\n",
        encoding="utf-8",
    )
    state_root = tmp_path / ".ce" / "state"
    db_path = state_root / "brain" / "recall.sqlite"
    rc = ce_cli.main(
        [
            "brain",
            "ingest",
            "--state-root",
            str(state_root),
            "--db",
            str(db_path),
            "--source",
            str(corpus),
            "--scope",
            "public",
            "--as-of",
            "2026-06-21T00:00:00Z",
            "--json",
        ]
    )
    assert rc == 0
    return state_root, db_path


def test_ce_brain_recall_cli_json_pointer_and_tier(tmp_path: Path, capsys):
    state_root, db_path = _ingest(tmp_path)
    capsys.readouterr()

    # Seed an SSOT assertion so the surface can show tier precedence.
    rc = ce_cli.main(
        [
            "brain",
            "assert",
            "--state-root",
            str(state_root),
            "--scope",
            "merge",
            "--claim-json",
            json.dumps({"fact": "merge queue uses reviewed head"}),
            "--evidence-ref",
            "design:merge",
        ]
    )
    assert rc == 0
    capsys.readouterr()

    rc = ce_cli.main(
        [
            "brain",
            "recall",
            "--state-root",
            str(state_root),
            "--db",
            str(db_path),
            "--top-k",
            "5",
            "--json",
            "merge queue prior art",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["context"] == "merge queue prior art"
    tiers = [item["tier"] for item in payload["items"]]
    assert "ssot" in tiers and "recall" in tiers
    # SSOT precedes recall.
    assert tiers.index("ssot") < tiers.index("recall")
    recall_item = next(item for item in payload["items"] if item["tier"] == "recall")
    assert recall_item["source_path"].endswith(".md")
    assert recall_item["as_of"] == "2026-06-21T00:00:00Z"
    assert recall_item["verify_against"] == recall_item["source_path"]
    assert "text" not in recall_item


def test_ce_brain_recall_cli_hydrate_additive(tmp_path: Path, capsys):
    state_root, db_path = _ingest(tmp_path)
    capsys.readouterr()
    core = tmp_path / "MEMORY-CORE.md"
    core.write_text("# CORE\n\nalways load.\n", encoding="utf-8")
    before = core.read_text(encoding="utf-8")

    rc = ce_cli.main(
        [
            "brain",
            "recall",
            "--state-root",
            str(state_root),
            "--db",
            str(db_path),
            "--hydrate",
            "--core-path",
            str(core),
            "--json",
            "seat topology",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["core_loaded"] is True
    assert payload["core_path"] == str(core)
    assert payload["recall"]
    # Hydration is additive: the CORE file is never mutated.
    assert core.read_text(encoding="utf-8") == before


def test_ce_brain_recall_cli_malformed_ssot_ledger_fails_closed(tmp_path: Path, capsys):
    """A malformed SSOT ledger makes ``ce brain recall`` exit non-zero (fail closed)."""

    state_root, db_path = _ingest(tmp_path)
    capsys.readouterr()
    ledger = brain_runtime.ledger_path(str(state_root))
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("kind: brain-assertion-ledger\nrecords: not-a-list\n", encoding="utf-8")

    rc = ce_cli.main(
        [
            "brain",
            "recall",
            "--state-root",
            str(state_root),
            "--db",
            str(db_path),
            "--json",
            "merge queue",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1, "malformed SSOT ledger must fail closed, not downgrade to recall-only"
    assert "refused" in captured.err.lower()


def test_ce_brain_recall_cli_embedder_mismatch_fails_closed(tmp_path: Path, capsys):
    """Recall with the wrong embedder dim for the store fails closed at the CLI."""

    from creator_engine_validator.brain_recall import DeterministicFakeEmbedding
    from creator_engine_validator import brain_ingest_runtime

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "merge.md").write_text("# Merge\n\nmerge queue prior art.\n", encoding="utf-8")
    state_root = tmp_path / ".ce" / "state"
    db_path = state_root / "brain" / "recall.sqlite"
    # Build a 768-dim (EmbeddingGemma-like) store directly through the ingest runtime.
    brain_ingest_runtime.ingest_markdown(
        sources=[str(corpus)],
        state_root=str(state_root),
        db_path=str(db_path),
        scope="public",
        as_of="2026-06-21T00:00:00Z",
        embedder=DeterministicFakeEmbedding(model_id="google/embeddinggemma-300m", dim=768),
    )
    capsys.readouterr()

    # The default (32-dim) embedder cannot query a 768-dim store.
    rc = ce_cli.main(
        [
            "brain",
            "recall",
            "--state-root",
            str(state_root),
            "--db",
            str(db_path),
            "--json",
            "merge queue prior art",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1, "embedder/store dimension mismatch must fail closed"
    assert "768" in captured.err and "32" in captured.err


def test_ce_brain_recall_cli_human_output(tmp_path: Path, capsys):
    state_root, db_path = _ingest(tmp_path)
    capsys.readouterr()
    rc = ce_cli.main(
        [
            "brain",
            "recall",
            "--state-root",
            str(state_root),
            "--db",
            str(db_path),
            "merge queue",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "ce brain recall:" in out
    assert "re-verify against source" in out
