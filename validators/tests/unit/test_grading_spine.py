from creator_engine_validator.grading_spine import (
    SpineSignalName,
    SpineStatus,
    deterministic_spine_verdict,
    semantic_grade_counting_decision,
)


def _green_signals():
    return {
        SpineSignalName.CI_VALIDATORS: True,
        SpineSignalName.RING1_REFUSAL: True,
        SpineSignalName.REQUIRE_CARRIER: True,
        SpineSignalName.BASELINE_DIFF: True,
        SpineSignalName.TESTS_BUILD: True,
    }


def test_spine_green_allows_semantic_grade_to_count():
    verdict = deterministic_spine_verdict(_green_signals())
    decision = semantic_grade_counting_decision(verdict)

    assert verdict.status == SpineStatus.GREEN
    assert verdict.blocking_signals == ()
    assert decision.can_count is True
    assert decision.reason == "spine_green"


def test_red_spine_blocks_semantic_grade_from_counting():
    signals = _green_signals()
    signals[SpineSignalName.BASELINE_DIFF] = False

    verdict = deterministic_spine_verdict(signals)
    decision = semantic_grade_counting_decision(verdict)

    assert verdict.status == SpineStatus.RED
    assert verdict.blocking_signals == (SpineSignalName.BASELINE_DIFF,)
    assert decision.can_count is False
    assert decision.reason == "spine_red:baseline_diff"


def test_missing_required_spine_signal_is_red():
    signals = _green_signals()
    del signals[SpineSignalName.REQUIRE_CARRIER]

    verdict = deterministic_spine_verdict(signals)

    assert verdict.status == SpineStatus.RED
    assert SpineSignalName.REQUIRE_CARRIER in verdict.blocking_signals
