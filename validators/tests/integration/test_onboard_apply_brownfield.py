"""Integration-style brownfield ADOPTION-APPLY run with all live seams faked (ce-ops#85).

The sibling of ``test_onboard_apply_greenfield.py`` for the E3 join-PR layer: it drives the
full ``apply_onboard`` leg loop end-to-end with the adoption seams faked, asserting the join-PR
flow converges, the greenfield forge legs skip, and the ledger carries value-free adoption
evidence.

REAL-shape (ce-ops#44, Mode B): the VERBATIM-captured forge JSON (``fixtures/ce88_live_forge/``,
see ``CAPTURE.md`` for the exact ``gh api`` commands) drives the LIVE adoption driver's forge
legs — the two-token model (read vs write), the never-force push, and the exactly-one-PR open —
in ``tests/unit/test_onboard_apply_live.py`` (the live-driver venue; only the forge legs run
there, so no host-leg fakes are needed). The live Mode-A join PR on a real non-CE repo is the
VPS-rehearsal DoD, run later by the orchestrator — not these tests.
"""

from __future__ import annotations

import json

from creator_engine_validator import onboard_apply
from validators.tests.unit.test_onboard_apply import (
    FakeAdoptionDriver,
    _adoption_apply,
    _brownfield_probe,
    _leg,
)


def test_onboard_apply_brownfield_adoption_opens_join_pr_with_fake_driver(tmp_path):
    driver = FakeAdoptionDriver()
    summary = _adoption_apply(tmp_path, driver)

    assert summary["action"] == "onboard_apply"
    assert summary["target_repo"] == "octo/greenfield"
    assert summary["failed"] == 0 and summary["refused"] == 0

    # the full leg sequence is recorded (greenfield + adoption legs) and the ledger mirrors it.
    assert [leg["id"] for leg in summary["legs"]] == list(onboard_apply.LEG_IDS)
    ledger = tmp_path / "state" / "onboard" / "ledger.ndjson"
    entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert [entry["leg_id"] for entry in entries] == list(onboard_apply.LEG_IDS)

    # the 7 adoption legs converged; the greenfield FORGE legs skipped (brownfield_adoption_mode).
    for leg_id in onboard_apply.ADOPTION_LEG_IDS:
        assert _leg(summary, leg_id)["status"] in {"applied", "already_satisfied"}
    for leg_id in onboard_apply.ADOPTION_SKIPPED_GREENFIELD_LEG_IDS:
        assert _leg(summary, leg_id)["status"] == "skipped"

    # the join PR was opened + counted exactly once (verified), no greenfield deferral.
    assert summary["brownfield_adopted"] == 1
    assert summary["brownfield_adoption_pr"]["pr_number"] == 7
    assert summary["brownfield_deferred"] == 0

    # the ledger's adoption-evidence entry is value-free (no secret values).
    record = _leg(summary, "brownfield_record_apply_evidence")["verification"]
    assert record["repo"] == "octo/greenfield"
    assert record["pr_number"] == 7
    rendered = json.dumps(summary, sort_keys=True)
    assert "secret-token" not in rendered


def test_onboard_apply_brownfield_scrub_finding_blocks_the_whole_run(tmp_path):
    # End-to-end fail-closed: an unwaived scrub finding stops the run before any branch/push/PR.
    driver = FakeAdoptionDriver(scrub_result={
        "scanners": {
            "gitleaks": {"ran": True, "exit_code": 0, "findings": ["gitleaks:secrets.py:5"]},
            "trufflehog": {"ran": True, "exit_code": 0, "findings": []},
        }
    })
    summary = _adoption_apply(tmp_path, driver, probe=_brownfield_probe())
    assert summary["refused"] == 1
    assert _leg(summary, "brownfield_secret_preflight")["verification"]["code"] == "brownfield_secret_findings"
    assert summary["brownfield_adopted"] == 0
    # nothing downstream of the scrub ran
    assert "build_adoption_scaffold" not in driver.calls
    assert "push_adoption_branch" not in driver.calls
    assert "open_adoption_pr" not in driver.calls
