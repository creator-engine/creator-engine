import pytest

from creator_engine_validator.cli import main
pytestmark = pytest.mark.slow



def test_runtime_evidence_well_formed_example_passes(capsys):
    assert main(["check", "examples/well-formed/runtime-evidence/example-runtime-evidence-chain.yml"]) == 0
    out = capsys.readouterr().out
    assert "PASS ce_runtime_evidence" in out


def test_runtime_evidence_broken_chain_link_example_fails(capsys):
    assert main(["check", "examples/malformed/runtime-evidence/broken-chain-link.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL ce_runtime_evidence" in out
    assert "runtime_evidence_chain_link" in out
    assert "docs/contracts/runtime-evidence.md" in out


def test_runtime_evidence_mutated_content_hash_example_fails(capsys):
    assert main(["check", "examples/malformed/runtime-evidence/mutated-content-hash.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL ce_runtime_evidence" in out
    assert "runtime_evidence_content_address" in out
    assert "docs/contracts/runtime-evidence.md" in out


def test_runtime_evidence_unbound_policy_sha_example_fails(capsys):
    assert main(["check", "examples/malformed/runtime-evidence/unbound-policy-sha.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL ce_runtime_evidence" in out
    assert "runtime_evidence_policy_unbound" in out
    assert "docs/contracts/runtime-evidence.md" in out


@pytest.mark.xdist_group("check-examples-sweep")
def test_check_examples_includes_runtime_evidence(check_examples_result):
    exit_code, out = check_examples_result
    assert "examples/malformed/runtime-evidence/broken-chain-link.yml" in out
    assert "examples/malformed/runtime-evidence/mutated-content-hash.yml" in out
    assert "examples/malformed/runtime-evidence/unbound-policy-sha.yml" in out
    assert exit_code == 0


# ---------------------------------------------------------------------------
# v3 G-4 — the runtime_agent_action record example pair (in the runtime-evidence
# chain family; the new record is a chain member, not a new chain wrapper).
# ---------------------------------------------------------------------------
def test_runtime_evidence_agent_action_well_formed_example_passes(capsys):
    assert main([
        "check",
        "examples/well-formed/runtime-evidence/example-runtime-evidence-chain-agent-action.yml",
    ]) == 0
    out = capsys.readouterr().out
    assert "PASS ce_runtime_evidence" in out


def test_runtime_evidence_agent_action_bad_op_example_fails(capsys):
    assert main(["check", "examples/malformed/runtime-evidence/agent-action-bad-op.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL ce_runtime_evidence" in out
    assert "runtime_evidence_schema_violation" in out
    assert "docs/contracts/runtime-evidence.md" in out


@pytest.mark.xdist_group("check-examples-sweep")
def test_check_examples_includes_agent_action(check_examples_result):
    exit_code, out = check_examples_result
    assert "examples/malformed/runtime-evidence/agent-action-bad-op.yml" in out
    assert exit_code == 0
