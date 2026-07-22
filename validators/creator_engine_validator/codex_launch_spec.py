"""CDX-D Ring 0 — pure Codex launch-spec evaluator + governed command builder.

This module is deliberately narrower than the Claude launch-spec. It refuses
obvious posture-defeating Codex surfaces before tmux spawn and builds the
command through an environment scrub that removes common ambient repo-write
credentials. Codex Ring-1 parity is conditioned on the managed PreToolUse
hook-pack being confirmed by the launcher before spawn.

Clause identifiers are stable and namespaced ``CDX-D-*``.
"""
from __future__ import annotations

import os
import shutil
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import model_effort_policy

CLAUSE_HEADLESS = "CDX-D-1"
CLAUSE_REMOTE = "CDX-D-2"
CLAUSE_TRANSCRIPT = "CDX-D-3"
CLAUSE_POSTURE_BYPASS = "CDX-D-4"
CLAUSE_ADD_DIR = "CDX-D-5"
CLAUSE_BYPASS_MODE = "CDX-D-6"
CLAUSE_ARG_ALLOWLIST = "CDX-D-7"
CLAUSE_MANAGED_HOOK_PACK = "CDX-D-8"
CLAUSE_CONTAINER_CREDENTIAL_ENV = "CDX-D-9"
CODEX_HARNESS_ENV = "CE_CODEX_HARNESS"
KNOWN_GOOD_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

HEADLESS_SUBCOMMANDS = frozenset(
    {"exec", "review", "mcp-server", "exec-server", "app-server", "apply"}
)
REMOTE_TOKEN_FLAGS = frozenset(
    {
        "--remote-token",
        "--remote-auth-token",
        "--remote-api-token",
        "--codex-remote-token",
    }
)
POSTURE_BYPASS_FLAGS = frozenset(
    {"--dangerously-bypass-hook-trust", "--ignore-rules", "--ignore-user-config"}
)
BYPASS_FLAG = "--dangerously-bypass-approvals-and-sandbox"
CREDENTIAL_ENV_UNSETS = (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GH_ENTERPRISE_TOKEN",
    "GITHUB_ENTERPRISE_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "BAO_TOKEN",
    "OPENBAO_TOKEN",
    "VAULT_TOKEN",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GITHUB_API_URL",
    "GH_HOST",
    "GH_CONFIG_DIR",
    "GH_DEBUG",
)
CREDENTIAL_ENV_NAMES = frozenset(
    {
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "BAO_TOKEN",
        "OPENBAO_TOKEN",
        "VAULT_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "GOOGLE_APPLICATION_CREDENTIALS",
    }
)
_CREDENTIAL_ENV_SUFFIXES = (
    "_TOKEN",
    "_OAUTH_TOKEN",
    "_API_KEY",
    "_SECRET",
    "_PRIVATE_KEY",
    "_AUTH_SOCK",
    "_CREDENTIALS",
)
_DOCKER_ENV_FLAGS = frozenset({"--env", "-e"})
_DOCKER_ENV_FILE_FLAGS = frozenset({"--env-file"})

_VALUE_FLAGS = frozenset({"--model", "-m", "--reasoning-effort", "--effort", "--add-dir"})
_SAFE_VALUE_FLAGS = frozenset({"--model", "-m", "--reasoning-effort", "--effort"})
_SAFE_BOOL_FLAGS = frozenset({BYPASS_FLAG})


class GovernedCommandError(ValueError):
    """Raised when a governed Codex command cannot be built safely."""


@dataclass(frozen=True)
class CodexLaunchSpec:
    """Parsed view of requested Codex args, excluding the ``codex`` token."""

    argv: tuple[str, ...]
    add_dirs: tuple[str, ...] = ()
    explicit_bypass: bool = False


@dataclass(frozen=True)
class LaunchRefusal:
    clause: str
    surface: str
    detail: str

    def to_dict(self) -> dict:
        return {"clause": self.clause, "surface": self.surface, "detail": self.detail}


@dataclass(frozen=True)
class ContainerCredentialEnvFinding:
    """A credential-bearing env carrier found in a container launch spec."""

    clause: str
    surface: str
    name: str
    detail: str

    def to_dict(self) -> dict:
        return {
            "clause": self.clause,
            "surface": self.surface,
            "name": self.name,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class LaunchSpecResult:
    refusals: tuple[LaunchRefusal, ...] = ()
    bypass_mode: str | None = None

    @property
    def ok(self) -> bool:
        return not self.refusals

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "bypass_mode": self.bypass_mode,
            "refusals": [r.to_dict() for r in self.refusals],
        }


def parse_codex_argv(argv: Sequence[str]) -> CodexLaunchSpec:
    """Parse requested ``codex`` args leniently for the Ring-0 evaluator."""
    tokens = list(argv)
    add_dirs: list[str] = []
    explicit_bypass = False
    i = 0
    while i < len(tokens):
        token = tokens[i]
        name, sep, inline_value = token.partition("=")
        if token == BYPASS_FLAG:
            explicit_bypass = True
        if name == "--add-dir":
            if sep:
                add_dirs.append(inline_value)
            elif i + 1 < len(tokens):
                add_dirs.append(tokens[i + 1])
                i += 1
        elif name in _VALUE_FLAGS and not sep:
            i += 1
        i += 1
    return CodexLaunchSpec(
        argv=tuple(tokens),
        add_dirs=tuple(add_dirs),
        explicit_bypass=explicit_bypass,
    )


