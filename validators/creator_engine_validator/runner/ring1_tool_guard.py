"""Runner-owned Ring-1 PATH shims for shell-level git/gh mediation.

This runner surface puts CE-rendered shims first on ``PATH`` inside a sandbox
and pins governed posture plus launcher-owned worker context in the rendered
shim, so a child process cannot downgrade hard-denies by rewriting posture or
``CE_WORKER_*`` environment. Absolute/bundled executable spelling is mediated by
the hook-check command classifier before shell execution; the shim layer covers
the default runtime command names.

The shims call the public ``creator_engine_validator hook-check`` CLI seam and
parse its raw JSON decision. Runner code must not import the v1 ``hook_check``
module directly; the version-boundary guard relies on that separation.
"""

from __future__ import annotations

import json
import os
import shlex
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fs_mediation import (
    FsMediationCapability,
    RunnerFsConfinement,
    build_runner_fs_capability,
    landlock_preexec,
)
from ..secret_paths import is_secret_path


_DEFAULT_SHIM_OWNER = str(os.getuid()) if hasattr(os, "getuid") else "nouid"
DEFAULT_SHIM_PARENT = f"/tmp/ce-ring1-tool-guard-{_DEFAULT_SHIM_OWNER}-{os.getpid()}"
DEFAULT_SHIM_DIR = f"{DEFAULT_SHIM_PARENT}/shim"
DEFAULT_BASE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
DEFAULT_EVIDENCE_ROOT = ".ce/state/ring1"
DEFAULT_POSTURE = "governed"
DEFAULT_VALIDATOR_ARGV = ("python", "-m", "creator_engine_validator")
DEFAULT_GUARDED_TOOLS = (
    "git",
    "gh",
    "ce",
    "ce-preflight.sh",
    "ce-preflight",
    "tar",
    "bsdtar",
    "gtar",
    "unzip",
    "python",
    "python3",
    "carrier-gen",
    "carrier_gen",
)
DEFAULT_REAL_BINARIES = (
    ("git", "/usr/bin/git"),
    ("gh", "/usr/bin/gh"),
    ("ce", "/usr/local/bin/ce"),
    ("ce-preflight.sh", "/usr/local/bin/ce-preflight.sh"),
    ("ce-preflight", "/usr/local/bin/ce-preflight"),
    ("tar", "/usr/bin/tar"),
    ("bsdtar", "/usr/bin/bsdtar"),
    ("gtar", "/usr/bin/gtar"),
    ("unzip", "/usr/bin/unzip"),
    ("python", "/usr/bin/python"),
    ("python3", "/usr/bin/python3"),
    ("carrier-gen", "/usr/local/bin/carrier-gen"),
    ("carrier_gen", "/usr/local/bin/carrier_gen"),
)
WORKER_CONTEXT_ENV_KEYS = {
    "worker_id": "CE_WORKER_ID",
    "record_ref": "CE_WORKER_RECORD_REF",
    "role": "CE_WORKER_ROLE",
    "lane_kind": "CE_WORKER_LANE_KIND",
    "scope_id": "CE_WORKER_SCOPE_ID",
    "worktree_path": "CE_WORKER_WORKTREE_PATH",
    "seat_id": "CE_WORKER_SEAT_ID",
    "actor": "CE_WORKER_ACTOR",
    "process_id": "CE_WORKER_PROCESS_ID",
}
# A deliberately non-standard exit code so a CE Ring-1 denial is observably
# distinct from shell exit 126 ("command found but not executable"), which a
# real exec failure would emit. Observability only — the deny semantics are
# unchanged; only the emitted code value differs.
DENY_EXIT_CODE = 121


class Ring1ShimRootError(RuntimeError):
    """The Ring-1 shim root is unsafe and must not be allow-listed."""


