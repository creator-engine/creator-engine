"""Unit tests for the ◆ CE Completion Report (``v3_report``) — G-7.3.

Pure render over a run-summary. Asserts: the canon Outcome/Verdict/Next/Artifacts
vocabulary (PR #165, stage-vocabulary.md §3) is used VERBATIM; the Outcome labels
stay set-equal to the conserved ``RUN_OUTCOMES`` enum (no third vocabulary, no
relabel of the machine); the report folds the REAL run-outcome record + the G-5
spend projection off an evidence chain; artifact awareness enumerates inspect
commands; the module is v3-classified and pure.
"""
from __future__ import annotations

from decimal import Decimal

from creator_engine_validator import _versions as ver
from creator_engine_validator import v3_report as rep
from creator_engine_validator.runtime_evidence_spine import (
    RUN_OUTCOMES,
    RUN_OUTCOME_RECORD_TYPE,
)


# ---------------------------------------------------------------------------
# Outcome — the canon plain renderings over the CONSERVED enum (no third vocab)
# ---------------------------------------------------------------------------
def test_outcome_labels_are_set_equal_to_conserved_enum():
    # the skin must cover exactly the conserved RUN_OUTCOMES — no drift, no extras
    assert set(rep.OUTCOME_LABELS) == set(RUN_OUTCOMES)


def test_outcome_labels_match_canon_renderings():
    assert rep.outcome_label("pr_opened") == "PR opened"
    assert rep.outcome_label("pr_merged") == "Merged"
    assert rep.outcome_label("review_submitted") == "Review submitted"
    assert rep.outcome_label("research_delivered") == "Research delivered"
    assert rep.outcome_label("no_change") == "No change needed"
    assert rep.outcome_label(None) == "—"


# ---------------------------------------------------------------------------
# Verdict — the grading synthesis (Done-when · CI · in-scope · of Budget)
# ---------------------------------------------------------------------------
def test_verdict_renders_canon_grading_line():
    s = {"done_when_total": 3, "done_when_met": 3, "ci": "green", "in_scope": True,
         "spent": 0.7, "budget": 5, "budget_size": "S"}
    v = rep.render_verdict(s)
    assert v == "Done-when 3/3 met · tests green · in scope ✓ · 14% of Budget S"


def test_verdict_percent_unit_renders_suffix_not_prefix():
    # % unit suffixes the amount ("of 10%"), $ prefixes it ("of $10")
    assert "of 10%" in rep.render_verdict({"spent": 2, "budget": 10, "unit": "%"})
    assert "of $10" in rep.render_verdict({"spent": 2, "budget": 10, "unit": "$"})


def test_verdict_out_of_scope_and_red_ci():
    s = {"done_when_total": 3, "done_when_met": 1, "ci": "red", "in_scope": False}
    v = rep.render_verdict(s)
    assert "Done-when 1/3 met" in v and "tests red" in v and "out of scope ✗" in v


# ---------------------------------------------------------------------------
# Next — derived (Outcome × Change-type)
# ---------------------------------------------------------------------------
def test_next_for_each_outcome():
    assert rep.render_next({"outcome": "pr_opened", "pr": 7, "change_type": "code"}) == \
        "→ Review PR #7  (Change-type code → your approval)"
    assert rep.render_next({"outcome": "pr_merged"}) == "→ Done — merged"
    assert rep.render_next({"outcome": "no_change"}).startswith("→ Nothing to ship")
    assert rep.render_next({"outcome": "research_delivered"}).startswith("→ Read")


# ---------------------------------------------------------------------------
# fold the REAL conserved signals off an evidence chain
# ---------------------------------------------------------------------------
def test_summary_from_evidence_folds_outcome_and_spend():
    records = [
        {"record_type": "runtime_spend_ledger", "unit": "$", "amount": 0.7, "run_id": "r-91a"},
        {"record_type": RUN_OUTCOME_RECORD_TYPE, "outcome": "pr_opened", "run_id": "r-91a",
         "change_set": {"branch": "b", "base": "m", "pr_number": 7}},
    ]
    s = rep.summary_from_evidence(records, scope_id="cs-4f2", budget=5, done_when_total=3,
                                  done_when_met=3, ci="green", in_scope=True, change_type="code",
                                  budget_size="S")
    assert s["outcome"] == "pr_opened"
    assert s["pr"] == 7
    assert s["run_id"] == "r-91a"
    assert s["spent"] == Decimal("0.7")  # the real G-5 projection fold
    # the assembled report reads in the canon vocabulary
    block = "\n".join(rep.render_report(s))
    assert "Outcome   PR opened → #7" in block
    assert "Done-when 3/3 met · tests green · in scope ✓ · 14% of Budget" in block
    assert "Next      → Review PR #7" in block


def test_summary_from_evidence_no_outcome_record():
    s = rep.summary_from_evidence([], scope_id="x")
    assert s["outcome"] is None
    assert rep.outcome_label(s["outcome"]) == "—"


# ---------------------------------------------------------------------------
# artifact awareness — enumerate inspect commands
# ---------------------------------------------------------------------------
def test_enumerate_artifacts():
    s = {"run_id": "r-1", "scope_id": "cs-1", "pr": 7, "spent": Decimal("1")}
    enumerated = rep.enumerate_artifacts(s)
    arts = {a["kind"] for a in enumerated}
    assert {"pr", "scope", "evidence", "spend"} <= arts
    pr = [a for a in enumerated if a["kind"] == "pr"][0]
    assert pr["inspect"] == "gh pr view 7"
    evidence = [a for a in enumerated if a["kind"] == "evidence"][0]
    spend = [a for a in enumerated if a["kind"] == "spend"][0]
    assert evidence["inspect"] == "ce artifacts cs-1 --run-id r-1"
    assert spend["inspect"] == "ce artifacts cs-1 --run-id r-1"
    assert evidence["inspect"] != "ce artifacts r-1"
    assert spend["inspect"] != "ce artifacts r-1"


def test_inspect_commands_use_user_facing_ce_not_cev3():
    # Operator-ratified directive: the user-facing command is `ce`, never `cev3`.
    assert rep.CE_CMD == "ce"
    s = {"run_id": "r-1", "scope_id": "cs-1", "pr": 7, "spent": Decimal("1")}
    for a in rep.enumerate_artifacts(s):
        assert "cev3" not in a["inspect"]
        if a["kind"] in ("scope", "evidence", "spend"):
            assert a["inspect"].startswith("ce ")


def test_report_block_shape():
    lines = rep.render_report({"run_id": "r-1", "scope_id": "cs-1", "outcome": "pr_merged"})
    assert lines[0].startswith("┌─ ◆ CE COMPLETION REPORT")
    assert any(l.startswith("│ Outcome") for l in lines)
    assert any(l.startswith("│ Verdict") for l in lines)
    assert any(l.startswith("│ Next") for l in lines)
    assert lines[-1].startswith("└")


# ---------------------------------------------------------------------------
# classification / purity
# ---------------------------------------------------------------------------
def test_v3_classified_and_pure():
    assert ver.classify("v3_report") == ver.V3
    import inspect
    src = inspect.getsource(rep)
    for io_marker in ("open(", "read_text", "write_text", "Path.home", "os.environ", "import subprocess"):
        assert io_marker not in src, f"report render must stay pure (found {io_marker!r})"
