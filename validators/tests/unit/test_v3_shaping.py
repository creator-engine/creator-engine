"""Unit tests for the v3 shaping dialogue (``v3_shaping``) — G-7.2.

The Frame→Shape grill-me engine + the chat→Scope detect-and-offer dial. Asserts:
the grill-me flags exactly the missing DoR gaps (rubric = `coordination.scope_is_ready`);
Budget (`appetite`) is human-only (the agent never drafts it); Change-type is
safe-by-default (tighten free / loosen needs ratification); the dial offers per the
`f(persona, risk-class)` table at the conservative default; the surface is
v3-classified and pure.
"""
from __future__ import annotations

from creator_engine_validator import _versions as ver
from creator_engine_validator import v3_shaping as sh


_FULL = {
    "scope_id": "rate-limit-login",
    "intent": "rate-limit POST /api/login",
    "acceptance_criteria": ["429 over 100/min", "unit test"],
    "appetite": {"amount": 5, "unit": "$"},
    "mutation_class": "code",
}


# ---------------------------------------------------------------------------
# grill-me — flags exactly the missing DoR gaps (rubric = scope_is_ready)
# ---------------------------------------------------------------------------
def test_full_scope_has_no_gaps_and_is_ready():
    r = sh.shape(_FULL)
    assert r.ready is True
    assert r.gaps == ()
    assert r.questions == ()


def test_grillme_flags_exact_gaps():
    draft = {"scope_id": "x", "intent": "do a thing"}  # missing Done-when, Budget, Change-type
    r = sh.shape(draft)
    fields = {g.field for g in r.gaps}
    assert fields == {"acceptance_criteria", "appetite", "mutation_class"}
    assert not r.ready
    # each gap carries its user-facing label + a minimum question
    labels = {g.label for g in r.gaps}
    assert labels == {"Done-when", "Budget", "Change-type"}
    assert all(g.question for g in r.gaps)


def test_grillme_rubric_is_scope_is_ready():
    # the engine's readiness IS the coordination DoR predicate (reuse, not re-derive)
    from creator_engine_validator import coordination
    for draft in ({}, {"intent": "x"}, _FULL):
        assert sh.shape(draft).ready == coordination.scope_is_ready(draft)[0]


# ---------------------------------------------------------------------------
# Budget is human-only — the agent never drafts the appetite
# ---------------------------------------------------------------------------
def test_budget_is_human_only():
    assert "appetite" in sh.HUMAN_ONLY_FIELDS
    assert sh.agent_may_draft("intent") is True
    assert sh.agent_may_draft("acceptance_criteria") is True
    assert sh.agent_may_draft("mutation_class") is True
    assert sh.agent_may_draft("appetite") is False


def test_budget_gap_is_flagged_human_only():
    # everything agent-draftable supplied; only the Budget remains → a human-only gap
    draft = {"scope_id": "x", "intent": "do", "acceptance_criteria": ["t"], "mutation_class": "code"}
    r = sh.shape(draft)
    assert [g.field for g in r.gaps] == ["appetite"]
    assert r.gaps[0].human_only is True
    assert r.human_only_gaps == r.gaps


def test_prd_seed_is_one_bounded_scope_and_reuses_grill():
    prd = """# Signup PRD

## User registration flow

Build registration for new users.

## Acceptance Criteria

- User can create an account with email and password.
- Duplicate email is rejected.

## Team management flow

- Invite teammates.
"""
    seed = sh.seed_scope_from_prd(prd, "docs/prd/signup.md")
    assert seed.candidate_slice == "User registration flow"
    assert seed.source_note == "Source PRD: docs/prd/signup.md"
    assert seed.draft["scope_id"] == "user-registration-flow"
    assert "Team management flow" not in seed.draft["intent"]
    result = sh.shape(seed.draft)
    assert {g.field for g in result.gaps} == {"appetite"}


