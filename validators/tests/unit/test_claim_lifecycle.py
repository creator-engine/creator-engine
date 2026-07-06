from __future__ import annotations

import json
from pathlib import Path

import pytest

import claim_lifecycle as lifecycle


NOW = "2026-07-06T14:00:00Z"


def _write_claim(root: Path, slug: str, state: str = "claimed") -> Path:
    path = root / ".ce" / "claims" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
slug: {slug}
issue: 476
repo: creator-engine/creator-engine
state: {state}
seat: seat-alpha
controller: CE-DEV-2
claimed_at: 2026-07-06T13:00:00Z
transitioned_at: 2026-07-06T13:00:00Z
pr: null
merge_sha: null
refs:
  - tracker#476
---
human notes
""",
        encoding="utf-8",
    )
    return path


def test_transition_moves_forward_and_emits_structured_log(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle")

    result = lifecycle.transition_claim(
        tmp_path,
        "ce-476-claim-lifecycle",
        "ready",
        pr="https://github.com/creator-engine/creator-engine/pull/123",
        now=NOW,
    )

    assert result.old_state == "claimed"
    assert result.new_state == "ready"
    payload = json.loads(lifecycle.structured_log_line(result))
    assert payload["event"] == "ce_claim_transition"
    assert payload["pr"].endswith("/123")
    written = (tmp_path / ".ce" / "claims" / "ce-476-claim-lifecycle.md").read_text(encoding="utf-8")
    assert "state: ready" in written
    assert "transitioned_at: 2026-07-06T14:00:00Z" in written
    assert "human notes" in written


def test_backward_transition_requires_force(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="ready")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="backward"):
        lifecycle.transition_claim(tmp_path, "ce-476-claim-lifecycle", "in-build", now=NOW)

    result = lifecycle.transition_claim(
        tmp_path,
        "ce-476-claim-lifecycle",
        "in-build",
        force=True,
        now=NOW,
    )
    assert result.new_state == "in-build"


def test_legacy_claim_is_upgraded_from_prose(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CE_SEAT", "seat-alpha")
    monkeypatch.setenv("CE_CONTROLLER", "CE-DEV-2")
    path = tmp_path / ".ce" / "claims" / "ce-476-claim-lifecycle.md"
    path.parent.mkdir(parents=True)
    path.write_text("CE-DEV-2 dispatched ce-476 to seat-alpha\n", encoding="utf-8")

    lifecycle.transition_claim(tmp_path, "ce-476-claim-lifecycle", "in-build", now=NOW)

    written = path.read_text(encoding="utf-8")
    assert written.startswith("---\nslug: ce-476-claim-lifecycle\n")
    assert "state: in-build" in written
    assert "seat: seat-alpha" in written
    assert "CE-DEV-2 dispatched ce-476" in written


def test_list_claims_filters_state_and_seat(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="ready")
    other = _write_claim(tmp_path, "ce-477-other", state="claimed")
    other.write_text(other.read_text(encoding="utf-8").replace("seat: seat-alpha", "seat: seat-beta"), encoding="utf-8")

    rows = lifecycle.list_claims(tmp_path, state="ready", seat="seat-alpha")

    assert [row["slug"] for row in rows] == ["ce-476-claim-lifecycle"]
    table = lifecycle.format_table(rows)
    assert "SLUG" in table
    assert "ce-476-claim-lifecycle" in table
