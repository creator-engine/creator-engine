from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from creator_engine_validator.release_publish import (
    PLACEHOLDER_SIGNATURE,
    ReleasePublishError,
    ReleaseStageResult,
    stage_signed_release,
)
from creator_engine_validator import cli, release_publish
from creator_engine_validator.wheel_bake import WheelManifest


BUILD_SHA = "a" * 40


def _write_minimal_repo(root: Path, *, version: str = "0.2.0") -> None:
    package = root / "validators" / "creator_engine_validator"
    package.mkdir(parents=True)
    (root / "validators" / "pyproject.toml").write_text(
        f'[project]\nname = "creator-engine-validator"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "_version.py").write_text(
        'SEMVER = "0.0.0"\nBUILD_GIT_SHA = "' + ("0" * 40) + '"\n',
        encoding="utf-8",
    )
    wheelhouse = root / "validators" / "wheelhouse"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "attrs-26.1.0-py3-none-any.whl").write_bytes(b"attrs-wheel\n")
    (wheelhouse / "jsonschema-4.26.0-py3-none-any.whl").write_bytes(b"jsonschema-wheel\n")

    docs = root / "docs"
    (docs / "schemas").mkdir(parents=True)
    (docs / "keys").mkdir(parents=True)
    (docs / "install.sh").write_text("#!/usr/bin/env bash\necho install\n", encoding="utf-8")
    (docs / "schemas" / "install-answers.schema.yaml").write_text(
        "kind: schema\n", encoding="utf-8"
    )
    (docs / "keys" / "ce-root-v1").write_text(
        "ce-dev1-root-v1 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest\n",
        encoding="utf-8",
    )
    (docs / "llms-install.md").write_text(
        """<!--
signature:
  key_id: ce-dev1-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: OLD_SIGNATURE
  content_sha256: 0000000000000000000000000000000000000000000000000000000000000000

artifact_manifest:
  artifact_manifest_version: 1
  package_name: creator-engine-validator
  package_version: 0.2.0
  python_requires: >=3.14
  artifact_base_url: https://creator-engine.dev/downloads/0.2.0
  sha256s_url: https://creator-engine.dev/downloads/0.2.0/SHA256SUMS
  sha256s_sha256: 1111111111111111111111111111111111111111111111111111111111111111
  install_sh_url: https://creator-engine.dev/install.sh
  install_sh_sha256s_entry: install.sh
  answers_schema_url: https://creator-engine.dev/schemas/install-answers.schema.yaml
  answers_schema_sha256: 2222222222222222222222222222222222222222222222222222222222222222
  app_wheel: creator_engine_validator-0.2.0-py3-none-any.whl
  required_wheels:
    - filename: attrs-26.1.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/attrs-26.1.0-py3-none-any.whl
      sha256: 5555555555555555555555555555555555555555555555555555555555555555
      platforms: all
    - filename: creator_engine_validator-0.2.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
      sha256: 3333333333333333333333333333333333333333333333333333333333333333
      platforms: all
    - filename: jsonschema-4.26.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/jsonschema-4.26.0-py3-none-any.whl
      sha256: 6666666666666666666666666666666666666666666666666666666666666666
      platforms: all
  python_acquisition:
    - platform: linux-x86_64-cp314
      tool: uv
      version: 0.11.21
      url: https://example.invalid/uv.tar.gz
      sha256: 4444444444444444444444444444444444444444444444444444444444444444
      command: uv python install 3.14
-->
# Install Creator Engine
""",
        encoding="utf-8",
    )


def _fake_builder(repo_root: Path, out_dir: Path) -> WheelManifest:
    version_file = repo_root / "validators" / "creator_engine_validator" / "_version.py"
    text = version_file.read_text(encoding="utf-8")
    semver = re.search(r'SEMVER = "([^"]+)"', text).group(1)  # type: ignore[union-attr]
    build_sha = re.search(r'BUILD_GIT_SHA = "([0-9a-f]{40})"', text).group(1)  # type: ignore[union-attr]
    wheel_name = f"creator_engine_validator-{semver}-py3-none-any.whl"
    wheel = out_dir / wheel_name
    wheel.write_bytes(f"wheel\nsemver={semver}\nsha={build_sha}\n".encode("utf-8"))
    return WheelManifest(
        wheel_name=wheel_name,
        sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
        version=semver,
        source_commit=build_sha,
    )


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        h.update(path.read_bytes() + b"\0")
    return h.hexdigest()


def test_stage_signed_release_is_deterministic_and_idempotent(tmp_path: Path):
    repo = tmp_path / "repo"
    _write_minimal_repo(repo)

    out_a = tmp_path / "stage-a"
    out_b = tmp_path / "stage-b"
    first = stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=BUILD_SHA,
        out=out_a,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )
    second = stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=BUILD_SHA,
        out=out_b,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )

    assert first.sha256s_sha256 == second.sha256s_sha256
    assert (out_a / "downloads" / "0.2.0" / "SHA256SUMS").read_text(encoding="utf-8") == (
        out_b / "downloads" / "0.2.0" / "SHA256SUMS"
    ).read_text(encoding="utf-8")
    assert _tree_digest(out_a) == _tree_digest(out_b)

    stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=BUILD_SHA,
        out=out_a,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )
    assert _tree_digest(out_a) == _tree_digest(out_b)


