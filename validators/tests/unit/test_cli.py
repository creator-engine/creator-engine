import pytest

from creator_engine_validator import check_profiles
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.cli import main


def _render_checks(checks):
    if not checks:
        return "No checks registered yet.\n"
    return "".join(f"{name}: {', '.join(defn.frs)}\n" for name, defn in checks.items())


def test_list_checks_includes_identity(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "identity" in out
    assert "FR-001" in out


def test_list_checks_includes_pco024(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "worktree_lease_schema" in out
    assert "PCO-024" in out


def test_list_checks_includes_ce_runtime_policy(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "ce_runtime_policy" in out
    assert "runtime_policy_image_not_digest_pinned" in out


def test_list_checks_includes_ce_runtime_evidence(capsys):
    assert main(["--list-checks"]) == 0
    out = capsys.readouterr().out
    assert "ce_runtime_evidence" in out
    assert "runtime_evidence_chain_link" in out


def test_list_checks_unprofiled_matches_full_inventory(capsys):
    assert main(["--list-checks"]) == 0
    captured = capsys.readouterr()

    assert captured.out == _render_checks(registered_checks())
    assert captured.err == ""


def test_list_checks_client_repo_profile_shows_effective_inventory(capsys):
    assert main(["--list-checks", "--profile", check_profiles.CLIENT_REPO_PROFILE]) == 0
    captured = capsys.readouterr()

    omitted = set(check_profiles.CLIENT_REPO_OMITTED_CHECK_REASONS)
    expected_checks = {
        name: defn
        for name, defn in registered_checks().items()
        if name not in omitted
    }
    assert captured.out == _render_checks(expected_checks)
    assert "identity:" in captured.out
    for name in omitted:
        assert f"{name}:" not in captured.out
    assert captured.err == "".join(
        f"NOTICE: omitted check {name} for profile client-repo because {reason}.\n"
        for name, reason in sorted(check_profiles.CLIENT_REPO_OMITTED_CHECK_REASONS.items())
    )


def test_check_well_formed_identity_returns_zero(capsys):
    assert main(["check", "examples/well-formed/identity-record.yml"]) == 0
    assert "PASS identity" in capsys.readouterr().out


@pytest.mark.xdist_group("check-examples-sweep")
def test_check_examples_returns_zero_when_example_expectations_hold(check_examples_result):
    exit_code, out = check_examples_result
    assert exit_code == 0
    assert "examples/well-formed" in out
    assert "examples/malformed/identity-record.missing-fields.yml" in out
    assert "examples/malformed/spec.creator-engine.missing-acceptance.yml" in out
    assert "examples/malformed/duplicate-spec-id" in out
    assert "examples/malformed/runtime-policy/unpinned-image.yml" in out
    assert "examples/malformed/runtime-policy/forbidden-mount.yml" in out
    assert "examples/malformed/runtime-policy/controller-key-secret.yml" in out
    assert "examples/malformed/runtime-evidence/broken-chain-link.yml" in out
    assert "examples/malformed/runtime-evidence/mutated-content-hash.yml" in out
    assert "examples/malformed/runtime-evidence/unbound-policy-sha.yml" in out


# ---------------------------------------------------------------------------
# PCO-027 / PCO-028: pco-allocate / pco-release CLI subcommands
# ---------------------------------------------------------------------------


def test_pco_allocate_help_exits_zero(capsys):
    """pco-allocate subcommand must be registered and print help without error."""
    import pytest
    with pytest.raises(SystemExit) as exc_info:
        main(["pco-allocate", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--lane-id" in out


def test_pco_release_help_exits_zero(capsys):
    """pco-release subcommand must be registered and print help without error."""
    import pytest
    with pytest.raises(SystemExit) as exc_info:
        main(["pco-release", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--lane-id" in out


def test_openbao_p3_plan_help_exits_zero(capsys):
    """OpenBao P3 plan subcommand must be registered and non-executing."""
    import pytest
    with pytest.raises(SystemExit) as exc_info:
        main(["openbao-p3-plan", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--profile" in out
    assert "--address" in out


def test_openbao_p3_controller_plan_json_flags_operator_steps(capsys):
    assert main(
        [
            "--json",
            "openbao-p3-plan",
            "--profile",
            "controller-pilot",
            "--host-ref",
            "controller-vps:ce-pilot-1",
            "--address",
            "https://openbao.internal.example",
            "--ca-bundle-ref",
            "secret-ref:openbao-ca",
        ]
    ) == 0
    out = capsys.readouterr().out
    assert "operator-provision-controller-vps" in out
    assert "operator-inject-wrapping-token" in out
    assert "root_token" not in out
