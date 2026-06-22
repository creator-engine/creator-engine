from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import brain_recall_surface, ce_cli

AS_OF = "2026-06-22T00:00:00Z"
HYDRATION_QUERY = "brain recall hydration additive pointers core unchanged no inlined text"


def _write_corpus(corpus: Path) -> None:
    corpus.mkdir()
    (corpus / "brain-hydration.md").write_text(
        "# Brain recall hydration\n\n"
        "G9 brain recall hydration returns additive recall pointers beside MEMORY CORE "
        "without inlined text. Hydrate session carries source_path, chunk_ref, "
        "content_hash, and as_of while keeping CORE unchanged.\n",
        encoding="utf-8",
    )
    (corpus / "merge-review.md").write_text(
        "# Merge queue review\n\n"
        "Merge queue review lanes compare reviewed-vs-merged heads and preserve "
        "reviewer evidence for merge throughput decisions.\n",
        encoding="utf-8",
    )
    (corpus / "seat-topology.md").write_text(
        "# Seat topology foreman\n\n"
        "Seat topology maps foreman and worker seats, controller host ownership, "
        "pane routing, and launch supervision.\n",
        encoding="utf-8",
    )
    (corpus / "decoy.md").write_text(
        "# Garden notes\n\n"
        "Tomatoes, calendars, and lunch menus are unrelated to recall hydration, "
        "merge queues, and seat topology.\n",
        encoding="utf-8",
    )


def _assert_pointer_payload(item: dict, *, source_path: str) -> None:
    assert item["tier"] == "recall"
    assert item["source_path"] == source_path
    assert item["verify_against"] == source_path
    assert item["chunk_ref"].startswith("heading:")
    assert item["content_hash"]
    assert item["as_of"] == AS_OF
    assert "text" not in item
    assert "G9 brain recall hydration returns" not in json.dumps(item, sort_keys=True)


def test_g9_brain_recall_and_hydrate_smoke(tmp_path: Path, capsys):
    corpus = tmp_path / "corpus"
    _write_corpus(corpus)
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
            AS_OF,
            "--json",
        ]
    )
    ingest_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert ingest_payload["model_id"] == "ce-deterministic-fake-embedding-v1"
    assert ingest_payload["source_count"] == 4
    assert ingest_payload["chunk_count"] == 4

    rc = ce_cli.main(
        [
            "brain",
            "recall",
            "--state-root",
            str(state_root),
            "--db",
            str(db_path),
            "--top-k",
            "4",
            "--json",
            HYDRATION_QUERY,
        ]
    )
    recall_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert recall_payload["context"] == HYDRATION_QUERY
    recall_items = recall_payload["items"]
    source_paths = [item["source_path"] for item in recall_items]
    assert source_paths[0] == "brain-hydration.md"
    assert "merge-review.md" in source_paths
    _assert_pointer_payload(recall_items[0], source_path="brain-hydration.md")
    assert all("text" not in item for item in recall_items)

    surface = brain_recall_surface.open_surface(
        db_path=str(db_path),
        state_root=str(state_root),
    )
    surface_result = surface.recall("foreman seat topology controller host", top_k=4)
    assert surface_result.recall_items
    top_hit = surface_result.recall_items[0]
    assert top_hit.source_path == "seat-topology.md"
    assert top_hit.chunk_ref == "heading:seat-topology-foreman"
    _assert_pointer_payload(top_hit.to_dict(), source_path="seat-topology.md")

    core = tmp_path / "MEMORY-CORE.md"
    core.write_text("# CORE\n\nAlways-loaded session core remains unchanged.\n", encoding="utf-8")
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
            "--top-k",
            "2",
            "--json",
            HYDRATION_QUERY,
        ]
    )
    hydrate_payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert hydrate_payload["core_loaded"] is True
    assert hydrate_payload["core_path"] == str(core)
    assert core.read_text(encoding="utf-8") == before
    assert hydrate_payload["recall"]
    _assert_pointer_payload(hydrate_payload["recall"][0], source_path="brain-hydration.md")
    assert all("text" not in item for item in hydrate_payload["recall"])

    hydration = surface.hydrate_session(
        HYDRATION_QUERY,
        top_k=2,
        core_path=str(core),
    )
    assert hydration.core_loaded is True
    assert hydration.core_path == str(core)
    assert core.read_text(encoding="utf-8") == before
    assert hydration.recall
    in_process_payload = hydration.to_dict()
    assert in_process_payload["core_loaded"] is True
    assert in_process_payload["core_path"] == str(core)
    _assert_pointer_payload(in_process_payload["recall"][0], source_path="brain-hydration.md")
    assert all("text" not in item for item in in_process_payload["recall"])
