"""Local conveyor harvest preparation helpers.

Slice 1 intentionally stops at local preparation and validation. It does not
push, open PRs, approve, invoke docker, or run any daemon/autonomy loop.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

from .carrier_gen import CarrierSpec, WrittenCarriers, write_carriers
from .checks.path_manifest_fidelity import branch_slug
from .forge.authority_contexts import ValidationSandboxContext
from .harvest_evidence import HarvestEvidenceAssessment, parse_harvest_evidence
from .validation_sandbox import ValidationSandboxSpec, run_validation_sandbox


OLD_WORK_CLASSES = frozenset({"tiny", "story", "feature", "epic"})
DEFAULT_VALIDATE_COMMAND = (
    sys.executable,
    "-m",
    "creator_engine_validator.ce_cli",
    "validate-pr",
)
DECLARED_WORK_CLASS_LINE = re.compile(
    r"^\s*[-*]?\s*(?:\*\*)?Declared work class(?:\*\*)?\s*:\s*`?[A-Za-z][A-Za-z0-9_-]*`?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ConveyorCommandResult:
    """Command result shape used by the conveyor's injected runners."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


class ConveyorGitPhase(str, Enum):
    """Minimal conveyor-local git authority phases.

    TODO(ce-410): replace this local seam with authority_contexts.py
    TransportCredentialContext/LocalGitContext once that module lands.
    """

    LOCAL = "local-git"
    TRANSPORT = "transport-authority"


GitRunner = Callable[[Sequence[str], Path, Mapping[str, str]], ConveyorCommandResult | tuple[int, str, str]]
ValidateRunner = Callable[[Sequence[str], Path, Mapping[str, str] | None], ConveyorCommandResult | tuple[int, str, str]]


_MINIMAL_GIT_PATH = "/usr/bin:/bin"
_BASE_GIT_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
    "PATH": _MINIMAL_GIT_PATH,
}


@dataclass(frozen=True)
class ConveyorHarvestSpec:
    """Inputs for deterministic local harvest prep."""

    worktree_path: Path
    branch: str
    base: str = "origin/main"
    issue: str = "ce-conveyor"
    title: str = "Conveyor harvest prep"
    kind: str = "changed"
    scope: str = "conveyor harvest"
    body: str = "- Prepared conveyor harvest carrier."
    declared_work_class: str = "story"
    carrier_date: str | None = None
    rebase: bool = True
    refresh_base: bool = True
    validate_command: tuple[str, ...] = DEFAULT_VALIDATE_COMMAND
    allow_dirty_validation: bool = True
    commit_carriers_before_validation: bool = False
    # Data-only evidence supplied by the controller's harvest seal.  No
    # implicit default: callers must explicitly claim non-test-bearing work.
    harvest_evidence: Mapping[str, object] | None = None


@dataclass(frozen=True)
class ConveyorHarvestResult:
    """Structured ready/not-ready result for local conveyor harvest prep."""

    ready: bool
    reasons: tuple[str, ...]
    worktree_path: Path
    branch: str
    branch_slug: str
    base: str
    removed_artifacts: tuple[str, ...]
    changelog_path: Path | None = None
    manifest_path: Path | None = None
    validation_returncode: int | None = None
    validation_stdout: str = ""
    validation_stderr: str = ""
    harvest_evidence: HarvestEvidenceAssessment | None = None


@dataclass(frozen=True)
class ConveyorLandingReason:
    """Machine-readable not-ready reason for bundle landing."""

    code: str
    message: str
    detail: str = ""


@dataclass(frozen=True)
class ConveyorBundleLandingResult:
    """Structured ready/not-ready result for host-side bundle landing."""

    ready: bool
    reasons: tuple[ConveyorLandingReason, ...]
    bundle_path: Path
    branch: str
    branch_slug: str
    base_ref: str
    head_sha: str | None = None
    ahead: int | None = None
    behind: int | None = None
    verify_stdout: str = ""
    verify_stderr: str = ""


