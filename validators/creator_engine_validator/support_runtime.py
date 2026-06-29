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

from . import support_bundle
from . import support_corpus
from . import support_leak_rules
from . import support_profile

MODEL_ID = "configured-command"
REFUSAL_ANSWER = "I don't know"
SYSTEM_PROMPT = Path(__file__).resolve().parent / "support_system_prompt.md"
DEFAULT_STATE_DIR = Path(".ce/state")
DEFAULT_USAGE_LOG_REL = Path("support-agent/usage.ndjson")

# Retained for callers/tests that still assert the P0 scaffold message exists.
SCAFFOLD_NOTICE = "support agent answering path available"

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
    token_spend: int | float | None = None

    def to_dict(self) -> dict:
        payload = {
            "answer": self.answer,
            "citations": list(self.citations),
            "accepted": self.accepted,
            "reason": self.reason,
            "model": self.model,
            "corpus_sha256": self.corpus_sha256,
        }
        if self.token_spend is not None:
            payload["token_spend"] = self.token_spend
        return payload


class ModelRunner(Protocol):
    def __call__(self, request: SupportRequest) -> str | dict:
        ...


@dataclass(frozen=True)
class _ModelOutput:
    answer: str
    token_spend: int | float | None = None


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT.read_text(encoding="utf-8")


def configured_model_id() -> str:
    return os.environ.get(ConfiguredCommandModelRunner.ENV_MODEL_ID, "").strip() or MODEL_ID


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


def _extract_token_spend(raw: object) -> int | float | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        return raw
    if not isinstance(raw, dict):
        return None
    total = raw.get("total_tokens")
    if isinstance(total, bool):
        return None
    if isinstance(total, int | float):
        return total
    input_tokens = raw.get("input_tokens")
    output_tokens = raw.get("output_tokens")
    if (
        isinstance(input_tokens, int | float)
        and not isinstance(input_tokens, bool)
        and isinstance(output_tokens, int | float)
        and not isinstance(output_tokens, bool)
    ):
        return input_tokens + output_tokens
    return None


def _extract_runner_output(raw: str | dict) -> _ModelOutput:
    if isinstance(raw, dict):
        value = raw.get("answer") or raw.get("text") or raw.get("content") or ""
        token_spend = _extract_token_spend(raw.get("token_spend"))
        if token_spend is None:
            token_spend = _extract_token_spend(raw.get("usage"))
        return _ModelOutput(str(value).strip(), token_spend)
    text = str(raw).strip()
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return _ModelOutput(text)
        if isinstance(parsed, dict):
            return _extract_runner_output(parsed)
    return _ModelOutput(text)


def _extract_runner_answer(raw: str | dict) -> str:
    return _extract_runner_output(raw).answer


def _leak_reason(answer: str) -> str | None:
    for label, pattern in support_leak_rules.DEFAULT_LEAK_RULES:
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
    ENV_MODEL_ID = "CE_SUPPORT_AGENT_MODEL_ID"
    ENV_TIMEOUT = "CE_SUPPORT_AGENT_MODEL_TIMEOUT"
    ENV_STATE_DIR = "CE_SUPPORT_AGENT_STATE_DIR"
    ENV_USAGE_LOG = "CE_SUPPORT_AGENT_USAGE_LOG"

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


def _usage_log_path(*, repo_root: Path) -> Path:
    configured = os.environ.get(ConfiguredCommandModelRunner.ENV_USAGE_LOG, "").strip()
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else repo_root / path

    state_dir_value = os.environ.get(ConfiguredCommandModelRunner.ENV_STATE_DIR, "").strip()
    state_dir = Path(state_dir_value) if state_dir_value else DEFAULT_STATE_DIR
    if not state_dir.is_absolute():
        state_dir = repo_root / state_dir
    return state_dir / DEFAULT_USAGE_LOG_REL


def _question_category(question: str) -> str:
    text = question.lower()
    if not text:
        return "empty"
    tokens = set(re.findall(r"[a-z0-9]+", text))
    if tokens & {"install", "setup", "bootstrap", "onboard"}:
        return "install"
    if tokens & {"error", "fail", "failed", "broken", "debug", "troubleshoot"}:
        return "troubleshooting"
    if tokens & {"contribute", "contributing", "review", "change", "changes"} or "pull request" in text:
        return "contribution"
    if tokens & {"govern", "governance", "policy", "profile", "refuse", "refusal"} or "read-only" in text:
        return "governance"
    if tokens & {"architecture", "design", "concept"} or "what is" in text:
        return "concept"
    return "usage"


def _append_usage_log(
    *,
    repo_root: Path,
    question_category: str,
    corpus_sha256: str,
    model_id: str,
    accepted: bool,
    reason: str,
    token_spend: int | float | None,
) -> None:
    record = {
        "question_category": question_category,
        "corpus_sha256": corpus_sha256,
        "model_id": model_id,
        "accepted": accepted,
        "reason": reason,
    }
    if token_spend is not None:
        record["token_spend"] = token_spend
    path = _usage_log_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
        f.write("\n")


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
    model_id = configured_model_id()
    question_category = _question_category(clean_question)
    if not clean_question:
        answer = SupportAnswer(
            answer=REFUSAL_ANSWER,
            citations=(),
            accepted=False,
            reason="empty-question",
            model=model_id,
            corpus_sha256=bundle.corpus_sha256,
        )
        _append_usage_log(
            repo_root=root,
            question_category=question_category,
            corpus_sha256=bundle.corpus_sha256,
            model_id=model_id,
            accepted=answer.accepted,
            reason=answer.reason,
            token_spend=answer.token_spend,
        )
        return answer

    request = SupportRequest(
        question=clean_question,
        model=model_id,
        system_prompt=_load_system_prompt(),
        bundle=bundle,
        profile_contract=_profile_contract(repo_root=root),
    )
    runner = model_runner or ConfiguredCommandModelRunner()
    raw = runner(request)
    output = _extract_runner_output(raw)
    answer, citations, accepted, reason = _validate_answer(output.answer, bundle=bundle)
    result = SupportAnswer(
        answer=answer,
        citations=citations,
        accepted=accepted,
        reason=reason,
        model=model_id,
        corpus_sha256=bundle.corpus_sha256,
        token_spend=output.token_spend,
    )
    _append_usage_log(
        repo_root=root,
        question_category=question_category,
        corpus_sha256=bundle.corpus_sha256,
        model_id=model_id,
        accepted=result.accepted,
        reason=result.reason,
        token_spend=result.token_spend,
    )
    return result


def _build_status() -> dict:
    result = support_corpus.evaluate()
    bundle = support_bundle.build_support_bundle()
    model_id = configured_model_id()
    return {
        "status": "available",
        "wired": True,
        "model": model_id,
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
            "live model invocation is behind CE_SUPPORT_AGENT_MODEL_CMD",
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
    "configured_model_id",
    "run_cli",
]
