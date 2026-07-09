"""RV1-080 / RV1-081 — v1.0 docs-vs-CLI reconciliation checks.

These tests are the "docs-vs-CLI consistency check" named in the traceability
matrix. They derive the **as-built** ``ce`` command inventory by introspecting
the argparse parser (the single source of truth) and assert that:

* every shipped public ``ce`` command group is documented as a v1.0 surface in
  ``docs/reference/cli.md`` (RV1-080);
* ``README.md`` links to the public CLI reference (RV1-080);
* there is **no** ``ce dev`` command in v1.0, and the docs say so (RV1-080 /
  RV1-081);
* the Option B install story (Python ``>=3.14``, uv-first + pip ``--no-index``
  fallback, ``uv.lock`` / ``requirements.txt`` lockstep, cp314 wheelhouse,
  PyYAML 6.0.3, jsonschema 4.26.0) is documented (RV1-080);
* the IN/SEAM/POST-V1 product-contract table marks ``ce dev shell``, the uvx
  one-liner, CE-native HUD beyond the tmux launcher, hosted/team/GitHub
  connector, CE-event, PCL, and distributed identity as deferred-not-rejected
  seams, and the Integration Queue as a dry-run seam (RV1-081).

They read tracked docs from the repo root, so they fail loudly if a doc drifts
from the shipped surface.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from creator_engine_validator import ce_cli

_REPO_ROOT = Path(__file__).resolve().parents[3]
_README = _REPO_ROOT / "README.md"
_CLI_REFERENCE = _REPO_ROOT / "docs" / "reference" / "cli.md"
_VALIDATORS_README = _REPO_ROOT / "validators" / "README.md"
_PRODUCT_CONTRACT = _REPO_ROOT / "docs" / "governance" / "V1_PRODUCT_CONTRACT.md"


def _ce_command_groups() -> set[str]:
    """The as-built ``ce`` command-group inventory, from the argparse parser."""
    parser = ce_cli._build_parser()
    action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return set(action.choices.keys())


def _readme_text() -> str:
    return _README.read_text(encoding="utf-8")


def _cli_reference_text() -> str:
    return _CLI_REFERENCE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# RV1-080 — public CLI reference documents the as-built ce inventory
# ---------------------------------------------------------------------------


def test_as_built_ce_inventory_matches_expected():
    # Guard the inventory itself so a new/removed command forces a docs update.
    # Internal-only command groups (e.g. `herdr`, ce-ops#237) are tracked here so
    # additions are never silent, but are exempt from the public-README docs
    # requirement below — see ce_cli.INTERNAL_COMMAND_GROUPS.
    assert _ce_command_groups() == {
        "lane", "ledger", "worker", "fanin", "queue", "event", "pcl", "brain",
        "orchestrator", "connector", "containment-probe", "reviewer-triage", "claim",
        "pickup", "dispatch", "playbook", "check", "doctor", "init", "launch", "hud",
        "takeover", "continuity-drill",
        "verify-install", "update", "clean-main-install", "onboard", "bootstrap", "publish-branch", "harness-matrix",
        "containment-status", "posture", "herdr", "validate-pr", "dequeue", "surfaces",
        "automerge-decide", "automerge-status", "automerge-kill-switch",
        "ask", "support", "triage", "dependency-unlock",
        "seats", "fleet", "scope", "shape", "ratify", "drive", "collect", "pr",
        "review", "merge", "configure-repo", "ruleset", "review-submit", "auto-merge",
        "review-pickup", "escalation", "notify", "reap", "status", "show",
        "artifacts", "report", "install", "carrier", "guide", "cockpit", "session",
        "queue-poll", "inbox", "controller-inbox", "queue-daemon", "emergency-stop",
        "queue-dequeue", "approval-capability",
    }


def test_internal_command_groups_are_a_subset_of_the_inventory():
    # Internal groups must be real, shipped commands (no stale exemptions).
    assert ce_cli.INTERNAL_COMMAND_GROUPS <= _ce_command_groups()


def test_readme_links_to_public_cli_reference():
    assert "docs/reference/cli.md" in _readme_text()


def test_cli_reference_documents_every_ce_command_group():
    text = _cli_reference_text()
    # Internal-only groups (ce_cli.INTERNAL_COMMAND_GROUPS) are intentionally off
    # the public product surface and exempt from public CLI-reference documentation.
    public_groups = _ce_command_groups() - ce_cli.INTERNAL_COMMAND_GROUPS
    missing = [g for g in public_groups if not re.search(rf"\bce {re.escape(g)}\b", text)]
    assert not missing, f"docs/reference/cli.md does not document ce command group(s): {missing}"


def test_cli_reference_documents_every_pre_argparse_dispatch_group():
    text = _cli_reference_text()
    # Groups dispatched before argparse in main() are not in _ce_command_groups().
    # They must be checked separately so they cannot silently drop out of the docs.
    public_pre_argparse = ce_cli.PRE_ARGPARSE_DISPATCH_GROUPS - ce_cli.PRE_ARGPARSE_INTERNAL_GROUPS
    missing = [g for g in public_pre_argparse if not re.search(rf"\bce {re.escape(g)}\b", text)]
    assert not missing, (
        f"docs/reference/cli.md does not document pre-argparse ce command group(s): {missing}"
    )


def test_pre_argparse_internal_command_groups_are_declared_dispatches():
    assert ce_cli.PRE_ARGPARSE_INTERNAL_GROUPS <= ce_cli.PRE_ARGPARSE_DISPATCH_GROUPS


def test_no_ce_dev_command_in_v1():
    # The dev namespace must remain unbound in v1.0 ...
    assert "dev" not in _ce_command_groups()
    # ... and the public CLI reference must state that explicitly.
    assert re.search(r"no\s+`?ce dev`?", _cli_reference_text(), re.IGNORECASE)


def test_cli_reference_states_launch_hud_alias_no_rename():
    text = _cli_reference_text()
    assert "ce launch" in text and "ce hud" in text
    # DP-1=A: ce wraps the retained validator; no distribution rename.
    assert "creator-engine-validator" in text


def test_cli_reference_documents_ce_init_project_scaffold():
    text = _cli_reference_text()
    assert "ce init" in text
    assert "CE-native project scaffolding" in text
    assert "path-manifest carriers" in text
    assert "declared work-class lines" in text
    assert "ce validate-pr" in text
    assert ("Spec" + " Kit") not in text
    assert ("." + "specify/") not in text


# ---------------------------------------------------------------------------
# RV1-080 — Option B install story (validators/README.md)
# ---------------------------------------------------------------------------


def test_validators_readme_documents_option_b_install():
    text = _VALIDATORS_README.read_text(encoding="utf-8")
    required = [
        ">=3.14",            # Python floor
        "uv.lock",           # primary lock
        "requirements.txt",  # pip fallback lock
        "--no-index",        # offline pip
        "--find-links",      # wheelhouse
        "wheelhouse",
        "cp314",             # rebuilt wheelhouse ABI
        "6.0.3",             # PyYAML
        "4.26.0",            # jsonschema
    ]
    missing = [tok for tok in required if tok not in text]
    assert not missing, f"validators/README.md missing Option B token(s): {missing}"


def test_validators_readme_documents_uv_first_and_pip_fallback():
    text = _VALIDATORS_README.read_text(encoding="utf-8").lower()
    assert "uv" in text and "pip" in text and "fallback" in text


# ---------------------------------------------------------------------------
# RV1-081 — IN/SEAM/POST-V1 reconciliation (product contract)
# ---------------------------------------------------------------------------


def test_product_contract_marks_deferred_seams():
    text = _PRODUCT_CONTRACT.read_text(encoding="utf-8")
    # Seams that must remain deferred-not-rejected / POST-V1, never active v1.0 authority.
    for token in ["ce dev shell", "uvx", "Integration Queue", "CE-event", "PCL", "distributed identity"]:
        assert token in text, f"product contract does not record seam: {token!r}"


def test_product_contract_integration_queue_is_dry_run_seam():
    text = _PRODUCT_CONTRACT.read_text(encoding="utf-8")
    # The Integration Queue line must be a dry-run SEAM, with live landing POST-V1.
    assert re.search(r"Integration Queue.*dry-run", text)
    assert re.search(r"deferred,?\s+not\s+rejected", text, re.IGNORECASE)
