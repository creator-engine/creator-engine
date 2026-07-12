from __future__ import annotations

import json

from creator_engine_validator import onboard_connection_status as status


LEG_IDS = status.LEG_IDS


def _entry(invocation: str, leg_id: str, action: str = "applied", outcome: str = "applied") -> dict:
    return {
        "schema_version": "1", "invocation_id": invocation, "target_repo": "creator-engine/example",
        "leg_id": leg_id, "timestamp": "2026-07-12T00:00:00+00:00",
        "result": {"id": leg_id, "status": outcome, "action": action},
    }


def _write_invocation(tmp_path, invocation: str, *, unresolved: bool = False) -> None:
    entries = []
    refusal_index = LEG_IDS.index("github_bootstrap_token_probe")
    for index, leg_id in enumerate(LEG_IDS):
        if unresolved and index == refusal_index:
            entries.append(_entry(invocation, leg_id, "forge_identity_unresolved", "refused"))
        elif unresolved and index > refusal_index:
            entries.append(_entry(invocation, leg_id, "dependency_not_verified", "skipped"))
        else:
            entries.append(_entry(invocation, leg_id))
    ledger = tmp_path / "onboard" / "ledger.ndjson"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8")


def test_exact_identity_refusal_cascade_is_unresolved(tmp_path):
    _write_invocation(tmp_path, "one", unresolved=True)
    assert status.read_status(tmp_path).state == status.UNRESOLVED_CONNECTION


def test_later_complete_invocation_clears_unresolved_advisory(tmp_path):
    _write_invocation(tmp_path, "one", unresolved=True)
    ledger = tmp_path / "onboard" / "ledger.ndjson"
    with ledger.open("a", encoding="utf-8") as fh:
        for leg_id in LEG_IDS:
            fh.write(json.dumps(_entry("two", leg_id)) + "\n")
    assert status.read_status(tmp_path).state == status.RESOLVED


def test_missing_ledger_is_resolved(tmp_path):
    assert status.read_status(tmp_path).state == status.RESOLVED


def test_malformed_or_incomplete_ledger_is_unknown(tmp_path):
    ledger = tmp_path / "onboard" / "ledger.ndjson"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("not-json\n", encoding="utf-8")
    assert status.read_status(tmp_path).state == status.UNKNOWN
    ledger.write_text(json.dumps(_entry("one", LEG_IDS[0])) + "\n", encoding="utf-8")
    assert status.read_status(tmp_path).state == status.UNKNOWN
    incomplete = _entry("one", LEG_IDS[0])
    del incomplete["timestamp"]
    ledger.write_text(json.dumps(incomplete) + "\n", encoding="utf-8")
    assert status.read_status(tmp_path).state == status.UNKNOWN


def test_unrelated_refusal_is_resolved(tmp_path):
    _write_invocation(tmp_path, "one")
    ledger = tmp_path / "onboard" / "ledger.ndjson"
    entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    entries[0]["result"] = {"id": LEG_IDS[0], "status": "refused", "action": "another_refusal"}
    ledger.write_text("".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8")
    assert status.read_status(tmp_path).state == status.RESOLVED


def test_leg_ids_matches_onboard_apply_composition():
    """onboard_connection_status.LEG_IDS must equal onboard_apply.LEG_IDS exactly.

    LEG_IDS in onboard_connection_status is a hard-coded copy kept separate from
    onboard_apply to avoid a version-boundary import at runtime (shared layer must
    not pull in a v3 executor).  But if the two diverge, read_status() returns
    UNKNOWN for every onboard invocation because the ledger leg-order check
    (``[entry["leg_id"] for entry in latest] != list(LEG_IDS)``) never matches,
    permanently killing the unresolved-connection advisory.
    """
    # Local import: onboard_apply is v3-runtime; importing it here in tests does
    # NOT cross the version boundary (the checker's AST scan covers only files
    # under creator_engine_validator/, not the tests/ tree).
    from creator_engine_validator import onboard_apply

    assert status.LEG_IDS == onboard_apply.LEG_IDS, (
        "onboard_connection_status.LEG_IDS is out of sync with onboard_apply.LEG_IDS. "
        "Drift here makes read_status() permanently return UNKNOWN, silently suppressing "
        "the unresolved-connection advisory for every onboard invocation."
    )


def test_watched_leg_refused_with_different_action_is_resolved(tmp_path):
    """github_bootstrap_token_probe refused with a non-forge-identity action is RESOLVED.

    Only the exact forge_identity_unresolved action at the watched leg position
    (combined with the full skipped cascade) triggers UNRESOLVED_CONNECTION.
    Any other refusal action at that leg must fall through to RESOLVED so that
    genuine PAT-permission errors are not misclassified as an identity advisory.
    """
    refusal_index = LEG_IDS.index("github_bootstrap_token_probe")
    entries = []
    for index, leg_id in enumerate(LEG_IDS):
        if index == refusal_index:
            entries.append(_entry("inv1", leg_id, "token_missing", "refused"))
        else:
            entries.append(_entry("inv1", leg_id))
    ledger = tmp_path / "onboard" / "ledger.ndjson"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    assert status.read_status(tmp_path).state == status.RESOLVED
