"""Deterministic signed-release staging pipeline.

The actual ``ce-root-v1`` private key stays Operator-held. This module stages a
publishable Pages mirror with a root-signature placeholder plus the exact
``ssh-keygen -Y sign`` command the Operator runs after reviewing the staged
canonical install spec.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping

from . import version as version_runtime
from .wheel_bake import WheelManifest, build_app_wheel_from_source
from .wheel_source_parity import verify_wheel_matches_source


PLACEHOLDER_SIGNATURE = "<RESIGN-REQUIRED-ce-root-v1>"
SIGNING_KEY_ID = "ce-dev1-root-v1"
SIGNING_NAMESPACE = "ce-spec-v1"
TRUST_ROOT_ID = "ce-root-v1"
SHA256SUMS = "SHA256SUMS"

SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ReleasePublishError(RuntimeError):
    """Release staging refused before publishable output was promoted."""


@dataclass(frozen=True)
class StagedArtifact:
    path: str
    sha256: str
    size: int


@dataclass(frozen=True)
class ReleaseStageResult:
    out_dir: Path
    version: str
    build_git_sha: str
    wheel_name: str
    wheel_sha256: str
    sha256s_sha256: str
    canonical_spec_sha256: str
    signature_placeholder: str
    signing_command: str
    artifacts: tuple[StagedArtifact, ...] = field(default_factory=tuple)


BuildWheelFn = Callable[[Path, Path], WheelManifest]
ParityVerifyFn = Callable[[Path], list[str]]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ReleasePublishError(f"missing {label}: {path}")


def _validate_inputs(version: str, build_git_sha: str | None, out: Path, sign_mode: str) -> None:
    if not SEMVER_RE.fullmatch(version):
        raise ReleasePublishError(f"invalid release version {version!r}")
    if build_git_sha is not None and not SHA_RE.fullmatch(build_git_sha):
        raise ReleasePublishError(f"invalid build git sha {build_git_sha!r}; expected 40 lowercase hex")
    if sign_mode != "placeholder":
        raise ReleasePublishError("only --sign-mode placeholder is supported; root signing is Operator-gated")
    if not str(out).strip():
        raise ReleasePublishError("explicit output directory is required")


def _checkout_head(repo_root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
        raise ReleasePublishError(f"cannot resolve checkout HEAD for {repo_root}: {exc}") from exc
    head = proc.stdout.strip().lower()
    if proc.returncode != 0 or not SHA_RE.fullmatch(head):
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise ReleasePublishError(f"cannot resolve checkout HEAD for {repo_root}: {detail}")
    return head


def _select_build_git_sha(repo_root: Path, requested: str | None) -> str:
    checkout_head = _checkout_head(repo_root)
    if requested is None:
        return checkout_head
    if requested != checkout_head:
        raise ReleasePublishError(
            f"requested build git sha {requested!r} does not match checkout HEAD {checkout_head!r}; "
            "run release-stage from a checkout at the requested commit, or omit --build-git-sha "
            "to use the current checkout HEAD"
        )
    return requested


def _copy_file(src: Path, dst: Path) -> None:
    _require_file(src, "source artifact")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _stage_dependency_wheelhouse(repo_root: Path, version: str, stage_downloads: Path) -> list[Path]:
    release_source = repo_root / "docs" / "downloads" / version
    source = release_source if release_source.is_dir() else repo_root / "validators" / "wheelhouse"
    if not source.is_dir():
        raise ReleasePublishError(f"missing dependency wheelhouse source: {source}")
    copied: list[Path] = []
    for wheel in sorted(source.glob("*.whl")):
        if wheel.name.startswith("creator_engine_validator-"):
            continue
        target = stage_downloads / wheel.name
        _copy_file(wheel, target)
        copied.append(target)
    if not copied:
        raise ReleasePublishError(f"dependency wheelhouse has no wheels: {source}")
    return copied


def _write_sha256s(stage_downloads: Path, files: Iterable[Path]) -> Path:
    lines = []
    seen: set[str] = set()
    for path in sorted(files, key=lambda p: p.name):
        if not path.is_file():
            raise ReleasePublishError(f"cannot hash missing staged artifact: {path}")
        if path.name in seen:
            raise ReleasePublishError(f"duplicate staged artifact name: {path.name}")
        seen.add(path.name)
        lines.append(f"{_sha256(path)}  {path.name}\n")
    if not lines:
        raise ReleasePublishError("refusing to write empty SHA256SUMS")
    sha_path = stage_downloads / SHA256SUMS
    sha_path.write_text("".join(lines), encoding="utf-8")
    return sha_path


def _parse_sha256s(path: Path) -> dict[str, str]:
    expected: dict[str, str] = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        parts = raw.split()
        if len(parts) != 2:
            raise ReleasePublishError(f"malformed SHA256SUMS line {lineno}")
        digest, name = parts
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ReleasePublishError(f"malformed SHA256SUMS digest on line {lineno}")
        if "/" in name or "\\" in name or name in {".", ".."}:
            raise ReleasePublishError(f"malformed SHA256SUMS filename on line {lineno}: {name!r}")
        if name in expected:
            raise ReleasePublishError(f"duplicate SHA256SUMS entry: {name}")
        expected[name] = digest
    return expected


def verify_stage_hashes(stage_downloads: Path) -> None:
    sha_path = stage_downloads / SHA256SUMS
    _require_file(sha_path, "staged SHA256SUMS")
    expected = _parse_sha256s(sha_path)
    files = {p.name: p for p in stage_downloads.iterdir() if p.is_file() and p.name != SHA256SUMS}
    missing = sorted(set(expected) - set(files))
    extra = sorted(set(files) - set(expected))
    if missing:
        raise ReleasePublishError(f"SHA256SUMS entries missing staged files: {missing}")
    if extra:
        raise ReleasePublishError(f"staged files missing from SHA256SUMS: {extra}")
    for name, digest in sorted(expected.items()):
        actual = _sha256(files[name])
        if actual != digest:
            raise ReleasePublishError(f"SHA256 mismatch for {name}: expected {digest}, got {actual}")


def _canonical_install_spec(spec_text: str) -> str:
    return re.sub(
        r"^(  (?:value|content_sha256): ).*$",
        r"\1<published-with-this-spec>",
        spec_text,
        flags=re.MULTILINE,
    )


def _replace_field(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^(  {re.escape(key)}: ).*$", flags=re.MULTILINE)
    replaced, count = pattern.subn(rf"\g<1>{value}", text)
    if count != 1:
        raise ReleasePublishError(f"expected exactly one signature field {key!r}, found {count}")
    return replaced


def _replace_manifest_scalar(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^(  {re.escape(key)}: ).*$", flags=re.MULTILINE)
    replaced, count = pattern.subn(rf"\g<1>{value}", text)
    if count != 1:
        raise ReleasePublishError(f"expected exactly one artifact_manifest field {key!r}, found {count}")
    return replaced


def _rewrite_required_wheels(text: str, *, app_wheel_name: str, sha_by_name: Mapping[str, str], base_url: str) -> str:
    lines = text.splitlines(keepends=True)
    in_wheels = False
    current_name: str | None = None
    app_matched = False
    seen: set[str] = set()
    for index, line in enumerate(lines):
        if line == "  required_wheels:\n":
            in_wheels = True
            continue
        if in_wheels and line == "  python_acquisition:\n":
            in_wheels = False
            current_name = None
            continue
        if not in_wheels:
            continue
        if line.startswith("    - filename: "):
            original = line.removeprefix("    - filename: ").strip()
            if original.startswith("creator_engine_validator-") and original.endswith(".whl"):
                current_name = app_wheel_name
                app_matched = True
                lines[index] = f"    - filename: {app_wheel_name}\n"
            else:
                current_name = original
            if current_name not in sha_by_name:
                raise ReleasePublishError(
                    f"required_wheels entry {current_name!r} is not present in staged SHA256SUMS"
                )
            seen.add(current_name)
            continue
        if current_name and line.startswith("      url: "):
            lines[index] = f"      url: {base_url}/{current_name}\n"
        elif current_name and line.startswith("      sha256: "):
            lines[index] = f"      sha256: {sha_by_name[current_name]}\n"
    if not app_matched:
        raise ReleasePublishError(f"required_wheels is missing an app wheel entry for {app_wheel_name!r}")
    missing = sorted(name for name in sha_by_name if name.endswith(".whl") and name not in seen)
    if missing:
        raise ReleasePublishError(f"staged wheels missing from required_wheels: {missing}")
    return "".join(lines)


def _render_placeholder_spec(
    source_spec: Path,
    *,
    version: str,
    app_wheel_name: str,
    sha_by_name: Mapping[str, str],
    sha256s_sha256: str,
    answers_schema_sha256: str,
    canonical_base_url: str,
    site_url: str,
) -> tuple[str, str]:
    text = source_spec.read_text(encoding="utf-8")
    base_url = f"{canonical_base_url}/downloads/{version}"
    text = _replace_manifest_scalar(text, "package_version", version)
    text = _replace_manifest_scalar(text, "artifact_base_url", base_url)
    text = _replace_manifest_scalar(text, "sha256s_url", f"{base_url}/SHA256SUMS")
    text = _replace_manifest_scalar(text, "sha256s_sha256", sha256s_sha256)
    text = _replace_manifest_scalar(text, "install_sh_url", f"{site_url}/install.sh")
    text = _replace_manifest_scalar(text, "install_sh_sha256s_entry", "install.sh")
    text = _replace_manifest_scalar(text, "answers_schema_url", f"{site_url}/schemas/install-answers.schema.yaml")
    text = _replace_manifest_scalar(text, "answers_schema_sha256", answers_schema_sha256)
    text = _replace_manifest_scalar(text, "app_wheel", app_wheel_name)
    text = _rewrite_required_wheels(
        text,
        app_wheel_name=app_wheel_name,
        sha_by_name=sha_by_name,
        base_url=base_url,
    )
    canonical = _canonical_install_spec(text)
    canonical_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    text = _replace_field(text, "value", PLACEHOLDER_SIGNATURE)
    text = _replace_field(text, "content_sha256", canonical_sha)
    return text, canonical_sha


def _render_signing_instructions(canonical_rel: str = "llms-install.canonical") -> str:
    return (
        "# Operator signing seam for ce-root-v1\n\n"
        "The staged install spec intentionally contains the placeholder "
        f"`{PLACEHOLDER_SIGNATURE}`. The Operator reviews the staged artifacts, "
        "signs the canonical spec bytes with the held root key, base64-encodes "
        "the SSHSIG, and replaces only the placeholder value.\n\n"
        "```bash\n"
        f"ssh-keygen -Y sign -f /path/to/ce-root-v1-private -I {SIGNING_KEY_ID} "
        f"-n {SIGNING_NAMESPACE} - < {canonical_rel} > llms-install.md.sig\n"
        "base64 -w0 llms-install.md.sig\n"
        "```\n\n"
        "No automated path in this command reads or invokes the root private key.\n"
    )


def _stage_manifest(
    *,
    version: str,
    build_git_sha: str,
    wheel_name: str,
    wheel_sha256: str,
    sha256s_sha256: str,
    canonical_spec_sha256: str,
    signing_command: str,
    artifacts: tuple[StagedArtifact, ...],
) -> str:
    lines = [
        "kind: ce-release-stage-manifest\n",
        'schema_version: "1"\n',
        f"package_version: {version}\n",
        f"build_git_sha: {build_git_sha}\n",
        f"app_wheel: {wheel_name}\n",
        f"app_wheel_sha256: {wheel_sha256}\n",
        f"sha256s_sha256: {sha256s_sha256}\n",
        f"canonical_spec_sha256: {canonical_spec_sha256}\n",
        f"signature_placeholder: {PLACEHOLDER_SIGNATURE}\n",
        f"signing_key_id: {SIGNING_KEY_ID}\n",
        f"signing_namespace: {SIGNING_NAMESPACE}\n",
        f"signing_command: {signing_command}\n",
        "artifacts:\n",
    ]
    for artifact in artifacts:
        lines.extend(
            [
                f"  - path: {artifact.path}\n",
                f"    sha256: {artifact.sha256}\n",
                f"    size: {artifact.size}\n",
            ]
        )
    return "".join(lines)


def _collect_artifacts(root: Path) -> tuple[StagedArtifact, ...]:
    artifacts: list[StagedArtifact] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        artifacts.append(StagedArtifact(path=rel, sha256=_sha256(path), size=path.stat().st_size))
    return tuple(artifacts)


def _ensure_output_target(out: Path, *, force: bool) -> None:
    if out.exists() and any(out.iterdir()) and not force:
        raise ReleasePublishError(f"output directory is not empty; pass --force to replace it: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)


def _promote_stage(temp_stage: Path, out: Path) -> None:
    backup: Path | None = None
    if out.exists():
        backup = out.with_name(f".{out.name}.previous.{os.getpid()}")
        if backup.exists():
            shutil.rmtree(backup)
        out.rename(backup)
    try:
        temp_stage.rename(out)
    except Exception:
        if backup is not None and backup.exists() and not out.exists():
            backup.rename(out)
        raise
    if backup is not None and backup.exists():
        shutil.rmtree(backup)


def stage_signed_release(
    *,
    repo_root: Path | str,
    version: str,
    build_git_sha: str | None = None,
    out: Path | str,
    sign_mode: str = "placeholder",
    force: bool = False,
    dry_run: bool = False,
    build_wheel: BuildWheelFn = build_app_wheel_from_source,
    verify_parity: ParityVerifyFn = verify_wheel_matches_source,
    stage_hash_verifier: Callable[[Path], None] = verify_stage_hashes,
    site_url: str = "https://creator-engine.dev",
) -> ReleaseStageResult:
    """Stage a deterministic Pages release mirror, stopping before root signing.

    Fail-closed ordering:
    1. require requested ``build_git_sha`` to match checkout HEAD, or default to HEAD;
    2. generate ``_version.py`` for that checkout commit;
    3. build app wheel and verify source parity;
    4. assemble a temporary mirror and re-pin ``SHA256SUMS``;
    5. write placeholder signed-spec bytes and signing instructions;
    6. verify staged hashes;
    7. atomically promote to the explicit output directory.
    """
    root = Path(repo_root).resolve()
    output = Path(out).resolve()
    _validate_inputs(version, build_git_sha, output, sign_mode)
    if not root.is_dir():
        raise ReleasePublishError(f"repo root does not exist: {root}")
    selected_build_git_sha = _select_build_git_sha(root, build_git_sha)
    _ensure_output_target(output, force=force or dry_run)

    validators_dir = root / "validators"
    package_dir = validators_dir / "creator_engine_validator"
    docs_dir = root / "docs"
    install_sh = docs_dir / "install.sh"
    source_spec = docs_dir / "llms-install.md"
    answers_schema = docs_dir / "schemas" / "install-answers.schema.yaml"
    trust_root = docs_dir / "keys" / TRUST_ROOT_ID
    for path, label in (
        (validators_dir / "pyproject.toml", "validator pyproject"),
        (package_dir, "validator package"),
        (install_sh, "install.sh"),
        (source_spec, "signed install spec template"),
        (answers_schema, "answers schema"),
        (trust_root, "trust root"),
    ):
        if path.is_dir():
            continue
        _require_file(path, label)

    original_version_bytes = (package_dir / "_version.py").read_bytes() if (package_dir / "_version.py").exists() else None
    try:
        (package_dir / "_version.py").write_text(
            version_runtime.render_build_file(version, selected_build_git_sha),
            encoding="utf-8",
        )
        with tempfile.TemporaryDirectory(prefix="ce-release-wheel-") as wheel_tmp:
            wheel_out = Path(wheel_tmp)
            wheel_manifest = build_wheel(root, wheel_out)
            if wheel_manifest.version != version:
                raise ReleasePublishError(
                    f"built wheel version {wheel_manifest.version!r} does not match requested {version!r}"
                )
            if wheel_manifest.source_commit != selected_build_git_sha:
                raise ReleasePublishError(
                    "built wheel source commit "
                    f"{wheel_manifest.source_commit!r} does not match requested {selected_build_git_sha!r}"
                )
            wheel_path = wheel_out / wheel_manifest.wheel_name
            _require_file(wheel_path, "built app wheel")
            actual_wheel_sha = _sha256(wheel_path)
            if actual_wheel_sha != wheel_manifest.sha256:
                raise ReleasePublishError(
                    f"built wheel manifest sha mismatch for {wheel_manifest.wheel_name}: "
                    f"{wheel_manifest.sha256} != {actual_wheel_sha}"
                )
            parity_violations = verify_parity(root)
            if parity_violations:
                raise ReleasePublishError(
                    "wheel/source parity failed: " + "; ".join(parity_violations)
                )

            temp_parent = output.parent
            temp_stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage.", dir=temp_parent))
            try:
                stage_downloads = temp_stage / "downloads" / version
                stage_downloads.mkdir(parents=True)
                staged_files = _stage_dependency_wheelhouse(root, version, stage_downloads)
                staged_wheel = stage_downloads / wheel_manifest.wheel_name
                _copy_file(wheel_path, staged_wheel)
                staged_files.append(staged_wheel)
                staged_install = stage_downloads / install_sh.name
                _copy_file(install_sh, staged_install)
                staged_files.append(staged_install)
                sha_path = _write_sha256s(stage_downloads, staged_files)
                sha256s_sha = _sha256(sha_path)
                sha_by_name = _parse_sha256s(sha_path)

                _copy_file(install_sh, temp_stage / "install.sh")
                _copy_file(answers_schema, temp_stage / "schemas" / "install-answers.schema.yaml")
                _copy_file(trust_root, temp_stage / "keys" / TRUST_ROOT_ID)
                answers_sha = _sha256(answers_schema)
                site = site_url.rstrip("/")
                spec_text, canonical_sha = _render_placeholder_spec(
                    source_spec,
                    version=version,
                    app_wheel_name=wheel_manifest.wheel_name,
                    sha_by_name=sha_by_name,
                    sha256s_sha256=sha256s_sha,
                    answers_schema_sha256=answers_sha,
                    canonical_base_url=site,
                    site_url=site,
                )
                staged_spec = temp_stage / "llms-install.md"
                staged_spec.write_text(spec_text, encoding="utf-8")
                canonical_text = _canonical_install_spec(spec_text)
                canonical_path = temp_stage / "llms-install.canonical"
                canonical_path.write_text(canonical_text, encoding="utf-8")
                if hashlib.sha256(canonical_text.encode("utf-8")).hexdigest() != canonical_sha:
                    raise ReleasePublishError("canonical install spec sha drifted during staging")
                instructions = _render_signing_instructions()
                (temp_stage / "SIGNING-INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")
                signing_command = (
                    f"ssh-keygen -Y sign -f /path/to/ce-root-v1-private -I {SIGNING_KEY_ID} "
                    f"-n {SIGNING_NAMESPACE} - < llms-install.canonical > llms-install.md.sig"
                )
                artifacts = _collect_artifacts(temp_stage)
                (temp_stage / "release-stage-manifest.yml").write_text(
                    _stage_manifest(
                        version=version,
                        build_git_sha=selected_build_git_sha,
                        wheel_name=wheel_manifest.wheel_name,
                        wheel_sha256=actual_wheel_sha,
                        sha256s_sha256=sha256s_sha,
                        canonical_spec_sha256=canonical_sha,
                        signing_command=signing_command,
                        artifacts=artifacts,
                    ),
                    encoding="utf-8",
                )
                artifacts = _collect_artifacts(temp_stage)
                stage_hash_verifier(stage_downloads)
                if dry_run:
                    shutil.rmtree(temp_stage)
                else:
                    _promote_stage(temp_stage, output)
                return ReleaseStageResult(
                    out_dir=output,
                    version=version,
                    build_git_sha=selected_build_git_sha,
                    wheel_name=wheel_manifest.wheel_name,
                    wheel_sha256=actual_wheel_sha,
                    sha256s_sha256=sha256s_sha,
                    canonical_spec_sha256=canonical_sha,
                    signature_placeholder=PLACEHOLDER_SIGNATURE,
                    signing_command=signing_command,
                    artifacts=artifacts,
                )
            except Exception:
                if temp_stage.exists():
                    shutil.rmtree(temp_stage)
                raise
    finally:
        version_file = package_dir / "_version.py"
        if original_version_bytes is None:
            version_file.unlink(missing_ok=True)
        else:
            version_file.write_bytes(original_version_bytes)
