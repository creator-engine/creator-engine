from __future__ import annotations

from pathlib import Path

from creator_engine_validator import (
    public_docs_confidentiality as confidentiality,
    support_bundle,
    support_corpus,
    support_profile,
    support_runtime,
)


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
    (tmp_path / "docs" / "guide").mkdir(parents=True)
    (tmp_path / "README.md").write_text("Creator Engine install docs\n", encoding="utf-8")
    pending = tmp_path / "docs" / "guide" / "contributing-to-ce.md"
    pending.write_text("Product-looking doc still pending cleanup\n", encoding="utf-8")
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
                "  onboarding:",
                "    description: Pending doc.",
                "    serve:",
                "      - docs/guide/contributing-to-ce.md",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(support_corpus, "manifest_path", lambda: manifest)

    bundle = support_bundle.build_support_bundle(repo_root=tmp_path)

    assert "README.md" in bundle.citation_paths()
    assert "docs/guide/contributing-to-ce.md" not in bundle.citation_paths()
    assert any(
        rel == "docs/guide/contributing-to-ce.md" and "KNOWN_PENDING" in reason
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
