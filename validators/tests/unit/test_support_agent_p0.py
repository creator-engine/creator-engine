"""P0 substrate tests for the `ce ask` support agent.

Covers the four P0 deliverables built in this slice:
  * P0.1 corpus allowlist + confidentiality intersection (support_corpus)
  * P0.3 read-only PreToolUse profile (support_profile)
  * P0.4/P1 dev-gated `ce ask` runtime (support_runtime + ce_cli registration)
  * P0.5 system-prompt contract asset
"""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path

import pytest

from creator_engine_validator import (
    ce_cli,
    hook_check,
    public_docs_confidentiality as confidentiality,
    support_corpus,
    support_profile,
    support_runtime,
)

_PKG = Path(support_corpus.__file__).resolve().parent


@pytest.fixture(autouse=True)
def _isolated_usage_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        support_runtime.ConfiguredCommandModelRunner.ENV_USAGE_LOG,
        str(tmp_path / "support-usage.ndjson"),
    )


# --------------------------------------------------------------------------
# P0.1 — corpus allowlist + confidentiality intersection
# --------------------------------------------------------------------------


def test_manifest_exists_and_parses():
    man = support_corpus.load_manifest()
    assert man["version"] == 1
    assert "families" in man
    patterns = support_corpus.product_lens_patterns(manifest=man)
    assert "README.md" in patterns


def test_eligible_corpus_is_subset_of_confidentiality_clean():
    """The corpus the agent may load is provably confidentiality-clean."""
    result = support_corpus.evaluate()
    root = support_corpus.repo_root()
    for rel in result.eligible:
        # not on KNOWN_PENDING
        assert rel not in confidentiality.KNOWN_PENDING, rel
        # not inside an internal guarded tree
        for tree_rel, _ in confidentiality.INTERNAL_GUARDED_TREES:
            assert not (rel == tree_rel or rel.startswith(tree_rel + "/")), rel
        # no forbidden-pattern offenses
        assert confidentiality.offenses(root / rel, repo_root=root) == [], rel


def test_real_manifest_passes_scan_support_corpus():
    """The shipped manifest must be confidentiality-clean (no rejected entries)."""
    result = support_corpus.evaluate()
    assert result.rejected == (), result.rejected
    check = support_corpus.run()
    assert check.ok, [e.message for e in check.errors]
    # And it must produce a non-empty eligible corpus.
    assert result.eligible, "expected at least one eligible product-lens doc"


def test_run_check_fails_closed_on_unclean_entry(tmp_path: Path):
    """A product-lens entry that leaks must be reported as a CE-SUPPORT-CORPUS error."""
    # Build a tiny fake repo root with a leaking doc + a manifest that serves it.
    (tmp_path / "docs").mkdir()
    leak = tmp_path / "docs" / "leaky.md"
    leak.write_text("see ce-ops#1234 for details\n", encoding="utf-8")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "version: 1\nfamilies:\n  x:\n    serve:\n      - docs/leaky.md\n",
        encoding="utf-8",
    )
    # Point the loader at our manifest, scan our tmp root.
    import creator_engine_validator.support_corpus as sc

    orig = sc.manifest_path
    sc.manifest_path = lambda: manifest  # type: ignore[assignment]
    try:
        result = sc.evaluate(repo_root=tmp_path)
        assert any(rel == "docs/leaky.md" for rel, _ in result.rejected)
        assert result.eligible == ()
        check = sc.run([tmp_path])
        assert not check.ok
        assert any(e.code == "CE-SUPPORT-CORPUS" for e in check.errors)
    finally:
        sc.manifest_path = orig  # type: ignore[assignment]


def test_known_pending_doc_excluded_from_corpus(tmp_path: Path):
    """A product-lens doc on KNOWN_PENDING must not be corpus-eligible."""
    rel = "docs/architecture/cockpit.md"
    assert rel in confidentiality.KNOWN_PENDING

    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_text("Public-facing placeholder content.\n", encoding="utf-8")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        f"version: 1\nfamilies:\n  x:\n    serve:\n      - {rel}\n",
        encoding="utf-8",
    )

    import creator_engine_validator.support_corpus as sc

    orig = sc.manifest_path
    sc.manifest_path = lambda: manifest  # type: ignore[assignment]
    try:
        result = sc.evaluate(repo_root=tmp_path)
        assert result.eligible == ()
        assert result.rejected == ((rel, "on the confidentiality KNOWN_PENDING debt ratchet"),)
    finally:
        sc.manifest_path = orig  # type: ignore[assignment]


def test_cleaned_contributing_and_playbook_docs_are_corpus_eligible():
    """Cleaned product-lens docs that left KNOWN_PENDING are eligible."""
    cleaned = {
        "docs/guide/contributing-to-ce.md",
        "docs/contracts/playbook-format.md",
    }
    patterns = set(support_corpus.product_lens_patterns())
    assert cleaned <= patterns
    assert cleaned.isdisjoint(confidentiality.KNOWN_PENDING)

    result = support_corpus.evaluate()
    assert cleaned <= set(result.eligible)


