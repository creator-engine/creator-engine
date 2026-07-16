from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

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
    binding = gate.producer.validate_release_tree(repo)
    record: dict[str, object] = {
        "schema_version": "1",
        "package_version": binding.package_version,
        "canonical_spec_sha256": hashlib.sha256(v3_installer.canonical_spec_bytes(spec)).hexdigest(),
        "signed_spec_sha256": hashlib.sha256(spec).hexdigest(),
        "artifacts_sha256": binding.artifacts_sha256,
        "finalize_manifest_sha256": hashlib.sha256(
            (repo / "docs/release-finalize-manifest.yml").read_bytes()
        ).hexdigest(),
        "summary": {"failed": 0, "stubbed": 0},
        "stages": {"install": "passed", "install_verify": "passed"},
        "containment": {"host_checkout_mount": False},
        "container_image": "registry.example.invalid/ce-smoke@sha256:" + "a" * 64,
        "installation": {
            "ce_version": f"{binding.package_version}+12345678",
            "cev3_version": f"{binding.package_version}+12345678",
            "verified_spec_sha256": binding.signed_spec_sha256,
            "pre_signed_spec_sha256": binding.signed_spec_sha256,
            "post_signed_spec_sha256": binding.signed_spec_sha256,
            "pre_finalize_manifest_sha256": binding.finalize_manifest_sha256,
            "post_finalize_manifest_sha256": binding.finalize_manifest_sha256,
        },
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
        yaml.safe_dump(_finalize_manifest(root, **overrides), sort_keys=False), encoding="utf-8"
    )


def _repo(tmp_path: Path) -> Path:
    root = tmp_path
    (root / "docs").mkdir(parents=True)
    (root / ".ce/release-evidence").mkdir(parents=True)
    (root / "docs/downloads/0.3.6").mkdir(parents=True)
    (root / "docs/downloads/0.3.6/SHA256SUMS").write_text("fixture\n", encoding="utf-8")
    spec = _spec()
    (root / "docs/llms-install.md").write_text(spec, encoding="utf-8")
    _write_finalize_manifest(root)
    historical = _record(root)
    historical["package_version"] = "0.3.5"
    historical["installation"]["ce_version"] = "0.3.5+12345678"
    historical["installation"]["cev3_version"] = "0.3.5+12345678"
    _write_record(root / ".ce/release-evidence/release-v0.3.5.json", historical)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii"))


def _amend(repo: Path, *paths: str) -> None:
    _git(repo, "add", *paths)
    _git(repo, "-c", "user.name=CE Test", "-c", "user.email=ce-test@example.invalid", "commit", "--amend", "--no-edit")


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
    _write_record(root / ".ce/release-evidence/release-v0.3.6.json", record)
    _amend(root, ".ce/release-evidence/release-v0.3.6.json")

    calls = []
    def verifier(algo, message, value, key):
        calls.append((algo, message, value, key))
        return True

    result = gate.run_with_base([root], "HEAD~1", verifier=verifier)

    assert result.ok
    assert calls and calls[0][0] == "ssh-ed25519"
    assert calls[0][3] == v3_installer.PINNED_KEYS["ce-root-v1"]


def test_release_evidence_allows_only_canonical_valid_strictly_prior_history(tmp_path: Path):
    root = _repo(tmp_path)
    evidence = root / ".ce/release-evidence"
    _write_record(evidence / "release-v0.3.6.json", _record(root))
    _amend(root, ".ce/release-evidence/release-v0.3.6.json")

    assert gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True).ok


def test_release_evidence_refuses_unchanged_future_same_alias_arbitrary_malformed_and_residue(tmp_path: Path):
    refusal_cases = (
        ("release-v9.9.9.json", "future"),
        ("release-v0.3.6+duplicate.json", "same-version alias"),
        ("arbitrary.json", "arbitrary"),
        ("release-v0.03.5.json", "malformed version"),
        ("README.txt", "non-JSON residue"),
    )
    for name, _label in refusal_cases:
        case_root = _repo(tmp_path / name.replace("/", "_"))
        evidence = case_root / ".ce/release-evidence"
        _write_record(evidence / "release-v0.3.6.json", _record(case_root))
        candidate = evidence / name
        if name.endswith(".json"):
            extra = _record(case_root)
            extra["package_version"] = "9.9.9" if "9.9.9" in name else "0.3.6"
            _write_record(candidate, extra)
        else:
            candidate.write_text("not evidence\n", encoding="utf-8")
        _git(case_root, "add", ".")
        _commit(case_root, "seed invalid unchanged history")
        # Make a release-class commit after the invalid entry is already in the base.
        (case_root / "docs/llms-install.md").write_text(_spec("next-signed-spec"), encoding="utf-8")
        _write_finalize_manifest(case_root)
        current = _record(case_root)
        current["signature"]["value"] = base64.b64encode(b"new-current-signature").decode("ascii")
        _write_record(evidence / "release-v0.3.6.json", current)
        _git(case_root, "add", ".")
        _commit(case_root, "next release candidate")

        assert _codes(gate.run_with_base([case_root], "HEAD~1", verifier=lambda *_args: True)) == {gate.CODE_INVALID}


