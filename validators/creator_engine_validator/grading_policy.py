"""Policy-only grading mode and reviewer-independence helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .reporting import ValidationError, make_error


class RunMode(str, Enum):
    DEV = "dev"
    STRANGE_LOOP = "strangeLoop"


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class IndependenceRequirement:
    run_mode: RunMode
    risk_tier: RiskTier
    available_model_diversity: int
    require_distinct_reviewer_model: bool
    require_authorship_obfuscated: bool
    require_adversarial_prompt: bool


@dataclass(frozen=True)
class ReviewIndependenceContext:
    run_mode: RunMode | str
    risk_tier: RiskTier | str
    available_model_diversity: int
    author_model: str


INDEPENDENCE_CODE = "CE-GRADE-INDEPENDENCE"
CONTRACT = "docs/contracts/review-evidence.md"


def select_independence_requirement(
    *,
    run_mode: RunMode | str,
    risk_tier: RiskTier | str,
    available_model_diversity: int,
) -> IndependenceRequirement:
    """Select the required reviewer independence for the active mode and tier.

    This is data/policy only: it does not open PRs, merge, mutate settings, or
    actuate any downstream system.
    """

    mode = RunMode(run_mode)
    tier = RiskTier(risk_tier)
    if available_model_diversity < 1:
        raise ValueError("available_model_diversity must be at least 1")

    model_diverse = available_model_diversity >= 2
    if mode == RunMode.DEV:
        return IndependenceRequirement(
            run_mode=mode,
            risk_tier=tier,
            available_model_diversity=available_model_diversity,
            require_distinct_reviewer_model=tier in {RiskTier.MEDIUM, RiskTier.HIGH, RiskTier.CRITICAL},
            require_authorship_obfuscated=tier in {RiskTier.HIGH, RiskTier.CRITICAL},
            require_adversarial_prompt=tier == RiskTier.CRITICAL,
        )

    return IndependenceRequirement(
        run_mode=mode,
        risk_tier=tier,
        available_model_diversity=available_model_diversity,
        require_distinct_reviewer_model=model_diverse,
        require_authorship_obfuscated=tier in {RiskTier.MEDIUM, RiskTier.HIGH, RiskTier.CRITICAL},
        require_adversarial_prompt=tier in {RiskTier.MEDIUM, RiskTier.HIGH, RiskTier.CRITICAL},
    )


def validate_review_evidence_independence(
    record: Mapping[str, Any],
    path: str | Path,
    context: ReviewIndependenceContext,
) -> list[ValidationError]:
    """Assert a review-evidence record meets the selected mode requirements."""

    try:
        requirement = select_independence_requirement(
            run_mode=context.run_mode,
            risk_tier=context.risk_tier,
            available_model_diversity=context.available_model_diversity,
        )
    except ValueError as exc:
        return [
            make_error(
                INDEPENDENCE_CODE,
                path,
                "run_mode",
                str(exc),
                CONTRACT,
            )
        ]

    errors: list[ValidationError] = []
    reviewer_model = record.get("reviewer_model")
    if not isinstance(reviewer_model, str) or not reviewer_model:
        errors.append(_err(path, "reviewer_model", "reviewer_model is required for independence attestation"))
        return errors

    if requirement.require_distinct_reviewer_model and reviewer_model == context.author_model:
        errors.append(
            _err(
                path,
                "reviewer_model",
                "reviewer_model must differ from author_model for the selected mode and risk tier",
            )
        )
    if requirement.require_authorship_obfuscated and record.get("authorship_obfuscated") is not True:
        errors.append(
            _err(
                path,
                "authorship_obfuscated",
                "authorship_obfuscated must be true for the selected mode and risk tier",
            )
        )
    if requirement.require_adversarial_prompt and record.get("adversarial_prompt") is not True:
        errors.append(
            _err(
                path,
                "adversarial_prompt",
                "adversarial_prompt must be true for the selected mode and risk tier",
            )
        )
    return errors


def approval_policy_sha(
    *,
    run_mode: RunMode | str,
    risk_tier: RiskTier | str,
    policy_material: Mapping[str, Any] | None = None,
) -> str:
    """Return a policy digest bound to the active run mode and risk tier."""

    payload = {
        "policy_material": policy_material or {},
        "risk_tier": RiskTier(risk_tier).value,
        "run_mode": RunMode(run_mode).value,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _err(path: str | Path, field: str, message: str) -> ValidationError:
    return make_error(INDEPENDENCE_CODE, path, field, message, CONTRACT)


__all__ = [
    "CONTRACT",
    "INDEPENDENCE_CODE",
    "IndependenceRequirement",
    "ReviewIndependenceContext",
    "RiskTier",
    "RunMode",
    "approval_policy_sha",
    "select_independence_requirement",
    "validate_review_evidence_independence",
]
