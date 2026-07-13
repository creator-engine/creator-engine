"""Pinned Dockerfile image-build smoke checks for committed PR changes.

The module deliberately has no image publication capability.  It only runs
hadolint and Docker Buildx ``--check`` for Dockerfiles changed in ``base..HEAD``.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol, TextIO


HADOLINT_VERSION = "v2.14.0"
HADOLINT_URL = "https://github.com/hadolint/hadolint/releases/download/v2.14.0/hadolint-linux-x86_64"
HADOLINT_SHA256 = "6bf226944684f56c84dd014e8b979d27425c0148f61b3bd99bcc6f39e9dc5a47"
SMOKE_TIMEOUT_ENV = "CE_IMAGE_BUILD_SMOKE_TIMEOUT_SECONDS"
DEFAULT_SMOKE_TIMEOUT_SECONDS = 120.0
LOCAL_IMAGE_PREFIXES = ("creator-engine/",)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class Runner(Protocol):
    def __call__(
        self,
        argv: Sequence[str],
        cwd: Path,
        env: Mapping[str, str] | None,
        *,
        timeout: float | None = None,
    ) -> CommandResult: ...


def default_runner(
    argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None, *, timeout: float | None = None
) -> CommandResult:
    try:
        completed = subprocess.run(
            list(argv), cwd=cwd, env=dict(env) if env is not None else None, capture_output=True,
            text=True, check=False, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CommandResult(124, stdout, stderr or f"command timed out after {timeout:g}s")
    except (FileNotFoundError, OSError) as exc:
        return CommandResult(127, "", str(exc))
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _timeout_seconds() -> float:
    raw = os.environ.get(SMOKE_TIMEOUT_ENV, str(DEFAULT_SMOKE_TIMEOUT_SECONDS))
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{SMOKE_TIMEOUT_ENV} must be a positive number of seconds") from exc
    if value <= 0:
        raise RuntimeError(f"{SMOKE_TIMEOUT_ENV} must be a positive number of seconds")
    return value


def _safe_repository_path(repo_root: Path, raw_path: str) -> Path:
    posix = PurePosixPath(raw_path)
    if not raw_path or posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        raise RuntimeError(f"unsafe Dockerfile path from committed diff: {raw_path!r}")
    candidate = (repo_root / Path(*posix.parts)).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"Dockerfile path resolves outside repository: {raw_path!r}") from exc
    return candidate


def _is_deploy_dockerfile(raw_path: str) -> bool:
    parts = PurePosixPath(raw_path).parts
    return len(parts) >= 2 and parts[0] == "deploy" and parts[-1] == "Dockerfile"


def _changed_entries(base: str, repo_root: Path, runner: Runner) -> list[tuple[str, str]]:
    result = runner(["git", "diff", "--name-status", "-z", f"{base}..HEAD"], repo_root, None)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git diff --name-status failed"
        raise RuntimeError(detail)
    tokens = result.stdout.split("\0")
    if tokens and tokens[-1] == "":
        tokens.pop()
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            raise RuntimeError("malformed empty git diff status")
        if status[0] in {"R", "C"}:
            if index + 1 >= len(tokens):
                raise RuntimeError("malformed rename/copy entry from git diff")
            index += 1  # old path is not present in HEAD and must never be built.
            path = tokens[index]
            index += 1
        else:
            if index >= len(tokens):
                raise RuntimeError("malformed path entry from git diff")
            path = tokens[index]
            index += 1
        entries.append((status[0], path))
    return entries


def select_changed_dockerfiles(base: str, repo_root: Path, runner: Runner = default_runner) -> tuple[Path, ...]:
    """Return sorted, unique, existing Dockerfiles changed in committed ``base..HEAD``."""
    selected: set[Path] = set()
    for status, raw_path in _changed_entries(base, repo_root, runner):
        if not _is_deploy_dockerfile(raw_path):
            continue
        path = _safe_repository_path(repo_root, raw_path)
        if status == "D":
            continue
        if not path.is_file():
            raise RuntimeError(f"selected Dockerfile is absent or not a regular file: {raw_path}")
        selected.add(path)
    return tuple(sorted(selected, key=lambda path: path.relative_to(repo_root).as_posix()))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_linux_x86_64() -> None:
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("hadolint smoke tier requires Linux x86_64; refusing an unverifiable/wrong-architecture binary")


def verify_hadolint(path: Path) -> Path:
    _require_linux_x86_64()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f"hadolint executable is unavailable: {path}")
    actual = _sha256(path)
    if actual != HADOLINT_SHA256:
        raise RuntimeError(f"hadolint bytes are not the required pinned artifact: expected {HADOLINT_SHA256}, got {actual}")
    return path


def provision_hadolint(destination: Path, *, opener=urllib.request.urlopen) -> Path:
    """Download only the pinned CI artifact, hash it, then make it executable."""
    _require_linux_x86_64()
    try:
        with opener(HADOLINT_URL, timeout=_timeout_seconds()) as response:
            payload = response.read()
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(f"could not download pinned hadolint {HADOLINT_VERSION}: {exc}") from exc
    actual = hashlib.sha256(payload).hexdigest()
    if actual != HADOLINT_SHA256:
        raise RuntimeError(f"refusing hadolint download with wrong SHA-256: expected {HADOLINT_SHA256}, got {actual}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        handle.write(payload)
        temp_path = Path(handle.name)
    temp_path.chmod(0o755)
    temp_path.replace(destination)
    return verify_hadolint(destination)


def _resolve_hadolint(*, provision: bool, hadolint_path: str | None) -> Path:
    if hadolint_path:
        return verify_hadolint(Path(hadolint_path).resolve())
    existing = shutil.which("hadolint")
    if existing:
        return verify_hadolint(Path(existing).resolve())
    if provision:
        return provision_hadolint(Path(tempfile.gettempdir()) / f"hadolint-{HADOLINT_VERSION}")
    raise RuntimeError(
        "hadolint is required for changed deploy Dockerfiles; install the pinned v2.14.0 artifact "
        f"with SHA-256 {HADOLINT_SHA256} or run this tier in CI"
    )


def _local_base_exemption(path: Path) -> str | None:
    """Return a local prefix for literal or same-file-default ``FROM`` bases.

    This is intentionally limited to single-pass ``ARG NAME=default`` values in
    the same Dockerfile. It does not implement nested substitutions or BuildKit
    multi-stage ARG scoping; unresolved variables therefore receive no exemption.
    """
    arg_defaults: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts and parts[0].upper() == "ARG" and len(parts) >= 2 and "=" in parts[1]:
            name, value = parts[1].split("=", 1)
            if name and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                    value = value[1:-1]
                arg_defaults[name] = value
            continue
        if not parts or parts[0].upper() != "FROM":
            continue
        image_parts = parts[1:]
        while image_parts and image_parts[0].startswith("--"):
            image_parts.pop(0)
        if not image_parts:
            continue
        image = image_parts[0]
        variable = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)", image)
        if variable is not None:
            image = arg_defaults.get(variable.group(1) or variable.group(2), image)
        for prefix in LOCAL_IMAGE_PREFIXES:
            if image.startswith(prefix):
                return prefix
    return None


def _run_phase(label: str, argv: Sequence[str], repo_root: Path, runner: Runner, out: TextIO) -> None:
    print(f"==> image smoke {label}: {' '.join(argv)}", file=out)
    result = runner(argv, repo_root, dict(os.environ), timeout=_timeout_seconds())
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n", file=out)
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=out)
    if result.returncode == 124:
        raise RuntimeError(f"image smoke {label} timed out after {_timeout_seconds():g}s")
    if result.returncode != 0:
        raise RuntimeError(f"image smoke {label} failed with exit code {result.returncode}")


def run_image_build_smoke(
    base: str,
    repo_root: Path,
    *,
    runner: Runner = default_runner,
    out: TextIO = sys.stdout,
    provision: bool = False,
    hadolint_path: str | None = None,
) -> str:
    """Run no-op-or-fail-closed smoke checks and return a concise check detail."""
    files = select_changed_dockerfiles(base, repo_root, runner)
    if not files:
        return "no-op: no changed deploy/**/Dockerfile in committed comparison range"
    hadolint = _resolve_hadolint(provision=provision, hadolint_path=hadolint_path)
    buildx_available = False
    for path in files:
        relative = path.relative_to(repo_root).as_posix()
        _run_phase(f"hadolint {relative}", [str(hadolint), "--failure-threshold", "error", relative], repo_root, runner, out)
        local_prefix = _local_base_exemption(path)
        if local_prefix is not None:
            print(
                f"==> image smoke Buildx exemption {relative}: FROM base matches local prefix {local_prefix!r}; "
                "hadolint completed and Docker Buildx --check is intentionally skipped",
                file=out,
            )
            continue
        if not buildx_available:
            _run_phase("Docker Buildx availability", ["docker", "buildx", "version"], repo_root, runner, out)
            buildx_available = True
        _run_phase(
            f"Docker Buildx --check {relative}",
            ["docker", "buildx", "build", "--check", "--progress=plain", "-f", relative, str(repo_root)],
            repo_root,
            runner,
            out,
        )
    return f"passed for {len(files)} changed Dockerfile(s); hadolint {HADOLINT_VERSION} SHA-256 verified"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="run pinned Dockerfile image-build smoke checks")
    parser.add_argument("--base", required=True, help="committed comparison base")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--provision-hadolint", action="store_true", help="CI-only download of the pinned artifact")
    parser.add_argument("--hadolint-path", help="explicit already-downloaded hadolint path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        detail = run_image_build_smoke(
            args.base, Path(args.repo_root).resolve(), provision=args.provision_hadolint, hadolint_path=args.hadolint_path
        )
    except RuntimeError as exc:
        print(f"FAIL: image build smoke: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: image build smoke: {detail}")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through module CLI
    raise SystemExit(main())