def detect_config_bypass_mode(config_path: Path | str | None = None) -> str | None:
    """Return ``"config"`` only when the live Codex config declares bypass posture."""
    path = Path(config_path) if config_path is not None else Path.home() / ".codex" / "config.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    if data.get("approval_policy") == "never" and data.get("sandbox_mode") == "danger-full-access":
        return "config"
    return None


def evaluate_codex_launch(
    spec: CodexLaunchSpec,
    *,
    allowed_root: Path | str,
    config_bypass_mode: str | None,
) -> LaunchSpecResult:
    """Fail closed for prohibited Codex authoring-seat launch surfaces."""
    refusals: list[LaunchRefusal] = []
    argv = spec.argv
    allowed = Path(allowed_root).resolve()

    if argv and argv[0] in HEADLESS_SUBCOMMANDS:
        refusals.append(
            LaunchRefusal(
                CLAUSE_HEADLESS,
                argv[0],
                "non-interactive/headless Codex subcommands are not governed authoring seats",
            )
        )

    if "remote-control" in argv:
        refusals.append(
            LaunchRefusal(CLAUSE_REMOTE, "remote-control", "remote-control is outside the visible seat")
        )
    for token in argv:
        name = token.partition("=")[0]
        if name == "--remote" or name in REMOTE_TOKEN_FLAGS:
            refusals.append(
                LaunchRefusal(CLAUSE_REMOTE, name, "remote surfaces and remote auth tokens are refused")
            )

    if "--ephemeral" in argv:
        refusals.append(
            LaunchRefusal(CLAUSE_TRANSCRIPT, "--ephemeral", "ephemeral mode disables durable transcript identity")
        )

    for token in argv:
        name = token.partition("=")[0]
        if name in POSTURE_BYPASS_FLAGS:
            refusals.append(
                LaunchRefusal(
                    CLAUSE_POSTURE_BYPASS,
                    name,
                    "trust/posture bypass surfaces are not ratified by G1-codex",
                )
            )

    for raw in spec.add_dirs:
        try:
            target = Path(raw).expanduser()
            if not target.is_absolute():
                target = allowed / target
            target.resolve().relative_to(allowed)
        except (OSError, ValueError):
            refusals.append(
                LaunchRefusal(
                    CLAUSE_ADD_DIR,
                    "--add-dir",
                    f"writable-scope expansion {raw!r} is outside the declared worktree root",
                )
            )

    for i, token in enumerate(argv):
        name, sep, _value = token.partition("=")
        if name in _SAFE_BOOL_FLAGS:
            continue
        if name in _SAFE_VALUE_FLAGS:
            continue
        if name == "--add-dir":
            continue
        if i > 0 and argv[i - 1].partition("=")[0] in _VALUE_FLAGS and "=" not in argv[i - 1]:
            continue
        if token.startswith("-"):
            refusals.append(
                LaunchRefusal(
                    CLAUSE_ARG_ALLOWLIST,
                    name,
                    "Codex harness args are allowlisted; this launch arg is not permitted by G1-codex",
                )
            )

    bypass_mode = "argv" if spec.explicit_bypass else config_bypass_mode
    if bypass_mode not in {"argv", "config"}:
        refusals.append(
            LaunchRefusal(
                CLAUSE_BYPASS_MODE,
                "codex_bypass_mode",
                "Codex bypass mode must be explicit in argv or verified from ~/.codex/config.toml",
            )
        )

    return LaunchSpecResult(refusals=tuple(refusals), bypass_mode=bypass_mode)


def is_credential_env_name(name: str) -> bool:
    """Return True for env names that may carry credentials into a container."""
    candidate = name.strip()
    if not candidate:
        return False
    if candidate in CREDENTIAL_ENV_NAMES:
        return True
    return candidate.endswith(_CREDENTIAL_ENV_SUFFIXES)


def _env_name_from_assignment(value: str) -> str:
    return value.split("=", 1)[0].strip()


