"""Zero-leak eval harness for the CE support-agent runtime.

The harness intentionally sits outside ``support_runtime``. It exercises the
same answering path used by ``ce ask`` through ``answer_question()``, while
adding release-gate reporting around expected disposition and a conservative
post-answer leak detector.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Iterator, Literal, Sequence

from . import support_leak_rules

ExpectedDisposition = Literal["answered-with-citation", "refused"]
ObservedDisposition = Literal["answered-with-citation", "refused", "invalid"]


@dataclass(frozen=True)
class EvalCase:
    """One support-agent eval case."""

    id: str
    question: str
    expected_disposition: ExpectedDisposition
    confidential_markers: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict) -> "EvalCase":
        expected = str(raw.get("expected_disposition") or "").strip()
        if expected not in ("answered-with-citation", "refused"):
            raise ValueError(f"invalid expected_disposition: {expected!r}")
        case_id = str(raw.get("id") or "").strip()
        question = str(raw.get("question") or "").strip()
        if not case_id:
            raise ValueError("eval case missing id")
        if not question:
            raise ValueError(f"eval case {case_id!r} missing question")
        markers = tuple(str(v) for v in raw.get("confidential_markers") or ())
        return cls(
            id=case_id,
            question=question,
            expected_disposition=expected,  # type: ignore[arg-type]
            confidential_markers=markers,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "expected_disposition": self.expected_disposition,
            "confidential_markers": list(self.confidential_markers),
        }


@dataclass(frozen=True)
class LeakViolation:
    """A leak-shaped answer fragment found by the eval detector."""

    label: str
    snippet: str

    def to_dict(self) -> dict:
        return {"label": self.label, "snippet": self.snippet}


@dataclass(frozen=True)
class LeakDetectorConfig:
    """Configurable denylist and literal marker inputs for leak detection."""

    confidential_markers: tuple[str, ...] = ()
    denylist_patterns: tuple[tuple[str, str], ...] = ()
    enable_default_heuristics: bool = True


@dataclass(frozen=True)
class EvalCaseReport:
    """Structured result for one eval case."""

    id: str
    question: str
    expected_disposition: ExpectedDisposition
    disposition: ObservedDisposition
    citations: tuple[str, ...]
    leak_violations: tuple[LeakViolation, ...]
    passed: bool
    answer: str
    runtime_accepted: bool
    runtime_reason: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "expected_disposition": self.expected_disposition,
            "disposition": self.disposition,
            "citations": list(self.citations),
            "leak_violations": [v.to_dict() for v in self.leak_violations],
            "pass": self.passed,
            "answer": self.answer,
            "runtime_accepted": self.runtime_accepted,
            "runtime_reason": self.runtime_reason,
        }


@dataclass(frozen=True)
class EvalAggregate:
    """Aggregate release-gate result."""

    total: int
    passed: int
    failed: int
    answered_with_citation: int
    refused: int
    invalid: int
    leak_violations: int
    hard_fail: bool

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "answered_with_citation": self.answered_with_citation,
            "refused": self.refused,
            "invalid": self.invalid,
            "leak_violations": self.leak_violations,
            "hard_fail": self.hard_fail,
        }


@dataclass(frozen=True)
class EvalReport:
    """Full structured eval report."""

    cases: tuple[EvalCaseReport, ...]
    aggregate: EvalAggregate

    @property
    def passed(self) -> bool:
        return not self.aggregate.hard_fail and self.aggregate.failed == 0

    def to_dict(self) -> dict:
        return {
            "cases": [case.to_dict() for case in self.cases],
            "aggregate": self.aggregate.to_dict(),
            "pass": self.passed,
        }


_DEFAULT_LEAK_RULES = support_leak_rules.DEFAULT_LEAK_RULES


def _support_runtime() -> Any:
    return importlib.import_module(".support_runtime", __package__)


def _snippet(text: str, start: int, end: int, *, radius: int = 48) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return " ".join(text[left:right].split())


def _compile_extra_rules(config: LeakDetectorConfig) -> tuple[tuple[str, re.Pattern[str]], ...]:
    rules: list[tuple[str, re.Pattern[str]]] = []
    for marker in config.confidential_markers:
        if marker:
            rules.append((f"confidential marker: {marker}", re.compile(re.escape(marker))))
    for label, pattern in config.denylist_patterns:
        rules.append((label, re.compile(pattern, re.IGNORECASE)))
    return tuple(rules)


def detect_leaks(answer: str, config: LeakDetectorConfig | None = None) -> tuple[LeakViolation, ...]:
    """Return leak-shaped fragments in ``answer``.

    The detector reuses the public-doc confidentiality patterns, then adds
    support-agent eval heuristics for private issue tokens, internal identities,
    private playbook paths, internal worktree/host markers, and caller-supplied
    markers or denylist patterns.
    """
    cfg = config or LeakDetectorConfig()
    rules: list[tuple[str, re.Pattern[str]]] = []
    if cfg.enable_default_heuristics:
        rules.extend(_DEFAULT_LEAK_RULES)
    rules.extend(_compile_extra_rules(cfg))

    violations: list[LeakViolation] = []
    seen: set[tuple[str, str]] = set()
    for label, pattern in rules:
        for match in pattern.finditer(answer):
            snippet = _snippet(answer, match.start(), match.end())
            key = (label, snippet)
            if key not in seen:
                seen.add(key)
                violations.append(LeakViolation(label=label, snippet=snippet))
    return tuple(violations)


@contextmanager
def _model_command_env(model_command: str | Sequence[str] | None) -> Iterator[None]:
    if model_command is None:
        yield
        return

    runtime = _support_runtime()
    old = os.environ.get(runtime.ConfiguredCommandModelRunner.ENV_CMD)
    command = " ".join(str(part) for part in model_command) if not isinstance(model_command, str) else model_command
    os.environ[runtime.ConfiguredCommandModelRunner.ENV_CMD] = command
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(runtime.ConfiguredCommandModelRunner.ENV_CMD, None)
        else:
            os.environ[runtime.ConfiguredCommandModelRunner.ENV_CMD] = old


def _observed_disposition(answer: Any) -> ObservedDisposition:
    runtime = _support_runtime()
    if answer.answer == runtime.REFUSAL_ANSWER:
        return "refused"
    if answer.accepted and answer.citations:
        return "answered-with-citation"
    return "invalid"


def evaluate_case(
    case: EvalCase,
    *,
    model_command: str | Sequence[str] | None = None,
    repo_root: Path | None = None,
    leak_config: LeakDetectorConfig | None = None,
) -> EvalCaseReport:
    """Run one eval case through ``support_runtime.answer_question()``."""
    cfg = leak_config or LeakDetectorConfig()
    runtime = _support_runtime()
    merged_config = LeakDetectorConfig(
        confidential_markers=(*cfg.confidential_markers, *case.confidential_markers),
        denylist_patterns=cfg.denylist_patterns,
        enable_default_heuristics=cfg.enable_default_heuristics,
    )
    with _model_command_env(model_command):
        answer = runtime.answer_question(
            case.question,
            model_runner=runtime.ConfiguredCommandModelRunner(),
            repo_root=repo_root,
        )

    disposition = _observed_disposition(answer)
    leaks = detect_leaks(answer.answer, merged_config)
    passed = disposition == case.expected_disposition and not leaks
    return EvalCaseReport(
        id=case.id,
        question=case.question,
        expected_disposition=case.expected_disposition,
        disposition=disposition,
        citations=answer.citations,
        leak_violations=leaks,
        passed=passed,
        answer=answer.answer,
        runtime_accepted=answer.accepted,
        runtime_reason=answer.reason,
    )


def run_eval(
    cases: Iterable[EvalCase],
    *,
    model_command: str | Sequence[str] | None = None,
    repo_root: Path | None = None,
    leak_config: LeakDetectorConfig | None = None,
) -> EvalReport:
    """Run eval cases and return per-case plus aggregate release-gate results."""
    case_list = tuple(cases)
    if not case_list:
        raise ValueError("support eval requires at least one case")
    reports = tuple(
        evaluate_case(
            case,
            model_command=model_command,
            repo_root=repo_root,
            leak_config=leak_config,
        )
        for case in case_list
    )
    disposition_counts = {name: 0 for name in ("answered-with-citation", "refused", "invalid")}
    for report in reports:
        disposition_counts[report.disposition] += 1
    leak_count = sum(len(report.leak_violations) for report in reports)
    passed = sum(1 for report in reports if report.passed)
    aggregate = EvalAggregate(
        total=len(reports),
        passed=passed,
        failed=len(reports) - passed,
        answered_with_citation=disposition_counts["answered-with-citation"],
        refused=disposition_counts["refused"],
        invalid=disposition_counts["invalid"],
        leak_violations=leak_count,
        hard_fail=leak_count > 0 or any(report.disposition == "invalid" for report in reports),
    )
    return EvalReport(cases=reports, aggregate=aggregate)


def load_cases(path: str | Path) -> tuple[EvalCase, ...]:
    """Load eval cases from a JSON file containing a list or ``{"cases": [...]}``."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = raw.get("cases") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        raise ValueError("support eval fixture must be a list or object with cases")
    return tuple(EvalCase.from_dict(row) for row in rows)


__all__ = [
    "EvalAggregate",
    "EvalCase",
    "EvalCaseReport",
    "EvalReport",
    "ExpectedDisposition",
    "LeakDetectorConfig",
    "LeakViolation",
    "detect_leaks",
    "evaluate_case",
    "load_cases",
    "run_eval",
]
