"""End-to-end integration coverage for the release finalize publish seam."""

from __future__ import annotations

import base64
import json
import shlex
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest

from creator_engine_validator import release_smoke_evidence, v3_installer
from creator_engine_validator.checks import (
    install_spec_signature_guard,
    release_artifact_parity_guard,
    release_smoke_evidence as release_smoke_gate,
)
from creator_engine_validator.release_orchestrator import orchestrate_release
from creator_engine_validator.release_publish import finalize_signed_release
from creator_engine_validator.update import DEFAULT_TRUST_ANCHOR_URL, resolve_latest_signed_release

from .test_install_bootstrap import _sign_with_test_key

pytestmark = pytest.mark.slow

requires_ssh_keygen = pytest.mark.skipif(
    shutil.which("ssh-keygen") is None,
    reason="stock ssh-keygen not available",
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _ignore_copy_noise(_directory: str, names: list[str]) -> set[str]:
    ignored = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
    }
    return {
        name
        for name in names
        if name in ignored or name.endswith((".pyc", ".pyo", ".egg-info"))
    }


def _copy_repo_fixture(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(REPO_ROOT, repo, symlinks=True, ignore=_ignore_copy_noise)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "CE Tests")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "release fixture")
    return repo


def _sshsig_verifier_with_trust_root(trust_root: str) -> install_spec_signature_guard.Verifier:
    def _verify(algo: str, raw: bytes, value: object, _key_material: object) -> bool:
        if algo != install_spec_signature_guard.SSH_ED25519_ALGO or not isinstance(value, str):
            return False
        verifier = install_spec_signature_guard.ssh_keygen_verifier()
        assert verifier is not None
        return verifier(algo, raw, value, trust_root)

    return _verify


def _copy_finalized_release_to_docs(finalized: Path, repo_root: Path, *, trust_root: str) -> None:
    docs = repo_root / "docs"
    for rel_dir in ("downloads", "keys", "schemas"):
        target = docs / rel_dir
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(finalized / rel_dir, target)
    for rel_file in ("install.sh", "llms-install.md"):
        shutil.copy2(finalized / rel_file, docs / rel_file)
    (docs / "keys" / "ce-root-v1").write_text(trust_root, encoding="utf-8")


def _docs_fetcher(docs: Path, trust_anchor: bytes):
    def _fetch(url: str) -> bytes:
        if url == DEFAULT_TRUST_ANCHOR_URL:
            return trust_anchor
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "creator-engine.dev"
        path = parsed.path.lstrip("/")
        return (docs / path).read_bytes()

    return _fetch


@requires_ssh_keygen
def test_release_finalize_docs_copy_passes_release_guards(tmp_path: Path):
    repo = _copy_repo_fixture(tmp_path)
    stage = tmp_path / "stage"
    finalized = tmp_path / "finalized"

    orchestration = orchestrate_release(
        repo_root=repo,
        out=stage,
        tag="release/v0.3.6",
        force=True,
        validate_pr_runner=lambda _repo: 0,
    )

    staged_spec = (stage / "llms-install.md").read_text(encoding="utf-8")
    signing_root = tmp_path / "signing"
    signing_root.mkdir()
    signed_spec, trust_root = _sign_with_test_key(staged_spec, signing_root)
    signature_base64 = install_spec_signature_guard.parse_embedded_signature_block(
        signed_spec
    )["value"]
    verifier = _sshsig_verifier_with_trust_root(trust_root)

    finalized_result = finalize_signed_release(
        stage=stage,
        signature_base64=signature_base64,
        out=finalized,
        verifier=verifier,
    )

    assert orchestration.version == "0.3.6"
    assert finalized_result.version == "0.3.6"
    assert finalized_result.canonical_spec_sha256 == orchestration.packet.canonical_spec_sha256

    _copy_finalized_release_to_docs(finalized, repo, trust_root=trust_root)
    pinned_keys = {"ce-root-v1": trust_root}
    signature_errors = install_spec_signature_guard.validate_repo(
        repo,
        verifier=verifier,
        pinned_keys=pinned_keys,
    )
    parity_errors = release_artifact_parity_guard.validate_repo(repo)

    assert signature_errors == []
    assert parity_errors == []

    fingerprint = v3_installer.public_key_fingerprint(trust_root)
    resolved = resolve_latest_signed_release(
        fetcher=_docs_fetcher(repo / "docs", f"ce-root-v1={fingerprint}\n".encode("utf-8")),
        os_name="linux",
        machine="x86_64",
    )

    assert resolved.identity.semver == "0.3.6"
    assert resolved.canonical_spec_sha256 == finalized_result.canonical_spec_sha256
    assert resolved.sha256s_sha256 == orchestration.stage.sha256s_sha256


