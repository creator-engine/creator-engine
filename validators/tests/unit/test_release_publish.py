from __future__ import annotations

import hashlib
import base64
import re
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator.release_publish import (
    PLACEHOLDER_SIGNATURE,
    ReleasePublishError,
    ReleaseStageResult,
    finalize_signed_release,
    stage_signed_release,
)
from creator_engine_validator import cli, release_publish
from creator_engine_validator.wheel_bake import WheelManifest


BUILD_SHA = "a" * 40


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


def _different_sha(sha: str) -> str:
    return ("0" if sha[0] != "0" else "1") + sha[1:]


def _write_minimal_repo(root: Path, *, version: str = "0.2.0") -> str:
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
        "ce-root-v1 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest\n",
        encoding="utf-8",
    )
    (docs / "llms-install.md").write_text(
        """<!--
signature:
  key_id: ce-root-v1
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

```bash
curl -fsSL https://creator-engine.dev/keys/ce-root-v1 -o ce-root-v1
curl -fsSL 'https://dns.google/resolve?name=_ce-root-v1.creator-engine.dev&type=TXT' \\
    -o ce-root-v1.anchor.raw
grep -Eo 'ce-root-v1[ =]SHA256:[A-Za-z0-9+/]{43}' ce-root-v1.anchor.raw \\
    | sed -E 's/[[:space:]]+/=/' > ce-root-v1.anchor
test "$(cut -d= -f2 ce-root-v1.anchor)" = "$(ssh-keygen -l -f ce-root-v1 -E sha256 \\
    | awk '$3 == "ce-root-v1" { print $2; exit }')"
ssh-keygen -Y verify -f ce-root-v1 -I ce-root-v1 -n ce-spec-v1 -s ce-spec.sig < ce-spec.canonical
```
""",
        encoding="utf-8",
    )
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "CE Tests")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "initial fixture")
    return _git(root, "rev-parse", "--verify", "HEAD")


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
    build_sha = _write_minimal_repo(repo)

    out_a = tmp_path / "stage-a"
    out_b = tmp_path / "stage-b"
    first = stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=build_sha,
        out=out_a,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )
    second = stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=build_sha,
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
        build_git_sha=build_sha,
        out=out_a,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )
    assert _tree_digest(out_a) == _tree_digest(out_b)


def test_stage_signed_release_fails_closed_on_parity_failure(tmp_path: Path):
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)
    out = tmp_path / "stage"

    with pytest.raises(ReleasePublishError, match="wheel/source parity failed"):
        stage_signed_release(
            repo_root=repo,
            version="0.2.0",
            build_git_sha=build_sha,
            out=out,
            force=True,
            build_wheel=_fake_builder,
            verify_parity=lambda root: ["wheel differs from source"],
        )

    assert not out.exists()


def test_stage_signed_release_fails_closed_on_stage_hash_failure(tmp_path: Path):
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)
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
            build_git_sha=build_sha,
            out=out,
            force=True,
            build_wheel=_fake_builder,
            verify_parity=lambda root: [],
            stage_hash_verifier=_bad_hash_verifier,
        )

    assert sentinel.read_text(encoding="utf-8") == "keep\n"


def test_stage_signed_release_stages_placeholder_signing_seam(tmp_path: Path):
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)
    out = tmp_path / "stage"

    result = stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=build_sha,
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
    build_sha = _write_minimal_repo(repo)
    out = tmp_path / "stage"
    out.mkdir()
    (out / "existing.txt").write_text("existing\n", encoding="utf-8")

    with pytest.raises(ReleasePublishError, match="output directory is not empty"):
        stage_signed_release(
            repo_root=repo,
            version="0.2.0",
            build_git_sha=build_sha,
            out=out,
            build_wheel=_fake_builder,
            verify_parity=lambda root: [],
        )


