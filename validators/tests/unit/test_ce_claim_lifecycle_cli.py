from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import ce_cli


def _write_claim(root: Path) -> None:
    path = root / ".ce" / "claims" / "ce-476-claim-lifecycle.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        """---
slug: ce-476-claim-lifecycle
issue: 476
repo: creator-engine/creator-engine
state: claimed
seat: seat-alpha
controller: CE-DEV-2
claimed_at: 2026-07-06T13:00:00Z
transitioned_at: 2026-07-06T13:00:00Z
pr: null
merge_sha: null
refs:
  - tracker#476
---
brief pointer
""",
        encoding="utf-8",
    )


def test_ce_claim_transition_json(tmp_path: Path, capsys) -> None:
    _write_claim(tmp_path)

    rc = ce_cli.main(
        [
            "claim",
            "transition",
            "ce-476-claim-lifecycle",
            "landed",
            "--sha",
            "abc123",
            "--repo-root",
            str(tmp_path),
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["new_state"] == "landed"
    assert payload["merge_sha"] == "abc123"


def test_ce_claim_transition_plain_output_is_structured_log(tmp_path: Path, capsys) -> None:
    _write_claim(tmp_path)

    rc = ce_cli.main(
        [
            "claim",
            "transition",
            "ce-476-claim-lifecycle",
            "in-build",
            "--repo-root",
            str(tmp_path),
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["event"] == "ce_claim_transition"
    assert payload["old_state"] == "claimed"
    assert payload["new_state"] == "in-build"


def test_ce_claim_list_filters(tmp_path: Path, capsys) -> None:
    _write_claim(tmp_path)

    rc = ce_cli.main(
        [
            "claim",
            "list",
            "--repo-root",
            str(tmp_path),
            "--state",
            "claimed",
            "--seat",
            "seat-alpha",
            "--json",
        ]
    )

    assert rc == 0
    rows = json.loads(capsys.readouterr().out)
    assert [row["slug"] for row in rows] == ["ce-476-claim-lifecycle"]