def find_container_credential_env_carriers(
    launch_spec: Sequence[str] | Mapping[str, Any],
) -> tuple[ContainerCredentialEnvFinding, ...]:
    """Find credential-bearing env carriers in a Docker argv or OCI-like spec.

    The check is value-free: findings name only the environment variable and the
    carrier surface. It catches Docker forms such as ``--env GH_TOKEN``,
    ``--env=GH_TOKEN=...``, ``-e GH_TOKEN``, direct OCI ``Env`` entries like
    ``GH_TOKEN=...``, and opaque ``--env-file`` carriers.
    """
    findings: list[ContainerCredentialEnvFinding] = []

    def add(surface: str, name: str, detail: str) -> None:
        findings.append(
            ContainerCredentialEnvFinding(
                CLAUSE_CONTAINER_CREDENTIAL_ENV,
                surface,
                name,
                detail,
            )
        )

    def scan_env_payload(surface: str, payload: str) -> None:
        env_name = _env_name_from_assignment(payload)
        if is_credential_env_name(env_name):
            add(
                surface,
                env_name,
                "contained launches must not pass credential env names or values into the container spec",
            )

    def scan_argv(argv: Sequence[str]) -> None:
        expect_env_payload: str | None = None
        expect_env_file = False
        for raw in argv:
            token = str(raw)
            if expect_env_payload is not None:
                scan_env_payload(expect_env_payload, token)
                expect_env_payload = None
                continue
            if expect_env_file:
                add(
                    "--env-file",
                    "<env-file>",
                    "contained launches must not use opaque Docker env files",
                )
                expect_env_file = False
                continue

            if token in _DOCKER_ENV_FLAGS:
                expect_env_payload = token
                continue
            if token in _DOCKER_ENV_FILE_FLAGS:
                expect_env_file = True
                continue
            if token.startswith("--env="):
                scan_env_payload("--env", token.split("=", 1)[1])
                continue
            if token.startswith("--env-file="):
                add(
                    "--env-file",
                    "<env-file>",
                    "contained launches must not use opaque Docker env files",
                )
                continue
            if token.startswith("-e") and token != "-e":
                scan_env_payload("-e", token[2:])
                continue
            if "=" in token:
                scan_env_payload("Env", token)

    def scan_spec(value: Any) -> None:
        if isinstance(value, str):
            if "=" in value:
                scan_env_payload("Env", value)
            return
        if isinstance(value, Mapping):
            for key, child in value.items():
                key_text = str(key)
                if is_credential_env_name(key_text):
                    add(
                        "environment",
                        key_text,
                        "contained launches must not pass credential env names or values into the container spec",
                    )
                scan_spec(child)
            return
        if isinstance(value, Sequence):
            argv = [str(part) for part in value]
            scan_argv(argv)
            for child in value:
                if not isinstance(child, str):
                    scan_spec(child)

    scan_spec(launch_spec)
    return tuple(findings)


def assert_no_container_credential_env(
    launch_spec: Sequence[str] | Mapping[str, Any],
) -> None:
    """Raise when a contained launch spec carries credential-bearing env."""
    findings = find_container_credential_env_carriers(launch_spec)
    if findings:
        names = ", ".join(f.name for f in findings)
        surfaces = ", ".join(f.surface for f in findings)
        raise GovernedCommandError(
            "contained launch passes credential-bearing env into the container "
            f"spec ({names}) via {surfaces}; use a broker/transport-deputy handoff instead"
        )


def _composed_path(path: str | None = None) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for chunk in (path if path is not None else os.environ.get("PATH", ""), KNOWN_GOOD_PATH):
        for part in str(chunk).split(os.pathsep):
            if part and part not in seen:
                parts.append(part)
                seen.add(part)
    return os.pathsep.join(parts)


def resolve_codex_harness_binary(
    configured: str | None = None,
    *,
    path: str | None = None,
) -> str:
    """Resolve the Codex harness to an executable absolute path before spawn."""
    configured = configured if configured is not None else os.environ.get(CODEX_HARNESS_ENV)
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise GovernedCommandError(
                f"{CODEX_HARNESS_ENV} must be an absolute Codex harness path"
            )
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        raise GovernedCommandError(
            f"cannot resolve Codex harness at configured path {str(candidate)!r}"
        )

    found = shutil.which("codex", path=_composed_path(path))
    if found:
        return str(Path(found).resolve())
    raise GovernedCommandError(
        "cannot resolve Codex harness binary 'codex' on the composed launch PATH; "
        f"set {CODEX_HARNESS_ENV} to an executable absolute path"
    )


def build_governed_codex_command(
    base_argv: Sequence[str],
    *,
    codex_bin: str | None = None,
    env_overrides: Mapping[str, str] | None = None,
    role: str | None = None,
    resolved_model_effort: model_effort_policy.ResolvedModelEffort | None = None,
) -> list[str]:
    """Build the governed Codex command with credentials and policy pinned.

    Model/effort flags are wrapper-owned: every raw spelling is removed before
    the resolved pair is injected.  That keeps a stale herdr/session restore
    from replaying a low-effort or Luna request behind the wrapper's back.
    """
    resolved = codex_bin or resolve_codex_harness_binary()
    policy = resolved_model_effort or model_effort_policy.resolve_model_effort(
        base_argv, role=role
    )
    passthrough = model_effort_policy.strip_model_effort_args(base_argv)
    return [
        "env",
        *(part for name in CREDENTIAL_ENV_UNSETS for part in ("-u", name)),
        *(f"{name}={value}" for name, value in sorted((env_overrides or {}).items())),
        resolved,
        *passthrough,
        "--model",
        policy.model,
        "--reasoning-effort",
        policy.effort,
    ]


def _main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--check-contained-launch-argv":
        try:
            assert_no_container_credential_env(args[1:])
        except GovernedCommandError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 78
        return 0
    print("usage: codex_launch_spec.py --check-contained-launch-argv <argv...>", file=sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover - exercised through launcher guards.
    raise SystemExit(_main())