def prepare_harvest(
    spec: ConveyorHarvestSpec,
    *,
    git_runner: GitRunner | None = None,
    validate_runner: ValidateRunner | None = None,
) -> ConveyorHarvestResult:
    """Prepare a local harvested worktree and run the injected validate-pr seam."""

    root = Path(spec.worktree_path)
    slug = branch_slug(spec.branch)
    reasons: list[str] = []
    removed: list[str] = []
    written: WrittenCarriers | None = None
    validation: ConveyorCommandResult | None = None

    evidence_assessment = parse_harvest_evidence(spec.harvest_evidence)

    if spec.declared_work_class not in OLD_WORK_CLASSES:
        return _result(
            spec,
            slug,
            ready=False,
            reasons=(f"declared_work_class must use old names: {', '.join(sorted(OLD_WORK_CLASSES))}",),
            removed_artifacts=(),
        )

    if not root.exists():
        return _result(
            spec,
            slug,
            ready=False,
            reasons=(f"worktree does not exist: {root}",),
            removed_artifacts=(),
        )

    if not evidence_assessment.ready:
        return _result(
            spec,
            slug,
            ready=False,
            reasons=(
                "harvest evidence not ready: "
                f"{evidence_assessment.reason_code}: {evidence_assessment.message}",
            ),
            removed_artifacts=(),
            harvest_evidence=evidence_assessment,
        )

    runner = git_runner or _default_git_runner
    validator = validate_runner or _default_validate_runner
    local_git_env = git_env_for_phase(ConveyorGitPhase.LOCAL)
    transport_git_env = git_env_for_phase(ConveyorGitPhase.TRANSPORT)

    removed.extend(_remove_validator_artifacts(root))

    current = _git(runner, ["branch", "--show-current"], root, env=local_git_env)
    if current.returncode != 0:
        reasons.append(_command_reason("git branch --show-current", current))
    else:
        current_branch = current.stdout.strip()
        if not current_branch:
            reasons.append("worktree is detached; cannot ensure branch slug")
        elif current_branch == slug:
            pass
        elif current_branch == spec.branch:
            renamed = _git(runner, ["branch", "-m", slug], root, env=local_git_env)
            if renamed.returncode != 0:
                reasons.append(_command_reason(f"git branch -m {slug}", renamed))
        else:
            reasons.append(
                f"current branch {current_branch!r} is neither requested branch {spec.branch!r} nor slug {slug!r}"
            )

    if not reasons and spec.refresh_base:
        fetched = _fetch_base(runner, root, spec.base, env=transport_git_env)
        if fetched is not None and fetched.returncode != 0:
            reasons.append(_command_reason(f"git {' '.join(_fetch_args(spec.base))}", fetched))

    if not reasons:
        if spec.rebase:
            rebased = _git(runner, ["rebase", spec.base], root, env=local_git_env)
            if rebased.returncode != 0:
                reasons.append(_command_reason(f"git rebase {spec.base}", rebased))
        else:
            verified = _git(runner, ["merge-base", "--is-ancestor", spec.base, "HEAD"], root, env=local_git_env)
            if verified.returncode != 0:
                reasons.append(f"base {spec.base!r} is not an ancestor of HEAD")

    if not reasons:
        try:
            written = write_carriers(
                root,
                _carrier_spec(spec),
                git_runner=_carrier_git_runner(runner, env=local_git_env),
            )
            _write_declared_work_class(written.manifest_path, spec.declared_work_class)
            if spec.commit_carriers_before_validation:
                committed = _commit_carriers_before_validation(runner, root, slug, written, env=local_git_env)
                if committed is not None and committed.returncode != 0:
                    reasons.append(_command_reason("git commit generated carriers", committed))
        except Exception as exc:  # write_carriers converts git failures to RuntimeError.
            reasons.append(f"carrier regeneration failed: {exc}")

    if not reasons:
        validation = _run_validation(validator, spec, slug, root)
        removed.extend(_remove_validator_artifacts(root))
        if validation.returncode != 0:
            reasons.append(_command_reason("validate-pr", validation))

    return _result(
        spec,
        slug,
        ready=not reasons,
        reasons=tuple(reasons),
        removed_artifacts=tuple(dict.fromkeys(removed)),
        written=written,
        validation=validation,
        harvest_evidence=evidence_assessment,
    )