def test_corpus_roots_are_static_prefixes():
    roots = support_corpus.corpus_roots()
    assert "." in roots  # README.md etc. live at repo root
    # no glob magic leaks into a root
    for r in roots:
        assert not any(ch in r for ch in "*?[]")


# --------------------------------------------------------------------------
# P0.3 — read-only PreToolUse profile
# --------------------------------------------------------------------------


def test_profile_denies_write_tools():
    for tool in hook_check.SCOPE_TOOLS:
        d = support_profile.evaluate(tool, {"file_path": "README.md"})
        assert d.decision == "deny"
        assert not d.ok


def test_profile_denies_exec_and_network():
    for tool in ("Bash", "WebFetch", "WebSearch"):
        d = support_profile.evaluate(tool, {"command": "ls"})
        assert d.decision == "deny"


def test_profile_denies_secret_read_even_in_tree():
    d = support_profile.evaluate("Read", {"file_path": "~/.ce-keys/overwatch.env"})
    assert d.decision == "deny"
    assert "secret" in d.reason.lower()


def test_profile_denies_out_of_corpus_read():
    d = support_profile.evaluate("Read", {"file_path": ".ce/state/secret.md"})
    assert d.decision == "deny"


def test_profile_allows_in_corpus_read():
    d = support_profile.evaluate("Read", {"file_path": "README.md"})
    assert d.decision == "allow"
    assert d.ok


def test_profile_denies_unknown_tool():
    d = support_profile.evaluate("SomePrivilegedTool", {})
    assert d.decision == "deny"


def test_profile_decision_renders_claude_hook_json():
    d = support_profile.evaluate("Write", {"file_path": "README.md"})
    rendered = d.to_claude_hook_dict()
    assert rendered["hookSpecificOutput"]["permissionDecision"] == "deny"


# --------------------------------------------------------------------------
# P0.4 — honest `ce ask` scaffold
# --------------------------------------------------------------------------


def _ce_command_groups() -> set[str]:
    parser = ce_cli._build_parser()
    action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return set(action.choices.keys())


def test_ask_and_support_registered_and_internal():
    groups = _ce_command_groups()
    assert "ask" in groups
    assert "support" in groups
    assert {"ask", "support"} <= ce_cli.INTERNAL_COMMAND_GROUPS


def test_ask_without_configured_model_refuses_no_faked_answer(capsys, monkeypatch):
    log_path = Path(os.environ[support_runtime.ConfiguredCommandModelRunner.ENV_USAGE_LOG])
    monkeypatch.delenv(support_runtime.ConfiguredCommandModelRunner.ENV_CMD, raising=False)
    rc = ce_cli.main(["ask", "how", "do", "I", "install"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip() == support_runtime.REFUSAL_ANSWER
    # It must NOT fabricate an answer (no invented install command).
    assert "curl" not in out
    assert "pip install" not in out
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["accepted"] is True
    assert records[0]["model_id"] == support_runtime.MODEL_ID
    assert records[0]["question_category"] == "install"
    assert records[0]["reason"] == "model-refusal"
    assert set(records[0]) == {
        "accepted",
        "corpus_sha256",
        "model_id",
        "question_category",
        "reason",
    }


def test_ask_support_alias_dispatches():
    rc = ce_cli.main(["support", "--json"])
    assert rc == 0


def test_ask_json_status_reports_wired_runtime():
    import json as _json

    buf = io.StringIO()
    import contextlib

    with contextlib.redirect_stdout(buf):
        rc = ce_cli.main(["ask", "--json"])
    assert rc == 0
    payload = _json.loads(buf.getvalue())
    assert payload["wired"] is True
    assert payload["status"] == "available"
    assert payload["model"] == support_runtime.MODEL_ID
    # foundations must surface the eligible corpus (real, computed)
    assert "eligible_corpus_files" in payload["foundations"]
    assert "bundle_skills" in payload["foundations"]


# --------------------------------------------------------------------------
# P0.5 — system-prompt contract asset
# --------------------------------------------------------------------------


def test_system_prompt_contract_asset_present_and_contractual():
    asset = _PKG / "support_system_prompt.md"
    assert asset.is_file()
    text = asset.read_text(encoding="utf-8")
    # The non-negotiable contract clauses must be present.
    assert "Cite or refuse" in text
    assert "I don't know" in text
    assert "Product-lens only" in text
    assert "Read-only" in text
    # And it must itself be confidentiality-clean (it's a checked-in asset).
    assert confidentiality.offenses(asset, repo_root=support_corpus.repo_root()) == []
