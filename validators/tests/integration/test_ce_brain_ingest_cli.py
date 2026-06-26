from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from creator_engine_validator import ce_cli
import pytest

pytestmark = pytest.mark.slow



def test_ce_brain_ingest_cli_json_roundtrip(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    corpus = tmp_path / "corpus"
    source = corpus / "brain.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Recall\n\nMarkdown source of truth.\n", encoding="utf-8")
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
    first = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert db_path.is_file()
    assert first["db_path"] == str(db_path)
    assert first["source_count"] == 1
    assert first["chunk_count"] == 1
    assert first["embedded_count"] == 1
    assert first["skipped_count"] == 0
    assert first["records"][0]["source_path"] == "corpus/brain.md"
    assert first["records"][0]["chunk_ref"] == "heading:recall"
    assert first["records"][0]["action"] == "upserted"
    with sqlite3.connect(db_path) as conn:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'recall_fts'"
        ).fetchone()
        fts_text = conn.execute(
            """
            SELECT text FROM recall_fts
            WHERE source_path = ? AND chunk_ref = ?
            """,
            ("corpus/brain.md", "heading:recall"),
        ).fetchone()
    assert table == ("recall_fts",)
    assert fts_text == ("# Recall\n\nMarkdown source of truth.\n",)

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
    second = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert second["embedded_count"] == 0
    assert second["skipped_count"] == 1
    assert second["records"][0]["action"] == "skipped"
    assert second["records"][0]["content_hash"] == first["records"][0]["content_hash"]
