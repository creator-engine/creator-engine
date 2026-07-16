from __future__ import annotations

import base64
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import carrier_gen, cli, v3_installer
from creator_engine_validator import release_smoke_evidence as producer


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout.strip()


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


def _artifact(docs: Path, relative: str) -> dict[str, object]:
    path = docs / relative
    raw = path.read_bytes()
    return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}


def _write_manifest(root: Path, artifacts: list[dict[str, object]] | None = None) -> Path:
    docs = root / "docs"
    spec = (docs / "llms-install.md").read_bytes()
    signature = v3_installer.parse_embedded_signature_block(spec)
    manifest = {
        "kind": "ce-release-finalize-manifest",
        "schema_version": "1",
        "package_version": "0.3.6",
        "canonical_spec_sha256": hashlib.sha256(v3_installer.canonical_spec_bytes(spec)).hexdigest(),
        "signed_spec_sha256": hashlib.sha256(spec).hexdigest(),
        "signature_sha256": hashlib.sha256(signature["value"].encode("ascii")).hexdigest(),
        "signing_key_id": signature["key_id"],
        "signing_namespace": signature["namespace"],
        "artifacts": artifacts
        if artifacts is not None
        else [
            _artifact(docs, "downloads/0.3.6/SHA256SUMS"),
            _artifact(docs, "llms-install.md"),
        ],
    }
    path = docs / "release-finalize-manifest.yml"
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return path


def _result(root: Path, **overrides: object) -> Path:
    binding = producer.validate_release_tree(root)
    value: dict[str, object] = {
        "schema_version": "1",
        "container_image": "registry.example.invalid/ce-smoke@sha256:" + "a" * 64,
        "containment": {"host_checkout_mount": False},
        "release_binding": {
            "package_version": binding.package_version,
            "canonical_spec_sha256": binding.canonical_spec_sha256,
            "signed_spec_sha256": binding.signed_spec_sha256,
            "finalize_manifest_sha256": binding.finalize_manifest_sha256,
            "artifacts_sha256": binding.artifacts_sha256,
        },
        "installation": {
            "ce_version": f"{binding.package_version}+12345678",
            "cev3_version": f"{binding.package_version}+12345678",
            "verified_spec_sha256": binding.signed_spec_sha256,
            "pre_signed_spec_sha256": binding.signed_spec_sha256,
            "post_signed_spec_sha256": binding.signed_spec_sha256,
            "pre_finalize_manifest_sha256": binding.finalize_manifest_sha256,
            "post_finalize_manifest_sha256": binding.finalize_manifest_sha256,
        },
        "summary": {"failed": 0, "stubbed": 0},
        "stages": {"install": "passed", "install_verify": "passed"},
    }
    value.update(overrides)
    path = root / "smoke-result.json"
    path.write_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii"))
    return path


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    docs = root / "docs"
    (docs / "downloads/0.3.6").mkdir(parents=True)
    (docs / "llms-install.md").write_text(_spec(), encoding="utf-8")
    (docs / "downloads/0.3.6/SHA256SUMS").write_text("fixture\n", encoding="utf-8")
    _write_manifest(root)
    (root / ".ce/pr-manifests").mkdir(parents=True)
    carrier_path = ".ce/pr-manifests/release-publish-v0.3.6.md"
    carrier = carrier_gen.render_manifest(
        "release-publish-v0.3.6",
        "release/v0.3.6",
        "Finalize signed Creator Engine v0.3.6",
        [carrier_path],
        1,
        hashlib.sha256((carrier_path + "\n").encode()).hexdigest(),
        declared_work_class="tiny",
    )
    (root / carrier_path).write_text(carrier, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "CE Tests")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "finalized release PR")
    return root


