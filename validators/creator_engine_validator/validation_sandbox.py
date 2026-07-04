"""Typed subprocess seam for validation runs with explicit environment allowlists."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .forge.authority_contexts import ValidationSandboxContext, require_no_credential_env


@dataclass(frozen=True)
class ValidationSandboxSpec:
    """Complete declaration for one validation subprocess."""

    context: ValidationSandboxContext
    command: Sequence[str]
    cwd: Path
    timeout_seconds: float
    env: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.context, ValidationSandboxContext):
            raise TypeError("ValidationSandboxSpec requires ValidationSandboxContext")
        env = dict(self.env)
        require_no_credential_env(env, context_name="ValidationSandboxSpec")
        object.__setattr__(self, "command", tuple(self.command))
        object.__setattr__(self, "cwd", Path(self.cwd))
        object.__setattr__(self, "env", MappingProxyType(env))

    @property
    def env_allowlist(self) -> tuple[str, ...]:
        return tuple(self.env.keys())


@dataclass(frozen=True)
class ValidationSandboxResult:
    """Subprocess result plus the spec that produced it for audit."""

    rc: int
    stdout: str
    stderr: str
    duration: float
    spec: ValidationSandboxSpec

    @property
    def returncode(self) -> int:
        return self.rc


def run_validation_sandbox(spec: ValidationSandboxSpec) -> ValidationSandboxResult:
    """Execute a validation sandbox with env exactly equal to the spec allowlist."""

    require_no_credential_env(spec.env, context_name="ValidationSandboxSpec")
    start = time.monotonic()
    try:
        completed = subprocess.run(
            list(spec.command),
            cwd=spec.cwd,
            env=dict(spec.env),
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return ValidationSandboxResult(
            1,
            _process_output(getattr(exc, "stdout", "")),
            str(exc),
            time.monotonic() - start,
            spec,
        )
    return ValidationSandboxResult(
        completed.returncode,
        completed.stdout,
        completed.stderr,
        time.monotonic() - start,
        spec,
    )


def _process_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


__all__ = ["ValidationSandboxResult", "ValidationSandboxSpec", "run_validation_sandbox"]
