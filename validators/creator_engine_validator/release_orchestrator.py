"""Release orchestrator for autonomous release (Phase A3, stage-to-seam).

Chains the Phase-A staging steps into one fail-closed sequence:

    preflight -> bump (A1) -> changelog (A2) -> release-stage -> packet

The output is a fully-staged, signature-shaped artifact: the same placeholder
signature mirror :mod:`.release_publish` already produces. Nothing here signs,
publishes, commits, or accepts a signature.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .release_bump import (
    BumpResult,
    ReleaseBumpError,
    SEMVER_RE,
    bump_release_version,
    next_version,
    version_from_tag,
)
from .release_changelog import (
    ChangelogResult,
    ReleaseChangelogError,
    aggregate_changelog,
)
from .release_publish import (
    PLACEHOLDER_SIGNATURE,
    ReleasePublishError,
    ReleaseStageResult,
    SIGNING_KEY_ID,
    stage_signed_release,
)

INTENDED_PUBLIC_ANCHOR = "ce-root-v1"
_PARTS = ("major", "minor", "patch")
_VERSION_ASSIGNMENT_RE = re.compile(r'^__version__ = "([^"]+)"$', re.MULTILINE)
_DEFAULT_RELEASE_TAG_TEST_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-p",
    "no:cacheprovider",
    "validators/tests/",
    "-m",
    "not wheel_bake_gate",
    "-q",
    "-n",
    "auto",
    "--dist",
    "loadgroup",
)


class ReleaseOrchestrationError(RuntimeError):
    """Orchestration refused before producing a staged artifact (fail-closed)."""


@dataclass(frozen=True)
class ValidatePrResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class PreflightResult:
    requested_version: str
    head_sha: str
    clean_head: bool
    validate_pr: ValidatePrResult


@dataclass(frozen=True)
class RatificationPacket:
    """Pointers and hashes the Operator needs at the offline signing seam."""

    version: str
    build_git_sha: str
    wheel_sha256: str
    sha256s_sha256: str
    canonical_spec_sha256: str
    signing_key_id: str
    intended_public_anchor: str
    signature_placeholder: str
    signing_command: str
    canonical_path: str
    manifest_path: str
    signing_instructions_path: str
    github_release_body: str


@dataclass(frozen=True)
class OrchestrationResult:
    version: str
    preflight: PreflightResult
    bump: BumpResult
    changelog: ChangelogResult
    stage: ReleaseStageResult
    packet: RatificationPacket
    changelog_out: Path | None
    github_out: Path | None


ValidatePrRunner = Callable[[Path], int | subprocess.CompletedProcess[str] | ValidatePrResult]
StageReleaseFn = Callable[..., ReleaseStageResult]


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _head_sha(repo_root: Path) -> str:
    proc = _git(repo_root, "rev-parse", "--verify", "HEAD")
    sha = proc.stdout.strip().lower()
    if proc.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise ReleaseOrchestrationError(f"cannot resolve checkout HEAD for preflight: {detail}")
    return sha


def _assert_clean_head(repo_root: Path) -> None:
    proc = _git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise ReleaseOrchestrationError(f"cannot inspect checkout cleanliness: {detail}")
    dirty = [line for line in proc.stdout.splitlines() if line.strip()]
    if dirty:
        preview = "; ".join(dirty[:5])
        if len(dirty) > 5:
            preview += f"; ... ({len(dirty)} total)"
        raise ReleaseOrchestrationError(
            f"checkout must be clean before release orchestration; dirty paths: {preview}"
        )


def _current_source_version(repo_root: Path) -> str:
    version_py = repo_root / "validators" / "creator_engine_validator" / "version.py"
    if not version_py.is_file():
        raise ReleaseOrchestrationError(f"missing canonical version source: {version_py}")
    match = _VERSION_ASSIGNMENT_RE.search(version_py.read_text(encoding="utf-8"))
    if match is None:
        raise ReleaseOrchestrationError(f"no __version__ assignment found in {version_py}")
    return match.group(1)


def _core_tuple(version: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(version.strip())
    if not match:
        raise ReleaseOrchestrationError(f"version {version!r} is not valid semver")
    core = match.group("core") if "core" in match.groupdict() else version.split("-", 1)[0].split("+", 1)[0]
    major, minor, patch = core.split(".")
    return int(major), int(minor), int(patch)


def _latest_release_tag_version(repo_root: Path) -> str | None:
    proc = _git(repo_root, "tag", "--list", "release/v*", "--sort=-creatordate")
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        tag = line.strip()
        if not tag:
            continue
        try:
            return version_from_tag(tag)
        except ReleaseBumpError:
            continue
    return None


def _resolve_requested_version(
    *,
    repo_root: Path,
    tag: str | None,
    version: str | None,
    part: str | None,
) -> str:
    provided = [name for name, val in (("tag", tag), ("version", version), ("part", part)) if val]
    if len(provided) != 1:
        raise ReleaseOrchestrationError(
            f"provide exactly one of tag/version/part; got {provided or 'none'}"
        )
    if tag is not None:
        return version_from_tag(tag)
    if version is not None:
        cleaned = version.strip()
        if not SEMVER_RE.fullmatch(cleaned):
            raise ReleaseOrchestrationError(f"version {version!r} is not valid semver")
        return cleaned
    if part not in _PARTS:
        raise ReleaseOrchestrationError(f"invalid part {part!r}; expected one of {_PARTS}")
    current = _current_source_version(repo_root)
    latest = _latest_release_tag_version(repo_root)
    baseline = latest if latest is not None and _core_tuple(latest) > _core_tuple(current) else current
    return next_version(baseline, part)


def _default_validate_pr_runner(
    repo_root: Path,
    *,
    preflight_head_ref: str | None,
    preflight_declared_work_class: str | None,
) -> ValidatePrResult:
    command = (
        sys.executable,
        "-m",
        "creator_engine_validator.ce_cli",
        "validate-pr",
        "--repo-root",
        str(repo_root),
    )
    if preflight_head_ref:
        command += ("--head-ref", preflight_head_ref)
    if preflight_declared_work_class:
        command += ("--declared-work-class", preflight_declared_work_class)
    proc = subprocess.run(command, check=False, capture_output=True, text=True)
    return ValidatePrResult(command=command, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def _default_release_tag_runner(repo_root: Path) -> ValidatePrResult:
    proc = subprocess.run(
        _DEFAULT_RELEASE_TAG_TEST_COMMAND,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return ValidatePrResult(
        command=_DEFAULT_RELEASE_TAG_TEST_COMMAND,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _coerce_validate_pr_result(
    raw: int | subprocess.CompletedProcess[str] | ValidatePrResult,
    *,
    default_command: tuple[str, ...],
) -> ValidatePrResult:
    if isinstance(raw, ValidatePrResult):
        return raw
    if isinstance(raw, int):
        return ValidatePrResult(command=default_command, returncode=raw)
    args = tuple(str(part) for part in raw.args) if isinstance(raw.args, (list, tuple)) else (str(raw.args),)
    return ValidatePrResult(
        command=args,
        returncode=raw.returncode,
        stdout=raw.stdout or "",
        stderr=raw.stderr or "",
    )


def _run_preflight(
    *,
    repo_root: Path,
    requested_version: str,
    require_clean_head: bool,
    validate_pr_runner: ValidatePrRunner | None,
    preflight_mode: str,
    preflight_head_ref: str | None,
    preflight_declared_work_class: str | None,
) -> PreflightResult:
    head = _head_sha(repo_root)
    if require_clean_head:
        _assert_clean_head(repo_root)
    if preflight_mode not in {"validate-pr", "release-tag"}:
        raise ReleaseOrchestrationError(
            f"invalid release preflight mode {preflight_mode!r}; expected 'validate-pr' or 'release-tag'"
        )
    if validate_pr_runner is not None:
        default_command = ("ce", "validate-pr", "--repo-root", str(repo_root))
        validate_pr = _coerce_validate_pr_result(
            validate_pr_runner(repo_root),
            default_command=default_command,
        )
    elif preflight_mode == "release-tag":
        validate_pr = _default_release_tag_runner(repo_root)
    else:
        validate_pr = _default_validate_pr_runner(
            repo_root,
            preflight_head_ref=preflight_head_ref,
            preflight_declared_work_class=preflight_declared_work_class,
        )
    if validate_pr.returncode != 0:
        detail = (validate_pr.stderr or validate_pr.stdout).strip()
        suffix = f": {detail}" if detail else ""
        raise ReleaseOrchestrationError(
            f"release preflight failed with exit {validate_pr.returncode}{suffix}"
        )
    return PreflightResult(
        requested_version=requested_version,
        head_sha=head,
        clean_head=require_clean_head,
        validate_pr=validate_pr,
    )


def orchestrate_release(
    *,
    repo_root: Path | str,
    out: Path | str,
    tag: str | None = None,
    version: str | None = None,
    part: str | None = None,
    signing_key_id: str = SIGNING_KEY_ID,
    changelog_out: Path | str | None = None,
    github_out: Path | str | None = None,
    force: bool = False,
    dry_run: bool = False,
    require_clean_head: bool = True,
    preflight_mode: str = "validate-pr",
    preflight_head_ref: str | None = None,
    preflight_declared_work_class: str | None = None,
    validate_pr_runner: ValidatePrRunner | None = None,
    stage_release: StageReleaseFn | None = None,
    build_wheel=None,
    verify_parity=None,
) -> OrchestrationResult:
    """Run preflight -> bump -> changelog -> stage, returning the packet.

    Version resolution accepts exactly one of ``tag``, ``version``, or ``part``.
    The preflight checks the checkout HEAD and runs ``ce validate-pr`` before
    any staged version mutation. ``stage_release`` is injectable for tests, but
    defaults to the existing :func:`release_publish.stage_signed_release` seam.
    """
    root = Path(repo_root).resolve()
    requested_version = _resolve_requested_version(
        repo_root=root,
        tag=tag,
        version=version,
        part=part,
    )
    preflight = _run_preflight(
        repo_root=root,
        requested_version=requested_version,
        require_clean_head=require_clean_head,
        validate_pr_runner=validate_pr_runner,
        preflight_mode=preflight_mode,
        preflight_head_ref=preflight_head_ref,
        preflight_declared_work_class=preflight_declared_work_class,
    )

    try:
        if tag is not None:
            bump = bump_release_version(repo_root=root, tag=tag)
        elif part is not None:
            bump = bump_release_version(repo_root=root, part=part)
        else:
            bump = bump_release_version(repo_root=root, tag=f"release/v{version}")
    except ReleaseBumpError as exc:
        raise ReleaseOrchestrationError(f"version bump failed: {exc}") from exc
    if bump.version != requested_version:
        raise ReleaseOrchestrationError(
            f"resolved version {requested_version!r} disagrees with bumped version {bump.version!r}"
        )

    try:
        changelog = aggregate_changelog(repo_root=root, version=bump.version)
    except ReleaseChangelogError as exc:
        raise ReleaseOrchestrationError(f"changelog aggregation failed: {exc}") from exc

    written_changelog: Path | None = None
    if changelog_out is not None:
        written_changelog = Path(changelog_out).resolve()
        written_changelog.parent.mkdir(parents=True, exist_ok=True)
        written_changelog.write_text(changelog.notes, encoding="utf-8")

    written_github: Path | None = None
    if github_out is not None:
        written_github = Path(github_out).resolve()
        written_github.parent.mkdir(parents=True, exist_ok=True)
        written_github.write_text(changelog.github_body, encoding="utf-8")

    stage_fn = stage_release or stage_signed_release
    stage_kwargs = dict(
        repo_root=root,
        version=bump.version,
        out=out,
        signing_key_id=signing_key_id,
        force=force,
        dry_run=dry_run,
    )
    if build_wheel is not None:
        stage_kwargs["build_wheel"] = build_wheel
    if verify_parity is not None:
        stage_kwargs["verify_parity"] = verify_parity
    try:
        stage = stage_fn(**stage_kwargs)
    except ReleasePublishError as exc:
        raise ReleaseOrchestrationError(f"release-stage failed: {exc}") from exc

    if stage.version != bump.version:
        raise ReleaseOrchestrationError(
            f"staged version {stage.version!r} disagrees with bumped version {bump.version!r}"
        )
    if stage.signature_placeholder != PLACEHOLDER_SIGNATURE:
        raise ReleaseOrchestrationError("release-stage did not preserve the placeholder signature seam")

    out_dir = stage.out_dir
    packet = RatificationPacket(
        version=stage.version,
        build_git_sha=stage.build_git_sha,
        wheel_sha256=stage.wheel_sha256,
        sha256s_sha256=stage.sha256s_sha256,
        canonical_spec_sha256=stage.canonical_spec_sha256,
        signing_key_id=signing_key_id,
        intended_public_anchor=INTENDED_PUBLIC_ANCHOR,
        signature_placeholder=stage.signature_placeholder,
        signing_command=stage.signing_command,
        canonical_path=str(out_dir / "llms-install.canonical"),
        manifest_path=str(out_dir / "release-stage-manifest.yml"),
        signing_instructions_path=str(out_dir / "SIGNING-INSTRUCTIONS.md"),
        github_release_body=changelog.github_body,
    )

    return OrchestrationResult(
        version=bump.version,
        preflight=preflight,
        bump=bump,
        changelog=changelog,
        stage=stage,
        packet=packet,
        changelog_out=written_changelog,
        github_out=written_github,
    )