def test_prepare_emits_exact_canonical_unsigned_bytes_and_offline_instruction(tmp_path: Path):
    root = _repo(tmp_path)
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"

    prepared = producer.prepare_evidence(
        repo_root=root,
        result_path=_result(root),
        unsigned_out=unsigned,
    )

    expected = json.dumps(prepared.record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    assert unsigned.read_bytes() == expected == prepared.canonical_bytes
    assert prepared.record["finalize_manifest_sha256"] == hashlib.sha256(
        (root / "docs/release-finalize-manifest.yml").read_bytes()
    ).hexdigest()
    assert prepared.record["package_version"] == "0.3.6"
    assert prepared.record["artifacts_sha256"] == producer.validate_release_tree(root).artifacts_sha256
    assert prepared.record["signature"] == {
        "algo": "ssh-ed25519",
        "key_id": "ce-root-v1",
        "namespace": "ce-release-smoke-v1",
    }
    assert prepared.signing_command == (
        f"ssh-keygen -Y sign -f /path/to/ce-root-v1-private -n ce-release-smoke-v1 {unsigned}"
    )
    assert "curl" not in prepared.signing_command


def test_prepare_shell_quotes_whitespace_and_metacharacter_output_as_one_operand(tmp_path: Path):
    root = _repo(tmp_path)
    injected = tmp_path / "unexpected-command-output"
    unsigned = tmp_path / f"release smoke; touch {injected.name}; $.json"

    prepared = producer.prepare_evidence(root, _result(root), unsigned)
    argv = shlex.split(prepared.signing_command)

    assert argv == [
        "ssh-keygen",
        "-Y",
        "sign",
        "-f",
        "/path/to/ce-root-v1-private",
        "-n",
        "ce-release-smoke-v1",
        str(unsigned),
    ]
    completed = subprocess.run(
        f"set -- {prepared.signing_command}; printf '%s\\n' \"$#\" \"${{@:$#}}\"",
        shell=True,
        executable="/bin/bash",
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.splitlines() == ["8", str(unsigned)]
    assert not injected.exists()


@pytest.mark.parametrize(
    "overrides",
    [
        {"container_image": "registry.example.invalid/ce-smoke:latest"},
        {"containment": {"host_checkout_mount": True}},
        {"summary": {"failed": 1, "stubbed": 0}},
        {"summary": {"failed": 0, "stubbed": 1}},
        {"stages": {"install": "failed", "install_verify": "passed"}},
        {"stages": {"install": "passed", "install_verify": "failed"}},
    ],
)
def test_prepare_refuses_unsafe_or_nonpassing_smoke_result(tmp_path: Path, overrides: dict[str, object]):
    root = _repo(tmp_path)
    with pytest.raises(producer.ReleaseSmokeEvidenceError):
        producer.prepare_evidence(root, _result(root, **overrides), tmp_path / "unsigned.json")


def test_prepare_refuses_missing_malformed_or_stale_observed_release_binding(tmp_path: Path):
    root = _repo(tmp_path)
    old_result = _result(root)
    old_result_bytes = old_result.read_bytes()

    for binding in (None, {}, {"package_version": "0.3.6"}):
        overrides = {} if binding is None else {"release_binding": binding}
        path = _result(root, **overrides)
        if binding is None:
            value = json.loads(path.read_text(encoding="ascii"))
            del value["release_binding"]
            path.write_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii"))
        with pytest.raises(producer.ReleaseSmokeEvidenceError, match="release_binding|result fields"):
            producer.prepare_evidence(root, path, tmp_path / "invalid-binding.json")

    stale = json.loads(old_result_bytes.decode("ascii"))
    stale["release_binding"]["signed_spec_sha256"] = "0" * 64
    old_result.write_bytes(json.dumps(stale, sort_keys=True, separators=(",", ":")).encode("ascii"))
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="signed_spec_sha256"):
        producer.prepare_evidence(root, old_result, tmp_path / "stale-spec.json")


def test_prepare_refuses_missing_malformed_or_mismatched_install_observation(tmp_path: Path):
    root = _repo(tmp_path)
    valid = json.loads(_result(root).read_text(encoding="ascii"))
    cases = []
    missing = dict(valid)
    del missing["installation"]
    cases.append(missing)
    malformed = json.loads(json.dumps(valid))
    malformed["installation"]["ce_version"] = "not-a-version"
    cases.append(malformed)
    stale_cli = json.loads(json.dumps(valid))
    stale_cli["installation"]["cev3_version"] = "0.3.5+12345678"
    cases.append(stale_cli)
    split_build = json.loads(json.dumps(valid))
    split_build["installation"]["cev3_version"] = "0.3.6+87654321"
    cases.append(split_build)
    drift = json.loads(json.dumps(valid))
    drift["installation"]["post_signed_spec_sha256"] = "0" * 64
    cases.append(drift)

    for index, value in enumerate(cases):
        path = root / f"bad-installation-{index}.json"
        path.write_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii"))
        with pytest.raises(producer.ReleaseSmokeEvidenceError, match="installation|version|signed_spec"):
            producer.prepare_evidence(root, path, tmp_path / f"unsigned-{index}.json")


def test_prepare_refuses_old_result_after_valid_release_tree_bytes_change(tmp_path: Path):
    root = _repo(tmp_path)
    stale_result = _result(root)

    (root / "docs/llms-install.md").write_text(_spec("new-signed-spec"), encoding="utf-8")
    _write_manifest(root)
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="canonical_spec_sha256|signed_spec_sha256"):
        producer.prepare_evidence(root, stale_result, tmp_path / "changed-spec.json")

    fresh_result = _result(root)
    manifest = root / "docs/release-finalize-manifest.yml"
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="finalize_manifest_sha256"):
        producer.prepare_evidence(root, fresh_result, tmp_path / "changed-manifest.json")

    fresh_result = _result(root)
    artifact = root / "docs/downloads/0.3.6/SHA256SUMS"
    artifact.write_text("new fixture\n", encoding="utf-8")
    _write_manifest(root)
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="artifacts_sha256|finalize_manifest_sha256"):
        producer.prepare_evidence(root, fresh_result, tmp_path / "changed-artifact.json")


