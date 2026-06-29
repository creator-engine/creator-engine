from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import sys

import pytest

from creator_engine_validator import (
    public_docs_confidentiality as confidentiality,
    support_bundle,
    support_corpus,
    support_profile,
    support_runtime,
)


@pytest.fixture(autouse=True)
def _isolated_usage_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        support_runtime.ConfiguredCommandModelRunner.ENV_USAGE_LOG,
        str(tmp_path / "support-usage.ndjson"),
    )


def _usage_log_path() -> Path:
    return Path(os.environ[support_runtime.ConfiguredCommandModelRunner.ENV_USAGE_LOG])


def _usage_records() -> list[dict]:
    path = _usage_log_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_projector_yields_deterministic_bundle_from_eligible_corpus():
    bundle = support_bundle.build_support_bundle()

    assert bundle.version == support_bundle.BUNDLE_VERSION
    assert bundle.eligible_paths
    assert bundle.skills
    assert bundle.corpus_sha256
    assert set(bundle.citation_paths()) == set(bundle.eligible_paths)
    assert "skills/ce-support-install/SKILL.md" in bundle.rendered_files()
    for rel in confidentiality.KNOWN_PENDING:
        assert rel not in bundle.citation_paths()


def test_projector_excludes_known_pending_even_if_manifest_lists_it(tmp_path: Path, monkeypatch):
    (tmp_path / "docs" / "contracts").mkdir(parents=True)
    (tmp_path / "README.md").write_text("Creator Engine install docs\n", encoding="utf-8")
    pending = tmp_path / "docs" / "contracts" / "devops-privileged-action-broker.md"
    pending.write_text("Internal broker contract still pending cleanup\n", encoding="utf-8")
    manifest = tmp_path / "support_corpus_allowlist.yaml"
    manifest.write_text(
        "\n".join(
            [
                "version: 1",
                "families:",
                "  install:",
                "    description: Install docs.",
                "    serve:",
                "      - README.md",
                "  contracts:",
                "    description: Pending contract doc.",
                "    serve:",
                "      - docs/contracts/devops-privileged-action-broker.md",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(support_corpus, "manifest_path", lambda: manifest)

    bundle = support_bundle.build_support_bundle(repo_root=tmp_path)

    assert "README.md" in bundle.citation_paths()
    assert "docs/contracts/devops-privileged-action-broker.md" not in bundle.citation_paths()
    assert any(
        rel == "docs/contracts/devops-privileged-action-broker.md" and "KNOWN_PENDING" in reason
        for rel, reason in bundle.rejected
    )


def test_grounded_mocked_model_returns_cited_answer_and_request_context():
    seen = {}

    def runner(request: support_runtime.SupportRequest) -> str:
        seen["request"] = request
        return "Use `ce verify-install` after install. Citation: `README.md`."

    answer = support_runtime.answer_question("How do I verify install?", model_runner=runner)

    assert answer.accepted
    assert answer.answer.endswith("Citation: `README.md`.")
    assert answer.citations == ("README.md",)
    request = seen["request"]
    assert request.model == support_runtime.MODEL_ID
    assert "Cite or refuse" in request.system_prompt
    assert request.bundle.skills
    assert request.profile_contract["posture"] == support_profile.POSTURE


def test_configured_command_runner_cited_answer_refusal_and_private_usage_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    seen_path = tmp_path / "seen-request.json"
    stub = tmp_path / "stub_model.py"
    stub.write_text(
        "\n".join(
            [
                "import json",
                "import os",
                "import sys",
                "",
                "request = json.loads(sys.stdin.read())",
                "with open(os.environ['STUB_SEEN_PATH'], 'w', encoding='utf-8') as f:",
                "    json.dump({",
                "        'question': request.get('question'),",
                "        'model': request.get('model'),",
                "        'bundle_sha': request.get('bundle', {}).get('corpus_sha256'),",
                "        'profile_posture': request.get('profile_contract', {}).get('posture'),",
                "    }, f, sort_keys=True)",
                "mode = os.environ.get('STUB_MODE', 'cited')",
                "if mode == 'refusal':",
                "    print(json.dumps({'answer': \"I don't know - not covered.\", 'token_spend': 7}))",
                "else:",
                "    print(json.dumps({",
                "        'answer': 'CANNED_ACCEPTED_SUPPORT_ANSWER. Citation: README.md',",
                "        'token_spend': {'total_tokens': 42},",
                "    }))",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("STUB_SEEN_PATH", str(seen_path))
    monkeypatch.setenv(
        support_runtime.ConfiguredCommandModelRunner.ENV_CMD,
        f"{shlex.quote(sys.executable)} {shlex.quote(str(stub))}",
    )

    raw_question = "How do I install for alice@example.com?"
    answer = support_runtime.answer_question(raw_question)

    assert answer.accepted
    assert answer.reason == "cited-corpus-answer"
    assert answer.citations == ("README.md",)
    assert answer.answer == "CANNED_ACCEPTED_SUPPORT_ANSWER. Citation: README.md"
    assert answer.token_spend == 42
    seen = json.loads(seen_path.read_text(encoding="utf-8"))
    assert seen["question"] == raw_question
    assert seen["model"] == support_runtime.MODEL_ID
    assert seen["bundle_sha"] == answer.corpus_sha256
    assert seen["profile_posture"] == support_profile.POSTURE

    monkeypatch.setenv("STUB_MODE", "refusal")
    refusal = support_runtime.answer_question("What is the private support roster for Bob?")

    assert refusal.accepted
    assert refusal.answer == support_runtime.REFUSAL_ANSWER
    assert refusal.reason == "model-refusal"
    assert refusal.token_spend == 7

    records = _usage_records()
    assert len(records) == 2
    assert records[0] == {
        "accepted": True,
        "corpus_sha256": answer.corpus_sha256,
        "model_id": support_runtime.MODEL_ID,
        "question_category": "install",
        "reason": "cited-corpus-answer",
        "token_spend": 42,
    }
    assert records[1] == {
        "accepted": True,
        "corpus_sha256": refusal.corpus_sha256,
        "model_id": support_runtime.MODEL_ID,
        "question_category": "concept",
        "reason": "model-refusal",
        "token_spend": 7,
    }

    raw_log = _usage_log_path().read_text(encoding="utf-8")
    assert "alice@example.com" not in raw_log
    assert "Bob" not in raw_log
    assert "CANNED_ACCEPTED_SUPPORT_ANSWER" not in raw_log
    assert "README.md" not in raw_log
    assert support_runtime.REFUSAL_ANSWER not in raw_log
    for record in records:
        assert set(record) <= {
            "accepted",
            "corpus_sha256",
            "model_id",
            "question_category",
            "reason",
            "token_spend",
        }


def test_uncited_model_output_returns_i_do_not_know():
    def runner(_request: support_runtime.SupportRequest) -> str:
        return "Run whatever installer command looks right."

    answer = support_runtime.answer_question("How do I install?", model_runner=runner)

    assert not answer.accepted
    assert answer.answer == support_runtime.REFUSAL_ANSWER
    assert answer.reason == "missing-corpus-citation"


def test_zero_leak_model_output_returns_i_do_not_know():
    def runner(_request: support_runtime.SupportRequest) -> str:
        return "That is tracked in ce-ops#354. Citation: `README.md`."

    answer = support_runtime.answer_question("What ticket tracks ask?", model_runner=runner)

    assert not answer.accepted
    assert answer.answer == support_runtime.REFUSAL_ANSWER
    assert answer.reason.startswith("zero-leak-filter:")


def test_model_refusal_is_cleaned_to_exact_refusal():
    def runner(_request: support_runtime.SupportRequest) -> str:
        return "I don't know — that's not covered in the Creator Engine docs I have."

    answer = support_runtime.answer_question("What is the internal topology?", model_runner=runner)

    assert answer.accepted
    assert answer.answer == support_runtime.REFUSAL_ANSWER
    assert answer.citations == ()


def test_read_only_profile_contract_is_applied_to_answering_request():
    seen = {}

    def runner(request: support_runtime.SupportRequest) -> dict:
        seen["profile"] = request.profile_contract
        return {"answer": "Creator Engine is terminal-first. Citation: README.md"}

    answer = support_runtime.answer_question("What is CE?", model_runner=runner)

    assert answer.accepted
    profile = seen["profile"]
    assert profile["decisions"]["read_readme"]["decision"] == "allow"
    assert profile["decisions"]["write_denied"]["decision"] == "deny"
    assert profile["decisions"]["exec_denied"]["decision"] == "deny"
    assert profile["decisions"]["unknown_denied"]["decision"] == "deny"
    assert support_profile.evaluate("SomePrivilegedTool", {}).decision == "deny"


def test_default_runtime_is_offline_safe_without_model_command(monkeypatch):
    monkeypatch.delenv(support_runtime.ConfiguredCommandModelRunner.ENV_CMD, raising=False)

    answer = support_runtime.answer_question("How do I install?")

    assert answer.answer == support_runtime.REFUSAL_ANSWER
    assert answer.reason == "model-refusal"
    records = _usage_records()
    assert len(records) == 1
    assert records[0]["question_category"] == "install"
    assert records[0]["reason"] == "model-refusal"
    assert set(records[0]) == {
        "accepted",
        "corpus_sha256",
        "model_id",
        "question_category",
        "reason",
    }