@dataclass(frozen=True)
class Ring1ToolGuardConfig:
    """Configuration for runner-installed command shims.

    ``posture`` is intentionally hard-pinned to ``governed`` for runner shims.
    ``tools`` is the guarded command surface for this first slice. ``real_binaries``
    pins the downstream executable each shim may exec after an allow decision.
    ``validator_argv`` invokes the public validator CLI and must name a command
    that accepts ``hook-check`` as its next argument. ``extra_read_roots`` names
    runner-owned runtime code/config roots that must remain readable after
    Section-8c Landlock is installed.
    """

    posture: str = DEFAULT_POSTURE
    evidence_root: str = DEFAULT_EVIDENCE_ROOT
    posture_root: str | None = None
    ledger_root: str | None = None
    extra_read_roots: tuple[str, ...] = ()
    posture_env: str = "CE_RING1_POSTURE"
    posture_root_env: str = "CE_RING1_POSTURE_ROOT"
    evidence_root_env: str = "CE_RING1_EVIDENCE_ROOT"
    ledger_root_env: str = "CE_LEDGER_ROOT"
    reviewer_authority_ref_env: str = "CE_REVIEWER_AUTHORITY_REF"
    base_path: str = DEFAULT_BASE_PATH
    tools: tuple[str, ...] = DEFAULT_GUARDED_TOOLS
    real_binaries: tuple[tuple[str, str], ...] = DEFAULT_REAL_BINARIES
    validator_argv: tuple[str, ...] = DEFAULT_VALIDATOR_ARGV
    worker_context: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.posture != DEFAULT_POSTURE:
            raise ValueError("runner Ring-1 tool guard posture is hard-pinned to 'governed'")
        if not self.tools:
            raise ValueError("at least one guarded tool is required")
        if not self.validator_argv:
            raise ValueError("validator_argv must not be empty")
        for label, value in (
            ("posture_root", self.posture_root),
            ("ledger_root", self.ledger_root),
        ):
            if value is not None and not value:
                raise ValueError(f"{label} must be non-empty when provided")
        for root in self.extra_read_roots:
            if not isinstance(root, str) or not root:
                raise ValueError(f"extra_read_roots entries must be non-empty strings: {root!r}")
        real = dict(self.real_binaries)
        for tool in self.tools:
            if not tool or "/" in tool:
                raise ValueError(f"guarded tool must be a bare command name: {tool!r}")
            if tool not in real or not real[tool]:
                raise ValueError(f"missing real binary path for guarded tool {tool!r}")
        for name in (
            self.posture_env,
            self.posture_root_env,
            self.evidence_root_env,
            self.ledger_root_env,
            self.reviewer_authority_ref_env,
        ):
            if not name or "=" in name:
                raise ValueError(f"invalid environment variable name {name!r}")
        if self.worker_context is not None:
            if not isinstance(self.worker_context, dict):
                raise ValueError("worker_context must be a mapping when provided")
            unknown = set(self.worker_context) - set(WORKER_CONTEXT_ENV_KEYS)
            if unknown:
                raise ValueError(f"unknown worker_context key(s): {sorted(unknown)!r}")
            required = set(WORKER_CONTEXT_ENV_KEYS) - {"process_id"}
            missing = required - set(self.worker_context)
            if missing:
                raise ValueError(f"incomplete worker_context missing key(s): {sorted(missing)!r}")
            for key, value in self.worker_context.items():
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"worker_context {key!r} must be a non-empty string")


@dataclass(frozen=True)
class Ring1GuardRuntime:
    """Installed guard directory plus launch mediation for sandbox runs."""

    shim_dir: str
    env: dict[str, str]
    fs_confinement: RunnerFsConfinement
    fs_capability: FsMediationCapability
    fs_preexec_fn: Callable[[], None] | None


def _real_binary_for(tool: str, config: Ring1ToolGuardConfig) -> str:
    return dict(config.real_binaries)[tool]


def _current_uid() -> int | None:
    return os.getuid() if hasattr(os, "getuid") else None


def _iter_existing_components(path: Path) -> list[Path]:
    """Return existing path components from root to ``path`` for lstat checks."""

    if not path.is_absolute():
        raise Ring1ShimRootError(f"Ring-1 shim root must be absolute: {path}")
    current = Path(path.anchor)
    components: list[Path] = []
    for part in path.parts[1:]:
        current = current / part
        if current.exists() or current.is_symlink():
            components.append(current)
    return components


def _reject_symlink_components(path: Path) -> None:
    for component in _iter_existing_components(path):
        try:
            st = os.lstat(component)
        except OSError as exc:
            raise Ring1ShimRootError(
                f"failed to inspect Ring-1 shim path component {component}: {exc}"
            ) from exc
        if stat.S_ISLNK(st.st_mode):
            raise Ring1ShimRootError(
                f"refusing unsafe Ring-1 shim root {path}: path component "
                f"{component} is a symlink"
            )


