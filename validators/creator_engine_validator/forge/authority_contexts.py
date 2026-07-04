"""Typed authority contexts for forge subprocess boundaries.

The classes in this module are intentionally distinct value objects. A
transport credential, local git posture, and validation sandbox are not
substitutable even when they all expose an ``env`` mapping for legacy plumbing.
"""
from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any


class AuthorityContextError(ValueError):
    """An authority context carried malformed or forbidden process state."""


GhRunner = Callable[[Sequence[str], str | None], subprocess.CompletedProcess]

_DEFAULT_TOKEN_ENV = "GH_TOKEN"
_SAFE_AMBIENT_KEYS = {
    "FORCE_COLOR",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "NO_COLOR",
    "PATH",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "TEMP",
    "TERM",
    "TMP",
    "TMPDIR",
    "TZ",
}
_FORBIDDEN_CREDENTIAL_KEYS = {
    "ANTHROPIC_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "BAO_TOKEN",
    "CE_FORGE_MINT_BROKER_USER_TOKEN",
    "CE_PICKUP_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "GIT_ASKPASS",
    "GIT_CREDENTIAL_HELPER",
    "GIT_SSH",
    "GIT_SSH_COMMAND",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "OPENAI_API_KEY",
    "OPENBAO_TOKEN",
    "SSH_AUTH_SOCK",
    "VAULT_TOKEN",
}
_FORBIDDEN_CREDENTIAL_PREFIXES = ("GH_", "GITHUB_", "SSH_")
_FORBIDDEN_CREDENTIAL_TOKENS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "PRIVATE_KEY",
    "API_KEY",
    "CREDENTIAL",
    "AUTH",
)


def _string_env(env: Mapping[str, str] | None) -> dict[str, str]:
    if env is None:
        return {}
    return {str(key): str(value) for key, value in env.items()}