def test_prepare_refuses_missing_drifted_extra_and_escaping_finalize_artifacts(tmp_path: Path):
    root = _repo(tmp_path)
    result = _result(root)
    artifact = root / "docs/downloads/0.3.6/SHA256SUMS"

    artifact.write_text("drift\n", encoding="utf-8")
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="size|sha256"):
        producer.prepare_evidence(root, result, tmp_path / "drift.json")

    artifact.write_text("fixture\n", encoding="utf-8")
    _write_manifest(root)
    artifact.unlink()
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="missing"):
        producer.prepare_evidence(root, result, tmp_path / "missing.json")

    artifact.write_text("fixture\n", encoding="utf-8")
    _write_manifest(root)
    (artifact.parent / "EXTRA").write_text("extra\n", encoding="utf-8")
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="extra"):
        producer.prepare_evidence(root, result, tmp_path / "extra.json")

    artifacts = [_artifact(root / "docs", "llms-install.md")]
    artifacts.append({"path": "../escape", "sha256": "0" * 64, "size": 0})
    _write_manifest(root, artifacts)
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="relative|escape"):
        producer.prepare_evidence(root, result, tmp_path / "escape.json")


def test_finalize_verifies_public_signature_writes_canonical_record_and_refreshes_carrier(tmp_path: Path):
    root = _repo(tmp_path)
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"
    prepared = producer.prepare_evidence(root, _result(root), unsigned)
    evidence = root / ".ce/release-evidence/release-v0.3.6.json"
    carrier = root / ".ce/pr-manifests/release-publish-v0.3.6.md"
    signature = base64.b64encode(b"public-detached-sshsig").decode("ascii")
    calls: list[tuple[object, ...]] = []

    def verifier(algo, message, value, key):
        calls.append((algo, message, value, key))
        return True

    finalized = producer.finalize_evidence(
        repo_root=root,
        unsigned_path=unsigned,
        signature_base64=signature,
        evidence_out=evidence,
        carrier_path=carrier,
        base="HEAD",
        verifier=verifier,
    )

    assert calls == [
        ("ssh-ed25519", prepared.canonical_bytes, signature, v3_installer.PINNED_KEYS["ce-root-v1"])
    ]
    raw = evidence.read_bytes()
    assert raw == json.dumps(finalized.record, sort_keys=True, separators=(",", ":")).encode("ascii")
    assert finalized.record["signature"]["value"] == signature
    assert ".ce/release-evidence/release-v0.3.6.json" in carrier.read_text(encoding="utf-8")


@pytest.mark.parametrize("target_location", ["inside", "outside"])
def test_finalize_refuses_canonical_evidence_symlink_without_touching_target(
    tmp_path: Path, target_location: str
):
    root = _repo(tmp_path)
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"
    producer.prepare_evidence(root, _result(root), unsigned)
    evidence = root / ".ce/release-evidence/release-v0.3.6.json"
    evidence.parent.mkdir(parents=True)
    target = (
        root / ".ce/release-evidence/real-record.json"
        if target_location == "inside"
        else tmp_path / "escaping-record.json"
    )
    target.write_bytes(b"target must remain unchanged\n")
    evidence.symlink_to(target)
    carrier = root / ".ce/pr-manifests/release-publish-v0.3.6.md"
    prior_carrier = carrier.read_bytes()

    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="must not be a symlink"):
        producer.finalize_evidence(
            root,
            unsigned,
            base64.b64encode(b"sig").decode(),
            evidence,
            carrier,
            "HEAD",
            verifier=lambda *_: True,
        )

    assert evidence.is_symlink()
    assert target.read_bytes() == b"target must remain unchanged\n"
    assert carrier.read_bytes() == prior_carrier


