"""Smoke tests: CONTROLLER_BOOTSTRAP.md references reality-grounded paths.

Tests that depend on not-yet-merged PRs use skipif guards so they pass
on current main and become green once the dependency lands.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
DOC_PATH = REPO_ROOT / "docs" / "operations" / "CONTROLLER_BOOTSTRAP.md"

pytestmark = pytest.mark.fast


def _doc_content() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_controller_bootstrap_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_doc_references_identity_registry_ssot() -> None:
    content = _doc_content()
    assert "infra/identity-registry.yaml" in content


def test_doc_lists_yaml_reader_prerequisite_for_registry_fallback() -> None:
    content = _doc_content()
    assert "yq '.apps[] | select(.name == strenv(APP_NAME))'" in content
    assert "`yq` or an equivalent structured YAML reader is installed" in content


def test_doc_lists_prerequisites_for_live_restore_commands() -> None:
    content = _doc_content()
    assert "rsync -a <state-snapshot-root>/arc_state/" in content
    assert "rsync -a <state-snapshot-root>/dispatch_briefs/" in content
    assert "rsync -a <state-snapshot-root>/dispatch_claims/" in content
    assert "`rsync` or an equivalent file-sync tool is installed" in content


def test_doc_references_provision_standby_script() -> None:
    content = _doc_content()
    assert "provision-standby-surface.sh" in content


def test_doc_references_state_sync_tool() -> None:
    content = _doc_content()
    assert "state_sync.py" in content


def test_doc_has_required_sections() -> None:
    content = _doc_content()
    required_headings = [
        "## 0. Purpose and scope",
        "## 1. Prerequisites",
        "## 2. Identity hydration",
        "## 3. State hydration",
        "## 4. Standby surface provisioning",
        "## 5. Launch - harness-agnostic",
        "## 6. Takeover drill",
        "## 7. Gap list",
        "## 8. Validation checklist",
    ]
    for heading in required_headings:
        assert heading in content, f"Missing section: {heading!r}"


def test_doc_references_openbao_secrets_gap() -> None:
    content = _doc_content()
    assert "OpenBao" in content or "openbao" in content.lower()
    assert "Gap list" in content


@pytest.mark.skipif(
    not (REPO_ROOT / "deploy/dgx-controller-runsc/provision-standby-surface.sh").exists(),
    reason="provision-standby-surface.sh not yet merged (pending standby surface PR)",
)
def test_provision_standby_script_exists_on_disk() -> None:
    assert (REPO_ROOT / "deploy/dgx-controller-runsc/provision-standby-surface.sh").exists()


@pytest.mark.skipif(
    not (REPO_ROOT / "tools/controller/state_sync.py").exists(),
    reason="state_sync.py not yet merged (pending state sync slice 1)",
)
def test_state_sync_tool_exists_on_disk() -> None:
    assert (REPO_ROOT / "tools/controller/state_sync.py").exists()


def test_doc_contains_gap_list_table() -> None:
    content = _doc_content()
    assert "Secrets custody" in content or "secrets custody" in content.lower()
    assert "OpenBao" in content


def test_doc_does_not_contain_secrets() -> None:
    content = _doc_content()
    assert not re.search(r"github_pat_[A-Za-z0-9_]{10,}", content)
    assert "BEGIN RSA PRIVATE KEY" not in content
    assert "BEGIN PRIVATE KEY" not in content


def test_doc_uses_public_placeholders_not_internal_topology_literals() -> None:
    content = _doc_content()
    forbidden_literals = [
        "ce-dev-" + "1",
        "100." + "72." + "252." + "20",
        "spark-" + "b824",
        "ssh " + "dev1",
        "ce" + "dev2",
        "~/" + ".ce" + "-keys",
        "D" + "GX",
        "V" + "PS",
    ]
    for literal in forbidden_literals:
        assert literal not in content

    assert "/" + "home/" not in content
    assert "<repo-root>" in content
    assert "<state-source>" in content
    assert "<standby-root>" in content


def test_doc_does_not_present_unimplemented_restore_command_as_runnable() -> None:
    content = _doc_content()
    assert "state_sync.py " + "--restore" not in content
    assert "restore inverse" in content
    assert "not implemented in slice 1" in content
    assert "restore manually" in content


def test_takeover_and_continuity_commands_include_required_parser_args() -> None:
    content = _doc_content()
    takeover_command = (
        "ce takeover --from <predecessor-controller> --harness <harness> "
        "--repo-root <repo-root> --dry-run --json"
    )
    continuity_command = (
        "ce continuity-drill --from <predecessor-controller> --harness <harness> "
        "--repo-root <repo-root> --json"
    )
    assert takeover_command in content
    assert continuity_command in content
    assert "```bash\nce takeover --dry-run --json" not in content
    assert "[ ] ce takeover --dry-run --json" not in content
    assert "ce continuity-drill --json" not in content


def test_standby_script_section_does_not_claim_takeover_acceptance() -> None:
    content = _doc_content()
    script_section = content.split("The script:", 1)[1].split("Required environment variables:", 1)[0]
    assert "ce takeover --from" not in script_section
    assert "ring0_verify" not in script_section
    assert "legacy embedded takeover check" in script_section
    assert "Direct execution is expected to exit" in script_section
    assert "Treat the script as pending repair" in script_section
    assert "bash <repo-root>/\"$STANDBY_SCRIPT\"" not in content
    assert "provision-standby-surface.sh --dry-run exits 0" not in content
    assert "Manual standby surface preparation until the script is repaired:" in content
    assert "Manual post-provisioning verification:" in content
    assert "manually confirm `<standby-root>` is on `origin/main`" in content
