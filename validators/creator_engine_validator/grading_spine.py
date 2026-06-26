"""Deterministic spine-first grading primitives.

The spine is the primary counting grader. Semantic grades are advisory unless
every required deterministic signal is green.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class SpineSignalName(str, Enum):
    CI_VALIDATORS = "ci_validators"
    RING1_REFUSAL = "ring1_refusal"
    REQUIRE_CARRIER = "require_carrier"
    BASELINE_DIFF = "baseline_diff"
    TESTS_BUILD = "tests_build"


class SpineSignalStatus(str, Enum):
    GREEN = "green"
    RED = "red"


class SpineStatus(str, Enum):
    GREEN = "green"
    RED = "red"


REQUIRED_SPINE_SIGNALS: tuple[SpineSignalName, ...] = (
    SpineSignalName.CI_VALIDATORS,
    SpineSignalName.RING1_REFUSAL,
    SpineSignalName.REQUIRE_CARRIER,
    SpineSignalName.BASELINE_DIFF,
    SpineSignalName.TESTS_BUILD,
)


@dataclass(frozen=True)
class DeterministicSignal:
    name: SpineSignalName
    status: SpineSignalStatus
    evidence: str = ""

    @classmethod
    def from_value(cls, name: SpineSignalName | str, value: Any) -> "DeterministicSignal":
        signal_name = _coerce_signal_name(name)
        if isinstance(value, DeterministicSignal):
            if value.name != signal_name:
                return cls(signal_name, value.status, value.evidence)
            return value
        if isinstance(value, bool):
            return cls(signal_name, SpineSignalStatus.GREEN if value else SpineSignalStatus.RED)
        if isinstance(value, str):
            return cls(signal_name, SpineSignalStatus(value))
        if isinstance(value, Mapping):
            raw_status = value.get("status")
            evidence = value.get("evidence", "")
            if not isinstance(evidence, str):
                evidence = str(evidence)
            return cls(signal_name, SpineSignalStatus(str(raw_status)), evidence)
        raise ValueError(f"unsupported deterministic signal value for {signal_name.value}")


@dataclass(frozen=True)
class SpineVerdict:
    status: SpineStatus
    signals: tuple[DeterministicSignal, ...]
    blocking_signals: tuple[SpineSignalName, ...]

    @property
    def green(self) -> bool:
        return self.status == SpineStatus.GREEN


@dataclass(frozen=True)
class SemanticGradeDecision:
    can_count: bool
    reason: str


def deterministic_spine_verdict(
    signals: Mapping[SpineSignalName | str, Any] | Iterable[DeterministicSignal],
) -> SpineVerdict:
    """Aggregate deterministic signals into one primary spine verdict.

    Missing required signals are red. A semantic grade must not count unless the
    returned verdict is green.
    """

    normalized = _normalize_signals(signals)
    ordered: list[DeterministicSignal] = []
    blocking: list[SpineSignalName] = []
    for name in REQUIRED_SPINE_SIGNALS:
        signal = normalized.get(name)
        if signal is None:
            signal = DeterministicSignal(name, SpineSignalStatus.RED, "missing required signal")
        ordered.append(signal)
        if signal.status != SpineSignalStatus.GREEN:
            blocking.append(name)
    status = SpineStatus.GREEN if not blocking else SpineStatus.RED
    return SpineVerdict(status=status, signals=tuple(ordered), blocking_signals=tuple(blocking))


def semantic_grade_counting_decision(spine: SpineVerdict) -> SemanticGradeDecision:
    """Return whether a semantic grade may count under the spine-first rule."""

    if spine.green:
        return SemanticGradeDecision(True, "spine_green")
    names = ",".join(signal.value for signal in spine.blocking_signals)
    return SemanticGradeDecision(False, f"spine_red:{names}")


def _normalize_signals(
    signals: Mapping[SpineSignalName | str, Any] | Iterable[DeterministicSignal],
) -> dict[SpineSignalName, DeterministicSignal]:
    if isinstance(signals, Mapping):
        return {
            _coerce_signal_name(name): DeterministicSignal.from_value(name, value)
            for name, value in signals.items()
        }
    normalized: dict[SpineSignalName, DeterministicSignal] = {}
    for signal in signals:
        normalized[signal.name] = signal
    return normalized


def _coerce_signal_name(value: SpineSignalName | str) -> SpineSignalName:
    if isinstance(value, SpineSignalName):
        return value
    return SpineSignalName(value)


__all__ = [
    "DeterministicSignal",
    "REQUIRED_SPINE_SIGNALS",
    "SemanticGradeDecision",
    "SpineSignalName",
    "SpineSignalStatus",
    "SpineStatus",
    "SpineVerdict",
    "deterministic_spine_verdict",
    "semantic_grade_counting_decision",
]