# ---------------------------------------------------------------------------
# Change-type is safe-by-default — tighten free, loosen needs ratification
# ---------------------------------------------------------------------------
def test_retier_tighten_is_free():
    res = sh.retier("code", "deploy")  # higher blast radius → tighten
    assert res.allowed and res.direction == "tighten" and res.mutation_class == "deploy"


def test_retier_same_is_noop():
    assert sh.retier("code", "code").direction == "same"


def test_retier_loosen_requires_ratification():
    res = sh.retier("deploy", "code")  # lower blast radius → loosen
    assert res.allowed is False and res.direction == "loosen"
    assert res.mutation_class == "deploy"  # unchanged on refusal (safe-by-default)
    res2 = sh.retier("deploy", "code", ratified=True)
    assert res2.allowed is True and res2.mutation_class == "code"


def test_retier_unknown_class_refused():
    assert sh.retier("code", "bogus").allowed is False


# ---------------------------------------------------------------------------
# the detect-and-offer dial — f(persona, risk-class), conservative default
# ---------------------------------------------------------------------------
def test_dial_thresholds_match_canon_table():
    assert sh.offer_threshold("dev", "code") == "clear"        # dev / low
    assert sh.offer_threshold("dev", "deploy") == "explicit"   # dev / high
    assert sh.offer_threshold("ceo", "docs") == "actionable"   # ceo / low
    assert sh.offer_threshold("ceo", "schema") == "clear"      # ceo / high


def test_dial_offers_when_signal_meets_threshold():
    # dev / low needs "clear"
    assert sh.should_offer("dev", "code", "clear") is True
    assert sh.should_offer("dev", "code", "explicit") is True
    assert sh.should_offer("dev", "code", "actionable") is False
    # dev / high needs "explicit"
    assert sh.should_offer("dev", "deploy", "clear") is False
    assert sh.should_offer("dev", "deploy", "explicit") is True
    # ceo / low is eager
    assert sh.should_offer("ceo", "docs", "actionable") is True


def test_dial_biases_conservative_when_uncertain():
    # unknown persona → strictest threshold (explicit); a weak signal → no offer
    assert sh.offer_threshold("unknown", "code") == "explicit"
    assert sh.should_offer("unknown", "code", "clear") is False
    # unknown signal → treated as weakest → no offer
    assert sh.should_offer("dev", "code", "???") is False


def test_risk_class_bands():
    assert sh.risk_class("docs") == "low" and sh.risk_class("code") == "low"
    for hi in ("schema", "deploy", "governance", "identity", "security"):
        assert sh.risk_class(hi) == "high"


def test_risk_class_unknown_biases_high():
    # an unknown or absent change-type → high band (bias conservative when uncertain)
    assert sh.risk_class(None) == "high"
    assert sh.risk_class("bogus") == "high"
    # so an omitted change-type makes the dial demand the strictest signal
    assert sh.offer_threshold("dev", None) == "explicit"
    assert sh.should_offer("dev", None, "clear") is False


def test_risk_order_covers_the_taxonomy_no_drift():
    # guard the NIT: the risk order must stay set-equal to the conserved taxonomy
    from creator_engine_validator import coordination
    assert set(sh.MUTATION_RISK_ORDER) == coordination.MUTATION_CLASSES


# ---------------------------------------------------------------------------
# the card render + classification/purity
# ---------------------------------------------------------------------------
def test_card_uses_canon_labels_and_marks_gaps():
    card = sh.render_card({"scope_id": "x", "intent": "do"}, sh.shape({"scope_id": "x", "intent": "do"}).gaps)
    for label in ("Goal", "Done-when", "Budget", "Change-type", "Ready"):
        assert label in card
    assert "?" in card  # unresolved fields are marked


def test_v3_classified_and_pure():
    assert ver.classify("v3_shaping") == ver.V3
    import inspect
    src = inspect.getsource(sh)
    # docstring-safe markers (only real I/O, never prose like "no subprocess")
    for io_marker in ("open(", "read_text", "write_text", "Path.home", "os.environ", "import subprocess"):
        assert io_marker not in src, f"shaping engine must stay pure (found {io_marker!r})"
