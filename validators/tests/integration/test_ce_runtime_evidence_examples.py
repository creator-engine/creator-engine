from creator_engine_validator.cli import main


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


def test_check_examples_includes_runtime_evidence(capsys):
    assert main(["check-examples"]) == 0
    out = capsys.readouterr().out
    assert "examples/malformed/runtime-evidence/broken-chain-link.yml" in out
    assert "examples/malformed/runtime-evidence/mutated-content-hash.yml" in out
    assert "examples/malformed/runtime-evidence/unbound-policy-sha.yml" in out
