"""Local PR preflight runner.

This module mirrors the repository's Validate workflow for a local PR worktree.
It validates committed ``<base>..HEAD`` state only; working-tree changes are
refused unless the caller explicitly opts into a noisy override.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

TOKEN_ENV_VARS = ("GH_TOKEN", "BAO_TOKEN", "OPENBAO_TOKEN", "CE_OVERWATCH_PAT")
WORK_CLASSES = ("tiny", "story", "feature", "epic")
DEFAULT_TEST_COMMAND = (
    f"{shlex.quote(sys.executable)} -m pytest -p no:cacheprovider "
    'validators/tests/ -m "not wheel_bake_gate" -q -n auto --dist loadgroup'
)
DECLARED_WORK_CLASS_PATTERN = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?Declared work class(?:\*\*)?\s*:\s*(?:\*\*)?\s*"
    r"`?([A-Za-z][A-Za-z0-9_-]*)`?\s*(?:<!--.*-->)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
PYTEST_FAILURE_PATTERN = re.compile(
    r"^(?:FAILED|ERROR)\s+([^\s]+(?:::[^\s]+)*)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class PreflightConfig:
    repo_root: Path
    base: str
    declared_work_class: str | None = None
    head_ref: str | None = None
    allow_dirty: bool = False
    test_command: str = DEFAULT_TEST_COMMAND


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class CheckDetail:
    name: str
    ok: bool
    detail: str


Runner = Callable[[Sequence[str], Path, Mapping[str, str] | None], CommandResult]


def default_runner(argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None) -> CommandResult:
    """Run a command without raising."""
    try:
        result = subprocess.run(
            list(argv),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError) as exc:
        return CommandResult(127, "", str(exc))
    return CommandResult(result.returncode, result.stdout, result.stderr)


def current_branch(repo_root: Path, runner: Runner = default_runner) -> str:
    result = runner(["git", "branch", "--show-current"], repo_root, None)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git branch --show-current failed")
    branch = result.stdout.strip()
    if not branch:
        raise RuntimeError("could not resolve current branch; pass --head-ref explicitly")
    return branch


def _print_streams(result: CommandResult, out: TextIO, err: TextIO) -> None:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n", file=out)
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=err)


def _run_checked(
    label: str,
    argv: Sequence[str],
    repo_root: Path,
    *,
    runner: Runner,
    env: Mapping[str, str] | None,
    out: TextIO,
    err: TextIO,
) -> None:
    print(f"==> {label}", file=out)
    result = runner(argv, repo_root, env)
    _print_streams(result, out, err)
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {result.returncode}")


def _git_capture(argv: Sequence[str], repo_root: Path, runner: Runner) -> str:
    result = runner(["git", *argv], repo_root, None)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"git {' '.join(argv)} failed"
        raise RuntimeError(detail)
    return result.stdout


def _git_capture_optional(argv: Sequence[str], repo_root: Path, runner: Runner) -> str:
    result = runner(["git", *argv], repo_root, None)
    if result.returncode != 0:
        return ""
    return result.stdout


def _repo_root(path: Path, runner: Runner) -> Path:
    result = runner(["git", "rev-parse", "--show-toplevel"], path, None)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "not inside a git worktree")
    return Path(result.stdout.strip()).resolve()


def _fetch_base(base: str, repo_root: Path, runner: Runner, out: TextIO, err: TextIO) -> None:
    remote_branch = None
    if base.startswith("origin/") and len(base.split("/", 1)[1]) > 0:
        remote_branch = base.split("/", 1)[1]
    elif "/" not in base and not _looks_like_sha(base):
        remote_branch = base

    if remote_branch is None:
        return

    result = runner(
        ["git", "fetch", "--no-tags", "--prune", "origin", f"+refs/heads/{remote_branch}:refs/remotes/origin/{remote_branch}"],
        repo_root,
        None,
    )
    _print_streams(result, out, err)
    if result.returncode != 0:
        raise RuntimeError(f"failed to fetch base branch {remote_branch!r}")


def _looks_like_sha(value: str) -> bool:
    return len(value) in (7, 40) and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _resolve_comparison_base(config: PreflightConfig, runner: Runner, out: TextIO, err: TextIO) -> str:
    print(f"==> Resolve live comparison base for {config.base}", file=out)
    _fetch_base(config.base, config.repo_root, runner, out, err)
    merge_base = _git_capture(["merge-base", config.base, "HEAD"], config.repo_root, runner).strip()
    if not merge_base:
        raise RuntimeError(f"could not derive merge-base for {config.base} and HEAD")
    print(f"Comparison base: {merge_base}", file=out)
    print(f"Committed diff command: git diff {merge_base}..HEAD", file=out)
    return merge_base


def _assert_clean_tree(config: PreflightConfig, runner: Runner, out: TextIO) -> None:
    status = _git_capture(["status", "--porcelain"], config.repo_root, runner)
    if not status.strip():
        return
    if config.allow_dirty:
        print(
            "WARNING: working tree is dirty; continuing because --allow-dirty was supplied. "
            "Preflight still validates committed base..HEAD state only.",
            file=out,
        )
        print(status, end="" if status.endswith("\n") else "\n", file=out)
        return
    raise RuntimeError(
        "working tree is dirty; commit/stash changes or rerun with --allow-dirty to validate committed state anyway"
    )


def _python_env(repo_root: Path, *, pytest: bool = False) -> dict[str, str]:
    env = dict(os.environ)
    pythonpath_parts = [str(repo_root / "validators")]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    if pytest:
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["TMPDIR"] = "/var/tmp"
        for key in TOKEN_ENV_VARS:
            env.pop(key, None)
    return env


def _extract_declared_work_classes(text: str) -> list[str]:
    return [match.group(1) for match in DECLARED_WORK_CLASS_PATTERN.finditer(text)]


def _changed_paths(repo_root: Path, base: str, runner: Runner) -> list[str]:
    stdout = _git_capture_optional(["diff", "--name-only", f"{base}..HEAD"], repo_root, runner)
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def _resolve_declared_work_class(
    config: PreflightConfig,
    comparison_base: str,
    runner: Runner,
) -> str:
    if config.declared_work_class:
        declared = config.declared_work_class
        if declared not in WORK_CLASSES:
            raise RuntimeError(
                f"declared work class {declared!r} is invalid; expected one of: {', '.join(WORK_CLASSES)}"
            )
        return declared

    from .checks.path_manifest_fidelity import MANIFEST_DIR, branch_slug

    if not config.head_ref:
        raise RuntimeError("could not resolve head ref for declared work class discovery")

    expected_slug = branch_slug(config.head_ref)
    changed = _changed_paths(config.repo_root, comparison_base, runner)
    carrier = f"{MANIFEST_DIR}/{expected_slug}.md"
    candidates: list[Path] = []
    if carrier in changed:
        candidates.append(config.repo_root / carrier)
    else:
        candidates.extend(config.repo_root / path for path in changed if path.endswith(".md"))

    found: list[tuple[Path, str]] = []
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        found.extend((path, value) for value in _extract_declared_work_classes(text))

    values = [value for _, value in found]
    if len(values) != 1:
        locations = ", ".join(str(path.relative_to(config.repo_root)) for path, _ in found) or "none"
        raise RuntimeError(
            "PR body/carrier must contain exactly one declared work class line: "
            "'- **Declared work class:** <tiny|story|feature|epic>' "
            f"(found {len(values)}; locations: {locations})"
        )
    declared = values[0]
    if declared not in WORK_CLASSES:
        raise RuntimeError(
            f"declared work class {declared!r} is invalid; expected one of: {', '.join(WORK_CLASSES)}"
        )
    return declared


def _test_command_argv(command: str) -> list[str]:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise RuntimeError(f"test command is not shell-parseable: {exc}") from exc
    if not argv:
        raise RuntimeError("test command must not be empty")
    return argv


def _failure_ids(result: CommandResult) -> set[str]:
    text = result.stdout + "\n" + result.stderr
    failures = {match.group(1) for match in PYTEST_FAILURE_PATTERN.finditer(text)}
    if result.returncode != 0 and not failures:
        failures.add(f"command_exit_{result.returncode}")
    return failures


def _run_baseline_diff_tests(
    config: PreflightConfig,
    comparison_base: str,
    *,
    runner: Runner,
    out: TextIO,
    err: TextIO,
) -> str:
    argv = _test_command_argv(config.test_command)
    with tempfile.TemporaryDirectory(prefix="ce-validate-pr-base-") as temp:
        base_worktree = Path(temp) / "base"
        add = runner(
            ["git", "worktree", "add", "--detach", str(base_worktree), comparison_base],
            config.repo_root,
            None,
        )
        _print_streams(add, out, err)
        if add.returncode != 0:
            raise RuntimeError(f"could not create baseline worktree for {comparison_base}")
        try:
            baseline = runner(argv, base_worktree, _python_env(base_worktree, pytest=True))
            _print_streams(baseline, out, err)
            head = runner(argv, config.repo_root, _python_env(config.repo_root, pytest=True))
            _print_streams(head, out, err)
        finally:
            remove = runner(["git", "worktree", "remove", "--force", str(base_worktree)], config.repo_root, None)
            _print_streams(remove, out, err)

    baseline_failures = _failure_ids(baseline)
    head_failures = _failure_ids(head)
    new_failures = sorted(head_failures - baseline_failures)
    if new_failures:
        preview = ", ".join(new_failures[:5])
        more = "" if len(new_failures) <= 5 else f" (+{len(new_failures) - 5} more)"
        raise RuntimeError(
            "baseline-diff test gate found new failure(s): "
            f"{preview}{more} (baseline={len(baseline_failures)}, head={len(head_failures)})"
        )
    return (
        "zero new failures "
        f"(baseline={len(baseline_failures)}, head={len(head_failures)}, command={config.test_command!r})"
    )


def _yaml_parse(paths: Sequence[Path], label: str, err: TextIO) -> None:
    import yaml

    errors: list[str] = []
    for path in paths:
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
            print(f"OK  {path}")
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            message = f"FAIL {path}: {exc}"
            errors.append(message)
            print(message, file=err)
    if errors:
        raise RuntimeError(f"{label} failed")


def _workflow_yaml_paths(repo_root: Path) -> list[Path]:
    return sorted((repo_root / ".github" / "workflows").glob("*.yml"))


def _artifact_yaml_paths(repo_root: Path) -> list[Path]:
    roots = ["schemas", "templates", "docs/contracts", "examples", "playbooks"]
    paths: list[Path] = []
    for root in roots:
        base = repo_root / root
        paths.extend(sorted(base.rglob("*.yml")))
        paths.extend(sorted(base.rglob("*.yaml")))
    return sorted(paths)


def _workflow_permissions_audit(repo_root: Path) -> None:
    import yaml

    workflow = repo_root / ".github" / "workflows" / "validate.yml"
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    write_found: list[str] = []

    def collect(obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "permissions":
                    if isinstance(value, dict):
                        for perm_key, perm_val in value.items():
                            if str(perm_val).lower() == "write":
                                write_found.append(f"{path}.{perm_key}: write")
                    elif isinstance(value, str) and value.lower() == "write":
                        write_found.append(f"{path}: write (all)")
                else:
                    collect(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                collect(item, f"{path}[{idx}]")

    collect(doc)
    if write_found:
        for finding in write_found:
            print(f"FAIL: write permission in YAML structure: {finding}")
        raise RuntimeError("workflow permissions audit failed")
    print(f"OK: declared permissions = {doc.get('permissions', {})}")
    print("OK: no write permissions found in YAML structure")


def _install_spec_signature_required(
    config: PreflightConfig,
    py: str,
    py_env: Mapping[str, str],
    *,
    runner: Runner,
    out: TextIO,
    err: TextIO,
) -> str:
    _run_checked(
        "Install-spec signature guard",
        [py, "-m", "creator_engine_validator", "scan-install-spec-signature", "."],
        config.repo_root,
        runner=runner,
        env=py_env,
        out=out,
        err=err,
    )
    return "install-spec signature scan passed"


def _run_check(name: str, func: Callable[[], str | None], out: TextIO, err: TextIO) -> CheckDetail:
    print(f"==> {name}", file=out)
    try:
        detail = func() or "ok"
    except Exception as exc:
        detail = str(exc)
        print(f"  FAIL {name}: {detail}", file=err)
        return CheckDetail(name=name, ok=False, detail=detail)
    print(f"  PASS {name}: {detail}", file=out)
    return CheckDetail(name=name, ok=True, detail=detail)


def _print_summary(checks: Sequence[CheckDetail], out: TextIO) -> None:
    ok = all(check.ok for check in checks)
    print(f"{'PASS' if ok else 'FAIL'}: PR preflight", file=out)
    for check in checks:
        print(f"  [{'PASS' if check.ok else 'FAIL'}] {check.name}: {check.detail}", file=out)


def run_preflight(
    config: PreflightConfig,
    *,
    runner: Runner = default_runner,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
) -> int:
    """Run the local PR preflight. Prints one final PASS/FAIL summary plus check detail."""
    checks: list[CheckDetail] = []
    try:
        repo_root = _repo_root(config.repo_root, runner)
        config = PreflightConfig(
            repo_root=repo_root,
            base=config.base,
            declared_work_class=config.declared_work_class,
            head_ref=config.head_ref or current_branch(repo_root, runner),
            allow_dirty=config.allow_dirty,
            test_command=config.test_command,
        )
    except Exception as exc:
        checks.append(CheckDetail(name="preflight setup", ok=False, detail=str(exc)))
        _print_summary(checks, out)
        print(f"FAIL: PR preflight failed: {exc}", file=err)
        return 1

    comparison_base: dict[str, str] = {}
    declared_work_class: dict[str, str] = {}
    py_env = _python_env(config.repo_root)
    py = sys.executable

    checks.append(
        _run_check(
            "clean worktree",
            lambda: (_assert_clean_tree(config, runner, out), "clean or explicitly allowed")[1],
            out,
            err,
        )
    )
    if not checks[-1].ok:
        _print_summary(checks, out)
        return 1
    checks.append(
        _run_check(
            "comparison base",
            lambda: comparison_base.setdefault("value", _resolve_comparison_base(config, runner, out, err)),
            out,
            err,
        )
    )
    if not checks[-1].ok:
        _print_summary(checks, out)
        return 1
    checks.append(
        _run_check(
            "declared work class",
            lambda: declared_work_class.setdefault(
                "value",
                _resolve_declared_work_class(config, comparison_base.get("value", config.base), runner),
            ),
            out,
            err,
        )
    )
    if not checks[-1].ok:
        _print_summary(checks, out)
        return 1
    checks.append(
        _run_check(
            "baseline-diff test command",
            lambda: _run_baseline_diff_tests(
                config,
                comparison_base["value"],
                runner=runner,
                out=out,
                err=err,
            ),
            out,
            err,
        )
    )
    if not checks[-1].ok:
        _print_summary(checks, out)
        return 1
    checks.append(
        _run_check(
            "Public-docs confidentiality scan (ce-ops# / internal refs, pre-push)",
            lambda: (
                _run_checked(
                    "Public-docs confidentiality scan (ce-ops# / internal refs, pre-push)",
                    [py, "-m", "creator_engine_validator", "scan-public-docs-confidentiality", "."],
                    config.repo_root,
                    runner=runner,
                    env=py_env,
                    out=out,
                    err=err,
                ),
                "no public-doc confidentiality leaks",
            )[1],
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "Install-spec signature guard",
            lambda: _install_spec_signature_required(
                config,
                py,
                py_env,
                runner=runner,
                out=out,
                err=err,
            ),
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "Support-corpus confidentiality intersection (ce ask product-lens allowlist)",
            lambda: (
                _run_checked(
                    "Support-corpus confidentiality intersection (ce ask product-lens allowlist)",
                    [py, "-m", "creator_engine_validator", "scan-support-corpus", "."],
                    config.repo_root,
                    runner=runner,
                    env=py_env,
                    out=out,
                    err=err,
                ),
                "support corpus is a subset of the confidentiality-clean surface",
            )[1],
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "YAML parse - workflow files",
            lambda: (_yaml_parse(_workflow_yaml_paths(config.repo_root), "workflow YAML parse", err), "valid YAML")[1],
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "YAML parse - schemas/templates/docs/contracts/examples/playbooks",
            lambda: (
                _yaml_parse(_artifact_yaml_paths(config.repo_root), "artifact YAML parse", err),
                "valid YAML",
            )[1],
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "Creator Engine validator - check-examples aggregate gate",
            lambda: (
                _run_checked(
                    "Creator Engine validator - check-examples aggregate gate",
                    [py, "-m", "creator_engine_validator", "check-examples"],
                    config.repo_root,
                    runner=runner,
                    env=py_env,
                    out=out,
                    err=err,
                ),
                "passed",
            )[1],
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "Creator Engine validator - well-formed examples",
            lambda: (
                _run_checked(
                    "Creator Engine validator - well-formed examples",
                    [py, "-m", "creator_engine_validator", "check", "examples/well-formed/"],
                    config.repo_root,
                    runner=runner,
                    env=py_env,
                    out=out,
                    err=err,
                ),
                "passed",
            )[1],
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "Creator Engine validator - ce_playbook_format gate",
            lambda: (
                _run_checked(
                    "Creator Engine validator - ce_playbook_format gate",
                    [py, "-m", "creator_engine_validator", "check", "playbooks/"],
                    config.repo_root,
                    runner=runner,
                    env=py_env,
                    out=out,
                    err=err,
                ),
                "passed",
            )[1],
            out,
            err,
        )
    )

    def malformed_gate() -> str:
        print("==> Creator Engine validator - malformed examples (expect failures)", file=out)
        malformed = runner(
            [py, "-m", "creator_engine_validator", "check", "examples/malformed/"],
            config.repo_root,
            py_env,
        )
        _print_streams(malformed, out, err)
        if malformed.returncode == 0:
            raise RuntimeError("malformed examples unexpectedly passed")
        print("OK: malformed examples correctly rejected", file=out)
        return "malformed examples rejected"

    checks.append(_run_check("Creator Engine validator - malformed examples", malformed_gate, out, err))
    checks.append(
        _run_check(
            "Creator Engine validator - list checks",
            lambda: (
                _run_checked(
                    "Creator Engine validator - list checks",
                    [py, "-m", "creator_engine_validator", "--list-checks"],
                    config.repo_root,
                    runner=runner,
                    env=py_env,
                    out=out,
                    err=err,
                ),
                "passed",
            )[1],
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "Creator Engine validator - brain drift check",
            lambda: (
                _run_checked(
                    "Creator Engine validator - brain drift check",
                    [
                        py,
                        "-m",
                        "creator_engine_validator.ce_cli",
                        "brain",
                        "verify",
                        "--drift",
                        "--state-root",
                        ".ce/state",
                    ],
                    config.repo_root,
                    runner=runner,
                    env=py_env,
                    out=out,
                    err=err,
                ),
                "passed",
            )[1],
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "Creator Engine validator - work-sizing floor PR-diff gate",
            lambda: (
                _run_checked(
                    "Creator Engine validator - work-sizing floor PR-diff gate",
                    [
                        py,
                        "-m",
                        "creator_engine_validator",
                        "verify-work-sizing-floor",
                        "--base",
                        comparison_base["value"],
                        "--declared-work-class",
                        declared_work_class["value"],
                        ".",
                    ],
                    config.repo_root,
                    runner=runner,
                    env=py_env,
                    out=out,
                    err=err,
                ),
                "passed",
            )[1],
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "Creator Engine validator - path-manifest PR-diff gate",
            lambda: (
                _run_checked(
                    "Creator Engine validator - path-manifest PR-diff gate",
                    [
                        py,
                        "-m",
                        "creator_engine_validator",
                        "verify-path-manifest",
                        "--base",
                        comparison_base["value"],
                        "--manifest-dir",
                        ".ce/pr-manifests",
                        "--head-ref",
                        config.head_ref or "",
                        "--require-carrier",
                    ],
                    config.repo_root,
                    runner=runner,
                    env=py_env,
                    out=out,
                    err=err,
                ),
                "passed",
            )[1],
            out,
            err,
        )
    )
    checks.append(
        _run_check(
            "Workflow permissions audit",
            lambda: (_workflow_permissions_audit(config.repo_root), "no write permissions")[1],
            out,
            err,
        )
    )

    _print_summary(checks, out)
    return 0 if all(check.ok for check in checks) else 1


def build_parser(prog: str = "ce validate-pr") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description="run the local PR preflight gate set")
    parser.add_argument("--repo-root", default=".", help="PR worktree root (default: current directory)")
    parser.add_argument("--base", default="origin/main", help="base branch/ref to fetch and merge-base against (default: origin/main)")
    parser.add_argument(
        "--declared-work-class",
        choices=WORK_CLASSES,
        help="declared PR work class; when omitted, read exactly one declared-work-class line from the PR carrier/body",
    )
    parser.add_argument("--head-ref", default=None, help="PR head branch name for carrier slug (default: current branch)")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="continue despite working-tree changes; committed base..HEAD state is still what gets validated",
    )
    parser.add_argument(
        "--test-command",
        default=DEFAULT_TEST_COMMAND,
        help=f"test command to compare at base and HEAD (default: {DEFAULT_TEST_COMMAND})",
    )
    return parser


def run_cli(args: argparse.Namespace) -> int:
    return run_preflight(
        PreflightConfig(
            repo_root=Path(args.repo_root),
            base=args.base,
            declared_work_class=args.declared_work_class,
            head_ref=args.head_ref,
            allow_dirty=args.allow_dirty,
            test_command=args.test_command,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(build_parser().parse_args(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
