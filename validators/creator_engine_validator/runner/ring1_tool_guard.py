"""Runner-owned Ring-1 PATH shims for shell-level git/gh mediation.

This increment is deliberately narrow: it proves harness-agnostic shell-level
``git``/``gh`` denial by putting CE-rendered shims first on ``PATH`` inside a
runner sandbox. It pins governed posture in the rendered shim, so a child
process cannot downgrade hard-denies by rewriting posture environment. It does
not harden absolute binary paths, bundled binaries, libgit2/JGit, raw HTTPS API
clients, PATH resets, or arbitrary filesystem syscalls. Those escape-hardening
layers are later gates.

The shims call the public ``creator_engine_validator hook-check`` CLI seam and
parse its raw JSON decision. Runner code must not import the v1 ``hook_check``
module directly; the version-boundary guard relies on that separation.
"""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass


DEFAULT_SHIM_DIR = "/tmp/ce-ring1-tool-guard"
DEFAULT_BASE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
DEFAULT_EVIDENCE_ROOT = ".ce/state/ring1"
DEFAULT_POSTURE = "governed"
DEFAULT_VALIDATOR_ARGV = ("python", "-m", "creator_engine_validator")
DEFAULT_REAL_BINARIES = (("git", "/usr/bin/git"), ("gh", "/usr/bin/gh"))
# A deliberately non-standard exit code so a CE Ring-1 denial is observably
# distinct from shell exit 126 ("command found but not executable"), which a
# real exec failure would emit. Observability only — the deny semantics are
# unchanged; only the emitted code value differs.
DENY_EXIT_CODE = 121


@dataclass(frozen=True)
class Ring1ToolGuardConfig:
    """Configuration for runner-installed command shims.

    ``posture`` is intentionally hard-pinned to ``governed`` for runner shims.
    ``tools`` is the guarded command surface for this first slice. ``real_binaries``
    pins the downstream executable each shim may exec after an allow decision.
    ``validator_argv`` invokes the public validator CLI and must name a command
    that accepts ``hook-check`` as its next argument.
    """

    posture: str = DEFAULT_POSTURE
    evidence_root: str = DEFAULT_EVIDENCE_ROOT
    posture_root: str | None = None
    ledger_root: str | None = None
    posture_env: str = "CE_RING1_POSTURE"
    posture_root_env: str = "CE_RING1_POSTURE_ROOT"
    evidence_root_env: str = "CE_RING1_EVIDENCE_ROOT"
    ledger_root_env: str = "CE_LEDGER_ROOT"
    reviewer_authority_ref_env: str = "CE_REVIEWER_AUTHORITY_REF"
    base_path: str = DEFAULT_BASE_PATH
    tools: tuple[str, ...] = ("git", "gh")
    real_binaries: tuple[tuple[str, str], ...] = DEFAULT_REAL_BINARIES
    validator_argv: tuple[str, ...] = DEFAULT_VALIDATOR_ARGV

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


@dataclass(frozen=True)
class Ring1GuardRuntime:
    """Installed guard directory plus environment injected into sandbox runs."""

    shim_dir: str
    env: dict[str, str]


def _real_binary_for(tool: str, config: Ring1ToolGuardConfig) -> str:
    return dict(config.real_binaries)[tool]


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
        "deny_exit_code": DENY_EXIT_CODE,
    }
    constants_json = json.dumps(constants, sort_keys=True)
    return f"""#!/usr/bin/env sh
# Generated by creator_engine_validator.runner.ring1_tool_guard.
# Increment 1 coverage: PATH-precedence shell shims for git/gh only. This is
# bypassable via absolute binaries, bundled clients, libgit2/JGit, raw HTTPS,
# PATH resets, and non-shell filesystem access; hardening is a later gate.
set -eu

if command -v python3 >/dev/null 2>&1; then
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
    completed = subprocess.run(
        argv,
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
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

    lines = [
        "#!/usr/bin/env sh",
        "set -eu",
        f"mkdir -p {shlex.quote(target_dir)}",
        f"chmod 0755 {shlex.quote(target_dir)}",
    ]
    for tool in config.tools:
        shim = render_posix_tool_shim(tool, _real_binary_for(tool, config), config)
        delimiter = f"__CE_RING1_{tool.upper()}_SHIM__"
        if delimiter in shim:
            raise ValueError(f"rendered shim for {tool!r} contains heredoc delimiter")
        target = f"{target_dir.rstrip('/')}/{tool}"
        lines.extend(
            [
                f"rm -f {shlex.quote(target)}",
                f"cat > {shlex.quote(target)} <<'{delimiter}'",
                shim.rstrip("\n"),
                delimiter,
                f"chmod 0555 {shlex.quote(target)}",
            ]
        )
    return "\n".join(lines) + "\n"


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


def build_runtime(
    config: Ring1ToolGuardConfig, shim_dir: str = DEFAULT_SHIM_DIR
) -> Ring1GuardRuntime:
    """Build the runtime descriptor for an installed guard directory."""

    return Ring1GuardRuntime(shim_dir=shim_dir, env=guarded_env(config, shim_dir))