def land_bundle(
    bundle_path: str | Path,
    branch_name: str,
    base_ref: str = "origin/main",
    *,
    repo_path: str | Path | None = None,
    git_runner: GitRunner | None = None,
) -> ConveyorBundleLandingResult:
    """Import a git bundle branch onto a fresh base, stopping before harvest prep.

    This slice-S helper is intentionally local-only: it verifies and fetches the
    supplied bundle, switches to the imported carrier-stem branch, rebases onto
    ``base_ref``, and reports the landed head. It does not push, open PRs,
    invoke docker/ssh, or call :func:`prepare_harvest`.
    """

    root = Path.cwd() if repo_path is None else Path(repo_path)
    bundle = Path(bundle_path)
    slug = branch_slug(branch_name)
    runner = git_runner or _default_git_runner
    local_git_env = git_env_for_phase(ConveyorGitPhase.LOCAL)
    transport_git_env = git_env_for_phase(ConveyorGitPhase.TRANSPORT)
    reasons: list[ConveyorLandingReason] = []
    verify = ConveyorCommandResult(0, "", "")

    if branch_name != slug:
        return _landing_result(
            bundle,
            branch_name,
            slug,
            base_ref,
            ready=False,
            reasons=(
                ConveyorLandingReason(
                    "branch_stem_mismatch",
                    "branch_name must already be the carrier stem produced by branch_slug",
                    f"branch_name={branch_name!r} branch_slug={slug!r}",
                ),
            ),
        )

    verify = _git(runner, ["bundle", "verify", str(bundle)], root, env=local_git_env)
    if verify.returncode != 0:
        reasons.append(
            ConveyorLandingReason(
                "bundle_verify_failed",
                "git bundle verify rejected the bundle",
                _command_detail(verify),
            )
        )
        return _landing_result(
            bundle,
            branch_name,
            slug,
            base_ref,
            ready=False,
            reasons=tuple(reasons),
            verify=verify,
        )

    fetched_branch = _git(runner, ["fetch", str(bundle), f"{branch_name}:{branch_name}"], root, env=local_git_env)
    if fetched_branch.returncode != 0:
        reasons.append(
            ConveyorLandingReason(
                "bundle_fetch_failed",
                "could not fetch the bundle branch into the carrier-stem branch",
                _command_detail(fetched_branch),
            )
        )

    if not reasons:
        fetched_base = _fetch_base(runner, root, base_ref, env=transport_git_env)
        if fetched_base is not None and fetched_base.returncode != 0:
            reasons.append(
                ConveyorLandingReason(
                    "base_fetch_failed",
                    "could not refresh the requested base ref",
                    _command_detail(fetched_base),
                )
            )

    if not reasons:
        switched = _git(runner, ["switch", branch_name], root, env=local_git_env)
        if switched.returncode != 0:
            reasons.append(
                ConveyorLandingReason(
                    "branch_switch_failed",
                    "could not switch to the imported carrier-stem branch",
                    _command_detail(switched),
                )
            )

    if not reasons:
        rebased = _git(runner, ["rebase", base_ref], root, env=local_git_env)
        if rebased.returncode != 0:
            reasons.append(
                ConveyorLandingReason(
                    "base_rebase_failed",
                    "could not rebase the imported branch onto the requested base",
                    _command_detail(rebased),
                )
            )

    head_sha: str | None = None
    ahead: int | None = None
    behind: int | None = None
    if not reasons:
        head = _git(runner, ["rev-parse", "HEAD"], root, env=local_git_env)
        if head.returncode != 0:
            reasons.append(
                ConveyorLandingReason(
                    "head_resolve_failed",
                    "could not resolve landed branch HEAD",
                    _command_detail(head),
                )
            )
        else:
            head_sha = head.stdout.strip()

    if not reasons:
        counts = _git(runner, ["rev-list", "--left-right", "--count", f"{base_ref}...HEAD"], root, env=local_git_env)
        if counts.returncode != 0:
            reasons.append(
                ConveyorLandingReason(
                    "ahead_behind_failed",
                    "could not compute ahead/behind against base",
                    _command_detail(counts),
                )
            )
        else:
            try:
                behind_text, ahead_text = counts.stdout.split()[:2]
                behind = int(behind_text)
                ahead = int(ahead_text)
            except (ValueError, IndexError) as exc:
                reasons.append(
                    ConveyorLandingReason(
                        "ahead_behind_parse_failed",
                        "git rev-list returned an unexpected ahead/behind shape",
                        f"{counts.stdout.strip()!r}: {exc}",
                    )
                )

    if not reasons and behind not in (0, None):
        reasons.append(
            ConveyorLandingReason(
                "base_not_ancestor",
                "landed branch remains behind base after rebase",
                f"behind={behind} ahead={ahead}",
            )
        )

    return _landing_result(
        bundle,
        branch_name,
        slug,
        base_ref,
        ready=not reasons,
        reasons=tuple(reasons),
        verify=verify,
        head_sha=head_sha,
        ahead=ahead,
        behind=behind,
    )