@pytest.mark.parametrize("parent_kind", ["symlink", "file"])
def test_finalize_refuses_non_directory_or_symlink_evidence_parent(
    tmp_path: Path, parent_kind: str
):
    root = _repo(tmp_path)
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"
    producer.prepare_evidence(root, _result(root), unsigned)
    evidence_parent = root / ".ce/release-evidence"
    external = tmp_path / "external-evidence"
    external.mkdir()
    if parent_kind == "symlink":
        evidence_parent.symlink_to(external, target_is_directory=True)
    else:
        evidence_parent.write_text("not a directory\n", encoding="utf-8")
    evidence = evidence_parent / "release-v0.3.6.json"
    carrier = root / ".ce/pr-manifests/release-publish-v0.3.6.md"

    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="non-symlink directory"):
        producer.finalize_evidence(
            root,
            unsigned,
            base64.b64encode(b"sig").decode(),
            evidence,
            carrier,
            "HEAD",
            verifier=lambda *_: True,
        )

    assert not list(external.iterdir())


def test_finalize_refuses_existing_non_regular_canonical_evidence_target(tmp_path: Path):
    root = _repo(tmp_path)
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"
    producer.prepare_evidence(root, _result(root), unsigned)
    evidence = root / ".ce/release-evidence/release-v0.3.6.json"
    evidence.mkdir(parents=True)
    carrier = root / ".ce/pr-manifests/release-publish-v0.3.6.md"

    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="must be a regular file"):
        producer.finalize_evidence(
            root,
            unsigned,
            base64.b64encode(b"sig").decode(),
            evidence,
            carrier,
            "HEAD",
            verifier=lambda *_: True,
        )

    assert evidence.is_dir()


def test_finalize_refuses_noncanonical_lexical_alias_for_evidence_output(tmp_path: Path):
    root = _repo(tmp_path)
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"
    producer.prepare_evidence(root, _result(root), unsigned)
    canonical = root / ".ce/release-evidence/release-v0.3.6.json"
    lexical_alias = root / ".ce/release-evidence/../release-evidence/release-v0.3.6.json"
    carrier = root / ".ce/pr-manifests/release-publish-v0.3.6.md"

    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="must be exactly"):
        producer.finalize_evidence(
            root,
            unsigned,
            base64.b64encode(b"sig").decode(),
            lexical_alias,
            carrier,
            "HEAD",
            verifier=lambda *_: True,
        )

    assert not canonical.exists()


def test_finalize_restores_both_outputs_when_second_replacement_fails(tmp_path: Path, monkeypatch):
    root = _repo(tmp_path)
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"
    producer.prepare_evidence(root, _result(root), unsigned)
    evidence = root / ".ce/release-evidence/release-v0.3.6.json"
    carrier = root / ".ce/pr-manifests/release-publish-v0.3.6.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b"prior evidence bytes\n")
    prior_evidence = evidence.read_bytes()
    prior_carrier = carrier.read_bytes()
    real_replace = producer.os.replace
    replacement_count = 0

    def fail_second_replacement(source, destination):
        nonlocal replacement_count
        replacement_count += 1
        if replacement_count == 2:
            raise OSError("injected second replacement failure")
        return real_replace(source, destination)

    monkeypatch.setattr(producer.os, "replace", fail_second_replacement)
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="prior outputs were restored"):
        producer.finalize_evidence(
            root,
            unsigned,
            base64.b64encode(b"sig").decode(),
            evidence,
            carrier,
            "HEAD",
            verifier=lambda *_: True,
        )

    assert evidence.read_bytes() == prior_evidence
    assert carrier.read_bytes() == prior_carrier
    assert not list(evidence.parent.glob(f".{evidence.name}.*"))
    assert not list(carrier.parent.glob(f".{carrier.name}.*"))


def test_finalize_refuses_release_tree_mutation_immediately_before_publication(tmp_path: Path, monkeypatch):
    root = _repo(tmp_path)
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"
    producer.prepare_evidence(root, _result(root), unsigned)
    evidence = root / ".ce/release-evidence/release-v0.3.6.json"
    carrier = root / ".ce/pr-manifests/release-publish-v0.3.6.md"
    prior_carrier = carrier.read_bytes()
    real_render = producer._render_refreshed_carrier

    def render_then_mutate(*args, **kwargs):
        rendered = real_render(*args, **kwargs)
        (root / "docs/llms-install.md").write_text(_spec("mutated-before-publication"), encoding="utf-8")
        _write_manifest(root)
        return rendered

    monkeypatch.setattr(producer, "_render_refreshed_carrier", render_then_mutate)
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="changed before evidence publication"):
        producer.finalize_evidence(
            root,
            unsigned,
            base64.b64encode(b"sig").decode(),
            evidence,
            carrier,
            "HEAD",
            verifier=lambda *_: True,
        )

    assert not evidence.exists()
    assert carrier.read_bytes() == prior_carrier
    assert not list(carrier.parent.glob(f".{carrier.name}.*"))


