from __future__ import annotations

import base64
import shutil
from pathlib import Path

from creator_engine_validator import cli
from creator_engine_validator import v3_installer
from creator_engine_validator.checks import install_spec_signature_guard as guard
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.install_spec_signature_guard import (
    CHECK_NAME,
    CODE_BASE64,
    CODE_PLACEHOLDER,
    CODE_VERIFY,
    validate_file,
    validate_repo,
    run,
)


SPEC_TEMPLATE = """<!--
signature:
  key_id: {key_id}
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: {value}
  content_sha256: {content_sha256}

artifact_manifest:
  artifact_manifest_version: 1
-->

# Install Creator Engine
"""


def _spec(value: str, *, key_id: str = "ce-root-v1") -> str:
    draft = SPEC_TEMPLATE.format(
        key_id=key_id,
        value=value,
        content_sha256=v3_installer.SIGNATURE_PLACEHOLDER,
    )
    canonical_sha = v3_installer.content_digest(v3_installer.canonical_spec_bytes(draft))
    return SPEC_TEMPLATE.format(key_id=key_id, value=value, content_sha256=canonical_sha)


def _write_spec(path: Path, value: str, *, key_id: str = "ce-root-v1") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_spec(value, key_id=key_id), encoding="utf-8")
    return path


def _repo_with_spec(root: Path, value: str) -> Path:
    return _write_spec(root / "docs" / "llms-install.md", value)


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def test_install_spec_signature_guard_is_registered():
    assert CHECK_NAME in registered_checks()


def test_guard_uses_v3_installer_signature_primitives():
    assert guard.PINNED_KEYS is v3_installer.PINNED_KEYS
    assert guard.PINNED_KEYS == v3_installer.PINNED_KEYS
    assert guard.content_digest is v3_installer.content_digest
    assert guard.canonical_spec_bytes is v3_installer.canonical_spec_bytes


def test_validate_file_rejects_placeholder_signature_value(tmp_path: Path):
    spec_path = _write_spec(tmp_path / "llms-install.md", "<RESIGN-REQUIRED-ce-root-v1>")

    errors = validate_file(spec_path, verifier=lambda *_args: True)

    assert _codes(errors) == {CODE_PLACEHOLDER}


def test_validate_file_rejects_any_angle_bracket_placeholder(tmp_path: Path):
    spec_path = _write_spec(tmp_path / "llms-install.md", "<published-with-this-spec>")

    errors = validate_file(spec_path, verifier=lambda *_args: True)

    assert _codes(errors) == {CODE_PLACEHOLDER}


def test_validate_file_rejects_invalid_base64_signature_value(tmp_path: Path):
    spec_path = _write_spec(tmp_path / "llms-install.md", "not base64!!!")

    errors = validate_file(spec_path, verifier=lambda *_args: True)

    assert _codes(errors) == {CODE_BASE64}


def test_validate_file_accepts_mocked_good_ssh_signature(tmp_path: Path):
    signature_value = base64.b64encode(b"mock-sshsig").decode("ascii")
    for key_id, expected_key_material in v3_installer.PINNED_KEYS.items():
        spec_path = _write_spec(tmp_path / f"{key_id}.md", signature_value, key_id=key_id)
        expected_canonical = v3_installer.canonical_spec_bytes(spec_path.read_bytes())

        def verifier(algo, raw, value, key_material):
            assert algo == v3_installer.SSH_ED25519_ALGO
            assert raw == expected_canonical
            assert value == signature_value
            assert key_material == expected_key_material
            return True

        assert validate_file(spec_path, verifier=verifier) == []


def test_validate_file_rejects_non_verifying_ssh_signature(tmp_path: Path):
    signature_value = base64.b64encode(b"mock-sshsig").decode("ascii")
    spec_path = _write_spec(tmp_path / "llms-install.md", signature_value)

    errors = validate_file(spec_path, verifier=lambda *_args: False)

    assert _codes(errors) == {CODE_VERIFY}


def test_validate_file_reports_actionable_missing_ssh_keygen(tmp_path: Path, monkeypatch):
    signature_value = base64.b64encode(b"mock-sshsig").decode("ascii")
    spec_path = _write_spec(tmp_path / "llms-install.md", signature_value)
    monkeypatch.setattr(guard.shutil, "which", lambda _name: None)

    errors = validate_file(spec_path, verifier=None)

    assert _codes(errors) == {CODE_VERIFY}
    assert "missing_dependency_ssh_keygen" in errors[0].message
    assert "sudo apt-get install -y openssh-client" in errors[0].message
    assert "sudo dnf install -y openssh-clients" in errors[0].message
    assert "brew install openssh" in errors[0].message


def test_validate_file_reports_actionable_ssh_keygen_exec_race(tmp_path: Path, monkeypatch):
    signature_value = base64.b64encode(b"mock-sshsig").decode("ascii")
    spec_path = _write_spec(tmp_path / "llms-install.md", signature_value)
    monkeypatch.setattr(guard.shutil, "which", lambda name: f"/usr/bin/{name}")

    def missing_binary(*_args, **_kwargs):
        raise FileNotFoundError("ssh-keygen")

    monkeypatch.setattr(guard.subprocess, "run", missing_binary)

    errors = validate_file(spec_path, verifier=None)

    assert _codes(errors) == {CODE_VERIFY}
    assert "missing_dependency_ssh_keygen" in errors[0].message
    assert "openssh-client" in errors[0].message


def test_validate_repo_checks_versioned_mirrors_when_present(tmp_path: Path):
    good_signature = base64.b64encode(b"mock-sshsig").decode("ascii")
    _repo_with_spec(tmp_path, good_signature)
    _write_spec(tmp_path / "docs" / "downloads" / "0.3.0" / "llms-install.md", "<mirror-placeholder>")

    errors = validate_repo(tmp_path, verifier=lambda *_args: True)

    assert _codes(errors) == {CODE_PLACEHOLDER}
    assert "docs/downloads/0.3.0/llms-install.md" in errors[0].path


def test_registered_adapter_reports_placeholder_signature_warning(tmp_path: Path):
    _repo_with_spec(tmp_path, "<RESIGN-REQUIRED-ce-root-v1>")

    result = run([tmp_path])

    assert result.ok
    assert _codes(result.warnings) == {CODE_PLACEHOLDER}


def test_cli_scan_install_spec_signature_fails_closed_on_placeholder(tmp_path: Path, monkeypatch):
    _repo_with_spec(tmp_path, "<RESIGN-REQUIRED-ce-root-v1>")
    monkeypatch.chdir(tmp_path)

    assert cli.main(["scan-install-spec-signature", "."]) == 1


def test_cli_scan_install_spec_signature_passes_mocked_good_spec(tmp_path: Path, monkeypatch):
    good_signature = base64.b64encode(b"mock-sshsig").decode("ascii")
    _repo_with_spec(tmp_path, good_signature)

    def fake_verifier():
        return lambda *_args: True

    monkeypatch.setattr(
        "creator_engine_validator.checks.install_spec_signature_guard.ssh_keygen_verifier",
        fake_verifier,
    )
    monkeypatch.chdir(tmp_path)

    assert cli.main(["scan-install-spec-signature", "."]) == 0


def test_real_sshsig_verifier_rejects_invalid_signature_when_ssh_keygen_available(tmp_path: Path):
    if shutil.which("ssh-keygen") is None:
        return
    invalid_signature = base64.b64encode(b"not-a-real-sshsig").decode("ascii")
    spec_path = _write_spec(tmp_path / "llms-install.md", invalid_signature)

    errors = validate_file(spec_path, verifier=None)

    assert _codes(errors) == {CODE_VERIFY}