def _carrier_spec(spec: ConveyorHarvestSpec) -> CarrierSpec:
    return CarrierSpec(
        head_ref=branch_slug(spec.branch),
        issue=spec.issue,
        title=spec.title,
        kind=spec.kind,
        scope=spec.scope,
        body=spec.body,
        date=spec.carrier_date or date.today().isoformat(),
        base=spec.base,
    )


def _remove_validator_artifacts(root: Path) -> tuple[str, ...]:
    validators = root / "validators"
    removed: list[str] = []
    build = validators / "build"
    if build.exists():
        shutil.rmtree(build)
        removed.append(str(build.relative_to(root)))
    if validators.exists():
        for egg_info in sorted(validators.glob("*.egg-info")):
            if egg_info.is_dir():
                shutil.rmtree(egg_info)
            else:
                egg_info.unlink()
            removed.append(str(egg_info.relative_to(root)))
    return tuple(removed)


def _write_declared_work_class(manifest_path: Path, work_class: str) -> None:
    text = manifest_path.read_text(encoding="utf-8")
    line = f"- **Declared work class:** {work_class}"
    kept = [existing for existing in text.splitlines() if not DECLARED_WORK_CLASS_LINE.match(existing)]
    if len(kept) > 1 and kept[0].startswith("# "):
        insert_at = 2 if kept[1] == "" else 1
        kept[insert_at:insert_at] = [line, ""]
    else:
        kept[0:0] = [line, ""]
    manifest_path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")


def _run_validation(
    runner: ValidateRunner,
    spec: ConveyorHarvestSpec,
    slug: str,
    root: Path,
) -> ConveyorCommandResult:
    command = [
        *spec.validate_command,
        "--repo-root",
        str(root),
        "--base",
        spec.base,
        "--declared-work-class",
        spec.declared_work_class,
        "--head-ref",
        slug,
    ]
    if spec.allow_dirty_validation:
        command.append("--allow-dirty")
    env = {"PYTHONPATH": str(root / "validators"), "TMPDIR": "/var/tmp", "PATH": _MINIMAL_GIT_PATH}
    sandbox = validation_sandbox_spec_from_command(command, root, env, timeout_seconds=600)
    return _coerce_result(runner(sandbox.command, sandbox.cwd, sandbox.env))


def validation_sandbox_spec_from_command(
    command: Sequence[str],
    cwd: Path,
    env: Mapping[str, str] | None,
    *,
    timeout_seconds: float,
) -> ValidationSandboxSpec:
    return ValidationSandboxSpec(
        context=_validation_sandbox_context(cwd),
        command=command,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        env={} if env is None else env,
    )


def _fetch_base(
    runner: GitRunner,
    root: Path,
    base: str,
    *,
    env: Mapping[str, str],
) -> ConveyorCommandResult | None:
    args = _fetch_args(base)
    if not args:
        return None
    return _git(runner, args, root, env=env)


def _fetch_args(base: str) -> list[str]:
    if base.count("/") >= 1:
        remote, ref = base.split("/", 1)
        if re.fullmatch(r"[A-Za-z0-9_.-]+", remote) and ref:
            return ["fetch", remote, ref]
    return []