def test_stage_signed_release_refuses_mismatched_requested_sha_before_mutation(tmp_path: Path):
    repo = tmp_path / "repo"
    checkout_head = _write_minimal_repo(repo)
    requested_sha = _different_sha(checkout_head)
    out = tmp_path / "stage"
    version_file = repo / "validators" / "creator_engine_validator" / "_version.py"
    original_version = version_file.read_text(encoding="utf-8")
    builder_called = False

    def _builder_must_not_run(repo_root: Path, out_dir: Path) -> WheelManifest:
        nonlocal builder_called
        builder_called = True
        raise AssertionError("builder should not run after checkout/build SHA mismatch")

    with pytest.raises(ReleasePublishError, match="does not match checkout HEAD"):
        stage_signed_release(
            repo_root=repo,
            version="0.2.0",
            build_git_sha=requested_sha,
            out=out,
            force=True,
            build_wheel=_builder_must_not_run,
            verify_parity=lambda root: [],
        )

    assert builder_called is False
    assert version_file.read_text(encoding="utf-8") == original_version
    assert not out.exists()


def test_stage_signed_release_defaults_build_sha_to_checkout_head(tmp_path: Path):
    repo = tmp_path / "repo"
    checkout_head = _write_minimal_repo(repo)
    out = tmp_path / "stage"

    result = stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        out=out,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )

    manifest = (out / "release-stage-manifest.yml").read_text(encoding="utf-8")
    assert result.build_git_sha == checkout_head
    assert f"build_git_sha: {checkout_head}\n" in manifest


def test_stage_signed_release_default_signing_key_id_is_public_root(tmp_path: Path):
    """The default/public path stages ce-root-v1 with NO recipe rewrite.

    Regression for ce-ops#324 (B1): the default anchor must equal the principal
    the docs/llms-install.md recipe is authored for (ce-root-v1), so a public
    release stages correctly with key_id, recipe, and instructions all agreeing
    and the dev anchor never leaking through.
    """
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)
    out = tmp_path / "stage"

    result = stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=build_sha,
        out=out,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )

    spec = (out / "llms-install.md").read_text(encoding="utf-8")
    canonical = (out / "llms-install.canonical").read_text(encoding="utf-8")
    manifest = (out / "release-stage-manifest.yml").read_text(encoding="utf-8")
    instructions = (out / "SIGNING-INSTRUCTIONS.md").read_text(encoding="utf-8")

    assert "  key_id: ce-root-v1\n" in spec
    assert "  key_id: ce-root-v1\n" in canonical
    assert "signing_key_id: ce-root-v1\n" in manifest
    assert "-I ce-root-v1 " in instructions
    assert "-I ce-root-v1 " in result.signing_command
    # The intact placeholder seam survives (no auto-signing).
    assert PLACEHOLDER_SIGNATURE in spec
    # The dev anchor must NOT appear anywhere on the public path.
    assert "ce-dev1-root-v1" not in spec
    assert "ce-dev1-root-v1" not in canonical
    assert "ce-dev1-root-v1" not in manifest
    assert "ce-dev1-root-v1" not in instructions
    # The recipe principal an installer follows agrees with the staged key_id.
    assert "ssh-keygen -Y verify -f ce-root-v1 -I ce-root-v1" in spec


def test_stage_signed_release_signs_with_selected_dev_anchor(tmp_path: Path):
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)
    out = tmp_path / "stage"

    result = stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=build_sha,
        out=out,
        signing_key_id="ce-dev1-root-v1",
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )

    spec = (out / "llms-install.md").read_text(encoding="utf-8")
    canonical = (out / "llms-install.canonical").read_text(encoding="utf-8")
    manifest = (out / "release-stage-manifest.yml").read_text(encoding="utf-8")
    instructions = (out / "SIGNING-INSTRUCTIONS.md").read_text(encoding="utf-8")

    # The chosen dev anchor must reach the spec, the signed canonical bytes, and the manifest.
    assert "  key_id: ce-dev1-root-v1\n" in spec
    assert "  key_id: ce-dev1-root-v1\n" in canonical
    assert "signing_key_id: ce-dev1-root-v1\n" in manifest
    assert "-I ce-dev1-root-v1 " in instructions
    assert "-I ce-dev1-root-v1 " in result.signing_command
    # The default public anchor must NOT leak through as a verify principal.
    assert "  key_id: ce-root-v1\n" not in spec
    assert "  key_id: ce-root-v1\n" not in canonical
    assert "signing_key_id: ce-root-v1\n" not in manifest

    # key_id is part of the signed bytes: the canonical sha must reflect the chosen anchor.
    assert (
        hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        == result.canonical_spec_sha256
    )