def test_stage_signed_release_fails_closed_on_parity_failure(tmp_path: Path):
    repo = tmp_path / "repo"
    _write_minimal_repo(repo)
    out = tmp_path / "stage"

    with pytest.raises(ReleasePublishError, match="wheel/source parity failed"):
        stage_signed_release(
            repo_root=repo,
            version="0.2.0",
            build_git_sha=BUILD_SHA,
            out=out,
            force=True,
            build_wheel=_fake_builder,
            verify_parity=lambda root: ["wheel differs from source"],
        )

    assert not out.exists()


def test_stage_signed_release_fails_closed_on_stage_hash_failure(tmp_path: Path):
    repo = tmp_path / "repo"
    _write_minimal_repo(repo)
    out = tmp_path / "stage"
    out.mkdir()
    sentinel = out / "sentinel.txt"
    sentinel.write_text("keep\n", encoding="utf-8")

    def _bad_hash_verifier(stage_downloads: Path) -> None:
        (stage_downloads / "SHA256SUMS").write_text("0" * 64 + "  missing.whl\n", encoding="utf-8")
        raise ReleasePublishError("forced hash failure")

    with pytest.raises(ReleasePublishError, match="forced hash failure"):
        stage_signed_release(
            repo_root=repo,
            version="0.2.0",
            build_git_sha=BUILD_SHA,
            out=out,
            force=True,
            build_wheel=_fake_builder,
            verify_parity=lambda root: [],
            stage_hash_verifier=_bad_hash_verifier,
        )

    assert sentinel.read_text(encoding="utf-8") == "keep\n"


def test_stage_signed_release_stages_placeholder_signing_seam(tmp_path: Path):
    repo = tmp_path / "repo"
    _write_minimal_repo(repo)
    out = tmp_path / "stage"

    result = stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=BUILD_SHA,
        out=out,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )

    spec = (out / "llms-install.md").read_text(encoding="utf-8")
    instructions = (out / "SIGNING-INSTRUCTIONS.md").read_text(encoding="utf-8")
    manifest = (out / "release-stage-manifest.yml").read_text(encoding="utf-8")

    assert PLACEHOLDER_SIGNATURE in spec
    assert result.signature_placeholder == PLACEHOLDER_SIGNATURE
    assert "ssh-keygen -Y sign" in instructions
    assert "-n ce-spec-v1" in instructions
    assert "ce-root-v1-private" in instructions
    assert PLACEHOLDER_SIGNATURE in manifest
    assert result.signing_command in manifest


def test_stage_signed_release_requires_explicit_force_for_non_empty_output(tmp_path: Path):
    repo = tmp_path / "repo"
    _write_minimal_repo(repo)
    out = tmp_path / "stage"
    out.mkdir()
    (out / "existing.txt").write_text("existing\n", encoding="utf-8")

    with pytest.raises(ReleasePublishError, match="output directory is not empty"):
        stage_signed_release(
            repo_root=repo,
            version="0.2.0",
            build_git_sha=BUILD_SHA,
            out=out,
            build_wheel=_fake_builder,
            verify_parity=lambda root: [],
        )


def test_release_stage_cli_dispatches_to_pipeline(monkeypatch, tmp_path: Path, capsys):
    calls: dict[str, object] = {}

    def _fake_stage(**kwargs):
        calls.update(kwargs)
        return ReleaseStageResult(
            out_dir=Path(kwargs["out"]),
            version=kwargs["version"],
            build_git_sha=kwargs["build_git_sha"],
            wheel_name="creator_engine_validator-0.2.0-py3-none-any.whl",
            wheel_sha256="1" * 64,
            sha256s_sha256="2" * 64,
            canonical_spec_sha256="3" * 64,
            signature_placeholder=PLACEHOLDER_SIGNATURE,
            signing_command="ssh-keygen -Y sign ...",
            artifacts=(),
        )

    monkeypatch.setattr(release_publish, "stage_signed_release", _fake_stage)

    out = tmp_path / "stage"
    code = cli.main(
        [
            "--json",
            "release-stage",
            "--repo-root",
            str(tmp_path / "repo"),
            "--version",
            "0.2.0",
            "--build-git-sha",
            BUILD_SHA,
            "--out",
            str(out),
            "--force",
        ]
    )

    assert code == 0
    assert calls["repo_root"] == str(tmp_path / "repo")
    assert calls["version"] == "0.2.0"
    assert calls["build_git_sha"] == BUILD_SHA
    assert calls["out"] == str(out)
    assert calls["sign_mode"] == "placeholder"
    assert calls["force"] is True
    assert calls["dry_run"] is False
    rendered = capsys.readouterr().out
    assert '"signature_placeholder": "<RESIGN-REQUIRED-ce-root-v1>"' in rendered