def _immutable_env(env: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(dict(env))


def _credential_env_findings(env: Mapping[str, str]) -> tuple[str, ...]:
    findings: list[str] = []
    for key, value in env.items():
        upper_key = key.upper()
        if (
            upper_key in _FORBIDDEN_CREDENTIAL_KEYS
            or upper_key.startswith(_FORBIDDEN_CREDENTIAL_PREFIXES)
            or any(token in upper_key for token in _FORBIDDEN_CREDENTIAL_TOKENS)
        ):
            findings.append(key)
            continue
        if upper_key.startswith("GIT_CONFIG_KEY_") and str(value).strip().lower() == "credential.helper":
            findings.append(key)
            continue
        if upper_key.startswith("GIT_CONFIG_VALUE_") and "credential.helper" in str(value).lower():
            findings.append(key)
    return tuple(sorted(findings))


def _require_no_credential_env(env: Mapping[str, str], *, context_name: str) -> None:
    findings = _credential_env_findings(env)
    if findings:
        joined = ", ".join(findings)
        raise AuthorityContextError(f"{context_name} refuses credential-bearing env keys: {joined}")


def require_no_credential_env(env: Mapping[str, str], *, context_name: str) -> None:
    """Reject env mappings that expose credential-bearing keys or git credential config."""

    _require_no_credential_env(env, context_name=context_name)


def is_credential_env_key(name: str) -> bool:
    """Return True when an environment variable name is shaped like credential material."""

    return bool(_credential_env_findings({str(name): ""}))


def _scrub_ambient_env(ambient_env: Mapping[str, str] | None) -> dict[str, str]:
    ambient = _string_env(os.environ if ambient_env is None else ambient_env)
    return {key: value for key, value in ambient.items() if key in _SAFE_AMBIENT_KEYS}


def _ensure_private_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            path.chmod(0o700)
        except PermissionError:
            # Keep the value object usable on filesystems that ignore chmod.
            pass


@dataclass(frozen=True)
class TransportCredentialContext:
    """Credentialed source-host transport authority for gh/git fetch/push."""

    env: Mapping[str, str] = field(repr=False, compare=False)
    token_env: str = _DEFAULT_TOKEN_ENV
    source_host: str = "github.com"
    token_provider: Callable[[], str] | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized = _string_env(self.env)
        token_env = str(self.token_env).strip()
        if not token_env:
            raise AuthorityContextError("transport token env name is required")
        if not str(normalized.get(token_env, "")).strip():
            raise AuthorityContextError(f"{token_env} is required for transport authority")
        object.__setattr__(self, "token_env", token_env)
        object.__setattr__(self, "source_host", str(self.source_host or "github.com"))
        object.__setattr__(self, "env", _immutable_env(normalized))

    @classmethod
    def from_token(
        cls,
        token: str,
        *,
        ambient_env: Mapping[str, str] | None = None,
        token_env: str = _DEFAULT_TOKEN_ENV,
        source_host: str = "github.com",
    ) -> "TransportCredentialContext":
        value = str(token).strip()
        if not value:
            raise AuthorityContextError("transport token is required")
        env = _scrub_ambient_env(ambient_env)
        env[token_env] = value
        return cls(env=env, token_env=token_env, source_host=source_host)

    @classmethod
    def from_token_provider(
        cls,
        provider: Callable[[], str],
        *,
        ambient_env: Mapping[str, str] | None = None,
        token_env: str = _DEFAULT_TOKEN_ENV,
        source_host: str = "github.com",
    ) -> "TransportCredentialContext":
        context = cls.from_token(
            provider(),
            ambient_env=ambient_env,
            token_env=token_env,
            source_host=source_host,
        )
        object.__setattr__(context, "token_provider", provider)
        return context


@dataclass(frozen=True)
class LocalGitContext:
    """Credentialless local git posture for non-transport commands."""

    env: Mapping[str, str] = field(repr=False, compare=False)
    home: Path
    xdg_config_home: Path
    hooks_path: str = "/dev/null"

    def __post_init__(self) -> None:
        normalized = _string_env(self.env)
        _require_no_credential_env(normalized, context_name="LocalGitContext")
        home = Path(self.home)
        xdg_config_home = Path(self.xdg_config_home)
        if not home.is_absolute() or not xdg_config_home.is_absolute():
            raise AuthorityContextError("LocalGitContext HOME and XDG_CONFIG_HOME must be absolute")
        if normalized.get("HOME") != str(home):
            raise AuthorityContextError("LocalGitContext HOME must point at its sandbox-private home")
        if normalized.get("XDG_CONFIG_HOME") != str(xdg_config_home):
            raise AuthorityContextError("LocalGitContext XDG_CONFIG_HOME must point at its sandbox-private config")
        if normalized.get("GIT_CONFIG_NOSYSTEM") != "1":
            raise AuthorityContextError("LocalGitContext requires GIT_CONFIG_NOSYSTEM=1")
        if normalized.get("GIT_TERMINAL_PROMPT") != "0":
            raise AuthorityContextError("LocalGitContext requires GIT_TERMINAL_PROMPT=0")
        if not _has_hooks_posture(normalized, self.hooks_path):
            raise AuthorityContextError("LocalGitContext requires core.hooksPath=/dev/null posture")
        object.__setattr__(self, "home", home)
        object.__setattr__(self, "xdg_config_home", xdg_config_home)
        object.__setattr__(self, "env", _immutable_env(normalized))

    @classmethod
    def from_sandbox(
        cls,
        sandbox_root: str | Path,
        *,
        ambient_env: Mapping[str, str] | None = None,
    ) -> "LocalGitContext":
        root = Path(sandbox_root)
        if not root.is_absolute():
            raise AuthorityContextError(f"LocalGitContext sandbox root must be absolute: {root}")
        home = root / "home"
        xdg_config_home = root / "xdg-config"
        _ensure_private_dirs(home, xdg_config_home)
        env = _scrub_ambient_env(ambient_env)
        env.update(
            {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(xdg_config_home),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.hooksPath",
                "GIT_CONFIG_VALUE_0": "/dev/null",
            }
        )
        return cls(env=env, home=home, xdg_config_home=xdg_config_home)


@dataclass(frozen=True)
class ValidationSandboxContext:
    """Credentialless verification-role context, with egress disabled by default."""

    env: Mapping[str, str] = field(repr=False, compare=False)
    home: Path
    xdg_config_home: Path
    role: str = "verification"
    egress_allowed: bool = False

    def __post_init__(self) -> None:
        normalized = _string_env(self.env)
        _require_no_credential_env(normalized, context_name="ValidationSandboxContext")
        home = Path(self.home)
        xdg_config_home = Path(self.xdg_config_home)
        if not home.is_absolute() or not xdg_config_home.is_absolute():
            raise AuthorityContextError("ValidationSandboxContext HOME and XDG_CONFIG_HOME must be absolute")
        if normalized.get("HOME") != str(home):
            raise AuthorityContextError("ValidationSandboxContext HOME must point at its sandbox-private home")
        if normalized.get("XDG_CONFIG_HOME") != str(xdg_config_home):
            raise AuthorityContextError(
                "ValidationSandboxContext XDG_CONFIG_HOME must point at its sandbox-private config"
            )
        if self.egress_allowed:
            raise AuthorityContextError("ValidationSandboxContext defaults to no egress")
        object.__setattr__(self, "home", home)
        object.__setattr__(self, "xdg_config_home", xdg_config_home)
        object.__setattr__(self, "role", "verification")
        object.__setattr__(self, "env", _immutable_env(normalized))

    @classmethod
    def from_sandbox(
        cls,
        sandbox_root: str | Path,
        *,
        ambient_env: Mapping[str, str] | None = None,
    ) -> "ValidationSandboxContext":
        root = Path(sandbox_root)
        if not root.is_absolute():
            raise AuthorityContextError(f"ValidationSandboxContext sandbox root must be absolute: {root}")
        home = root / "home"
        xdg_config_home = root / "xdg-config"
        _ensure_private_dirs(home, xdg_config_home)
        env = _scrub_ambient_env(ambient_env)
        env.update(
            {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(xdg_config_home),
                "CE_VALIDATION_ROLE": "verification",
                "CE_EGRESS_ALLOWED": "0",
            }
        )
        return cls(env=env, home=home, xdg_config_home=xdg_config_home)


@dataclass(frozen=True)
class EnvGhRunner:
    """``gh`` runner that supplies credentials through an explicit child env."""

    transport_context: TransportCredentialContext
    runner: GhRunner | None = None
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if not isinstance(self.transport_context, TransportCredentialContext):
            raise TypeError("EnvGhRunner requires TransportCredentialContext")

    def __call__(self, argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        if self.runner is not None:
            return self.runner(argv, input_text)
        return subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
            input=input_text,
            env=dict(self.transport_context.env),
            timeout=self.timeout_seconds,
        )


def gh_runner_from_transport_context(
    context: TransportCredentialContext,
    runner: GhRunner | None = None,
) -> GhRunner:
    if not isinstance(context, TransportCredentialContext):
        raise TypeError("gh runner requires TransportCredentialContext")
    return EnvGhRunner(context, runner=runner)


def git_env_from_transport_context(context: TransportCredentialContext) -> Mapping[str, str]:
    if not isinstance(context, TransportCredentialContext):
        raise TypeError("transport git env requires TransportCredentialContext")
    return context.env


def git_env_from_local_context(context: LocalGitContext) -> Mapping[str, str]:
    if not isinstance(context, LocalGitContext):
        raise TypeError("local git env requires LocalGitContext")
    return context.env


def validation_env_from_context(context: ValidationSandboxContext) -> Mapping[str, str]:
    if not isinstance(context, ValidationSandboxContext):
        raise TypeError("validation env requires ValidationSandboxContext")
    return context.env


def _has_hooks_posture(env: Mapping[str, str], hooks_path: str) -> bool:
    try:
        count = int(env.get("GIT_CONFIG_COUNT", "0"))
    except ValueError:
        return False
    for index in range(count):
        key = env.get(f"GIT_CONFIG_KEY_{index}", "")
        value = env.get(f"GIT_CONFIG_VALUE_{index}", "")
        if key == "core.hooksPath" and value == hooks_path:
            return True
    return False


__all__ = [
    "AuthorityContextError",
    "EnvGhRunner",
    "LocalGitContext",
    "TransportCredentialContext",
    "ValidationSandboxContext",
    "gh_runner_from_transport_context",
    "git_env_from_local_context",
    "git_env_from_transport_context",
    "is_credential_env_key",
    "require_no_credential_env",
    "validation_env_from_context",
]