def test_stage_signed_release_parameterizes_verify_recipe_principal(tmp_path: Path):
    """The embedded verify recipe must name the chosen signer, not the source.

    Regression for ce-ops#198 + ce-ops#324 (B1): the recipe is authored for the
    public ce-root-v1, so staging at the default public anchor leaves it intact
    (no rewrite), and staging at the dev anchor rewrites every recipe principal
    to ce-dev1-root-v1 — never the reverse. An installer following the rendered
    recipe always verifies against the staged signature.key_id.
    """
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)

    # Dev anchor: every recipe principal reference must become ce-dev1-root-v1.
    selected_out = tmp_path / "selected"
    stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=build_sha,
        out=selected_out,
        signing_key_id="ce-dev1-root-v1",
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )
    selected_spec = (selected_out / "llms-install.md").read_text(encoding="utf-8")
    assert "grep -Eo 'ce-dev1-root-v1[ =]SHA256:" in selected_spec
    assert 'awk \'$3 == "ce-dev1-root-v1" {' in selected_spec
    assert "-I ce-dev1-root-v1 -n ce-spec-v1" in selected_spec
    # The signer-independent trust-root key file + anchor record name are kept.
    assert "https://creator-engine.dev/keys/ce-root-v1 -o ce-root-v1" in selected_spec
    assert "ssh-keygen -Y verify -f ce-root-v1 -I ce-dev1-root-v1" in selected_spec
    assert "_ce-root-v1.creator-engine.dev" in selected_spec

    # Default (public) anchor: recipe principals stay ce-root-v1 (no rewrite).
    default_out = tmp_path / "default"
    stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=build_sha,
        out=default_out,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )
    default_spec = (default_out / "llms-install.md").read_text(encoding="utf-8")
    assert "grep -Eo 'ce-root-v1[ =]SHA256:" in default_spec
    assert 'awk \'$3 == "ce-root-v1" {' in default_spec
    assert "-I ce-root-v1 -n ce-spec-v1" in default_spec
    # No dev principal leaks onto the public path.
    assert "ce-dev1-root-v1" not in default_spec


def test_stage_signed_release_rejects_unknown_signing_key_id(tmp_path: Path):
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)
    out = tmp_path / "stage"
    builder_called = False

    def _builder_must_not_run(repo_root: Path, out_dir: Path) -> WheelManifest:
        nonlocal builder_called
        builder_called = True
        raise AssertionError("builder should not run when signing_key_id is rejected")

    with pytest.raises(ReleasePublishError, match="invalid signing_key_id"):
        stage_signed_release(
            repo_root=repo,
            version="0.2.0",
            build_git_sha=build_sha,
            out=out,
            signing_key_id="ce-attacker-v1",
            force=True,
            build_wheel=_builder_must_not_run,
            verify_parity=lambda root: [],
        )

    assert builder_called is False
    assert not out.exists()


