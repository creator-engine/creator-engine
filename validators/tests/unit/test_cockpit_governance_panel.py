"""Unit tests for the Governance/Authority panel projection (v3.5-B.3, L2).

The differentiator surface: the envelope access matrix (rakkess pattern) + the
``can-i`` probe, the ★ REFUSED feed off the hook's refusal chain (+ the legacy
advisory log, labelled), explicit-vs-implicit deny classification (IAM
pattern), ratifier attribution, and the posture (hard-vs-advisory) section —
ALL computed in L2 and present in the ``--json`` snapshot (principle 6).
"""

from __future__ import annotations

from pathlib import Path

from creator_engine_validator import hook_check
from creator_engine_validator.runner import cockpit_demo_seed, cockpit_readmodel


def _demo_snapshot() -> dict:
    return cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())


# --- the envelope matrix (rakkess pattern) -----------------------------------

def test_matrix_is_truthful_against_the_envelope_fixture():
    snapshot = _demo_snapshot()
    seats = snapshot["governance"]["seats"]
    reviewer = seats["pr-300-review"]
    assert reviewer["matrix"]["pr_review"] == "granted"
    for mechanic, cell in reviewer["matrix"].items():
        if mechanic != "pr_review":
            assert cell == "withheld", mechanic
    # A seat with NO envelope: every mechanic withheld.
    builder = seats["gate-uploads"]
    assert set(builder["matrix"].values()) == {"withheld"}
    # The blocked push seat carries envelope_ref=none -> the standing
    # no-write-authority fact.
    push_seat = seats["gate-push-refusal"]
    assert push_seat["no_write_authority"] is True
    assert set(push_seat["matrix"].values()) == {"withheld"}


def test_matrix_rows_are_the_restricted_mechanics():
    snapshot = _demo_snapshot()
    assert snapshot["governance"]["mechanics"] == list(
        cockpit_readmodel.RESTRICTED_MECHANICS
    )
    for seat in snapshot["governance"]["seats"].values():
        assert list(seat["matrix"].keys()) == list(cockpit_readmodel.RESTRICTED_MECHANICS)


# --- the can-i probe ----------------------------------------------------------

def test_can_i_probe_answers_from_the_matrix():
    snapshot = _demo_snapshot()
    reviewer = snapshot["governance"]["seats"]["pr-300-review"]
    granted = cockpit_readmodel.can_i(reviewer, "pr_review", pr_number=300)
    assert granted["allowed"] is True
    assert "rva-demo-pr300" in granted["why"]

    wrong_pr = cockpit_readmodel.can_i(reviewer, "pr_review", pr_number=311)
    assert wrong_pr["allowed"] is False
    assert "300" in wrong_pr["why"]

    push = cockpit_readmodel.can_i(reviewer, "deploy")
    assert push["allowed"] is False
    assert "Operator" in push["why"]  # the standing push/deploy fact

    unknown = cockpit_readmodel.can_i(reviewer, "format_disk")
    assert unknown["allowed"] is False


# --- explicit vs implicit deny classification (IAM pattern) -------------------

def test_push_refusal_is_an_explicit_deny_with_the_deciding_clause():
    snapshot = _demo_snapshot()
    chain_entries = [
        e for e in snapshot["refusals"]["entries"] if e.get("source") == "refusal-chain"
    ]
    push = [e for e in chain_entries if e["run_id"] == "gate-push-refusal"]
    assert push, "the push refusal must be on the feed"
    assert push[0]["deny_kind"] == "explicit"
    assert push[0]["deciding_clause"] == "G2.007.2"


def test_envelope_scope_denial_is_an_implicit_deny():
    snapshot = _demo_snapshot()
    chain_entries = [
        e for e in snapshot["refusals"]["entries"] if e.get("source") == "refusal-chain"
    ]
    scope_denial = [e for e in chain_entries if e["run_id"] == "envelope-scope-denial"]
    assert scope_denial, "the envelope-scope denial must be on the feed"
    assert scope_denial[0]["deny_kind"] == "implicit"
    assert scope_denial[0]["deciding_clause"] is None


# --- the feed: ordering, sources, chain verification --------------------------

def test_feed_orders_newest_first_and_labels_sources():
    snapshot = _demo_snapshot()
    refusals = snapshot["refusals"]
    stamps = [e.get("recorded_at") for e in refusals["entries"]]
    assert stamps == sorted(stamps, reverse=True)
    sources = {e.get("source") for e in refusals["entries"]}
    assert sources == {"refusal-chain", "legacy-observations"}
    legacy = [e for e in refusals["entries"] if e["source"] == "legacy-observations"]
    assert all(e.get("advisory") is True for e in legacy)
    assert refusals["chain_verified"] is True
    assert "refusal-chain" in refusals["source_label"]


def test_demo_refusal_chain_verifies_clean():
    from creator_engine_validator.runtime_evidence_spine import verify_chain

    seed = cockpit_demo_seed.seed()
    assert verify_chain(seed["refusal_chain"]) == []


# --- attribution --------------------------------------------------------------

def test_attribution_renders_the_envelope_bindings():
    snapshot = _demo_snapshot()
    envelope = snapshot["governance"]["seats"]["pr-300-review"]["envelope"]
    assert envelope["envelope_id"] == "rva-demo-pr300"
    assert envelope["pr_number"] == 300
    assert len(envelope["ratified_prompt_sha"]) == 64
    assert envelope["actor"]
    assert envelope["emitting_role"] == "operator"
    facts = snapshot["governance"]["standing_facts"]
    assert any("git push" in f and "Operator" in f for f in facts)


# --- posture (hard vs advisory, the G-i split) ---------------------------------

def test_posture_section_carries_the_g_i_split():
    snapshot = _demo_snapshot()
    posture = snapshot["governance"]["posture"]
    assert any("secret" in h for h in posture["hard_denies"])
    assert any("restricted mechanic" in h for h in posture["hard_denies"])
    assert any("manifest" in a for a in posture["advisory"])


# --- --json parity (everything the panel renders is in the snapshot) ----------

def test_json_parity_panel_sections_present():
    import json

    snapshot = _demo_snapshot()
    assert json.loads(json.dumps(snapshot, sort_keys=True)) == snapshot
    governance = snapshot["governance"]
    for key in ("mechanics", "seats", "standing_facts", "posture"):
        assert key in governance
    assert "entries" in snapshot["refusals"]


# --- end-to-end: the hook writes, the read-model projects ---------------------

def test_hook_refusal_lands_on_the_live_panel(tmp_path):
    """The live proof at test level: a governed deny -> chain file -> feed entry."""
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git push origin main"},
        "session_id": "live-seat",
    }
    ctx = hook_check.HookContext(
        posture="governed", manifest_paths=("README.md",), repo_root=str(tmp_path)
    )
    decision = hook_check.evaluate(event, ctx)
    assert decision.decision == "deny"

    observations_dir = tmp_path / ".hermes" / "cc-g-c-hook-observations"
    state_root = tmp_path / "state"
    state_root.mkdir()
    snapshot = cockpit_readmodel.snapshot_from_roots(
        state_root, observations_dir=observations_dir, environ={}
    )
    entries = snapshot["refusals"]["entries"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["source"] == "refusal-chain"
    assert entry["classification"] == "denied"
    assert entry["run_id"] == "live-seat"
    assert entry["deny_kind"] == "explicit"
    assert entry["deciding_clause"] == "G2.007.2"
    assert snapshot["refusals"]["chain_verified"] is True
    assert snapshot["availability"]["refusals"] == "ok"
