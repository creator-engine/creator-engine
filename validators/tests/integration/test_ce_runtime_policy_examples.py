import pytest

from creator_engine_validator.cli import main


def test_runtime_policy_well_formed_example_passes(capsys):
    assert main(["check", "examples/well-formed/runtime-policy/example-runtime-policy.yml"]) == 0
    out = capsys.readouterr().out
    assert "PASS ce_runtime_policy" in out


def test_runtime_policy_unpinned_image_example_fails(capsys):
    assert main(["check", "examples/malformed/runtime-policy/unpinned-image.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL ce_runtime_policy" in out
    assert "runtime_policy_image_not_digest_pinned" in out
    assert "docs/contracts/runtime-policy.md" in out


def test_runtime_policy_forbidden_mount_example_fails(capsys):
    assert main(["check", "examples/malformed/runtime-policy/forbidden-mount.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL ce_runtime_policy" in out
    assert "runtime_policy_forbidden_mount" in out
    assert "docs/contracts/runtime-policy.md" in out


def test_runtime_policy_controller_key_secret_example_fails(capsys):
    assert main(["check", "examples/malformed/runtime-policy/controller-key-secret.yml"]) == 1
    out = capsys.readouterr().out
    assert "FAIL ce_runtime_policy" in out
    assert "runtime_policy_secret_names_only_violation" in out
    assert "docs/contracts/runtime-policy.md" in out


def test_scan_runtime_policy_well_formed_dir_passes(capsys):
    assert main(["scan-runtime-policy", "examples/well-formed/runtime-policy"]) == 0
    out = capsys.readouterr().out
    assert "PASS ce_runtime_policy" in out


def test_scan_runtime_policy_malformed_dir_fails(capsys):
    assert main(["scan-runtime-policy", "examples/malformed/runtime-policy"]) == 1
    out = capsys.readouterr().out
    assert "FAIL ce_runtime_policy" in out
    assert "runtime_policy_image_not_digest_pinned" in out
    assert "runtime_policy_forbidden_mount" in out
    assert "runtime_policy_secret_names_only_violation" in out


@pytest.mark.xdist_group("check-examples-sweep")
def test_check_examples_includes_runtime_policy(check_examples_result):
    exit_code, out = check_examples_result
    assert "examples/malformed/runtime-policy/unpinned-image.yml" in out
    assert "examples/malformed/runtime-policy/forbidden-mount.yml" in out
    assert "examples/malformed/runtime-policy/controller-key-secret.yml" in out
    assert exit_code == 0