def _carrier_git_runner(
    runner: GitRunner,
    *,
    env: Mapping[str, str],
) -> Callable[[Sequence[str], Path], tuple[int, str, str]]:
    def run(args: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        result = _git(runner, args, cwd, env=env)
        return result.returncode, result.stdout, result.stderr

    return run


def _commit_carriers_before_validation(
    runner: GitRunner,
    root: Path,
    slug: str,
    written: WrittenCarriers,
    *,
    env: Mapping[str, str],
) -> ConveyorCommandResult | None:
    rel_paths = tuple(_relative_to_root(root, path) for path in (written.changelog_path, written.manifest_path))
    added = _git(runner, ["add", "--", *rel_paths], root, env=env)
    if added.returncode != 0:
        return added
    staged = _git(runner, ["diff", "--cached", "--quiet", "--", *rel_paths], root, env=env)
    if staged.returncode == 0:
        return None
    if staged.returncode != 1:
        return staged
    return _git(
        runner,
        ["commit", "-m", f"Add conveyor harvest carriers for {slug}", "--", *rel_paths],
        root,
        env=env,
    )


def _relative_to_root(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _git(
    runner: GitRunner,
    args: Sequence[str],
    cwd: Path,
    *,
    env: Mapping[str, str],
) -> ConveyorCommandResult:
    return _coerce_result(runner(args, cwd, env))


def _coerce_result(result: ConveyorCommandResult | tuple[int, str, str]) -> ConveyorCommandResult:
    if isinstance(result, ConveyorCommandResult):
        return result
    return ConveyorCommandResult(result[0], result[1], result[2])


def git_env_for_phase(phase: ConveyorGitPhase) -> dict[str, str]:
    if phase in (ConveyorGitPhase.LOCAL, ConveyorGitPhase.TRANSPORT):
        return dict(_BASE_GIT_ENV)
    raise ValueError(f"unsupported conveyor git phase: {phase}")


def _default_git_runner(args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> ConveyorCommandResult:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=dict(env),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return ConveyorCommandResult(1, "", str(exc))
    return ConveyorCommandResult(completed.returncode, completed.stdout, completed.stderr)


def _default_validate_runner(
    args: Sequence[str],
    cwd: Path,
    env: Mapping[str, str] | None,
) -> ConveyorCommandResult:
    result = run_validation_sandbox(
        ValidationSandboxSpec(
            context=_validation_sandbox_context(cwd),
            command=args,
            cwd=cwd,
            timeout_seconds=600,
            env={} if env is None else env,
        )
    )
    return ConveyorCommandResult(result.rc, result.stdout, result.stderr)


def _validation_sandbox_context(root: Path) -> ValidationSandboxContext:
    sandbox_root = Path("/var/tmp") / "creator-engine-validation-sandbox" / branch_slug(str(root.resolve()))
    return ValidationSandboxContext.from_sandbox(sandbox_root)


def _command_reason(label: str, result: ConveyorCommandResult) -> str:
    return f"{label} failed: {_command_detail(result)}"


def _command_detail(result: ConveyorCommandResult) -> str:
    return result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"


def _landing_result(
    bundle: Path,
    branch: str,
    slug: str,
    base_ref: str,
    *,
    ready: bool,
    reasons: tuple[ConveyorLandingReason, ...],
    verify: ConveyorCommandResult | None = None,
    head_sha: str | None = None,
    ahead: int | None = None,
    behind: int | None = None,
) -> ConveyorBundleLandingResult:
    return ConveyorBundleLandingResult(
        ready=ready,
        reasons=reasons,
        bundle_path=bundle,
        branch=branch,
        branch_slug=slug,
        base_ref=base_ref,
        head_sha=head_sha,
        ahead=ahead,
        behind=behind,
        verify_stdout="" if verify is None else verify.stdout,
        verify_stderr="" if verify is None else verify.stderr,
    )


def _result(
    spec: ConveyorHarvestSpec,
    slug: str,
    *,
    ready: bool,
    reasons: tuple[str, ...],
    removed_artifacts: tuple[str, ...],
    written: WrittenCarriers | None = None,
    validation: ConveyorCommandResult | None = None,
    harvest_evidence: HarvestEvidenceAssessment | None = None,
) -> ConveyorHarvestResult:
    return ConveyorHarvestResult(
        ready=ready,
        reasons=reasons,
        worktree_path=Path(spec.worktree_path),
        branch=spec.branch,
        branch_slug=slug,
        base=spec.base,
        removed_artifacts=removed_artifacts,
        changelog_path=None if written is None else written.changelog_path,
        manifest_path=None if written is None else written.manifest_path,
        validation_returncode=None if validation is None else validation.returncode,
        validation_stdout="" if validation is None else validation.stdout,
        validation_stderr="" if validation is None else validation.stderr,
        harvest_evidence=harvest_evidence,
    )


__all__ = [
    "ConveyorGitPhase",
    "ConveyorBundleLandingResult",
    "ConveyorCommandResult",
    "ConveyorHarvestResult",
    "ConveyorHarvestSpec",
    "ConveyorLandingReason",
    "GitRunner",
    "land_bundle",
    "git_env_for_phase",
    "prepare_harvest",
    "validation_sandbox_spec_from_command",
]