def test_finalize_signed_release_verifies_signature_and_promotes_publishable_artifacts(tmp_path: Path):
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)
    stage = tmp_path / "stage"
    stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=build_sha,
        out=stage,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )
    signature = base64.b64encode(b"mock-sshsig").decode("ascii")
    seen: dict[str, object] = {}

    def _verifier(algo, raw, value, key_material):
        seen["algo"] = algo
        seen["raw_sha"] = hashlib.sha256(raw).hexdigest()
        seen["value"] = value
        seen["key_material"] = key_material
        return True

    out = tmp_path / "signed"
    result = finalize_signed_release(
        stage=stage,
        signature_base64=signature,
        out=out,
        verifier=_verifier,
    )

    signed_spec = (out / "llms-install.md").read_text(encoding="utf-8")
    finalize_manifest = (out / "release-finalize-manifest.yml").read_text(encoding="utf-8")
    canonical_sha = hashlib.sha256((stage / "llms-install.canonical").read_bytes()).hexdigest()

    assert result.version == "0.2.0"
    assert result.signing_key_id == "ce-root-v1"
    assert result.canonical_spec_sha256 == canonical_sha
    assert PLACEHOLDER_SIGNATURE not in signed_spec
    assert f"  value: {signature}\n" in signed_spec
    assert "kind: ce-release-finalize-manifest" in finalize_manifest
    assert f"canonical_spec_sha256: {canonical_sha}\n" in finalize_manifest
    assert seen["raw_sha"] == canonical_sha
    assert seen["value"] == signature


def test_finalize_signed_release_fails_closed_on_non_verifying_signature(tmp_path: Path):
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)
    stage = tmp_path / "stage"
    stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=build_sha,
        out=stage,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )

    with pytest.raises(ReleasePublishError, match="signed install spec verification failed"):
        finalize_signed_release(
            stage=stage,
            signature_base64=base64.b64encode(b"bad-sshsig").decode("ascii"),
            out=tmp_path / "signed",
            verifier=lambda *_args: False,
        )

    assert not (tmp_path / "signed").exists()


def test_finalize_signed_release_requires_exactly_one_placeholder(tmp_path: Path):
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)
    stage = tmp_path / "stage"
    stage_signed_release(
        repo_root=repo,
        version="0.2.0",
        build_git_sha=build_sha,
        out=stage,
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda root: [],
    )
    spec = stage / "llms-install.md"
    spec.write_text(
        spec.read_text(encoding="utf-8").replace(PLACEHOLDER_SIGNATURE, "not-base64"),
        encoding="utf-8",
    )

    with pytest.raises(ReleasePublishError, match="expected exactly one placeholder"):
        finalize_signed_release(
            stage=stage,
            signature_base64=base64.b64encode(b"mock").decode("ascii"),
            out=tmp_path / "signed",
            verifier=lambda *_args: True,
        )


def test_anchor_recipe_guard_raises_on_divergence():
    """Fail-closed guard: staged key_id must equal the recipe verify principal.

    Regression for ce-ops#324 (B1): a spec whose signature.key_id and embedded
    verify recipe name different principals must be refused before any artifact
    is emitted, making anchor/recipe divergence impossible to ship.
    """
    divergent = (
        "<!--\nsignature:\n  key_id: ce-root-v1\n-->\n"
        "ssh-keygen -Y verify -f ce-root-v1 -I ce-dev1-root-v1 -n ce-spec-v1\n"
    )
    with pytest.raises(ReleasePublishError, match="anchor/recipe divergence"):
        release_publish._assert_anchor_recipe_match(divergent, "ce-root-v1")

    # Anchor vs staged key_id mismatch is also refused.
    wrong_key = (
        "<!--\nsignature:\n  key_id: ce-dev1-root-v1\n-->\n"
        "ssh-keygen -Y verify -f ce-root-v1 -I ce-dev1-root-v1 -n ce-spec-v1\n"
    )
    with pytest.raises(ReleasePublishError, match="does not match requested"):
        release_publish._assert_anchor_recipe_match(wrong_key, "ce-root-v1")

    # An agreeing spec passes the guard.
    agreeing = (
        "<!--\nsignature:\n  key_id: ce-root-v1\n-->\n"
        "ssh-keygen -Y verify -f ce-root-v1 -I ce-root-v1 -n ce-spec-v1\n"
    )
    release_publish._assert_anchor_recipe_match(agreeing, "ce-root-v1")


