"""Integration-style greenfield apply run with all live seams faked."""

from __future__ import annotations

import json

from creator_engine_validator import onboard_apply
from validators.tests.unit.test_onboard_apply import FakeDriver, _apply


def test_onboard_apply_greenfield_converges_with_fake_driver(tmp_path):
    driver = FakeDriver()
    summary = _apply(tmp_path, driver)

    assert summary["action"] == "onboard_apply"
    assert summary["target_repo"] == "octo/greenfield"
    assert summary["greenfield_repos_created"] == 1
    assert summary["failed"] == 0
    assert summary["refused"] == 0
    assert [leg["id"] for leg in summary["legs"]] == list(onboard_apply.LEG_IDS)

    ledger = tmp_path / "state" / "onboard" / "ledger.ndjson"
    entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert [entry["leg_id"] for entry in entries] == list(onboard_apply.LEG_IDS)
    assert all(entry["target_repo"] == "octo/greenfield" for entry in entries)