def test_release_evidence_refuses_unchanged_malformed_or_noncanonical_prior_record(tmp_path: Path):
    for mode in ("shape", "canonical", "signature"):
        root = _repo(tmp_path / mode)
        evidence = root / ".ce/release-evidence"
        prior = evidence / "release-v0.3.5.json"
        if mode == "shape":
            _write_record(prior, {"package_version": "0.3.5"})
        elif mode == "canonical":
            prior.write_bytes(prior.read_bytes() + b"\n")
        else:
            value = json.loads(prior.read_text(encoding="ascii"))
            value["signature"]["namespace"] = "wrong"
            _write_record(prior, value)
        _git(root, "add", ".")
        _commit(root, "seed invalid prior record")
        (root / "docs/llms-install.md").write_text(_spec("next-signed-spec"), encoding="utf-8")
        _write_finalize_manifest(root)
        _write_record(evidence / "release-v0.3.6.json", _record(root))
        _git(root, "add", ".")
        _commit(root, "next release candidate")

        assert _codes(gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)) == {gate.CODE_INVALID}


def test_release_evidence_refuses_absent_altered_stale_and_unsafe_records(tmp_path: Path):
    root = _repo(tmp_path)
    result = gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)
    assert _codes(result) == {gate.CODE_INVALID}

    cases = (
        {"package_version": "0.3.5"},
        {"canonical_spec_sha256": "0" * 64},
        {"artifacts_sha256": "0" * 64},
        {"finalize_manifest_sha256": "0" * 64},
        {"summary": {"failed": 1, "stubbed": 0}},
        {"stages": {"install": "passed", "install_verify": "failed"}},
        {"containment": {"host_checkout_mount": True}},
        {"container_image": "registry.example.invalid/ce-smoke:latest"},
        {"extra": "not permitted"},
        {"signature": {"key_id": "ce-root-v1", "algo": "ssh-ed25519", "namespace": "wrong", "value": "bad"}},
    )
    for index, overrides in enumerate(cases):
        _write_record(root / ".ce/release-evidence/release-v0.3.6.json", _record(root, **overrides))
        _amend(root, ".ce/release-evidence/release-v0.3.6.json")
        result = gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)
        assert _codes(result) == {gate.CODE_INVALID}, index


def test_release_evidence_refuses_unverified_or_wrong_ambiguous_changed_records(tmp_path: Path):
    root = _repo(tmp_path)
    record = _record(root)
    evidence = root / ".ce/release-evidence"
    _write_record(evidence / "release-v0.3.6.json", record)
    _amend(root, ".ce/release-evidence/release-v0.3.6.json")
    assert _codes(gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: False)) == {gate.CODE_INVALID}

    (evidence / "release-v0.3.6.json").unlink()
    _write_record(evidence / "release-v9.9.9.json", record)
    _amend(root, ".ce/release-evidence")
    assert _codes(gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)) == {gate.CODE_INVALID}

    _write_record(evidence / "release-v0.3.6.json", record)
    _write_record(evidence / "extra.json", record)
    _amend(root, ".ce/release-evidence")
    assert _codes(gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)) == {gate.CODE_INVALID}


def test_release_evidence_refuses_alternate_pinned_identity_without_verifying(tmp_path: Path):
    root = _repo(tmp_path)
    record = _record(root)
    record["signature"]["key_id"] = "ce-dev1-root-v1"
    _write_record(root / ".ce/release-evidence/release-v0.3.6.json", record)
    _amend(root, ".ce/release-evidence/release-v0.3.6.json")
    calls = []

    result = gate.run_with_base([root], "HEAD~1", verifier=lambda *args: calls.append(args) or True)

    assert _codes(result) == {gate.CODE_INVALID}
    assert calls == []


def test_release_evidence_refuses_truncated_or_altered_finalize_contract(tmp_path: Path):
    root = _repo(tmp_path)
    _write_record(root / ".ce/release-evidence/release-v0.3.6.json", _record(root))
    _amend(root, ".ce/release-evidence/release-v0.3.6.json")

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
    (root / "docs/release-finalize-manifest.yml").write_text(yaml.safe_dump(truncated, sort_keys=False), encoding="utf-8")
    assert _codes(gate.run_with_base([root], "HEAD~1", verifier=lambda *_args: True)) == {gate.CODE_INVALID}
