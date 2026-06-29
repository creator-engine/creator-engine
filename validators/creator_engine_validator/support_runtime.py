"""``ce ask`` / ``ce support`` runtime for the internal support-agent pilot.

The runtime is deliberately narrow: it projects the product-lens corpus into a
docs-as-skills bundle, hands that bundle plus the checked-in system prompt to an
injectable model boundary, and accepts only answers that cite eligible corpus
sources. Uncited, ungrounded, empty, or leak-shaped output is normalized to the
safe refusal: ``I don't know``.

Tests inject the model runner. The default runner performs no live model call
unless ``CE_SUPPORT_AGENT_MODEL_CMD`` is configured, keeping the suite and local
preflight offline-safe.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Protocol

from . import public_docs_confidentiality as confidentiality
from . import support_bundle
from . import support_corpus
from . import support_profile

MODEL_ID = "claude-sonnet-4-6"
REFUSAL_ANSWER = "I don't know"
SYSTEM_PROMPT = Path(__file__).resolve().parent / "support_system_prompt.md"

# Retained for callers/tests that still assert the P0 scaffold message exists.
SCAFFOLD_NOTICE = "support agent answering path available"

_INTERNAL_OUTPUT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("internal merge queue", re.compile(r"\bmerge[- ]queue\b", re.IGNORECASE)),
    ("internal integrator", re.compile(r"\bintegrator\b", re.IGNORECASE)),
    ("internal approval wall", re.compile(r"\bapproval[- ]wall\b", re.IGNORECASE)),
    ("internal fleet topology", re.compile(r"\bdev[- ]fleet\b", re.IGNORECASE)),
)


@dataclass(frozen=True)
class SupportRequest:
    """Payload passed across the model boundary."""

    question: str
    model: str
    system_prompt: str
    bundle: support_bundle.SupportBundle
    profile_contract: dict

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "bundle": self.bundle.to_dict(),
            "profile_contract": self.profile_contract,
        }


@dataclass(frozen=True)
class SupportAnswer:
    """Validated support-agent answer returned to the CLI."""

    answer: str
    citations: tuple[str, ...]
    accepted: bool
    reason: str
    model: str
    corpus_sha256: str

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "citations": list(self.citations),
            "accepted": self.accepted,
            "reason": self.reason,
            "model": self.model,
            "corpus_sha256": self.corpus_sha256,
        }


class ModelRunner(Protocol):
    def __call__(self, request: SupportRequest) -> str | dict:
        ...


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT.read_text(encoding="utf-8")


def _profile_contract(*, repo_root: Path) -> dict:
    """Build and sanity-check the read-only support profile contract."""
    decisions = {
        "read_readme": support_profile.evaluate(
            "Read", {"file_path": "README.md"}, repo_root=repo_root
        ),
        "write_denied": support_profile.evaluate(
            "Write", {"file_path": "README.md"}, repo_root=repo_root
        ),
        "exec_denied": support_profile.evaluate("Bash", {"command": "ce validate-pr"}, repo_root=repo_root),
        "unknown_denied": support_profile.evaluate("SomePrivilegedTool", {}, repo_root=repo_root),
    }
    if not decisions["read_readme"].ok:
        raise RuntimeError("support read-only profile does not allow in-corpus reads")
    for key in ("write_denied", "exec_denied", "unknown_denied"):
        if decisions[key].ok:
            raise RuntimeError(f"support read-only profile failed deny-by-default check: {key}")

    return {
        "posture": support_profile.POSTURE,
        "allowed_tools": sorted(support_profile.READ_TOOLS),
        "denied_write_tools": sorted(support_profile.WRITE_TOOLS),
        "denied_exec_network_tools": sorted(support_profile.EXEC_NETWORK_TOOLS),
        "corpus_roots": list(support_corpus.corpus_roots()),
        "decisions": {
            key: {
                "decision": value.decision,
                "ok": value.ok,
                "reason": value.reason,
            }
            for key, value in decisions.items()
        },
    }


def _extract_runner_answer(raw: str | dict) -> str:
    if isinstance(raw, dict):
        value = raw.get("answer") or raw.get("text") or raw.get("content") or ""
        return str(value).strip()
    text = str(raw).strip()
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(parsed, dict):
            return _extract_runner_answer(parsed)
    return text


def _leak_reason(answer: str) -> str | None:
    for label, pattern in confidentiality.FORBIDDEN_PATTERNS:
        if pattern.search(answer):
            return label
    for label, pattern in _INTERNAL_OUTPUT_PATTERNS:
        if pattern.search(answer):
            return label
    return None


def _citations_in(answer: str, *, bundle: support_bundle.SupportBundle) -> tuple[str, ...]:
    cited: list[str] = []
    for rel in bundle.citation_paths():
        if rel in answer:
            cited.append(rel)
    return tuple(cited)


def _validate_answer(raw_answer: str, *, bundle: support_bundle.SupportBundle) -> tuple[str, tuple[str, ...], bool, str]:
    answer = raw_answer.strip()
    if not answer:
        return REFUSAL_ANSWER, (), False, "empty-model-output"

    if answer == REFUSAL_ANSWER or answer.startswith(f"{REFUSAL_ANSWER} "):
        return REFUSAL_ANSWER, (), True, "model-refusal"

    leak = _leak_reason(answer)
    if leak:
        return REFUSAL_ANSWER, (), False, f"zero-leak-filter:{leak}"

    citations = _citations_in(answer, bundle=bundle)
    if not citations:
        return REFUSAL_ANSWER, (), False, "missing-corpus-citation"

    return answer, citations, True, "cited-corpus-answer"


class ConfiguredCommandModelRunner:
    """Model boundary backed by an explicit JSON-over-stdin command."""

    ENV_CMD = "CE_SUPPORT_AGENT_MODEL_CMD"
    ENV_TIMEOUT = "CE_SUPPORT_AGENT_MODEL_TIMEOUT"

    def __call__(self, request: SupportRequest) -> str | dict:
        command = os.environ.get(self.ENV_CMD, "").strip()
        if not command:
            return REFUSAL_ANSWER

        argv = shlex.split(command)
        if not argv:
            return REFUSAL_ANSWER
        timeout = float(os.environ.get(self.ENV_TIMEOUT, "120"))
        try:
            result = subprocess.run(
                argv,
                input=json.dumps(request.to_dict(), sort_keys=True),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return REFUSAL_ANSWER
        if result.returncode != 0:
            return REFUSAL_ANSWER
        return result.stdout.strip()


def answer_question(
    question: str,
    *,
    model_runner: ModelRunner | None = None,
    repo_root: Path | None = None,
) -> SupportAnswer:
    """Answer one support question, enforcing cite-or-refuse after the model call."""
    clean_question = question.strip()
    root = (repo_root or support_corpus.repo_root()).resolve()
    bundle = support_bundle.build_support_bundle(repo_root=root)
    if not clean_question:
        return SupportAnswer(
            answer=REFUSAL_ANSWER,
            citations=(),
            accepted=False,
            reason="empty-question",
            model=MODEL_ID,
            corpus_sha256=bundle.corpus_sha256,
        )

    request = SupportRequest(
        question=clean_question,
        model=MODEL_ID,
        system_prompt=_load_system_prompt(),
        bundle=bundle,
        profile_contract=_profile_contract(repo_root=root),
    )
    runner = model_runner or ConfiguredCommandModelRunner()
    raw = runner(request)
    raw_answer = _extract_runner_answer(raw)
    answer, citations, accepted, reason = _validate_answer(raw_answer, bundle=bundle)
    return SupportAnswer(
        answer=answer,
        citations=citations,
        accepted=accepted,
        reason=reason,
        model=MODEL_ID,
        corpus_sha256=bundle.corpus_sha256,
    )


def _build_status() -> dict:
    result = support_corpus.evaluate()
    bundle = support_bundle.build_support_bundle()
    return {
        "status": "available",
        "wired": True,
        "model": MODEL_ID,
        "model_boundary": ConfiguredCommandModelRunner.ENV_CMD,
        "corpus_sha256": bundle.corpus_sha256,
        "foundations": {
            "corpus_allowlist": support_corpus.CONTRACT,
            "system_prompt_contract": (
                "validators/creator_engine_validator/support_system_prompt.md"
            ),
            "readonly_profile": (
                "validators/creator_engine_validator/support_profile.py"
            ),
            "skill_bundle_projector": (
                "validators/creator_engine_validator/support_bundle.py"
            ),
            "eligible_corpus_files": list(result.eligible),
            "bundle_skills": [skill.name for skill in bundle.skills],
            "corpus_roots": list(support_corpus.corpus_roots()),
            "rejected_not_clean": [
                {"path": rel, "reason": reason} for rel, reason in result.rejected
            ],
            "missing_not_yet_present": list(result.missing),
        },
        "deferrals": [
            "live Claude Code seat invocation is behind CE_SUPPORT_AGENT_MODEL_CMD",
            "Phase-2 eval harness (accuracy / zero-leak / refusal)",
            "external public graduation and containment hardening",
        ],
    }


def run_cli(args) -> int:
    """CLI entrypoint for dev-gated ``ce ask`` / ``ce support``."""
    json_output = bool(getattr(args, "json_output", False))
    show_foundations = bool(getattr(args, "foundations", False))
    question = " ".join(getattr(args, "question", []) or []).strip()

    if not question:
        payload = _build_status()
        if json_output:
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        print("ce ask: internal support agent is available for cited, product-lens answers.")
        print("Ask a question, or run `ce ask --foundations` to inspect the substrate.")
        show_foundations = True
    else:
        answer = answer_question(question)
        if json_output:
            payload = _build_status()
            payload["question"] = question
            payload["answer"] = answer.to_dict()
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        print(answer.answer)

    if show_foundations:
        status = _build_status()
        f = status["foundations"]
        print("", file=sys.stdout)
        print("foundations:")
        print(f"  corpus allowlist:        {f['corpus_allowlist']}")
        print(f"  system-prompt contract:  {f['system_prompt_contract']}")
        print(f"  read-only profile:       {f['readonly_profile']}")
        print(f"  skill-bundle projector:  {f['skill_bundle_projector']}")
        print(f"  eligible corpus files:   {len(f['eligible_corpus_files'])}")
        for rel in f["eligible_corpus_files"]:
            print(f"    - {rel}")
        print(f"  bundle skills:           {len(f['bundle_skills'])}")
        for skill in f["bundle_skills"]:
            print(f"    - {skill}")
        if f["rejected_not_clean"]:
            print("  rejected (not confidentiality-clean, excluded):")
            for item in f["rejected_not_clean"]:
                print(f"    - {item['path']}: {item['reason']}")
        print("  deferrals:")
        for item in status["deferrals"]:
            print(f"    - {item}")

    return 0


__all__ = [
    "MODEL_ID",
    "REFUSAL_ANSWER",
    "SupportAnswer",
    "SupportRequest",
    "ConfiguredCommandModelRunner",
    "answer_question",
    "run_cli",
]
