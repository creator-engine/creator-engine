from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path

from creator_engine_validator import v3_installer
from creator_engine_validator.checks import release_smoke_evidence as gate


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _commit(repo: Path, message: str) -> None:
    _git(repo, "-c", "user.name=CE Test", "-c", "user.email=ce-test@example.invalid", "commit", "-m", message)


def _spec(value: str = "signed-spec") -> str:
    draft = """<!--
signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: {value}
  content_sha256: <published-with-this-spec>
-->
# install

artifact_manifest:
  package_version: 0.3.6
""".format(value=value)
    canonical = hashlib.sha256(v3_installer.canonical_spec_bytes(draft)).hexdigest()
    return draft.replace("<published-with-this-spec>", canonical)


def _record(repo: Path, **overrides: object) -> dict[str, object]:
    spec = (repo / "docs/llms-install.md").read_bytes()
    record: dict[str, object] = {
        "schema_version": "1",
        "canonical_spec_sha256": hashlib.sha256(v3_installer.canonical_spec_bytes(spec)).hexdigest(),
        "signed_spec_sha256": hashlib.sha256(spec).hexdigest(),
        "finalize_manifest_sha256": hashlib.sha256(
            (repo / "docs/release-finalize-manifest.yml").read_bytes()
        ).hexdigest(),
        "summary": {"failed": 0, "stubbed": 0},
        "stages": {"install": "passed", "install_verify": "passed"},
        "containment": {"host_checkout_mount": False},
        "container_image": "registry.example.invalid/ce-smoke@sha256:" + "a" * 64,
        "signature": {
            "key_id": "ce-root-v1",
            "algo": "ssh-ed25519",
            "namespace": "ce-release-smoke-v1",
            "value": base64.b64encode(b"test-sshsig").decode("ascii"),
        },
    }
    record.update(overrides)
    return record


def _finalize_manifest(repo: Path, **overrides: object) -> dict[str, object]:
    spec = (repo / "docs/llms-install.md").read_bytes()
    signature = v3_installer.parse_embedded_signature_block(spec)
    manifest: dict[str, object] = {
        "kind": "ce-release-finalize-manifest",
        "schema_version": "1",
        "package_version": gate._signed_spec_package_version(spec),
        "canonical_spec_sha256": hashlib.sha256(v3_installer.canonical_spec_bytes(spec)).hexdigest(),
        "signed_spec_sha256": hashlib.sha256(spec).hexdigest(),
        "signature_sha256": hashlib.sha256(signature["value"].encode("ascii")).hexdigest(),
        "signing_key_id": signature["key_id"],
        "signing_namespace": signature["namespace"],
        "artifacts": [
            {
                "path": "downloads/0.3.6/SHA256SUMS",
                "sha256": hashlib.sha256((repo / "docs/downloads/0.3.6/SHA256SUMS").read_bytes()).hexdigest(),
                "size": (repo / "docs/downloads/0.3.6/SHA256SUMS").stat().st_size,
            },
            {
                "path": "llms-install.md",
                "sha256": hashlib.sha256(spec).hexdigest(),
                "size": len(spec),
            },
        ],
    }
    manifest.update(overrides)
    return manifest


def _write_finalize_manifest(root: Path, **overrides: object) -> None:
    (root / "docs/release-finalize-manifest.yml").write_text(
        json.dumps(_finalize_manifest(root, **overrides), sort_keys=True), encoding="utf-8"
    )


def _repo(tmp_path: Path) -> Path:
    root = tmp_path
    (root / "docs").mkdir()
    (root / ".ce/release-evidence").mkdir(parents=True)
    (root / "docs/downloads/0.3.6").mkdir(parents=True)
    (root / "docs/downloads/0.3.6/SHA256SUMS").write_text("fixture\n", encoding="utf-8")
    spec = _spec()
    (root / "docs/llms-install.md").write_text(spec, encoding="utf-8")
    _write_finalize_manifest(root)
    _git(root, "init")
    _git(root, "add", ".")
    _commit(root, "base")
    # A release-class PR changes both binding files.
    (root / "docs/llms-install.md").write_text(_spec("changed-signed-spec"), encoding="utf-8")
    _write_finalize_manifest(root)
    _git(root, "add", ".")
    _commit(root, "release candidate")
    return root


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def _write_record(path: Path, record: dict[str, object]) -> None:
    path.write_bytes(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii"))


def test_non_release_diff_is_neutral(tmp_path: Path):
    root = _repo(tmp_path)
    (root / "README.md").write_text("unrelated\n", encoding="utf-8")
    _git(root, "add", ".")
    _commit(root, "unrelated")

    result = gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: False)

    assert result.ok


def test_release_evidence_accepts_exact_valid_record(tmp_path: Path):
    root = _repo(tmp_path)
    record = _record(root)
    _write_record(root / ".ce/release-evidence/smoke.json", record)

    calls = []
    def verifier(algo, message, value, key):
        calls.append((algo, message, value, key))
        return True

    result = gate.run_with_base([root], "HEAD~1", verifier=verifier)

    assert result.ok
    assert calls and calls[0][0] == "ssh-ed25519"
    assert calls[0][3] == v3_installer.PINNED_KEYS["ce-root-v1"]


def test_release_evidence_refuses_absent_altered_stale_and_unsafe_records(tmp_path: Path):
    root = _repo(tmp_path)
    result = gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)
    assert _codes(result) == {gate.CODE_INVALID}

    cases = (
        {"canonical_spec_sha256": "0" * 64},
        {"finalize_manifest_sha256": "0" * 64},
        {"summary": {"failed": 1, "stubbed": 0}},
        {"stages": {"install": "passed", "install_verify": "failed"}},
        {"containment": {"host_checkout_mount": True}},
        {"container_image": "registry.example.invalid/ce-smoke:latest"},
        {"extra": "not permitted"},
        {"signature": {"key_id": "ce-root-v1", "algo": "ssh-ed25519", "namespace": "wrong", "value": "bad"}},
    )
    for index, overrides in enumerate(cases):
        _write_record(root / ".ce/release-evidence/smoke.json", _record(root, **overrides))
        result = gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)
        assert _codes(result) == {gate.CODE_INVALID}, index


def test_release_evidence_refuses_unverified_or_multiple_records(tmp_path: Path):
    root = _repo(tmp_path)
    record = _record(root)
    evidence = root / ".ce/release-evidence"
    _write_record(evidence / "one.json", record)
    assert _codes(gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: False)) == {gate.CODE_INVALID}
    _write_record(evidence / "two.json", record)
    assert _codes(gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)) == {gate.CODE_INVALID}


def test_release_evidence_refuses_truncated_or_altered_finalize_contract(tmp_path: Path):
    root = _repo(tmp_path)
    _write_record(root / ".ce/release-evidence/smoke.json", _record(root))

    cases = (
        {"kind": "not-a-finalize-manifest"},
        {"schema_version": "2"},
        {"package_version": "99.0.0"},
        {"signature_sha256": "0" * 64},
        {"signing_key_id": "ce-dev1-root-v1"},
        {"signing_namespace": "wrong"},
        {"artifacts": []},
        {"artifacts": [{"path": "../escape", "sha256": "b" * 64, "size": 1}]},
    )
    for index, overrides in enumerate(cases):
        _write_finalize_manifest(root, **overrides)
        result = gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)
        assert _codes(result) == {gate.CODE_INVALID}, index

    truncated = _finalize_manifest(root)
    del truncated["artifacts"]
    (root / "docs/release-finalize-manifest.yml").write_text(json.dumps(truncated), encoding="utf-8")
    assert _codes(gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)) == {gate.CODE_INVALID}