def _validate_owned_private_dir(path: Path, *, label: str) -> None:
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise Ring1ShimRootError(f"failed to inspect Ring-1 {label} {path}: {exc}") from exc
    if stat.S_ISLNK(st.st_mode):
        raise Ring1ShimRootError(f"refusing Ring-1 {label} {path}: it is a symlink")
    if not stat.S_ISDIR(st.st_mode):
        raise Ring1ShimRootError(f"refusing Ring-1 {label} {path}: it is not a directory")
    uid = _current_uid()
    if uid is not None and st.st_uid != uid:
        raise Ring1ShimRootError(
            f"refusing Ring-1 {label} {path}: owner uid {st.st_uid} != current uid {uid}"
        )
    if stat.S_IMODE(st.st_mode) & 0o077:
        raise Ring1ShimRootError(
            f"refusing Ring-1 {label} {path}: mode {stat.S_IMODE(st.st_mode):04o} "
            "is not private"
        )


def prepare_shim_root(shim_dir: str) -> str:
    """Create and validate the Ring-1 shim root, returning its real path.

    The returned path is the only shim root allowed into Landlock read roots.
    This closes the symlink-TOCTOU gap where a predictable ``/tmp`` path could be
    pre-created as a symlink to a credential-bearing directory before Landlock
    opened the configured root.
    """

    raw = Path(shim_dir)
    if not raw.is_absolute():
        raise Ring1ShimRootError(f"Ring-1 shim root must be absolute: {shim_dir!r}")
    _reject_symlink_components(raw)

    parent = raw.parent
    if not parent.exists():
        parent.mkdir(mode=0o700, parents=True, exist_ok=False)
    _reject_symlink_components(raw)
    _validate_owned_private_dir(parent, label="shim parent")

    if raw.exists() or raw.is_symlink():
        _validate_owned_private_dir(raw, label="shim root")
    else:
        try:
            raw.mkdir(mode=0o700)
        except FileExistsError:
            _validate_owned_private_dir(raw, label="shim root")
    _reject_symlink_components(raw)
    _validate_owned_private_dir(raw, label="shim root")

    resolved = Path(os.path.realpath(raw))
    label = is_secret_path(str(resolved))
    if label is not None:
        raise Ring1ShimRootError(
            f"refusing Ring-1 shim root {raw}: resolved path {resolved} is "
            f"credential-shaped (matched rule: {label})"
        )
    return str(resolved)