def test_stage_signed_release_guard_blocks_divergent_recipe(tmp_path: Path):
    """End-to-end: a source recipe that diverges from the anchor refuses to stage."""
    repo = tmp_path / "repo"
    build_sha = _write_minimal_repo(repo)
    # Corrupt the source recipe so its verify principal no longer matches the
    # public anchor the default stage will request.
    spec_path = repo / "docs" / "llms-install.md"
    text = spec_path.read_text(encoding="utf-8")
    text = text.replace(
        "ssh-keygen -Y verify -f ce-root-v1 -I ce-root-v1",
        "ssh-keygen -Y verify -f ce-root-v1 -I ce-imposter-v1",
    )
    spec_path.write_text(text, encoding="utf-8")
    _git(repo, "commit", "-aqm", "corrupt recipe principal")
    head = _git(repo, "rev-parse", "--verify", "HEAD")
    out = tmp_path / "stage"

    with pytest.raises(ReleasePublishError, match="anchor/recipe divergence"):
        stage_signed_release(
            repo_root=repo,
            version="0.2.0",
            build_git_sha=head,
            out=out,
            force=True,
            build_wheel=_fake_builder,
            verify_parity=lambda root: [],
        )

    assert not out.exists()


def test_release_stage_cli_rejects_invalid_signing_key_id(tmp_path: Path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "release-stage",
                "--repo-root",
                str(tmp_path / "repo"),
                "--version",
                "0.2.0",
                "--out",
                str(tmp_path / "stage"),
                "--signing-key-id",
                "ce-attacker-v1",
            ]
        )
    assert exc.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


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
    assert calls["signing_key_id"] == "ce-root-v1"
    rendered = capsys.readouterr().out
    assert '"signature_placeholder": "<RESIGN-REQUIRED-ce-root-v1>"' in rendered


def test_release_stage_cli_allows_build_git_sha_to_default(monkeypatch, tmp_path: Path):
    calls: dict[str, object] = {}

    def _fake_stage(**kwargs):
        calls.update(kwargs)
        return ReleaseStageResult(
            out_dir=Path(kwargs["out"]),
            version=kwargs["version"],
            build_git_sha="b" * 40,
            wheel_name="creator_engine_validator-0.2.0-py3-none-any.whl",
            wheel_sha256="1" * 64,
            sha256s_sha256="2" * 64,
            canonical_spec_sha256="3" * 64,
            signature_placeholder=PLACEHOLDER_SIGNATURE,
            signing_command="ssh-keygen -Y sign ...",
            artifacts=(),
        )

    monkeypatch.setattr(release_publish, "stage_signed_release", _fake_stage)

    code = cli.main(
        [
            "release-stage",
            "--repo-root",
            str(tmp_path / "repo"),
            "--version",
            "0.2.0",
            "--out",
            str(tmp_path / "stage"),
        ]
    )

    assert code == 0
    assert calls["build_git_sha"] is None
    assert calls["signing_key_id"] == "ce-root-v1"


def test_release_stage_cli_threads_selected_signing_key_id(monkeypatch, tmp_path: Path):
    calls: dict[str, object] = {}

    def _fake_stage(**kwargs):
        calls.update(kwargs)
        return ReleaseStageResult(
            out_dir=Path(kwargs["out"]),
            version=kwargs["version"],
            build_git_sha="b" * 40,
            wheel_name="creator_engine_validator-0.2.0-py3-none-any.whl",
            wheel_sha256="1" * 64,
            sha256s_sha256="2" * 64,
            canonical_spec_sha256="3" * 64,
            signature_placeholder=PLACEHOLDER_SIGNATURE,
            signing_command="ssh-keygen -Y sign ...",
            artifacts=(),
        )

    monkeypatch.setattr(release_publish, "stage_signed_release", _fake_stage)

    code = cli.main(
        [
            "release-stage",
            "--repo-root",
            str(tmp_path / "repo"),
            "--version",
            "0.2.0",
            "--out",
            str(tmp_path / "stage"),
            "--signing-key-id",
            "ce-dev1-root-v1",
        ]
    )

    assert code == 0
    assert calls["signing_key_id"] == "ce-dev1-root-v1"
