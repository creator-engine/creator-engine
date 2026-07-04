from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from creator_engine_validator.forge.authority_contexts import (
    AuthorityContextError,
    ValidationSandboxContext,
)
from creator_engine_validator.validation_sandbox import ValidationSandboxSpec, run_validation_sandbox


def _context(tmp_path: Path) -> ValidationSandboxContext:
    return ValidationSandboxContext.from_sandbox(tmp_path / "validation-sandbox")


def test_validation_sandbox_spec_refuses_credential_shaped_env_key(tmp_path: Path):
    with pytest.raises(ValueError, match="credential-bearing env keys: GH_TOKEN"):
        ValidationSandboxSpec(
            context=_context(tmp_path),
            command=(sys.executable, "-c", "print('nope')"),
            cwd=tmp_path,
            timeout_seconds=10,
            env={"PATH": "/usr/bin:/bin", "GH_TOKEN": "secret"},
        )


def test_validation_sandbox_spec_refuses_git_credential_helper_env_value(tmp_path: Path):
    with pytest.raises(ValueError, match="credential-bearing env keys: GIT_CONFIG_KEY_0"):
        ValidationSandboxSpec(
            context=_context(tmp_path),
            command=(sys.executable, "-c", "print('nope')"),
            cwd=tmp_path,
            timeout_seconds=10,
            env={
                "PATH": "/usr/bin:/bin",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "credential.helper",
                "GIT_CONFIG_VALUE_0": "store",
            },
        )


def test_validation_sandbox_runner_revalidates_value_sensitive_env_before_exec(tmp_path: Path):
    spec = ValidationSandboxSpec(
        context=_context(tmp_path),
        command=(sys.executable, "-c", "print('nope')"),
        cwd=tmp_path,
        timeout_seconds=10,
        env={"PATH": "/usr/bin:/bin"},
    )
    object.__setattr__(
        spec,
        "env",
        {
            "PATH": "/usr/bin:/bin",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "credential.helper",
            "GIT_CONFIG_VALUE_0": "store",
        },
    )

    with pytest.raises(ValueError, match="credential-bearing env keys: GIT_CONFIG_KEY_0"):
        run_validation_sandbox(spec)


def test_validation_sandbox_context_refuses_egress(tmp_path: Path):
    context = _context(tmp_path)

    with pytest.raises(AuthorityContextError, match="defaults to no egress"):
        ValidationSandboxContext(
            env=context.env,
            home=context.home,
            xdg_config_home=context.xdg_config_home,
            egress_allowed=True,
        )


def test_validation_sandbox_spec_env_is_immutable_after_construction(tmp_path: Path):
    source_env = {"PATH": "/usr/bin:/bin", "PYTHONCOERCECLOCALE": "0"}
    spec = ValidationSandboxSpec(
        context=_context(tmp_path),
        command=(sys.executable, "-c", "import os; print(os.environ.get('GH_TOKEN', ''))"),
        cwd=tmp_path,
        timeout_seconds=10,
        env=source_env,
    )

    source_env["GH_TOKEN"] = "late-secret"
    with pytest.raises(TypeError):
        spec.env["GH_TOKEN"] = "late-secret"  # type: ignore[index]

    result = run_validation_sandbox(spec)

    assert result.rc == 0
    assert result.stdout == "\n"
    assert "GH_TOKEN" not in result.spec.env


def test_validation_sandbox_runner_child_receives_exact_allowlisted_env(tmp_path: Path):
    old_token = os.environ.get("GH_TOKEN")
    os.environ["GH_TOKEN"] = "ambient-secret"
    allowed_env = {
        "ONLY_ALLOWED": "yes",
        "PATH": "/usr/bin:/bin",
        "PYTHONCOERCECLOCALE": "0",
    }
    try:
        spec = ValidationSandboxSpec(
            context=_context(tmp_path),
            command=(
                sys.executable,
                "-c",
                "import json, os; print(json.dumps(dict(os.environ), sort_keys=True))",
            ),
            cwd=tmp_path,
            timeout_seconds=10,
            env=allowed_env,
        )

        result = run_validation_sandbox(spec)
    finally:
        if old_token is None:
            os.environ.pop("GH_TOKEN", None)
        else:
            os.environ["GH_TOKEN"] = old_token

    assert result.rc == 0
    assert json.loads(result.stdout) == allowed_env
    assert result.stderr == ""
    assert result.duration >= 0
    assert result.spec == spec
    assert result.spec.env_allowlist == tuple(allowed_env)
