"""RV1-060 — integration tests for ``ce check`` over bundled examples.

Confirms the ``ce check`` umbrella faithfully wraps the retained
``creator-engine-validator`` conformance surface end-to-end (well-formed pass /
malformed fail) without reimplementing it.
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path
import shutil

from creator_engine_validator import check_profiles
from creator_engine_validator import ce_cli, cli as validator_cli
from creator_engine_validator.reporting import make_error
import pytest

pytestmark = pytest.mark.slow


def _client_repo_fixture(tmp_path: Path, repo_root: Path) -> Path:
    """Reusable adopted-client shape without CE-resident taxonomy/surfaces/schema files."""

    client = tmp_path / "client-repo"
    (client / ".ce" / "brain").mkdir(parents=True)
    (client / "docs" / "contracts").mkdir(parents=True)
    (client / "docs" / "operations").mkdir(parents=True)
    (client / ".ce" / "brain" / "doctrine-coverage.yaml").write_text(
        "\n".join(
            [
                "kind: brain-doctrine-coverage-manifest",
                'schema_version: "1"',
                "governed_trees:",
                "  - docs/contracts",
                "exceptions: []",
                "",
            ]
        ),
        encoding="utf-8",
    )
    shutil.copy2(
        repo_root / "docs" / "operations" / "SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md",
        client / "docs" / "operations" / "SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md",
    )
    return client


def _failed_names(payload: dict[str, object]) -> set[str]:
    return {
        str(result["name"])
        for result in payload["results"]  # type: ignore[index]
        if not result["ok"]  # type: ignore[index]
    }


def test_ce_check_passes_wellformed_examples(repo_root: Path, capsys):
    example = repo_root / "examples" / "well-formed" / "state-version-record"
    ret = ce_cli.main(["check", str(example), "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_ce_check_fails_malformed_example_like_validator(repo_root: Path, capsys):
    malformed = repo_root / "examples" / "malformed" / "state-version-record" / "stale-version.yaml"
    ce_ret = ce_cli.main(["check", str(malformed), "--json"])
    ce_output = capsys.readouterr()
    validator_ret = validator_cli.main(["--json", "check", str(malformed)])
    validator_output = capsys.readouterr()
    assert ce_ret == validator_ret != 0
    assert ce_output.out == validator_output.out
    assert ce_output.err == validator_output.err


def test_ce_check_list_checks(capsys):
    ret = ce_cli.main(["check", "--list-checks", "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert "checks" in payload


def test_ce_check_client_repo_profile_omits_only_ce_resident_checks(
    tmp_path: Path,
    repo_root: Path,
    monkeypatch,
    capsys,
):
    from creator_engine_validator.checks import v3_naming_hygiene

    client = _client_repo_fixture(tmp_path, repo_root)
    # v3_naming_hygiene.evaluate() is self-referential to the installed package
    # location via v3_naming_hygiene.py:70-72, so this in-process client-tree
    # test cannot fixture it by changing cwd. Omitting it is justified because it
    # is a CE-self check with no meaningful signal against an adopted client tree.
    monkeypatch.setattr(
        v3_naming_hygiene,
        "evaluate",
        lambda: (
            [
                make_error(
                    "VAL-V3NAME-MISSING-SCHEMA",
                    "schemas/client-side-missing.schema.yaml",
                    "",
                    "declared v3 schema no longer exists",
                    "docs/contracts/v3-naming-hygiene.md",
                )
            ],
            [],
        ),
    )

    with contextlib.chdir(client):
        default_ret = ce_cli.main(["check", "--json"])
    default_output = capsys.readouterr()
    default_payload = json.loads(default_output.out)

    assert default_ret == 1
    assert _failed_names(default_payload) == set(check_profiles.CLIENT_REPO_OMITTED_CHECK_REASONS)

    with contextlib.chdir(client):
        profile_ret = ce_cli.main(["check", "--profile", check_profiles.CLIENT_REPO_PROFILE, "--json"])
    profile_output = capsys.readouterr()
    profile_payload = json.loads(profile_output.out)

    assert profile_ret == 0
    assert profile_payload["ok"] is True
    result_names = {result["name"] for result in profile_payload["results"]}
    assert "ce_scope" in result_names
    assert not (result_names & set(check_profiles.CLIENT_REPO_OMITTED_CHECK_REASONS))
    expected_notice = "".join(
        f"NOTICE: omitted check {name} for profile client-repo because {reason}.\n"
        for name, reason in sorted(check_profiles.CLIENT_REPO_OMITTED_CHECK_REASONS.items())
    )
    assert profile_output.err == expected_notice


def test_ce_check_rejects_unknown_profile(capsys):
    with pytest.raises(SystemExit) as exc_info:
        ce_cli.main(["check", "--profile", "bogus"])

    assert exc_info.value.code == 2
    assert "invalid choice: 'bogus'" in capsys.readouterr().err
