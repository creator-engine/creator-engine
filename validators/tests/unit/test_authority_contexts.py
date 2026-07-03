"""Unit tests for forge authority context value objects."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import get_type_hints

import pytest

from creator_engine_validator.forge import authority_contexts as contexts


def test_gh_runner_with_token_never_mutates_process_global_env(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    captured_env = {}
    started = threading.Event()
    observed: list[str | None] = []

    def fake_run(**kwargs):
        captured_env.update(kwargs["env"])
        started.set()
        time.sleep(0.1)
        return subprocess.CompletedProcess(kwargs["args"], 0, stdout="{}", stderr="")

    def fake_subprocess_run(
        args,
        *,
        check,
        capture_output,
        text,
        input,
        env,
        timeout,
    ):
        return fake_run(
            args=args,
            check=check,
            capture_output=capture_output,
            text=text,
            input=input,
            env=env,
            timeout=timeout,
        )

    monkeypatch.setattr(contexts.subprocess, "run", fake_subprocess_run)

    observer_done = threading.Event()

    def observe_global_env():
        started.wait(timeout=1)
        deadline = time.monotonic() + 0.1
        while time.monotonic() < deadline:
            observed.append(os.environ.get("GH_TOKEN"))
            time.sleep(0.005)
        observer_done.set()

    observer = threading.Thread(target=observe_global_env)
    observer.start()
    runner = contexts.gh_runner_from_transport_context(
        contexts.TransportCredentialContext.from_token("ghp_fake_token", ambient_env={"PATH": "/usr/bin"})
    )
    proc = runner(["gh", "api", "graphql"])
    observer_done.wait(timeout=1)
    observer.join(timeout=1)

    assert proc.returncode == 0
    assert captured_env["GH_TOKEN"] == "ghp_fake_token"
    assert os.environ.get("GH_TOKEN") is None
    assert observed
    assert all(value is None for value in observed)


def test_local_git_context_scrubs_credential_env_and_sets_hardened_posture(tmp_path: Path):
    ctx = contexts.LocalGitContext.from_sandbox(
        tmp_path / "local-git",
        ambient_env={
            "PATH": "/usr/bin",
            "GH_TOKEN": "ghp_forbidden",
            "GITHUB_TOKEN": "github_forbidden",
            "SSH_AUTH_SOCK": "/tmp/ssh-agent.sock",
            "GIT_ASKPASS": "askpass",
            "GIT_CONFIG_KEY_9": "credential.helper",
            "HOME": "/host/home",
        },
    )

    assert ctx.env["PATH"] == "/usr/bin"
    assert ctx.env["HOME"] == str(tmp_path / "local-git" / "home")
    assert ctx.env["XDG_CONFIG_HOME"] == str(tmp_path / "local-git" / "xdg-config")
    assert ctx.env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert ctx.env["GIT_TERMINAL_PROMPT"] == "0"
    assert ctx.env["GIT_CONFIG_KEY_0"] == "core.hooksPath"
    assert ctx.env["GIT_CONFIG_VALUE_0"] == "/dev/null"
    assert not any(key.startswith(("GH_", "GITHUB_", "SSH_")) for key in ctx.env)
    assert "GIT_ASKPASS" not in ctx.env
    assert "GIT_CONFIG_KEY_9" not in ctx.env


def test_local_git_context_rejects_credential_bearing_explicit_env(tmp_path: Path):
    with pytest.raises(contexts.AuthorityContextError, match="GH_TOKEN"):
        contexts.LocalGitContext(
            env={
                "HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(tmp_path / "xdg"),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.hooksPath",
                "GIT_CONFIG_VALUE_0": "/dev/null",
                "GH_TOKEN": "ghp_forbidden",
            },
            home=tmp_path / "home",
            xdg_config_home=tmp_path / "xdg",
        )


def test_validation_sandbox_context_has_no_credentials_or_egress_by_default(tmp_path: Path):
    ctx = contexts.ValidationSandboxContext.from_sandbox(
        tmp_path / "validation",
        ambient_env={
            "PATH": "/usr/bin",
            "GITHUB_TOKEN": "github_forbidden",
            "SSH_PRIVATE_KEY": "forbidden",
            "GIT_ASKPASS": "forbidden",
        },
    )

    assert ctx.role == "verification"
    assert ctx.egress_allowed is False
    assert ctx.env["CE_VALIDATION_ROLE"] == "verification"
    assert ctx.env["CE_EGRESS_ALLOWED"] == "0"
    assert not any(key.startswith(("GH_", "GITHUB_", "SSH_")) for key in ctx.env)
    assert "GIT_ASKPASS" not in ctx.env

    with pytest.raises(contexts.AuthorityContextError, match="GITHUB_TOKEN"):
        contexts.ValidationSandboxContext(
            env={
                "HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(tmp_path / "xdg"),
                "GITHUB_TOKEN": "github_forbidden",
            },
            home=tmp_path / "home",
            xdg_config_home=tmp_path / "xdg",
        )


def test_context_consumers_are_typed_and_reject_confusion(tmp_path: Path):
    transport = contexts.TransportCredentialContext.from_token("ghp_fake", ambient_env={"PATH": "/usr/bin"})
    local = contexts.LocalGitContext.from_sandbox(tmp_path / "local")
    validation = contexts.ValidationSandboxContext.from_sandbox(tmp_path / "validation")

    assert get_type_hints(contexts.gh_runner_from_transport_context)["context"] is contexts.TransportCredentialContext
    assert get_type_hints(contexts.git_env_from_local_context)["context"] is contexts.LocalGitContext
    assert get_type_hints(contexts.validation_env_from_context)["context"] is contexts.ValidationSandboxContext

    with pytest.raises(TypeError):
        contexts.gh_runner_from_transport_context(local)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        contexts.git_env_from_local_context(transport)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        contexts.validation_env_from_context(local)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        contexts.EnvGhRunner(validation)  # type: ignore[arg-type]
