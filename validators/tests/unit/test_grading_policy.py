from pathlib import Path

from creator_engine_validator.grading_policy import (
    ReviewIndependenceContext,
    approval_policy_sha,
    select_independence_requirement,
    validate_review_evidence_independence,
)


def _record(**overrides):
    record = {
        "reviewer_model": "reviewer-model",
        "authorship_obfuscated": False,
        "adversarial_prompt": False,
    }
    record.update(overrides)
    return record


def test_dev_medium_selects_distinct_reviewer_model_requirement():
    requirement = select_independence_requirement(
        run_mode="dev",
        risk_tier="medium",
        available_model_diversity=2,
    )

    assert requirement.require_distinct_reviewer_model is True
    assert requirement.require_authorship_obfuscated is False
    assert requirement.require_adversarial_prompt is False


def test_dev_medium_rejects_same_reviewer_and_author_model(tmp_path: Path):
    errors = validate_review_evidence_independence(
        _record(reviewer_model="author-model"),
        tmp_path / "review.yml",
        ReviewIndependenceContext(
            run_mode="dev",
            risk_tier="medium",
            available_model_diversity=2,
            author_model="author-model",
        ),
    )

    assert errors
    assert any("must differ from author_model" in error.message for error in errors)


def test_dev_medium_accepts_cross_model_review(tmp_path: Path):
    errors = validate_review_evidence_independence(
        _record(reviewer_model="reviewer-model"),
        tmp_path / "review.yml",
        ReviewIndependenceContext(
            run_mode="dev",
            risk_tier="medium",
            available_model_diversity=2,
            author_model="author-model",
        ),
    )

    assert errors == []


def test_strangeloop_medium_requires_obfuscation_and_adversarial_prompt(tmp_path: Path):
    errors = validate_review_evidence_independence(
        _record(reviewer_model="reviewer-model"),
        tmp_path / "review.yml",
        ReviewIndependenceContext(
            run_mode="strangeLoop",
            risk_tier="medium",
            available_model_diversity=2,
            author_model="author-model",
        ),
    )

    assert {error.path.rsplit(":", 1)[-1] for error in errors} == {
        "authorship_obfuscated",
        "adversarial_prompt",
    }


def test_policy_sha_binds_run_mode_and_risk_tier():
    material = {"policy": "approval-wall-v1"}

    dev_low = approval_policy_sha(run_mode="dev", risk_tier="low", policy_material=material)
    dev_medium = approval_policy_sha(run_mode="dev", risk_tier="medium", policy_material=material)
    strange_medium = approval_policy_sha(
        run_mode="strangeLoop",
        risk_tier="medium",
        policy_material=material,
    )

    assert len(dev_low) == 64
    assert dev_low != dev_medium
    assert dev_medium != strange_medium
