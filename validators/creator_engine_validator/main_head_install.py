"""Verified main-HEAD source build install path.

This module is intentionally separate from the signed release updater. Public
releases stay rooted in the ce-root-v1 signature path; a main-HEAD install is
trusted only when it is built locally from a freshly resolved ``origin/main``
commit and every source/artifact hash check passes before promotion.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from . import version as version_runtime
from .release_publish import SEMVER_RE
from .venv_install_common import (
    InstallLock,
    build_venv_target,
    promote_and_write_state,
    venv_target_ok,
    write_text_atomic,
)
from .wheel_bake import WheelBakeError, WheelManifest, build_app_wheel_from_source

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TRACK = "main"
REMOTE = "origin"
BRANCH = "main"
PACKAGE_NAME = "creator-engine-validator"

BuildWheelFn = Callable[..., WheelManifest]


class MainHeadInstallRefused(Exception):
    """Fail-closed refusal for the main-HEAD install path."""


@dataclass(frozen=True)
class ResolvedMainHead:
    repo_root: Path
    remote: str
    branch: str
    commit: str
    git_source_sha256: str


@dataclass(frozen=True)
class MainHeadArtifact:
    identity: ResolvedMainHead
    worktree: Path
    wheel_path: Path
    wheel_name: str
    wheel_sha256: str
    package_version: str
    build_source_sha256: str
    artifact_manifest_sha256: str
    dependency_wheels: Mapping[str, Path] = field(default_factory=dict)
    dependency_sha256: Mapping[str, str] = field(default_factory=dict)

    @property
    def token(self) -> str:
        return f"main@{self.identity.commit[:12]}"

    def manifest(self) -> dict[str, Any]:
        return {
            "kind": "ce-main-head-artifact",
            "schema_version": "1",
            "track": TRACK,
            "remote": self.identity.remote,
            "branch": self.identity.branch,
            "source_commit": self.identity.commit,
            "git_source_sha256": self.identity.git_source_sha256,
            "build_source_sha256": self.build_source_sha256,
            "package_name": PACKAGE_NAME,
            "package_version": self.package_version,
            "wheel_name": self.wheel_name,
            "wheel_sha256": self.wheel_sha256,
            "dependencies": [
                {"filename": name, "sha256": self.dependency_sha256[name]}
                for name in sorted(self.dependency_sha256)
            ],
            "trust_model": "verified-source-build-main-head",
            "signature": "none",
        }


@dataclass(frozen=True)
class CleanMainInstallResult:
    ok: bool
    status: str
    reason: str
    identity: ResolvedMainHead | None = None
    artifact: Mapping[str, Any] = field(default_factory=dict)
    install_root: str | None = None
    actions: tuple[str, ...] = ()
    read_only: bool = False
    problems: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        identity = None
        if self.identity is not None:
            identity = {
                "remote": self.identity.remote,
                "branch": self.identity.branch,
                "commit": self.identity.commit,
                "token": f"main@{self.identity.commit[:12]}",
                "git_source_sha256": self.identity.git_source_sha256,
            }
        return {
            "ok": self.ok,
            "status": self.status,
            "reason": self.reason,
            "read_only": self.read_only,
            "identity": identity,
            "artifact": dict(self.artifact),
            "install_root": self.install_root,
            "actions": list(self.actions),
            "problems": list(self.problems),
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _default_install_root() -> Path:
    if os.environ.get("CE_INSTALL_ROOT"):
        return Path(os.environ["CE_INSTALL_ROOT"])
    base = os.environ.get("CE_HOME")
    if base:
        return Path(base) / "bootstrap"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "creator-engine" / "bootstrap"
    return Path.home() / ".local" / "share" / "creator-engine" / "bootstrap"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_json_sha256(payload: Mapping[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(data)


def _run_git(repo_root: Path, args: list[str], *, input_bytes: bytes | None = None) -> bytes:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            input=input_bytes,
            check=False,
            capture_output=True,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
        raise MainHeadInstallRefused(f"git_refused: cannot run git: {exc}") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip() or proc.stdout.decode(
            "utf-8", errors="replace"
        ).strip()
        raise MainHeadInstallRefused(f"git_refused: {' '.join(args)} failed: {detail}")
    return proc.stdout


def _validate_main_track(remote: str, branch: str) -> None:
    if remote != REMOTE or branch != BRANCH:
        raise MainHeadInstallRefused(
            "unsupported_track: clean main install supports exactly origin/main"
        )


def _require_sha(value: str, label: str) -> str:
    cleaned = value.strip().lower()
    if not SHA_RE.fullmatch(cleaned):
        raise MainHeadInstallRefused(f"{label}_refused: expected 40 lowercase hex, got {value!r}")
    return cleaned


def _git_archive_sha256(repo_root: Path, commit: str) -> str:
    return _sha256_bytes(_run_git(repo_root, ["archive", "--format=tar", commit]))


def resolve_origin_main(
    repo_root: str | Path,
    *,
    remote: str = REMOTE,
    branch: str = BRANCH,
    fetch: bool = True,
) -> ResolvedMainHead:
    """Resolve ``origin/main`` to an exact commit and source archive digest."""

    _validate_main_track(remote, branch)
    root = Path(repo_root).resolve()
    if not (root / ".git").exists():
        raise MainHeadInstallRefused(f"repo_root_refused: not a git checkout: {root}")
    if fetch:
        _run_git(root, ["fetch", remote, branch])
    ref = f"refs/remotes/{remote}/{branch}^{{commit}}"
    commit = _require_sha(_run_git(root, ["rev-parse", "--verify", ref]).decode().strip(), "main_head")
    source_sha = _git_archive_sha256(root, commit)
    return ResolvedMainHead(
        repo_root=root,
        remote=remote,
        branch=branch,
        commit=commit,
        git_source_sha256=source_sha,
    )


def _source_file_paths(worktree: Path) -> tuple[Path, ...]:
    validators = worktree / "validators"
    package = validators / "creator_engine_validator"
    paths: list[Path] = [validators / "pyproject.toml"]
    readme = validators / "README.md"
    if readme.is_file():
        paths.append(readme)
    if package.is_dir():
        for path in package.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            paths.append(path)
    return tuple(sorted(paths))


def _source_tree_sha256(worktree: Path) -> str:
    h = hashlib.sha256()
    for path in _source_file_paths(worktree):
        rel = path.relative_to(worktree).as_posix()
        h.update(rel.encode("utf-8") + b"\0")
        h.update(path.read_bytes() + b"\0")
    return h.hexdigest()


def _project_version(worktree: Path) -> str:
    import tomllib

    pyproject = worktree / "validators" / "pyproject.toml"
    try:
        version = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {}).get("version")
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise MainHeadInstallRefused(f"source_refused: cannot read project version: {exc}") from exc
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        raise MainHeadInstallRefused(f"source_refused: invalid project version {version!r}")
    return version


def _write_build_identity(worktree: Path, commit: str) -> None:
    version = _project_version(worktree)
    target = worktree / "validators" / "creator_engine_validator" / "_version.py"
    if not target.parent.is_dir():
        raise MainHeadInstallRefused(f"source_refused: missing package directory: {target.parent}")
    target.write_text(version_runtime.render_build_file(version, commit), encoding="utf-8")


def _call_build_wheel(build_wheel: BuildWheelFn, worktree: Path, out_dir: Path, build_dir: Path) -> WheelManifest:
    try:
        sig = inspect.signature(build_wheel)
    except (TypeError, ValueError):
        sig = None
    accepts_build_dir = False
    if sig is not None:
        accepts_build_dir = "build_dir" in sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
    try:
        if accepts_build_dir:
            return build_wheel(worktree, out_dir, build_dir=build_dir)
        return build_wheel(worktree, out_dir)
    except WheelBakeError as exc:
        raise MainHeadInstallRefused(f"wheel_build_refused: {exc}") from exc


def _dependency_wheels(worktree: Path) -> tuple[Path, ...]:
    wheelhouse = worktree / "validators" / "wheelhouse"
    if not wheelhouse.is_dir():
        return ()
    return tuple(
        sorted(
            path
            for path in wheelhouse.glob("*.whl")
            if not path.name.startswith("creator_engine_validator-")
        )
    )


def build_main_head_artifact(
    resolved: ResolvedMainHead,
    *,
    work_root: str | Path | None = None,
    build_wheel: BuildWheelFn = build_app_wheel_from_source,
) -> MainHeadArtifact:
    """Build and verify the first-party wheel from the resolved main commit."""

    root = resolved.repo_root
    if _git_archive_sha256(root, resolved.commit) != resolved.git_source_sha256:
        raise MainHeadInstallRefused("source_hash_mismatch: resolved source archive hash changed")
    cleanup_parent = None
    if work_root is None:
        cleanup_parent = Path(tempfile.mkdtemp(prefix="ce-main-head-"))
        parent = cleanup_parent
    else:
        parent = Path(work_root).resolve()
        parent.mkdir(parents=True, exist_ok=True)
    worktree = parent / f"source-{resolved.commit[:12]}"
    wheel_out = parent / "wheelhouse"
    build_dir = parent / "build"
    try:
        _run_git(root, ["worktree", "add", "--detach", "--force", str(worktree), resolved.commit])
        actual_head = _require_sha(
            _run_git(worktree, ["rev-parse", "--verify", "HEAD"]).decode().strip(),
            "worktree_head",
        )
        if actual_head != resolved.commit:
            raise MainHeadInstallRefused(
                f"source_commit_mismatch: worktree HEAD {actual_head} != {resolved.commit}"
            )
        if _git_archive_sha256(worktree, "HEAD") != resolved.git_source_sha256:
            raise MainHeadInstallRefused("source_hash_mismatch: materialized worktree does not match resolved source")
        _write_build_identity(worktree, resolved.commit)
        build_source_sha = _source_tree_sha256(worktree)
        wheel_out.mkdir(parents=True, exist_ok=True)
        build_dir.mkdir(parents=True, exist_ok=True)
        manifest = _call_build_wheel(build_wheel, worktree, wheel_out, build_dir)
        if manifest.source_commit != resolved.commit:
            raise MainHeadInstallRefused(
                f"wheel_source_mismatch: built wheel source {manifest.source_commit} != {resolved.commit}"
            )
        wheel_path = wheel_out / manifest.wheel_name
        if not wheel_path.is_file():
            raise MainHeadInstallRefused(f"wheel_missing: builder did not produce {manifest.wheel_name}")
        wheel_sha = _sha256_file(wheel_path)
        if wheel_sha != manifest.sha256:
            raise MainHeadInstallRefused(
                f"wheel_hash_mismatch: builder reported {manifest.sha256}, actual {wheel_sha}"
            )
        after_build_source_sha = _source_tree_sha256(worktree)
        if after_build_source_sha != build_source_sha:
            raise MainHeadInstallRefused("source_hash_mismatch: source changed during wheel build")
        dependencies = {path.name: path for path in _dependency_wheels(worktree)}
        dependency_sha = {name: _sha256_file(path) for name, path in dependencies.items()}
        artifact = MainHeadArtifact(
            identity=resolved,
            worktree=worktree,
            wheel_path=wheel_path,
            wheel_name=manifest.wheel_name,
            wheel_sha256=wheel_sha,
            package_version=manifest.version,
            build_source_sha256=build_source_sha,
            artifact_manifest_sha256="",
            dependency_wheels=dependencies,
            dependency_sha256=dependency_sha,
        )
        artifact_sha = _canonical_json_sha256(artifact.manifest())
        return MainHeadArtifact(
            identity=artifact.identity,
            worktree=artifact.worktree,
            wheel_path=artifact.wheel_path,
            wheel_name=artifact.wheel_name,
            wheel_sha256=artifact.wheel_sha256,
            package_version=artifact.package_version,
            build_source_sha256=artifact.build_source_sha256,
            artifact_manifest_sha256=artifact_sha,
            dependency_wheels=artifact.dependency_wheels,
            dependency_sha256=artifact.dependency_sha256,
        )
    except Exception:
        if worktree.exists():
            try:
                _run_git(root, ["worktree", "remove", "--force", str(worktree)])
            except MainHeadInstallRefused:
                pass
        if cleanup_parent is not None:
            shutil.rmtree(cleanup_parent, ignore_errors=True)
        raise


def _remove_worktree(resolved: ResolvedMainHead, worktree: Path) -> None:
    if not worktree.exists():
        return
    try:
        _run_git(resolved.repo_root, ["worktree", "remove", "--force", str(worktree)])
    except MainHeadInstallRefused:
        shutil.rmtree(worktree, ignore_errors=True)


def verify_artifact_files(artifact: MainHeadArtifact) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    def add_row(name: str, expected: str, actual: str) -> None:
        rows.append(
            {
                "artifact": name,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "ok": expected == actual,
            }
        )

    if not artifact.wheel_path.is_file():
        raise MainHeadInstallRefused(f"artifact_missing: {artifact.wheel_path}")
    add_row(artifact.wheel_name, artifact.wheel_sha256, _sha256_file(artifact.wheel_path))
    for name, path in sorted(artifact.dependency_wheels.items()):
        if not path.is_file():
            raise MainHeadInstallRefused(f"artifact_missing: {path}")
        add_row(name, artifact.dependency_sha256[name], _sha256_file(path))
    manifest_sha = _canonical_json_sha256(
        {**artifact.manifest(), "artifact_manifest_sha256": artifact.artifact_manifest_sha256}
    )
    # The stored manifest hash is over the manifest without its self-reference.
    expected_manifest_sha = _canonical_json_sha256(artifact.manifest())
    add_row("artifact-manifest.json", artifact.artifact_manifest_sha256, expected_manifest_sha)
    if manifest_sha == artifact.artifact_manifest_sha256:
        raise MainHeadInstallRefused("artifact_manifest_refused: manifest hash must not be self-referential")
    problems = [row["artifact"] for row in rows if row["ok"] is not True]
    if problems:
        raise MainHeadInstallRefused("artifact_hash_mismatch: " + ", ".join(problems))
    return {"ok": True, "rows": rows}


class MainHeadVenvPromoter:
    """Build a verified main-HEAD venv target and atomically promote it."""

    def __init__(self, *, python_executable: str | None = None):
        self.python_executable = python_executable or sys.executable

    def apply(self, install_root: Path, artifact: MainHeadArtifact) -> tuple[str, ...]:
        verification = verify_artifact_files(artifact)
        root = install_root
        root.mkdir(parents=True, exist_ok=True)
        lock = InstallLock(root, MainHeadInstallRefused)
        with lock:
            target = root / (
                f"venv-main-{artifact.identity.commit[:12]}-"
                f"{artifact.artifact_manifest_sha256[:12]}"
            )
            actions: list[str] = []
            if not venv_target_ok(target):
                build_venv_target(
                    target,
                    python_executable=self.python_executable,
                    populate_wheelhouse=lambda wheelhouse: self._populate_wheelhouse(wheelhouse, artifact),
                    requirement=f"{PACKAGE_NAME}=={artifact.package_version}",
                )
                actions.append("build_verified_main_head_venv")
            else:
                actions.append("reuse_verified_main_head_venv_target")
            promote_and_write_state(
                root,
                target,
                lambda: self._write_main_head_state(root, target, artifact, verification),
            )
            actions.append("promote_verified_main_head_venv")
            actions.append("write_main_head_install_state")
            return tuple(actions)

    @staticmethod
    def _populate_wheelhouse(wheelhouse: Path, artifact: MainHeadArtifact) -> None:
        shutil.copy2(artifact.wheel_path, wheelhouse / artifact.wheel_name)
        for name, path in artifact.dependency_wheels.items():
            shutil.copy2(path, wheelhouse / name)
        verify_artifact_files(
            MainHeadArtifact(
                identity=artifact.identity,
                worktree=artifact.worktree,
                wheel_path=wheelhouse / artifact.wheel_name,
                wheel_name=artifact.wheel_name,
                wheel_sha256=artifact.wheel_sha256,
                package_version=artifact.package_version,
                build_source_sha256=artifact.build_source_sha256,
                artifact_manifest_sha256=artifact.artifact_manifest_sha256,
                dependency_wheels={name: wheelhouse / name for name in artifact.dependency_wheels},
                dependency_sha256=artifact.dependency_sha256,
            )
        )

    def _write_main_head_state(
        self,
        root: Path,
        target: Path,
        artifact: MainHeadArtifact,
        verification: Mapping[str, Any],
    ) -> None:
        manifest_path = root / f"main-head-artifact-{artifact.identity.commit[:12]}.json"
        manifest_payload = {
            **artifact.manifest(),
            "artifact_manifest_sha256": artifact.artifact_manifest_sha256,
            "verification": verification,
        }
        write_text_atomic(manifest_path, json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n")

        state_path = root / "install-state"
        lines = [
            "install_kind=main-head",
            f"track={TRACK}",
            f"source_remote={artifact.identity.remote}",
            f"source_branch={artifact.identity.branch}",
            f"source_commit={artifact.identity.commit}",
            f"git_source_sha256={artifact.identity.git_source_sha256}",
            f"build_source_sha256={artifact.build_source_sha256}",
            f"package_version={artifact.package_version}",
            f"app_wheel={artifact.wheel_name}",
            f"app_wheel_sha256={artifact.wheel_sha256}",
            f"artifact_manifest_sha256={artifact.artifact_manifest_sha256}",
            f"artifact_manifest_path={manifest_path}",
            "trust_model=verified-source-build-main-head",
            "signature=none",
            f"python_executable={self.python_executable}",
            f"venv_path={root / 'venv'}",
            f"venv_target={target}",
            f"timestamp={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        ]
        write_text_atomic(state_path, "\n".join(lines) + "\n")


def clean_main_install(
    *,
    repo_root: str | Path = ".",
    install_root: str | Path | None = None,
    remote: str = REMOTE,
    branch: str = BRANCH,
    fetch: bool = True,
    check_only: bool = False,
    build_wheel: BuildWheelFn = build_app_wheel_from_source,
    promoter: MainHeadVenvPromoter | None = None,
) -> CleanMainInstallResult:
    resolved = resolve_origin_main(repo_root, remote=remote, branch=branch, fetch=fetch)
    with tempfile.TemporaryDirectory(prefix="ce-main-head-artifact-") as tmp:
        artifact = build_main_head_artifact(resolved, work_root=tmp, build_wheel=build_wheel)
        try:
            verification = verify_artifact_files(artifact)
            artifact_summary = {
                "token": artifact.token,
                "package_version": artifact.package_version,
                "wheel_name": artifact.wheel_name,
                "wheel_sha256": artifact.wheel_sha256,
                "build_source_sha256": artifact.build_source_sha256,
                "artifact_manifest_sha256": artifact.artifact_manifest_sha256,
                "verification": verification,
                "trust_model": "verified-source-build-main-head",
                "signature": "none",
            }
            if check_only:
                return CleanMainInstallResult(
                    ok=True,
                    status="verified",
                    reason="main HEAD source and artifact hashes verified",
                    identity=resolved,
                    artifact=artifact_summary,
                    read_only=True,
                    actions=("resolve_origin_main", "build_verified_main_head_artifact", "verify_artifact_hashes"),
                )
            root = Path(install_root) if install_root is not None else _default_install_root()
            runner = promoter or MainHeadVenvPromoter()
            try:
                actions = runner.apply(root, artifact)
            except Exception as exc:
                return CleanMainInstallResult(
                    ok=False,
                    status="refuse",
                    reason="main HEAD install refused before promotion completed",
                    identity=resolved,
                    artifact=artifact_summary,
                    install_root=str(root),
                    problems=(f"promote_failed:{exc.__class__.__name__}:{exc}",),
                )
            return CleanMainInstallResult(
                ok=True,
                status="installed",
                reason="installed verified main HEAD artifact",
                identity=resolved,
                artifact=artifact_summary,
                install_root=str(root),
                actions=("resolve_origin_main", "build_verified_main_head_artifact", "verify_artifact_hashes", *actions),
            )
        finally:
            _remove_worktree(resolved, artifact.worktree)


def run_cli(args: Any) -> int:
    try:
        result = clean_main_install(
            repo_root=getattr(args, "repo_root", "."),
            install_root=getattr(args, "install_root", None),
            remote=getattr(args, "remote", REMOTE),
            branch=getattr(args, "branch", BRANCH),
            fetch=not bool(getattr(args, "no_fetch", False)),
            check_only=bool(getattr(args, "check", False)),
        )
    except MainHeadInstallRefused as exc:
        result = CleanMainInstallResult(
            ok=False,
            status="refuse",
            reason=str(exc),
            install_root=getattr(args, "install_root", None),
            read_only=bool(getattr(args, "check", False)),
            problems=(str(exc),),
        )
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_json(), indent=2, sort_keys=True))
    elif result.ok and result.status == "verified":
        token = result.artifact.get("token", "main@unknown")
        print(f"ce clean-main-install: verified {token}")
    elif result.ok:
        token = result.artifact.get("token", "main@unknown")
        print(f"ce clean-main-install: installed {token}")
    else:
        print(f"ERROR: ce clean-main-install refused: {result.reason}", file=sys.stderr)
    return 0 if result.ok else 1