def render_posix_tool_shim(
    tool: str, real_binary: str, config: Ring1ToolGuardConfig
) -> str:
    """Render one executable shim.

    The shim builds a Bash-shaped PreToolUse event, calls the validator CLI with
    ``--format raw``, parses the JSON decision, and converts ``deny``/``block``
    to exit ``DENY_EXIT_CODE`` (121) before the real binary can run.
    """

    if tool not in config.tools:
        raise ValueError(f"{tool!r} is not enabled in this guard config")
    constants = {
        "tool": tool,
        "real_binary": real_binary,
        "validator_argv": list(config.validator_argv),
        "posture": config.posture,
        "default_evidence_root": config.evidence_root,
        "posture_root": config.posture_root or "",
        "evidence_root_env": config.evidence_root_env,
        "ledger_root": config.ledger_root or "",
        "reviewer_authority_ref_env": config.reviewer_authority_ref_env,
        "worker_context": dict(config.worker_context or {}),
        "worker_context_env_keys": WORKER_CONTEXT_ENV_KEYS,
        "deny_exit_code": DENY_EXIT_CODE,
    }
    constants_json = json.dumps(constants, sort_keys=True)
    return f"""#!/usr/bin/env sh
# Generated by creator_engine_validator.runner.ring1_tool_guard.
# Default runtime coverage: governed PATH shims for Ring-1 command names.
# Absolute/bundled spelling is classified by hook-check before shell exec.
set -eu

if [ -x /usr/bin/python3 ]; then
    _ce_ring1_python=/usr/bin/python3
elif [ -x /usr/local/bin/python3 ]; then
    _ce_ring1_python=/usr/local/bin/python3
elif [ -x /usr/bin/python ]; then
    _ce_ring1_python=/usr/bin/python
elif command -v python3 >/dev/null 2>&1; then
    _ce_ring1_python=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
    _ce_ring1_python=$(command -v python)
else
    echo "CE Ring-1 guard: python is required to evaluate hook-check; refusing {tool}" >&2
    exit {DENY_EXIT_CODE}
fi

exec "$_ce_ring1_python" - "$@" <<'PY'
import json
import os
import shlex
import subprocess
import sys

CFG = {constants_json}


def _fail(message):
    print(f"CE Ring-1 guard: {{message}}", file=sys.stderr)
    raise SystemExit(CFG["deny_exit_code"])


tool_args = sys.argv[1:]
command = shlex.join([CFG["tool"], *tool_args])
posture = CFG["posture"]
evidence_root = os.environ.get(CFG["evidence_root_env"], CFG["default_evidence_root"])
posture_root = CFG["posture_root"] or os.getcwd()

event = {{
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {{"command": command}},
    "cwd": os.getcwd(),
    "ce": {{
        "posture": posture,
        "evidence_root": evidence_root,
    }},
}}
worker_context = dict(CFG["worker_context"])
if worker_context:
    worker_context["process_id"] = str(os.getpid())
    event["ce"]["authenticated_worker_context"] = dict(worker_context)

argv = [
    *CFG["validator_argv"],
    "hook-check",
    "--stdin",
    "--format",
    "raw",
    "--posture",
    posture,
    "--posture-root",
    posture_root,
    "--evidence-root",
    evidence_root,
]
ledger_root = CFG["ledger_root"]
if ledger_root:
    argv.extend(["--ledger-root", ledger_root])
reviewer_ref = os.environ.get(CFG["reviewer_authority_ref_env"])
if reviewer_ref:
    argv.extend(["--reviewer-authority-ref", reviewer_ref])

try:
    hook_env = {{
        key: value
        for key, value in os.environ.items()
        if not key.startswith("CE_WORKER_")
    }}
    for key, env_name in CFG["worker_context_env_keys"].items():
        value = worker_context.get(key)
        if value:
            hook_env[env_name] = value
    completed = subprocess.run(
        argv,
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
        env=hook_env,
    )
except OSError as exc:
    _fail(f"hook-check CLI could not be executed for {{CFG['tool']}}: {{exc}}")

if completed.returncode != 0:
    detail = (completed.stderr or completed.stdout or "").strip()
    suffix = f": {{detail}}" if detail else ""
    _fail(f"hook-check CLI failed for {{CFG['tool']}}{{suffix}}")

try:
    decision_payload = json.loads(completed.stdout)
except (TypeError, ValueError) as exc:
    _fail(f"hook-check returned invalid JSON for {{CFG['tool']}}: {{exc}}")
if not isinstance(decision_payload, dict):
    _fail(f"hook-check returned a non-object decision for {{CFG['tool']}}")

decision = decision_payload.get("decision")
posture_seen = decision_payload.get("posture", "unknown")
reason = str(decision_payload.get("reason") or "no reason supplied")

if decision == "allow":
    try:
        os.execv(CFG["real_binary"], [CFG["tool"], *tool_args])
    except OSError as exc:
        _fail(f"allowed {{CFG['tool']}} could not exec real binary {{CFG['real_binary']}}: {{exc}}")

if decision in {{"deny", "block"}}:
    print(
        f"CE Ring-1 guard: {{CFG['tool']}} {{decision}} by hook-check "
        f"(posture={{posture_seen}}): {{reason}}",
        file=sys.stderr,
    )
    raise SystemExit(CFG["deny_exit_code"])

_fail(f"hook-check returned malformed decision {{decision!r}} for {{CFG['tool']}}")
PY
"""


