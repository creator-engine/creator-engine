from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ce-claim-closeout.yml"


def _load() -> dict:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return doc


def _on_block(doc: dict) -> dict:
    return doc.get("on", doc.get(True))


def test_claim_closeout_triggers_only_on_closed_pull_request() -> None:
    on = _on_block(_load())

    assert on == {"pull_request": {"types": ["closed"]}}


def test_claim_closeout_uses_narrow_permissions() -> None:
    doc = _load()

    assert doc["permissions"] == {"contents": "read", "pull-requests": "read"}
    job = doc["jobs"]["claim-closeout"]
    assert job["permissions"] == {"contents": "write", "pull-requests": "read"}
    assert "github.event.pull_request.merged == true" in job["if"]


def test_claim_closeout_invokes_claim_transition_without_run_expressions() -> None:
    doc = _load()
    steps = doc["jobs"]["claim-closeout"]["steps"]
    run_blocks = "\n".join(step.get("run", "") for step in steps if isinstance(step, dict))

    assert "claim transition" in run_blocks
    assert "landed" in run_blocks
    assert "${{" not in run_blocks