@requires_ssh_keygen
def test_finalized_docs_smoke_prepare_public_finalize_and_gate_round_trip(tmp_path: Path):
    repo = _copy_repo_fixture(tmp_path)
    stage = tmp_path / "stage"
    finalized = tmp_path / "finalized"
    orchestrate_release(
        repo_root=repo,
        out=stage,
        tag="release/v0.3.6",
        force=True,
        validate_pr_runner=lambda _repo: 0,
    )
    staged_spec = (stage / "llms-install.md").read_text(encoding="utf-8")
    install_signing = tmp_path / "install-signing"
    install_signing.mkdir()
    signed_spec, install_trust_root = _sign_with_test_key(staged_spec, install_signing)
    install_signature = install_spec_signature_guard.parse_embedded_signature_block(signed_spec)["value"]
    finalized_result = finalize_signed_release(
        stage=stage,
        signature_base64=install_signature,
        out=finalized,
        verifier=_sshsig_verifier_with_trust_root(install_trust_root),
    )
    _copy_finalized_release_to_docs(finalized, repo, trust_root=install_trust_root)
    shutil.copytree(finalized, repo / "docs", dirs_exist_ok=True)

    result_path = tmp_path / "release-smoke-result.json"
    result_path.write_bytes(
        json.dumps(
            {
                "schema_version": "1",
                "container_image": "registry.example.invalid/ce-smoke@sha256:" + "a" * 64,
                "containment": {"host_checkout_mount": False},
                "release_binding": {
                    "package_version": release_smoke_evidence.validate_release_tree(repo).package_version,
                    "canonical_spec_sha256": release_smoke_evidence.validate_release_tree(repo).canonical_spec_sha256,
                    "signed_spec_sha256": release_smoke_evidence.validate_release_tree(repo).signed_spec_sha256,
                    "finalize_manifest_sha256": release_smoke_evidence.validate_release_tree(repo).finalize_manifest_sha256,
                    "artifacts_sha256": release_smoke_evidence.validate_release_tree(repo).artifacts_sha256,
                },
                "installation": {
                    "ce_version": "0.3.6+12345678",
                    "cev3_version": "0.3.6+12345678",
                    "verified_spec_sha256": release_smoke_evidence.validate_release_tree(repo).signed_spec_sha256,
                    "pre_signed_spec_sha256": release_smoke_evidence.validate_release_tree(repo).signed_spec_sha256,
                    "post_signed_spec_sha256": release_smoke_evidence.validate_release_tree(repo).signed_spec_sha256,
                    "pre_finalize_manifest_sha256": release_smoke_evidence.validate_release_tree(repo).finalize_manifest_sha256,
                    "post_finalize_manifest_sha256": release_smoke_evidence.validate_release_tree(repo).finalize_manifest_sha256,
                },
                "summary": {"failed": 0, "stubbed": 0},
                "stages": {"install": "passed", "install_verify": "passed"},
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    )
    unsigned = tmp_path / "release-v0.3.6.unsigned.json"
    prepared = release_smoke_evidence.prepare_evidence(repo, result_path, unsigned)

    smoke_key = tmp_path / "smoke-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(smoke_key), "-C", "ce-root-v1"],
        check=True,
        capture_output=True,
    )
    signing_argv = shlex.split(prepared.signing_command)
    signing_argv[signing_argv.index("/path/to/ce-root-v1-private")] = str(smoke_key)
    subprocess.run(signing_argv, check=True, capture_output=True)
    signature_base64 = base64.b64encode((tmp_path / "release-v0.3.6.unsigned.json.sig").read_bytes()).decode("ascii")
    public = (tmp_path / "smoke-key.pub").read_text(encoding="utf-8").split()
    smoke_trust_root = f"ce-root-v1 {public[0]} {public[1]}"

    def smoke_verifier(algo: str, message: bytes, value: object, _key: object) -> bool:
        assert algo == "ssh-ed25519"
        assert isinstance(value, str)
        return install_spec_signature_guard._ssh_keygen_verify_runner(
            message=message,
            signature=base64.b64decode(value),
            allowed_signers=smoke_trust_root,
            identity="ce-root-v1",
            namespace=release_smoke_evidence.SSH_SIG_NAMESPACE,
        )

    evidence = repo / ".ce/release-evidence/release-v0.3.6.json"
    carrier = repo / ".ce/pr-manifests/ce-559-release-smoke-evidence-gate.md"
    release_smoke_evidence.finalize_evidence(
        repo_root=repo,
        unsigned_path=unsigned,
        signature_base64=signature_base64,
        evidence_out=evidence,
        carrier_path=carrier,
        base="HEAD",
        verifier=smoke_verifier,
        pinned_keys={"ce-root-v1": smoke_trust_root},
    )
    assert prepared.canonical_bytes == release_smoke_gate._canonical_record_bytes(
        json.loads(evidence.read_text(encoding="ascii"))
    )

    _git(repo, "add", "docs", ".ce/release-evidence", ".ce/pr-manifests")
    _git(repo, "commit", "-q", "-m", "finalized docs and public smoke evidence")
    result = release_smoke_gate.run_with_base([repo], "HEAD~1", verifier=smoke_verifier)

    assert finalized_result.version == "0.3.6"
    assert result.ok, [error.format() for error in result.errors]