def render_install_script(config: Ring1ToolGuardConfig, target_dir: str) -> str:
    """Render a POSIX install script that writes all configured tool shims."""

    shims: list[tuple[str, str]] = []
    execution_plane_shims: list[tuple[str, str]] = []
    for tool in config.tools:
        shim = render_posix_tool_shim(tool, _real_binary_for(tool, config), config)
        if tool in {"git", "gh"}:
            shims.append((tool, shim))
        else:
            execution_plane_shims.append((tool, shim))
    payload = json.dumps(
        {
            "target_dir": target_dir,
            "shims": shims,
            "execution_plane_shims": execution_plane_shims,
        },
        sort_keys=True,
    )
    return f"""#!/usr/bin/env sh
set -eu

if command -v python3 >/dev/null 2>&1; then
    _ce_ring1_python=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
    _ce_ring1_python=$(command -v python)
else
    echo "CE Ring-1 guard install: python is required to install shims" >&2
    exit 1
fi

exec "$_ce_ring1_python" - <<'PY'
import json
import os
import stat
import sys

PAYLOAD = json.loads({payload!r})


def fail(message):
    print(f"CE Ring-1 guard install: {{message}}", file=sys.stderr)
    raise SystemExit(1)


def reject_symlink_components(path):
    current = os.path.abspath(os.sep)
    for part in os.path.abspath(path).split(os.sep)[1:]:
        current = os.path.join(current, part)
        if os.path.lexists(current):
            st = os.lstat(current)
            if stat.S_ISLNK(st.st_mode):
                fail(f"refusing unsafe shim path {{path}}: component {{current}} is a symlink")


def validate_private_dir(path, label):
    try:
        st = os.lstat(path)
    except OSError as exc:
        fail(f"failed to inspect {{label}} {{path}}: {{exc}}")
    if stat.S_ISLNK(st.st_mode):
        fail(f"refusing {{label}} {{path}}: it is a symlink")
    if not stat.S_ISDIR(st.st_mode):
        fail(f"refusing {{label}} {{path}}: it is not a directory")
    if hasattr(os, "getuid") and st.st_uid != os.getuid():
        fail(f"refusing {{label}} {{path}}: not owned by current uid")
    if stat.S_IMODE(st.st_mode) & 0o077:
        fail(f"refusing {{label}} {{path}}: mode {{stat.S_IMODE(st.st_mode):04o}} is not private")


target_dir = PAYLOAD["target_dir"]
if not os.path.isabs(target_dir):
    fail(f"shim directory must be absolute: {{target_dir!r}}")
reject_symlink_components(target_dir)
parent = os.path.dirname(target_dir)
if not os.path.exists(parent):
    os.makedirs(parent, mode=0o700, exist_ok=False)
reject_symlink_components(target_dir)
validate_private_dir(parent, "shim parent")
if os.path.lexists(target_dir):
    validate_private_dir(target_dir, "shim directory")
else:
    os.mkdir(target_dir, 0o700)
validate_private_dir(target_dir, "shim directory")

for tool, content in [*PAYLOAD["shims"], *PAYLOAD.get("execution_plane_shims", [])]:
    if not tool or os.path.sep in tool or tool in (".", ".."):
        fail(f"invalid shim name {{tool!r}}")
    target = os.path.join(target_dir, tool)
    if os.path.lexists(target):
        st = os.lstat(target)
        if stat.S_ISLNK(st.st_mode):
            fail(f"refusing to replace symlink shim {{target}}")
        os.unlink(target)
    tmp = os.path.join(target_dir, f".{{tool}}.{{os.getpid()}}.tmp")
    try:
        fd = os.open(
            tmp,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o500,
        )
    except FileExistsError:
        fail(f"exclusive shim temp already exists: {{tmp}}")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            if not content.endswith("\\n"):
                fh.write("\\n")
        os.replace(tmp, target)
        os.chmod(target, 0o500)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
PY
"""


def guarded_env(config: Ring1ToolGuardConfig, shim_dir: str) -> dict[str, str]:
    """Return environment values to inject when running inside the sandbox."""

    env = {
        "PATH": f"{shim_dir}:{config.base_path}",
        config.posture_env: config.posture,
        config.evidence_root_env: config.evidence_root,
    }
    if config.posture_root is not None:
        env[config.posture_root_env] = config.posture_root
    if config.ledger_root is not None:
        env[config.ledger_root_env] = config.ledger_root
    return env


def _workspace_read_roots(config: Ring1ToolGuardConfig, shim_dir: str) -> tuple[str, ...]:
    roots: list[str] = [config.posture_root or os.getcwd(), shim_dir]
    if config.ledger_root is not None and config.ledger_root not in roots:
        roots.append(config.ledger_root)
    for root in config.extra_read_roots:
        if root not in roots:
            roots.append(root)
    return tuple(roots)


def build_runtime(
    config: Ring1ToolGuardConfig,
    shim_dir: str = DEFAULT_SHIM_DIR,
    *,
    require_fs_enforcement: bool = True,
) -> Ring1GuardRuntime:
    """Build the runtime descriptor for an installed guard directory."""

    resolved_shim_dir = prepare_shim_root(shim_dir)
    confinement = RunnerFsConfinement(
        workspace_read_roots=_workspace_read_roots(config, resolved_shim_dir)
    )
    capability = build_runner_fs_capability(
        confinement, require_enforcement=require_fs_enforcement
    )
    fs_preexec_fn = landlock_preexec(confinement) if capability.sandbox_fs_enforced else None
    return Ring1GuardRuntime(
        shim_dir=resolved_shim_dir,
        env=guarded_env(config, resolved_shim_dir),
        fs_confinement=confinement,
        fs_capability=capability,
        fs_preexec_fn=fs_preexec_fn,
    )
