"""Detection-only validation of a representative change composed with main.

Every validation attempt is made from a newly-created, owned worktree.  The
default strategy creates a real, deterministic merge commit from the two
immutable input commits, then runs ``ce validate-pr`` against that exact
committed pairing.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


GREEN = "GREEN"
RED_DETERMINISTIC = "RED_FIRST_TRY_THEN_RETRY_ALSO_RED"
RED_FLAKE = "RED_FIRST_TRY_THEN_GREEN"
MERGE_CONFLICT = "MERGE_CONFLICT"
MERGE_ABORT = "MERGE_ABORT"
VALIDATOR_ABORT = "VALIDATOR_ABORT"

_SHA_RE = re.compile(r"[0-9a-fA-F]{40}\Z")
_MAX_OUTPUT = 4096
_MAX_PATH = 4096
_ALLOWED_REQUEST_KEYS = frozenset({"main_tip_sha", "representative_pr"})
_ALLOWED_PR_KEYS = frozenset({"number", "head_sha"})
_REDACTIONS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)((?:token|password|secret|api[_-]?key)\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"(?:gh[opusr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,})"),
)


@dataclass(frozen=True)
class MergeSimulation:
    """The result of constructing one committed composition."""

    status: str
    merge_base: str | None = None
    tree_ref: str | None = None
    repo_path: str | None = None


@dataclass(frozen=True)
class ValidationAttempt:
    """A validator verdict and its bounded, redacted output."""

    green: bool
    output: str = ""


@dataclass(frozen=True)
class CompositionProbeResult:
    outcome: str
    main_tip_sha: str
    pr_number: int
    pr_head_sha: str
    merge_base: str | None
    validation_attempt_count: int
    validation_output: str
    incident_record: dict[str, object] | None = None
    error: str | None = None
    incident_sink_error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


ValidatorFn = Callable[[str, str], object]
MergeStrategy = Callable[[str, str, str, str], object]
IncidentSink = Callable[[Mapping[str, object]], None]


def probe_composition(
    main_tip_sha: str,
    representative_pr: Mapping[str, object],
    *,
    validator_fn: ValidatorFn | None = None,
    merge_strategy: MergeStrategy | None = None,
    tmp_dir: str | Path | None = None,
    incident_sink: IncidentSink | None = None,
) -> CompositionProbeResult:
    """Classify one immutable PR head composed with one immutable main tip.

    A red result is retried once from a separately owned worktree.  The
    optional incident sink is an injected capability: JSON input cannot choose
    a path, and sink failure never changes a deterministic-red verdict.
    """

    main_sha, pr_number, head_sha = _validate_inputs(main_tip_sha, representative_pr)
    temp_parent = _validate_temp_parent(tmp_dir)
    _validate_optional_callable(validator_fn, "validator_fn")
    _validate_optional_callable(merge_strategy, "merge_strategy")
    _validate_optional_callable(incident_sink, "incident_sink")
    repo_path = str(Path.cwd())
    merge = merge_strategy or _default_merge_strategy
    validate = validator_fn or _default_validator
    first_red: ValidationAttempt | None = None

    for attempt_number in (1, 2):
        owned_root = Path(tempfile.mkdtemp(prefix="ce-composition-probe-", dir=temp_parent))
        attempt_repo = owned_root / "repo"
        simulation = MergeSimulation("abort")
        try:
            try:
                simulation = _coerce_merge_result(
                    merge(repo_path, main_sha, head_sha, str(attempt_repo))
                )
            except Exception as exc:
                return _result(
                    MERGE_ABORT,
                    main_sha,
                    pr_number,
                    head_sha,
                    simulation,
                    attempt_number - 1,
                    "",
                    error=_safe_error("merge setup failed", exc),
                )

            if simulation.status == "conflict":
                outcome = MERGE_CONFLICT if attempt_number == 1 else MERGE_ABORT
                return _result(
                    outcome,
                    main_sha,
                    pr_number,
                    head_sha,
                    simulation,
                    attempt_number - 1,
                    first_red.output if first_red else "",
                    error=None if attempt_number == 1 else "retry composition conflicted",
                )
            if simulation.status != "clean" or not simulation.tree_ref:
                return _result(
                    MERGE_ABORT,
                    main_sha,
                    pr_number,
                    head_sha,
                    simulation,
                    attempt_number - 1,
                    first_red.output if first_red else "",
                    error="composition setup aborted",
                )

            try:
                verdict = _coerce_validation_result(validate(str(attempt_repo), simulation.tree_ref))
            except Exception as exc:
                return _result(
                    VALIDATOR_ABORT,
                    main_sha,
                    pr_number,
                    head_sha,
                    simulation,
                    attempt_number,
                    first_red.output if first_red else "",
                    error=_safe_error("validator failed", exc),
                )

            if verdict.green:
                return _result(
                    GREEN if attempt_number == 1 else RED_FLAKE,
                    main_sha,
                    pr_number,
                    head_sha,
                    simulation,
                    attempt_number,
                    verdict.output,
                )
            if attempt_number == 1:
                first_red = verdict
                continue

            record = _incident_record(
                main_sha, pr_number, head_sha, simulation.merge_base, verdict.output
            )
            sink_error = None
            if incident_sink is not None:
                try:
                    incident_sink(record)
                except Exception as exc:
                    sink_error = _safe_error("incident sink failed", exc)
            return _result(
                RED_DETERMINISTIC,
                main_sha,
                pr_number,
                head_sha,
                simulation,
                2,
                verdict.output,
                incident=record,
                incident_sink_error=sink_error,
            )
        finally:
            # Remove only the child allocated by this attempt.  Never register
            # or delete a caller-provided temporary parent or a strategy-
            # supplied path.
            _git(repo_path, "worktree", "remove", "--force", str(attempt_repo), check=False)
            shutil.rmtree(owned_root, ignore_errors=True)

    raise AssertionError("unreachable")


def _result(
    outcome: str,
    main_tip_sha: str,
    pr_number: int,
    head_sha: str,
    simulation: MergeSimulation,
    attempts: int,
    output: str,
    incident: dict[str, object] | None = None,
    *,
    error: str | None = None,
    incident_sink_error: str | None = None,
) -> CompositionProbeResult:
    return CompositionProbeResult(
        outcome=outcome,
        main_tip_sha=main_tip_sha,
        pr_number=pr_number,
        pr_head_sha=head_sha,
        merge_base=simulation.merge_base,
        validation_attempt_count=attempts,
        validation_output=_sanitize_output(output),
        incident_record=incident,
        error=_sanitize_output(error) if error else None,
        incident_sink_error=_sanitize_output(incident_sink_error) if incident_sink_error else None,
    )


def _validate_inputs(
    main_tip_sha: object, representative_pr: object
) -> tuple[str, int, str]:
    main_sha = _immutable_sha(main_tip_sha, "main_tip_sha")
    if not isinstance(representative_pr, Mapping):
        raise ValueError("representative_pr must be an object")
    if set(representative_pr) - _ALLOWED_PR_KEYS:
        raise ValueError("representative_pr contains unsupported fields")
    number = representative_pr.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ValueError("representative_pr.number must be a positive integer")
    head_sha = _immutable_sha(representative_pr.get("head_sha"), "representative_pr.head_sha")
    return main_sha, number, head_sha


def _immutable_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be an immutable 40-hex SHA")
    return value.lower()


def _validate_temp_parent(value: str | Path | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, (str, Path)):
        raise ValueError("tmp_dir must be a filesystem path")
    text = os.fspath(value)
    if not text or len(text) > _MAX_PATH or "\x00" in text:
        raise ValueError("tmp_dir is invalid")
    parent = Path(text)
    if not parent.is_dir():
        raise ValueError("tmp_dir must name an existing directory")
    return text


def _validate_optional_callable(value: object, label: str) -> None:
    if value is not None and not callable(value):
        raise ValueError(f"{label} must be callable")


def _coerce_merge_result(value: object) -> MergeSimulation:
    if isinstance(value, MergeSimulation):
        result = value
    elif isinstance(value, Mapping):
        result = MergeSimulation(
            status=_bounded_string(value.get("status", "abort"), "merge status"),
            merge_base=_optional_sha(value.get("merge_base")),
            tree_ref=_optional_sha(value.get("tree_ref")),
        )
    elif isinstance(value, tuple) and value:
        result = MergeSimulation(
            status=_bounded_string(value[0], "merge status"),
            merge_base=_optional_sha(value[1]) if len(value) > 1 else None,
            tree_ref=_optional_sha(value[2]) if len(value) > 2 else None,
        )
    else:
        return MergeSimulation("abort")
    if result.status not in {"clean", "conflict", "abort"}:
        return MergeSimulation("abort", merge_base=result.merge_base)
    tree_ref = _optional_sha(result.tree_ref)
    merge_base = _optional_sha(result.merge_base)
    return MergeSimulation(result.status, merge_base=merge_base, tree_ref=tree_ref)


def _coerce_validation_result(value: object) -> ValidationAttempt:
    if isinstance(value, ValidationAttempt):
        return ValidationAttempt(value.green, _sanitize_output(value.output))
    if isinstance(value, bool):
        return ValidationAttempt(value)
    if isinstance(value, Mapping):
        output = value.get("output", "")
        if not isinstance(output, str):
            raise TypeError("validator output must be a string")
        return ValidationAttempt(bool(value.get("green")), _sanitize_output(output))
    if isinstance(value, tuple) and value:
        output = value[1] if len(value) > 1 else ""
        if not isinstance(output, str):
            raise TypeError("validator output must be a string")
        return ValidationAttempt(bool(value[0]), _sanitize_output(output))
    raise TypeError("validator_fn must return bool, ValidationAttempt, mapping, or tuple")


def _bounded_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise ValueError(f"{label} is invalid")
    return value


def _optional_sha(value: object) -> str | None:
    if value is None:
        return None
    return _immutable_sha(value, "composition SHA")


def _default_merge_strategy(
    repo_path: str, main_tip_sha: str, head_sha: str, tmp_dir: str
) -> MergeSimulation:
    """Create a hook-free, unsigned merge commit from the exact input SHAs."""

    merge_base = _git(repo_path, "merge-base", main_tip_sha, head_sha).stdout.strip()
    add = _git(repo_path, "worktree", "add", "--detach", tmp_dir, main_tip_sha, check=False)
    if add.returncode != 0:
        return MergeSimulation("abort", merge_base=merge_base)
    identity = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Creator Engine Composition Probe",
        "GIT_AUTHOR_EMAIL": "composition-probe@creator-engine.invalid",
        "GIT_COMMITTER_NAME": "Creator Engine Composition Probe",
        "GIT_COMMITTER_EMAIL": "composition-probe@creator-engine.invalid",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
    }
    merged = _git(
        tmp_dir,
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "commit.gpgSign=false",
        "merge",
        "--no-ff",
        "--no-edit",
        "--no-gpg-sign",
        head_sha,
        check=False,
        env=identity,
    )
    if merged.returncode != 0:
        unresolved = _git(tmp_dir, "diff", "--name-only", "--diff-filter=U", check=False)
        _git(tmp_dir, "merge", "--abort", check=False)
        status = "conflict" if unresolved.stdout.strip() else "abort"
        return MergeSimulation(status, merge_base=merge_base)
    commit_sha = _git(tmp_dir, "rev-parse", "HEAD").stdout.strip()
    parents = _git(tmp_dir, "show", "-s", "--format=%P", commit_sha).stdout.split()
    if parents != [main_tip_sha, head_sha]:
        return MergeSimulation("abort", merge_base=merge_base)
    return MergeSimulation("clean", merge_base=merge_base, tree_ref=commit_sha)


def _git(
    repo_path: str,
    *args: str,
    check: bool = True,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=check,
        text=True,
        capture_output=True,
        env=env,
    )


def _default_validator(repo_path: str, tree_ref: str) -> ValidationAttempt:
    """Validate the committed composition against its exact first parent."""

    expected = _immutable_sha(tree_ref, "tree_ref")
    actual = _git(repo_path, "rev-parse", "HEAD").stdout.strip().lower()
    if actual != expected:
        raise RuntimeError("composition worktree HEAD does not match the prepared commit")
    base = _git(repo_path, "rev-parse", f"{expected}^1").stdout.strip().lower()
    base = _immutable_sha(base, "composition base")
    argv = ["ce", "validate-pr", "--base", base]
    carrier = _single_carrier_slug(repo_path, base)
    if carrier is not None:
        argv.extend(["--head-ref", carrier])
    verdict = _run_validator_bounded(argv, repo_path)
    after = _git(repo_path, "rev-parse", "HEAD").stdout.strip().lower()
    if after != expected:
        raise RuntimeError("validator mutated the prepared composition commit")
    return verdict


def _single_carrier_slug(repo_path: str, base: str) -> str | None:
    changed = _git(repo_path, "diff", "--name-only", "--diff-filter=A", f"{base}..HEAD")
    carriers = [
        Path(line).stem
        for line in changed.stdout.splitlines()
        if line.startswith(".ce/pr-manifests/") and line.endswith(".md")
    ]
    return carriers[0] if len(carriers) == 1 else None


def _run_validator_bounded(argv: Sequence[str], repo_path: str) -> ValidationAttempt:
    process = subprocess.Popen(
        list(argv),
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    chunks = bytearray()
    assert process.stdout is not None
    while True:
        chunk = process.stdout.read(4096)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > _MAX_OUTPUT * 4:
            del chunks[: len(chunks) - (_MAX_OUTPUT * 4)]
    returncode = process.wait()
    output = chunks.decode("utf-8", errors="replace")
    return ValidationAttempt(returncode == 0, _sanitize_output(output))


def _sanitize_output(value: object) -> str:
    if not isinstance(value, str):
        return ""
    redacted = value
    for pattern in _REDACTIONS:
        if pattern.groups:
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    if len(redacted) > _MAX_OUTPUT:
        redacted = "[truncated]\n" + redacted[-_MAX_OUTPUT:]
    return redacted


def _safe_error(prefix: str, exc: Exception) -> str:
    return _sanitize_output(f"{prefix}: {type(exc).__name__}: {exc}")


def _incident_record(
    main_tip_sha: str,
    pr_number: int,
    head_sha: str,
    merge_base: str | None,
    validation_output: str,
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "class": "composition_probe_red_deterministic",
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evidence": {
            "main_tip_sha": main_tip_sha,
            "pr_number": pr_number,
            "pr_head_sha": head_sha,
            "merge_base": merge_base,
            "validation_output": _sanitize_output(validation_output),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Read one bounded-shape JSON request and print its bounded result."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="-", help="JSON file, or - for stdin")
    args = parser.parse_args(argv)
    if args.input == "-":
        payload = json.load(sys.stdin)
    else:
        if len(args.input) > _MAX_PATH or "\x00" in args.input:
            raise ValueError("input path is invalid")
        with open(args.input, encoding="utf-8") as input_file:
            payload = json.load(input_file)
    if not isinstance(payload, Mapping):
        raise ValueError("input must be a JSON object")
    if set(payload) - _ALLOWED_REQUEST_KEYS:
        raise ValueError("input contains unsupported fields")
    result = probe_composition(payload.get("main_tip_sha"), payload.get("representative_pr", {}))
    print(json.dumps(result.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