def test_finalize_refuses_tampered_bytes_key_namespace_digest_and_bad_public_signature(tmp_path: Path):
    root = _repo(tmp_path)
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"
    producer.prepare_evidence(root, _result(root), unsigned)
    evidence = root / ".ce/release-evidence/release-v0.3.6.json"
    carrier = root / ".ce/pr-manifests/release-publish-v0.3.6.md"

    for field, value in (
        ("finalize_manifest_sha256", "0" * 64),
        ("signature.key_id", "ce-dev1-root-v1"),
        ("signature.namespace", "wrong"),
    ):
        record = json.loads(unsigned.read_text(encoding="ascii"))
        if "." in field:
            outer, inner = field.split(".")
            record[outer][inner] = value
        else:
            record[field] = value
        unsigned.write_bytes(json.dumps(record, sort_keys=True, separators=(",", ":")).encode("ascii"))
        with pytest.raises(producer.ReleaseSmokeEvidenceError):
            producer.finalize_evidence(root, unsigned, base64.b64encode(b"sig").decode(), evidence, carrier, "HEAD", verifier=lambda *_: True)
        producer.prepare_evidence(root, _result(root), unsigned)

    unsigned.write_bytes(unsigned.read_bytes() + b"\n")
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="canonical"):
        producer.finalize_evidence(root, unsigned, base64.b64encode(b"sig").decode(), evidence, carrier, "HEAD", verifier=lambda *_: True)

    producer.prepare_evidence(root, _result(root), unsigned)
    with pytest.raises(producer.ReleaseSmokeEvidenceError, match="verify"):
        producer.finalize_evidence(root, unsigned, base64.b64encode(b"sig").decode(), evidence, carrier, "HEAD", verifier=lambda *_: False)
    assert not evidence.exists()


def test_producer_module_has_no_private_signing_or_egress_surface():
    source = Path(producer.__file__).read_text(encoding="utf-8")
    forbidden = ("urlopen", "requests.", "httpx.", "OpenBao", "private_key", "ssh-keygen -Y sign\"", "subprocess.run")
    assert not [token for token in forbidden if token in source]


def test_cli_prepare_and_finalize_are_public_file_only(tmp_path: Path, monkeypatch, capsys):
    root = _repo(tmp_path)
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"
    assert cli.main(
        [
            "--json",
            "release-smoke-prepare",
            "--repo-root",
            str(root),
            "--result",
            str(_result(root)),
            "--unsigned-out",
            str(unsigned),
        ]
    ) == 0
    prepare_payload = json.loads(capsys.readouterr().out)
    assert prepare_payload["unsigned_path"] == str(unsigned)
    assert "ssh-keygen -Y sign" in prepare_payload["operator_signing_command"]

    signature_file = tmp_path / "public.sig"
    signature_file.write_bytes(b"public detached signature fixture")
    evidence = root / ".ce/release-evidence/release-v0.3.6.json"
    carrier = root / ".ce/pr-manifests/release-publish-v0.3.6.md"
    calls: list[dict[str, object]] = []

    def fake_finalize(**kwargs):
        calls.append(kwargs)
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_bytes(b"{}")
        return producer.FinalizedEvidence(record={}, evidence_path=evidence, carrier_path=carrier)

    monkeypatch.setattr(producer, "finalize_evidence", fake_finalize)
    assert cli.main(
        [
            "--json",
            "release-smoke-finalize",
            "--repo-root",
            str(root),
            "--unsigned",
            str(unsigned),
            "--signature-file",
            str(signature_file),
            "--evidence-out",
            str(evidence),
            "--carrier",
            str(carrier),
            "--base",
            "HEAD",
        ]
    ) == 0
    finalize_payload = json.loads(capsys.readouterr().out)
    assert finalize_payload["evidence_path"] == str(evidence)
    assert calls[0]["signature_base64"] == base64.b64encode(signature_file.read_bytes()).decode("ascii")
    parsed = cli._build_parser().parse_args(
        [
            "release-smoke-finalize",
            "--unsigned",
            str(unsigned),
            "--signature-file",
            str(signature_file),
            "--evidence-out",
            str(evidence),
            "--carrier",
            str(carrier),
        ]
    )
    assert not hasattr(parsed, "signing_key")
