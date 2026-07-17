"""Fail-closed, policy-bound ``ce worker launch`` Codex one-shot launcher.

The only production policy source is the canonical tracked policy inside the
allocated worktree.  Prompt bodies never enter a plan: exact canonical role
policy bytes and SHA-256-verified brief bytes are framed only for runner stdin.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import string
import subprocess
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any, Protocol, Sequence

import yaml


CANONICAL_POLICY_RELATIVE_PATH = "governance/policies/codex-one-shot-launch-v1.yaml"
CANONICAL_BRIEF_AREA = ".ce/briefs"
CANONICAL_ROLE_AREA = ".claude/agents"
POLICY_REQUIRED_KEYS = frozenset(
    {
        "kind",
        "schema_version",
        "policy_id",
        "version",
        "supported_roles",
        "role_provider_credentials",
        "venues",
        "model_defaults",
        "canonical_add_dirs",
    }
)
VENUE_REQUIRED_KEYS = frozenset(
    {"codex_binary_template", "outer_isolation_attestation", "role_sandboxes"}
)
POLICY_KIND = "codex-one-shot-launch-policy"
POLICY_SCHEMA_VERSION = "1"
V1_SUPPORTED_ROLES = (
    "architect_research",
    "implementer",
    "reviewer",
    "verification",
)
V1_VENUES = ("dgx-relay", "vps-tmux", "dev1-local", "in-seat")
V1_ROLE_SANDBOX_MATRIX = (
    (
        "dgx-relay",
        (
            ("architect_research", "read-only"),
            ("implementer", None),
            ("reviewer", "read-only"),
            ("verification", "read-only"),
        ),
    ),
    (
        "vps-tmux",
        tuple((role, None) for role in V1_SUPPORTED_ROLES),
    ),
    (
        "dev1-local",
        (
            ("architect_research", "read-only"),
            ("implementer", None),
            ("reviewer", "read-only"),
            ("verification", "read-only"),
        ),
    ),
    (
        "in-seat",
        tuple((role, None) for role in V1_SUPPORTED_ROLES),
    ),
)
ALLOWED_SANDBOXES = frozenset({"read-only", "workspace-write", "danger-full-access"})
ALLOWED_MODEL_PROVIDER_CREDENTIAL_ENV_NAMES = frozenset({"OPENAI_API_KEY"})
SAFE_RUNTIME_ENV_NAMES = frozenset({"LANG", "PATH", "TERM"})
_EXACT_CREDENTIAL_ENV_NAMES = frozenset(
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
        "GITHUB_API_URL",
        "GH_HOST",
        "GH_CONFIG_DIR",
        "GH_DEBUG",
        "GITHUB_PAT",
        "GITHUB_APP_PRIVATE_KEY",
        "GIT_ASKPASS",
        "SSH_ASKPASS",
        "SSH_AUTH_SOCK",
        "CE_PICKUP_TOKEN",
        "CE_FORGE_MINT_BROKER_USER_TOKEN",
    }
)
_SECRET_ENV_TOKENS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "PRIVATE_KEY",
    "API_KEY",
    "CREDENTIAL",
    "AUTH",
)
_RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
_ROLE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")


class CodexWorkerLaunchError(ValueError):
    """A policy, filesystem, deployment, or caller input was refused."""


def _is_credential_env_name(name: str) -> bool:
    upper = name.upper()
    return upper in _EXACT_CREDENTIAL_ENV_NAMES or any(
        token in upper for token in _SECRET_ENV_TOKENS
    )


@contextmanager
def _isolated_child_environment(
    source: Mapping[str, str],
    *,
    provider_credential_env_names: Sequence[str] = (),
) -> Iterator[dict[str, str]]:
    """Yield a cleanup-bound environment with invocation-owned state roots."""
    with tempfile.TemporaryDirectory(prefix="ce-codex-one-shot-") as invocation_root:
        home = os.path.join(invocation_root, "home")
        codex_home = os.path.join(invocation_root, "codex")
        tmpdir = os.path.join(invocation_root, "tmp")
        xdg_config = os.path.join(invocation_root, "xdg-config")
        xdg_cache = os.path.join(invocation_root, "xdg-cache")
        xdg_data = os.path.join(invocation_root, "xdg-data")
        for directory in (home, codex_home, tmpdir, xdg_config, xdg_cache, xdg_data):
            os.mkdir(directory, mode=0o700)
        child_env = {
            name: value
            for name, value in source.items()
            if name in SAFE_RUNTIME_ENV_NAMES
            or (name.startswith("LC_") and not _is_credential_env_name(name))
        }
        child_env.update(
            {
                name: source[name]
                for name in provider_credential_env_names
                if name in source
            }
        )
        child_env.update(
            {
                "HOME": home,
                "CODEX_HOME": codex_home,
                "TMPDIR": tmpdir,
                "XDG_CONFIG_HOME": xdg_config,
                "XDG_CACHE_HOME": xdg_cache,
                "XDG_DATA_HOME": xdg_data,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        yield child_env


class LauncherFilesystem(Protocol):
    def realpath(self, path: str) -> str: ...
    def lexists(self, path: str) -> bool: ...
    def is_dir(self, path: str) -> bool: ...
    def is_file(self, path: str) -> bool: ...
    def is_readable(self, path: str) -> bool: ...
    def is_executable(self, path: str) -> bool: ...
    def read_bytes(self, path: str) -> bytes: ...


class RealLauncherFilesystem:
    """Small injectable filesystem seam used by every preflight check."""

    def realpath(self, path: str) -> str:
        return os.path.realpath(path)

    def lexists(self, path: str) -> bool:
        return os.path.lexists(path)

    def is_dir(self, path: str) -> bool:
        return os.path.isdir(path)

    def is_file(self, path: str) -> bool:
        return os.path.isfile(path)

    def is_readable(self, path: str) -> bool:
        return os.access(path, os.R_OK)

    def is_executable(self, path: str) -> bool:
        return os.access(path, os.X_OK)

    def read_bytes(self, path: str) -> bytes:
        with open(path, "rb") as handle:
            return handle.read()


class CodexVersionProbe(Protocol):
    def probe(self, binary: str) -> str: ...


class SubprocessCodexVersionProbe:
    """Probe the already-preflighted absolute executable, never ambient PATH."""

    def __init__(self, *, environ: Mapping[str, str] | None = None) -> None:
        self._environ = environ

    def probe(self, binary: str) -> str:
        source = dict(os.environ if self._environ is None else self._environ)
        try:
            with _isolated_child_environment(source) as child_env:
                completed = subprocess.run(
                    [binary, "--version"],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=child_env,
                )
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise CodexWorkerLaunchError("Codex version probe could not execute pinned binary") from exc
        if completed.returncode != 0:
            raise CodexWorkerLaunchError("Codex version probe failed")
        output = f"{completed.stdout}\n{completed.stderr}"
        match = re.search(r"(?<![0-9A-Za-z.])([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?)", output)
        if match is None:
            raise CodexWorkerLaunchError("Codex version probe returned no parseable version")
        return match.group(1)


@dataclass(frozen=True)
class VenuePolicy:
    name: str
    codex_binary_template: str
    outer_isolation_attestation: str | None
    role_sandboxes: tuple[tuple[str, str | None], ...]

    def sandbox_for(self, role: str) -> str:
        for candidate, sandbox in self.role_sandboxes:
            if candidate != role:
                continue
            if sandbox is None:
                raise CodexWorkerLaunchError(
                    f"role {role} at venue {self.name} is not attested for required isolation"
                )
            return sandbox
        raise CodexWorkerLaunchError(f"role {role} has no venue matrix entry for {self.name}")


@dataclass(frozen=True)
class CodexOneShotPolicy:
    policy_id: str
    version: str
    supported_roles: tuple[str, ...]
    venues: tuple[VenuePolicy, ...]
    model: str
    effort: str
    role_provider_credentials: tuple[tuple[str, tuple[str, ...]], ...]
    canonical_add_dirs: tuple[str, ...]
    worktree: str
    source_path: str
    source_sha256: str

    @property
    def venue_names(self) -> tuple[str, ...]:
        return tuple(venue.name for venue in self.venues)

    def venue(self, name: str) -> VenuePolicy:
        for venue in self.venues:
            if venue.name == name:
                return venue
        raise CodexWorkerLaunchError(f"unknown venue: {name}")

    def sandbox_for(self, *, role: str, venue: str) -> str:
        return self.venue(venue).sandbox_for(role)

    def provider_credentials_for(self, role: str) -> tuple[str, ...]:
        for candidate, credentials in self.role_provider_credentials:
            if candidate == role:
                return credentials
        raise CodexWorkerLaunchError(f"role {role} has no provider credential policy")


def _require_exact_v1_names(actual: Sequence[str], expected: tuple[str, ...], field: str) -> None:
    if len(actual) != len(expected) or set(actual) != set(expected):
        raise CodexWorkerLaunchError(f"policy must define the exact v1 {field} set")


def _require_trusted_v1_matrix(policy: CodexOneShotPolicy) -> None:
    """Revalidate trusted v1 invariants even for directly constructed policies."""
    _require_exact_v1_names(policy.supported_roles, V1_SUPPORTED_ROLES, "supported-role")
    _require_exact_v1_names(
        tuple(venue.name for venue in policy.venues), V1_VENUES, "venue"
    )
    trusted = {venue: dict(matrix) for venue, matrix in V1_ROLE_SANDBOX_MATRIX}
    for venue in policy.venues:
        role_names = tuple(role for role, _sandbox in venue.role_sandboxes)
        if len(role_names) != len(V1_SUPPORTED_ROLES) or len(set(role_names)) != len(role_names):
            raise CodexWorkerLaunchError(
                f"v1 venue {venue.name} must define exactly one cell for each supported role"
            )
        matrix = dict(venue.role_sandboxes)
        _require_exact_v1_names(tuple(matrix), V1_SUPPORTED_ROLES, "supported-role")
        if matrix != trusted[venue.name]:
            raise CodexWorkerLaunchError(
                f"v1 role sandbox cells at venue {venue.name} must match the exact trusted matrix"
            )


@dataclass(frozen=True)
class GovernedWorkerInput:
    role: str
    role_policy_path: str
    role_policy_sha256: str
    brief_path: str
    brief_sha256: str
    stdin: bytes


@dataclass(frozen=True)
class CodexWorkerLaunchPlan:
    policy_id: str
    policy_version: str
    policy_path: str
    policy_sha256: str
    role: str
    role_policy_path: str
    role_policy_sha256: str
    brief_path: str
    brief_sha256: str
    venue: str
    sandbox: str
    model: str
    effort: str
    provider_credential_env_names: tuple[str, ...]
    worktree: str
    run_id: str
    output: str
    argv: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_path": self.policy_path,
            "policy_sha256": self.policy_sha256,
            "role": self.role,
            "role_policy_path": self.role_policy_path,
            "role_policy_sha256": self.role_policy_sha256,
            "brief_path": self.brief_path,
            "brief_sha256": self.brief_sha256,
            "venue": self.venue,
            "sandbox": self.sandbox,
            "model": self.model,
            "effort": self.effort,
            "provider_credential_env_names": list(self.provider_credential_env_names),
            "worktree": self.worktree,
            "run_id": self.run_id,
            "output": self.output,
            "argv": list(self.argv),
        }


class CodexOneShotRunner(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        stdin: bytes,
        provider_credential_env_names: Sequence[str],
    ) -> int:
        """Run a governed plan without altering argv or verified stdin bytes."""


class SubprocessCodexOneShotRunner:
    """Run with an invocation-owned home and an explicit environment allowlist."""

    def __init__(self, *, environ: Mapping[str, str] | None = None) -> None:
        self._environ = environ

    def run(
        self,
        argv: Sequence[str],
        *,
        stdin: bytes,
        provider_credential_env_names: Sequence[str],
    ) -> int:
        source = dict(os.environ if self._environ is None else self._environ)
        credential_names = tuple(provider_credential_env_names)
        if any(
            name not in ALLOWED_MODEL_PROVIDER_CREDENTIAL_ENV_NAMES
            for name in credential_names
        ):
            raise CodexWorkerLaunchError("runner received a non-provider credential name")
        try:
            with _isolated_child_environment(
                source, provider_credential_env_names=credential_names
            ) as child_env:
                completed = subprocess.run(
                    list(argv),
                    input=stdin,
                    text=False,
                    check=False,
                    env=child_env,
                )
                return completed.returncode
        except CodexWorkerLaunchError:
            raise
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise CodexWorkerLaunchError("Codex subprocess execution failed") from exc


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CodexWorkerLaunchError(f"policy {field} must be a nonempty string")
    return value.strip()


def _require_string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise CodexWorkerLaunchError(f"policy {field} must be a nonempty string list")
    values = tuple(item.strip() for item in value)
    if len(set(values)) != len(values):
        raise CodexWorkerLaunchError(f"policy {field} must not contain duplicates")
    return values


def _render_binary_template(*, template: str, version: str, venue: str) -> str:
    """Render exactly one plain ``{version}`` field and no other format syntax."""
    try:
        parsed = tuple(string.Formatter().parse(template))
    except ValueError as exc:
        raise CodexWorkerLaunchError(
            f"policy venue {venue} has an invalid binary template"
        ) from exc
    fields = tuple(
        (field_name, format_spec, conversion)
        for _literal, field_name, format_spec, conversion in parsed
        if field_name is not None
    )
    if (
        template.count("{version}") != 1
        or fields != (("version", "", None),)
    ):
        raise CodexWorkerLaunchError(
            f"policy venue {venue} binary template must contain exactly one plain version field"
        )
    try:
        return template.format(version=version)
    except (AttributeError, IndexError, KeyError, ValueError) as exc:
        raise CodexWorkerLaunchError(
            f"policy venue {venue} has an invalid binary template"
        ) from exc


def _inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath((path, root)) == root
    except ValueError:
        return False


def _lexical_absolute(path: str, *, field: str) -> str:
    pure = PurePath(path)
    if not path or not pure.is_absolute():
        raise CodexWorkerLaunchError(f"{field} must be an absolute path")
    if ".." in pure.parts:
        raise CodexWorkerLaunchError(f"{field} must not contain '..'")
    return os.path.normpath(path)


def _real_directory(path: str, *, field: str, filesystem: LauncherFilesystem) -> str:
    normalized = _lexical_absolute(path, field=field)
    resolved = filesystem.realpath(normalized)
    if resolved != normalized:
        raise CodexWorkerLaunchError(f"{field} must be a real directory, not a symlink")
    if not filesystem.is_dir(resolved):
        raise CodexWorkerLaunchError(f"{field} must be an existing real directory")
    return resolved


def _read_contained_regular_file(
    path: str,
    *,
    root: str,
    field: str,
    filesystem: LauncherFilesystem,
) -> tuple[str, bytes]:
    normalized = _lexical_absolute(path, field=field)
    resolved = filesystem.realpath(normalized)
    if resolved != normalized:
        raise CodexWorkerLaunchError(f"{field} must not be a symlink")
    if not _inside(resolved, root) or resolved == root:
        raise CodexWorkerLaunchError(f"{field} escapes its canonical area")
    if not filesystem.is_file(resolved) or not filesystem.is_readable(resolved):
        raise CodexWorkerLaunchError(f"{field} must be a regular readable file")
    try:
        payload = filesystem.read_bytes(resolved)
    except OSError as exc:
        raise CodexWorkerLaunchError(f"{field} cannot be read") from exc
    return resolved, payload


def _parse_policy(raw_bytes: bytes, *, worktree: str, source_path: str) -> CodexOneShotPolicy:
    try:
        raw = yaml.safe_load(raw_bytes)
    except yaml.YAMLError as exc:
        raise CodexWorkerLaunchError("cannot parse canonical launcher policy") from exc
    if not isinstance(raw, dict) or set(raw) != POLICY_REQUIRED_KEYS:
        raise CodexWorkerLaunchError("policy keys must exactly match the v1 schema")
    if raw["kind"] != POLICY_KIND or raw["schema_version"] != POLICY_SCHEMA_VERSION:
        raise CodexWorkerLaunchError("unsupported launcher policy kind or schema_version")
    version = _require_string(raw["version"], "version")
    if not _VERSION_RE.fullmatch(version):
        raise CodexWorkerLaunchError("policy version must be a Codex deployment version")
    roles = _require_string_list(raw["supported_roles"], "supported_roles")
    if any(not _ROLE_RE.fullmatch(role) for role in roles):
        raise CodexWorkerLaunchError("policy supported_roles contains an invalid role name")
    _require_exact_v1_names(roles, V1_SUPPORTED_ROLES, "supported-role")
    raw_credentials = raw["role_provider_credentials"]
    if not isinstance(raw_credentials, dict) or set(raw_credentials) != set(roles):
        raise CodexWorkerLaunchError(
            "policy role_provider_credentials must define every supported role exactly once"
        )
    role_provider_credentials: list[tuple[str, tuple[str, ...]]] = []
    for role in roles:
        raw_role_credentials = raw_credentials[role]
        if not isinstance(raw_role_credentials, list) or any(
            not isinstance(name, str) for name in raw_role_credentials
        ):
            raise CodexWorkerLaunchError(
                f"policy role_provider_credentials.{role} must be a string list"
            )
        credentials = tuple(raw_role_credentials)
        if len(set(credentials)) != len(credentials):
            raise CodexWorkerLaunchError(
                f"policy role_provider_credentials.{role} must not contain duplicates"
            )
        if any(
            name not in ALLOWED_MODEL_PROVIDER_CREDENTIAL_ENV_NAMES
            for name in credentials
        ):
            raise CodexWorkerLaunchError(
                f"policy role_provider_credentials.{role} contains a non-provider credential"
            )
        role_provider_credentials.append((role, credentials))
    raw_venues = raw["venues"]
    if not isinstance(raw_venues, dict) or not raw_venues:
        raise CodexWorkerLaunchError("policy venues must be a nonempty mapping")
    _require_exact_v1_names(tuple(raw_venues), V1_VENUES, "venue")
    venues: list[VenuePolicy] = []
    for raw_name, raw_venue in raw_venues.items():
        name = _require_string(raw_name, "venue")
        if not isinstance(raw_venue, dict) or set(raw_venue) != VENUE_REQUIRED_KEYS:
            raise CodexWorkerLaunchError(f"policy venue {name} keys must exactly match the v1 schema")
        template = _require_string(raw_venue["codex_binary_template"], f"venues.{name}.codex_binary_template")
        rendered = _render_binary_template(template=template, version=version, venue=name)
        if not PurePath(rendered).is_absolute() or ".." in PurePath(rendered).parts:
            raise CodexWorkerLaunchError(f"policy venue {name} Codex binary must be absolute and nonescaping")
        attestation = raw_venue["outer_isolation_attestation"]
        if attestation is not None:
            attestation = _require_string(attestation, f"venues.{name}.outer_isolation_attestation")
        matrix = raw_venue["role_sandboxes"]
        if not isinstance(matrix, dict) or set(matrix) != set(roles):
            raise CodexWorkerLaunchError(f"policy venue {name} must define every supported role exactly once")
        role_sandboxes: list[tuple[str, str | None]] = []
        for role in roles:
            sandbox = matrix[role]
            if role == "implementer" and sandbox is not None:
                raise CodexWorkerLaunchError(
                    f"v1 implementer sandbox at venue {name} must be null"
                )
            if sandbox is not None:
                sandbox = _require_string(sandbox, f"venues.{name}.role_sandboxes.{role}")
                if sandbox not in ALLOWED_SANDBOXES:
                    raise CodexWorkerLaunchError(f"policy venue {name} has unsupported sandbox {sandbox}")
                if sandbox == "danger-full-access" and not attestation:
                    raise CodexWorkerLaunchError(
                        f"policy venue {name} danger-full-access requires outer isolation attestation"
                    )
                if role != "implementer" and sandbox == "danger-full-access":
                    raise CodexWorkerLaunchError("read-only roles may not receive danger-full-access")
            role_sandboxes.append((role, sandbox))
        venues.append(VenuePolicy(name, template, attestation, tuple(role_sandboxes)))
    defaults = raw["model_defaults"]
    if not isinstance(defaults, dict) or set(defaults) != {"model", "effort"}:
        raise CodexWorkerLaunchError("policy model_defaults must contain only model and effort")
    policy = CodexOneShotPolicy(
        policy_id=_require_string(raw["policy_id"], "policy_id"),
        version=version,
        supported_roles=roles,
        venues=tuple(venues),
        model=_require_string(defaults["model"], "model_defaults.model"),
        effort=_require_string(defaults["effort"], "model_defaults.effort"),
        role_provider_credentials=tuple(role_provider_credentials),
        canonical_add_dirs=_require_string_list(raw["canonical_add_dirs"], "canonical_add_dirs"),
        worktree=worktree,
        source_path=source_path,
        source_sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )
    _require_trusted_v1_matrix(policy)
    return policy


def load_canonical_policy(
    worktree: str | os.PathLike[str],
    *,
    filesystem: LauncherFilesystem | None = None,
) -> CodexOneShotPolicy:
    """Load exactly the canonical tracked policy from the allocated worktree."""
    fs = filesystem or RealLauncherFilesystem()
    root = _real_directory(os.fspath(worktree), field="worktree", filesystem=fs)
    policy_root = _real_directory(
        os.path.join(root, "governance", "policies"),
        field="canonical launcher policy area",
        filesystem=fs,
    )
    path, raw = _read_contained_regular_file(
        os.path.join(root, CANONICAL_POLICY_RELATIVE_PATH),
        root=policy_root,
        field="canonical launcher policy",
        filesystem=fs,
    )
    return _parse_policy(raw, worktree=root, source_path=path)


def load_governed_worker_input(
    *,
    worktree: str,
    role: str,
    brief_path: str,
    brief_sha256: str,
    filesystem: LauncherFilesystem | None = None,
) -> GovernedWorkerInput:
    """Read canonical role policy and verified brief exactly once and frame bytes."""
    fs = filesystem or RealLauncherFilesystem()
    root = _real_directory(worktree, field="worktree", filesystem=fs)
    if not _ROLE_RE.fullmatch(role):
        raise CodexWorkerLaunchError("role must be a canonical role name")
    if not _SHA256_RE.fullmatch(brief_sha256):
        raise CodexWorkerLaunchError("brief SHA-256 must be exactly 64 lowercase hex characters")
    role_root = _real_directory(
        os.path.join(root, CANONICAL_ROLE_AREA),
        field="canonical role policy area",
        filesystem=fs,
    )
    role_path, role_bytes = _read_contained_regular_file(
        os.path.join(role_root, f"{role}.md"),
        root=role_root,
        field="canonical role policy",
        filesystem=fs,
    )
    brief_root = _real_directory(
        os.path.join(root, CANONICAL_BRIEF_AREA),
        field="governed brief area",
        filesystem=fs,
    )
    if PurePath(brief_path).is_absolute():
        candidate = brief_path
    else:
        if ".." in PurePath(brief_path).parts:
            raise CodexWorkerLaunchError("governed brief escapes its canonical area")
        candidate = os.path.join(root, brief_path)
    brief_resolved, brief_bytes = _read_contained_regular_file(
        candidate,
        root=brief_root,
        field="governed brief",
        filesystem=fs,
    )
    actual_brief_sha256 = hashlib.sha256(brief_bytes).hexdigest()
    if actual_brief_sha256 != brief_sha256:
        raise CodexWorkerLaunchError("brief SHA-256 mismatch")
    role_sha256 = hashlib.sha256(role_bytes).hexdigest()
    header = (
        "CE-GOVERNED-CODEX-WORKER-PROMPT-V1\n"
        f"ROLE-SHA256 {role_sha256}\n"
        f"ROLE-BYTES {len(role_bytes)}\n"
        f"BRIEF-SHA256 {actual_brief_sha256}\n"
        f"BRIEF-BYTES {len(brief_bytes)}\n\n"
    ).encode("ascii")
    return GovernedWorkerInput(
        role=role,
        role_policy_path=role_path,
        role_policy_sha256=role_sha256,
        brief_path=brief_resolved,
        brief_sha256=actual_brief_sha256,
        stdin=header + role_bytes + brief_bytes,
    )


def _canonical_add_dirs(
    policy: CodexOneShotPolicy,
    worktree: str,
    *,
    filesystem: LauncherFilesystem,
) -> tuple[str, ...]:
    directories: list[str] = []
    for relative in policy.canonical_add_dirs:
        if PurePath(relative).is_absolute() or ".." in PurePath(relative).parts:
            raise CodexWorkerLaunchError("policy canonical_add_dirs must be relative and nonescaping")
        candidate = os.path.normpath(os.path.join(worktree, relative))
        if not _inside(candidate, worktree) or candidate == worktree:
            raise CodexWorkerLaunchError("policy canonical_add_dirs escapes the worktree")
        resolved = filesystem.realpath(candidate)
        if resolved != candidate:
            raise CodexWorkerLaunchError("canonical add-dir must not be a symlink")
        if not filesystem.is_dir(resolved):
            raise CodexWorkerLaunchError("canonical add-dir must be an existing real directory")
        directories.append(resolved)
    return tuple(directories)


def _derive_run_id(
    *, policy: CodexOneShotPolicy, role: str, venue: str, worktree: str, brief_sha256: str
) -> str:
    seed = json.dumps(
        {
            "policy_sha256": policy.source_sha256,
            "role": role,
            "venue": venue,
            "worktree": worktree,
            "brief_sha256": brief_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "codex-one-shot-" + hashlib.sha256(seed.encode()).hexdigest()[:16]


def _preflight_binary(
    *,
    policy: CodexOneShotPolicy,
    venue: VenuePolicy,
    filesystem: LauncherFilesystem,
    version_probe: CodexVersionProbe,
) -> str:
    declared = _lexical_absolute(
        _render_binary_template(
            template=venue.codex_binary_template,
            version=policy.version,
            venue=venue.name,
        ),
        field=f"policy Codex binary for {venue.name}",
    )
    parts = PurePath(declared).parts
    indexes = [index for index, part in enumerate(parts) if part == policy.version]
    if len(indexes) != 1:
        raise CodexWorkerLaunchError("policy Codex binary must live under its declared version root")
    version_root = os.path.normpath(str(PurePath(*parts[: indexes[0] + 1])))
    real_version_root = filesystem.realpath(version_root)
    if real_version_root != version_root:
        raise CodexWorkerLaunchError("Codex declared version root must not be a symlink")
    resolved = filesystem.realpath(declared)
    if not _inside(resolved, real_version_root) or resolved == real_version_root:
        raise CodexWorkerLaunchError("Codex binary symlink escapes the declared version root")
    if not filesystem.is_file(resolved) or not filesystem.is_executable(resolved):
        raise CodexWorkerLaunchError("policy Codex binary must be an existing regular executable")
    try:
        actual_version = version_probe.probe(resolved)
    except CodexWorkerLaunchError:
        raise
    except OSError as exc:
        raise CodexWorkerLaunchError("Codex version probe failed") from exc
    if actual_version != policy.version:
        raise CodexWorkerLaunchError(
            f"Codex version probe mismatch: expected {policy.version}, got {actual_version}"
        )
    return resolved


def build_launch_plan(
    *,
    policy: CodexOneShotPolicy,
    governed_input: GovernedWorkerInput,
    role: str,
    venue: str,
    worktree: str,
    run_id: str | None = None,
    filesystem: LauncherFilesystem | None = None,
    version_probe: CodexVersionProbe | None = None,
) -> CodexWorkerLaunchPlan:
    """Build a deterministic digest/path-only plan after all preflights pass."""
    _require_trusted_v1_matrix(policy)
    for venue_policy in policy.venues:
        _render_binary_template(
            template=venue_policy.codex_binary_template,
            version=policy.version,
            venue=venue_policy.name,
        )
    fs = filesystem or RealLauncherFilesystem()
    probe = version_probe or SubprocessCodexVersionProbe()
    root = _real_directory(worktree, field="worktree", filesystem=fs)
    if root != policy.worktree:
        raise CodexWorkerLaunchError("policy does not belong to the allocated worktree")
    if role not in policy.supported_roles:
        raise CodexWorkerLaunchError(f"unknown role: {role}")
    if governed_input.role != role:
        raise CodexWorkerLaunchError("governed role policy does not match requested role")
    if not _inside(governed_input.role_policy_path, root) or not _inside(governed_input.brief_path, root):
        raise CodexWorkerLaunchError("governed input does not belong to the allocated worktree")
    venue_policy = policy.venue(venue)
    sandbox = venue_policy.sandbox_for(role)
    add_dirs = _canonical_add_dirs(policy, root, filesystem=fs)
    state_root = _real_directory(
        os.path.join(root, ".ce", "state"), field="worktree state root", filesystem=fs
    )
    binary = _preflight_binary(
        policy=policy, venue=venue_policy, filesystem=fs, version_probe=probe
    )
    chosen_run_id = run_id or _derive_run_id(
        policy=policy,
        role=role,
        venue=venue,
        worktree=root,
        brief_sha256=governed_input.brief_sha256,
    )
    if not _RUN_ID_RE.fullmatch(chosen_run_id):
        raise CodexWorkerLaunchError("run_id must be lowercase slug text")
    output = os.path.join(state_root, f"{chosen_run_id}.json")
    if not _inside(output, state_root):
        raise CodexWorkerLaunchError("deterministic output escapes the real worktree state root")
    if fs.realpath(output) != output:
        raise CodexWorkerLaunchError("deterministic output must not be a symlink")
    if fs.lexists(output) and not fs.is_file(output):
        raise CodexWorkerLaunchError("deterministic output must be a regular file when it already exists")
    argv = [
        binary,
        "exec",
        "--ephemeral",
        "-m",
        policy.model,
        "-c",
        f"model_reasoning_effort={policy.effort}",
        "-c",
        "features.multi_agent=false",
        "-c",
        "features.multi_agent_v2=false",
        "-s",
        sandbox,
        "-C",
        root,
    ]
    for directory in add_dirs:
        argv.extend(("--add-dir", directory))
    argv.extend(("-o", output, "-"))
    return CodexWorkerLaunchPlan(
        policy_id=policy.policy_id,
        policy_version=policy.version,
        policy_path=policy.source_path,
        policy_sha256=policy.source_sha256,
        role=role,
        role_policy_path=governed_input.role_policy_path,
        role_policy_sha256=governed_input.role_policy_sha256,
        brief_path=governed_input.brief_path,
        brief_sha256=governed_input.brief_sha256,
        venue=venue,
        sandbox=sandbox,
        model=policy.model,
        effort=policy.effort,
        provider_credential_env_names=policy.provider_credentials_for(role),
        worktree=root,
        run_id=chosen_run_id,
        output=output,
        argv=tuple(argv),
    )


def launch(
    plan: CodexWorkerLaunchPlan,
    *,
    governed_input: GovernedWorkerInput,
    runner: CodexOneShotRunner,
) -> int:
    """Execute only if the verified input metadata is exactly plan-bound."""
    if (
        plan.role != governed_input.role
        or plan.role_policy_path != governed_input.role_policy_path
        or plan.role_policy_sha256 != governed_input.role_policy_sha256
        or plan.brief_path != governed_input.brief_path
        or plan.brief_sha256 != governed_input.brief_sha256
    ):
        raise CodexWorkerLaunchError("governed stdin does not match the launch plan")
    try:
        return runner.run(
            plan.argv,
            stdin=governed_input.stdin,
            provider_credential_env_names=plan.provider_credential_env_names,
        )
    except CodexWorkerLaunchError:
        raise
    except Exception as exc:
        raise CodexWorkerLaunchError("Codex subprocess execution failed") from exc
