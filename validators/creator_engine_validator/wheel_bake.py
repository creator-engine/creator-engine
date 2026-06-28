"""Build helper for ADR-0010 Phase-A first-party app-wheel baking.

This module contains only the reusable source-to-wheel primitive. The CI job
that will call it is intentionally out of scope for F-wheel-1.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


APP_WHEEL_GLOB = "creator_engine_validator-*.whl"
# Fixed, version-independent timestamp for reproducible wheel zip members.
SOURCE_DATE_EPOCH = "946684800"


class WheelBakeError(RuntimeError):
    """The first-party wheel could not be built or identified deterministically."""


@dataclass(frozen=True)
class WheelManifest:
    wheel_name: str
    sha256: str
    version: str
    source_commit: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project_version(validators_dir: Path) -> str:
    pyproject = validators_dir / "pyproject.toml"
    if not pyproject.is_file():
        raise WheelBakeError(f"missing validator pyproject: {pyproject}")
    version = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise WheelBakeError(f"missing project.version in {pyproject}")
    return version


def _source_commit(repo_root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
        raise WheelBakeError(f"cannot resolve source commit: {exc}") from exc
    commit = proc.stdout.strip().lower()
    if proc.returncode != 0 or len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise WheelBakeError(f"cannot resolve source commit for {repo_root}: {detail}")
    return commit


def _clean_build_artifacts(validators_dir: Path) -> None:
    for rel in ("build", "creator_engine_validator.egg-info"):
        path = validators_dir / rel
        if path.exists():
            shutil.rmtree(path)


def _stage_build_source(validators_dir: Path, build_dir: Path) -> Path:
    staged = build_dir / "source"
    if staged.exists():
        shutil.rmtree(staged)
    staged.mkdir(parents=True, exist_ok=True)
    shutil.copy2(validators_dir / "pyproject.toml", staged / "pyproject.toml")
    readme = validators_dir / "README.md"
    if readme.is_file():
        shutil.copy2(readme, staged / "README.md")
    shutil.copytree(
        validators_dir / "creator_engine_validator",
        staged / "creator_engine_validator",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return staged


def _build_wheel(validators_dir: Path, out_dir: Path, *, build_dir: Path | None = None) -> None:
    env = os.environ.copy()
    env["PIP_NO_INDEX"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONNOUSERSITE"] = "1"
    env["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    build_source = validators_dir
    if build_dir is None:
        _clean_build_artifacts(validators_dir)
    else:
        build_source = _stage_build_source(validators_dir, build_dir)
    for stale_wheel in out_dir.glob(APP_WHEEL_GLOB):
        stale_wheel.unlink()
    cmd = [
        sys.executable,
        "-m",
        "build",
        "--wheel",
        "--no-isolation",
        "--outdir",
        str(out_dir),
        str(build_source),
    ]
    try:
        try:
            proc = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise WheelBakeError(f"wheel build failed to start: {exc}") from exc
        if proc.returncode != 0:
            raise WheelBakeError(
                "wheel build failed: "
                + " ".join(cmd)
                + f"\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )
    finally:
        if build_dir is None:
            _clean_build_artifacts(validators_dir)
        else:
            shutil.rmtree(build_source, ignore_errors=True)


def build_app_wheel_from_source(
    repo_root: Path | str,
    out_dir: Path | str,
    *,
    build_dir: Path | str | None = None,
) -> WheelManifest:
    """Build the first-party validator wheel from checkout source into ``out_dir``.

    The digest is always recomputed from the freshly built wheel. The caller gets
    metadata only; updating ``SHA256SUMS`` or committing artifacts belongs to the
    later bake job, not this helper. ``build_dir`` stages an isolated source copy
    for backend build artifacts, so stale checkout-local ``validators/build``
    state cannot influence the wheel.
    """
    root = Path(repo_root).resolve()
    validators_dir = root / "validators"
    if not validators_dir.is_dir():
        raise WheelBakeError(f"missing validator source directory: {validators_dir}")
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    isolated_build = Path(build_dir).resolve() if build_dir is not None else None
    if isolated_build is not None:
        isolated_build.mkdir(parents=True, exist_ok=True)

    version = _project_version(validators_dir)
    source_commit = _source_commit(root)
    _build_wheel(validators_dir, out, build_dir=isolated_build)

    wheels = sorted(out.glob(APP_WHEEL_GLOB))
    if len(wheels) != 1:
        names = [wheel.name for wheel in wheels]
        raise WheelBakeError(f"expected exactly one app wheel in {out}, found {names}")
    wheel = wheels[0]
    return WheelManifest(
        wheel_name=wheel.name,
        sha256=_sha256(wheel),
        version=version,
        source_commit=source_commit,
    )
