"""Fresh capability probes for the Knowledge-SSOT brain surface.

Capability probes deliberately interrogate current reality. They do not cache
answers and they never convert an unknown capability into a guessed verdict.
"""

from __future__ import annotations

import ast
import getpass
import importlib
import json
import os
import platform
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Sequence

import yaml

from .wheel_source_parity import verify_wheel_matches_source

Verdict = Literal["present", "absent", "unknown"]
ProbeFn = Callable[["ProbeContext"], "ProbeResult"]

CODE_PROBE_DISAGREEMENT = "brain_assertion_probe_disagreement"
CODE_PROBE_EXPECTED_VERDICT = "brain_assertion_probe_expected_verdict"
PROBE_EVIDENCE_PREFIX = "probe:"
_VERDICTS: frozenset[str] = frozenset({"present", "absent", "unknown"})
_TRUE_VALUES = {"1", "true", "yes", "on", "present", "enabled"}
_FALSE_VALUES = {"0", "false", "no", "off", "absent", "disabled"}
_FAN_OUT_ENV_KEYS = (
    "CE_HARNESS_FAN_OUT",
    "CE_MULTI_AGENT_FAN_OUT",
    "CODEX_SUBAGENTS",
)
SELF_IDENTITY_PROBE = "self_identity"
SELF_IDENTITY_EXPECTED_EVIDENCE_KEY = "expected_live_evidence"
SELF_IDENTITY_PROBE_EVIDENCE_PATHS = {
    "arch": ("arch",),
    "current_user": ("os_users", "current_user"),
    "runtime_name": ("runtime_name",),
}
SELF_IDENTITY_SEAT_SCOPE_KEYS = ("seat", "seat_id", "current_user")


def _default_run(command: Sequence[str]) -> Any:  # pragma: no cover - live edge
    return subprocess.run(
        list(command),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
    )


def _default_read_text(path: Path) -> str:  # pragma: no cover - live edge
    return path.read_text(encoding="utf-8")


def _default_wheel_source_checker(repo_root: Path) -> list[str]:
    root = Path(repo_root)
    source_root = root / "validators" / "creator_engine_validator"
    if not source_root.is_dir():
        return [f"missing validator source tree at {source_root}"]
    return verify_wheel_matches_source(root)


@dataclass(frozen=True)
class ProbeResult:
    name: str
    verdict: Verdict
    evidence: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": dict(self.evidence),
            "name": self.name,
            "verdict": self.verdict,
        }


@dataclass(frozen=True)
class ProbeContext:
    repo_root: Path | str = Path(".")
    env: Mapping[str, str] | None = None
    run: Callable[[Sequence[str]], Any] = _default_run
    read_text: Callable[[Path], str] = _default_read_text
    wheel_source_checker: Callable[[Path], list[str]] = _default_wheel_source_checker
    probes: Mapping[str, ProbeFn] | None = None

    def root(self) -> Path:
        return Path(self.repo_root)

    def environ(self) -> Mapping[str, str]:
        return os.environ if self.env is None else self.env


def _result(name: str, verdict: Verdict, evidence: Mapping[str, Any]) -> ProbeResult:
    return ProbeResult(name=name, verdict=verdict, evidence=evidence)


def _unknown(name: str, *, reason: str, error: BaseException | None = None) -> ProbeResult:
    evidence: dict[str, Any] = {"reason": reason}
    if error is not None:
        evidence["error"] = error.__class__.__name__
    return _result(name, "unknown", evidence)


def _returncode(completed: Any) -> int:
    return int(getattr(completed, "returncode"))


def _stdout(completed: Any) -> str:
    value = getattr(completed, "stdout", "")
    return value if isinstance(value, str) else ""


def _gh_authenticated(context: ProbeContext) -> ProbeResult:
    command = ["gh", "auth", "status"]
    try:
        completed = context.run(command)
        returncode = _returncode(completed)
    except Exception as exc:
        return _unknown("gh_authenticated", reason="probe_error", error=exc)
    verdict: Verdict = "present" if returncode == 0 else "absent"
    return _result("gh_authenticated", verdict, {"command": command, "returncode": returncode})


def _workflow_triggers(data: Any) -> Any:
    if not isinstance(data, dict):
        return None
    return data.get("on", data.get(True))


def _merge_group_trigger(context: ProbeContext) -> ProbeResult:
    path = context.root() / ".github" / "workflows" / "validate.yml"
    try:
        data = yaml.safe_load(context.read_text(path))
    except Exception as exc:
        return _unknown("merge_group_trigger", reason="probe_error", error=exc)
    triggers = _workflow_triggers(data)
    merge_group = None
    if isinstance(triggers, dict):
        merge_group = triggers.get("merge_group")
    elif isinstance(triggers, list):
        merge_group = "merge_group" if "merge_group" in triggers else None
    if merge_group is None:
        return _result("merge_group_trigger", "absent", {"workflow": str(path), "merge_group": False})
    types = merge_group.get("types") if isinstance(merge_group, dict) else None
    type_values = [str(item) for item in types] if isinstance(types, list) else []
    if type_values and "checks_requested" not in type_values:
        return _result(
            "merge_group_trigger",
            "absent",
            {"workflow": str(path), "merge_group": True, "types": type_values},
        )
    return _result(
        "merge_group_trigger",
        "present",
        {"workflow": str(path), "merge_group": True, "types": type_values},
    )


def _harness_fan_out(context: ProbeContext) -> ProbeResult:
    env = context.environ()
    present_keys = [key for key in _FAN_OUT_ENV_KEYS if key in env]
    for key in _FAN_OUT_ENV_KEYS:
        value = str(env.get(key, "")).strip().lower()
        if value in _TRUE_VALUES:
            return _result("harness_fan_out", "present", {"signal": key, "checked": list(_FAN_OUT_ENV_KEYS)})
        if value in _FALSE_VALUES:
            return _result("harness_fan_out", "absent", {"signal": key, "checked": list(_FAN_OUT_ENV_KEYS)})
    return _result(
        "harness_fan_out",
        "unknown",
        {"reason": "no_explicit_harness_signal", "checked": list(_FAN_OUT_ENV_KEYS), "present_keys": present_keys},
    )


def _codex_pretooluse_hook(context: ProbeContext) -> ProbeResult:
    path = context.root() / ".codex" / "hooks" / "ce-pretooluse-codex.py"
    try:
        text = context.read_text(path)
    except Exception as exc:
        return _unknown("codex_pretooluse_hook", reason="probe_error", error=exc)
    expected = "from creator_engine_validator.codex_pretooluse import main"
    present = path.is_file() and expected in text
    return _result(
        "codex_pretooluse_hook",
        "present" if present else "absent",
        {"hook": str(path), "imports_validator_entrypoint": expected in text},
    )


def _python_module_tree(context: ProbeContext, path: Path, probe_name: str) -> tuple[ast.Module | None, ProbeResult | None]:
    try:
        text = context.read_text(path)
        return ast.parse(text), None
    except Exception as exc:
        return None, _unknown(probe_name, reason="probe_error", error=exc)


def _function_def(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _assigned_value(tree: ast.Module, name: str) -> ast.AST | None:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return node.value
    return None


def _string_constants(node: ast.AST | None) -> list[str]:
    if node is None:
        return []
    return [child.value for child in ast.walk(node) if isinstance(child, ast.Constant) and isinstance(child.value, str)]


def _calls_name(node: ast.AST | None, name: str) -> bool:
    if node is None:
        return False
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == name:
            return True
    return False


def _is_attr(node: ast.AST, base: str, attr: str) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == attr and isinstance(node.value, ast.Name) and node.value.id == base


def _pr_preflight_ci_parity(context: ProbeContext) -> ProbeResult:
    name = "pr_preflight_ci_parity"
    path = context.root() / "validators" / "creator_engine_validator" / "pr_preflight.py"
    tree, error = _python_module_tree(context, path, name)
    if error is not None or tree is None:
        return error or _unknown(name, reason="probe_error")
    default_command = _assigned_value(tree, "DEFAULT_TEST_COMMAND")
    default_markers = _string_constants(default_command)
    run_preflight = _function_def(tree, "run_preflight")
    invokes_baseline_diff = _calls_name(run_preflight, "_run_baseline_diff_tests")
    targets_validator_tree = any("validators/tests/" in marker for marker in default_markers)
    excludes_wheel_bake_gate = any("not wheel_bake_gate" in marker for marker in default_markers)
    present = targets_validator_tree and excludes_wheel_bake_gate and invokes_baseline_diff
    return _result(
        name,
        "present" if present else "absent",
        {
            "preflight": str(path),
            "default_command_targets_validator_tree": targets_validator_tree,
            "default_command_excludes_wheel_bake_gate": excludes_wheel_bake_gate,
            "run_preflight_invokes_baseline_diff_tests": invokes_baseline_diff,
        },
    )


def _pr_preflight_clean_tree_guard(context: ProbeContext) -> ProbeResult:
    name = "pr_preflight_clean_tree_guard"
    path = context.root() / "validators" / "creator_engine_validator" / "pr_preflight.py"
    tree, error = _python_module_tree(context, path, name)
    if error is not None or tree is None:
        return error or _unknown(name, reason="probe_error")
    fn = _function_def(tree, "_assert_clean_tree")
    checks_git_status = False
    allows_explicit_dirty_override = False
    raises_on_dirty_tree = False
    if fn is not None:
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_git_capture":
                args = node.args
                if args and any(value == "status" for value in _string_constants(args[0])):
                    checks_git_status = True
            if isinstance(node, ast.If) and _is_attr(node.test, "config", "allow_dirty"):
                allows_explicit_dirty_override = True
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                func = node.exc.func
                if isinstance(func, ast.Name) and func.id == "RuntimeError":
                    raises_on_dirty_tree = True
    present = checks_git_status and allows_explicit_dirty_override and raises_on_dirty_tree
    return _result(
        name,
        "present" if present else "absent",
        {
            "preflight": str(path),
            "function": "_assert_clean_tree",
            "checks_git_status": checks_git_status,
            "allows_explicit_dirty_override": allows_explicit_dirty_override,
            "raises_on_dirty_tree": raises_on_dirty_tree,
        },
    )


def _pr_preflight_scrubs_credential_env(context: ProbeContext) -> ProbeResult:
    name = "pr_preflight_scrubs_credential_env"
    path = context.root() / "validators" / "creator_engine_validator" / "pr_preflight.py"
    tree, error = _python_module_tree(context, path, name)
    if error is not None or tree is None:
        return error or _unknown(name, reason="probe_error")
    token_vars = set(_string_constants(_assigned_value(tree, "TOKEN_ENV_VARS")))
    fn = _function_def(tree, "_python_env")
    scrub_loop_present = False
    if fn is not None:
        for node in ast.walk(fn):
            if not isinstance(node, ast.If) or not isinstance(node.test, ast.Name) or node.test.id != "pytest":
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.For):
                    continue
                if not isinstance(child.target, ast.Name) or child.target.id != "key":
                    continue
                if not isinstance(child.iter, ast.Name) or child.iter.id != "TOKEN_ENV_VARS":
                    continue
                scrub_loop_present = any(
                    isinstance(call, ast.Call)
                    and _is_attr(call.func, "env", "pop")
                    and call.args
                    and isinstance(call.args[0], ast.Name)
                    and call.args[0].id == "key"
                    for call in ast.walk(child)
                )
    required_tokens = {"GH_TOKEN", "BAO_TOKEN", "OPENBAO_TOKEN", "CE_OVERWATCH_PAT"}
    present = required_tokens.issubset(token_vars) and scrub_loop_present
    return _result(
        name,
        "present" if present else "absent",
        {
            "preflight": str(path),
            "function": "_python_env",
            "required_token_env_vars_present": sorted(required_tokens.intersection(token_vars)),
            "scrubs_tokens_for_pytest": scrub_loop_present,
        },
    )


def _codex_fan_out_surfaces(context: ProbeContext) -> ProbeResult:
    root = context.root()
    required = [
        root / ".claude" / "agents" / "architect_research.md",
        root / ".claude" / "agents" / "implementer.md",
        root / ".claude" / "agents" / "reviewer.md",
        root / ".claude" / "agents" / "verification.md",
    ]
    missing: list[str] = []
    for path in required:
        try:
            text = context.read_text(path)
        except Exception:
            missing.append(str(path))
            continue
        if "Governed" not in text and "governed" not in text:
            missing.append(str(path))
    return _result(
        "codex_fan_out_surfaces",
        "absent" if missing else "present",
        {"required": [str(path) for path in required], "missing": missing},
    )


def _wheelhouse_matches_source(context: ProbeContext) -> ProbeResult:
    try:
        violations = context.wheel_source_checker(context.root())
    except Exception as exc:
        return _unknown("wheelhouse_matches_source", reason="probe_error", error=exc)
    verdict: Verdict = "present" if not violations else "absent"
    return _result(
        "wheelhouse_matches_source",
        verdict,
        {"violation_count": len(violations), "violations": list(violations)},
    )


def _current_user(env: Mapping[str, str]) -> str:
    for key in ("USER", "LOGNAME", "USERNAME"):
        value = str(env.get(key, "")).strip()
        if value:
            return value
    try:
        return getpass.getuser()
    except Exception:
        return ""


def _local_os_users(env: Mapping[str, str]) -> dict[str, Any]:
    user = _current_user(env)
    evidence: dict[str, Any] = {
        "current_user": user,
        "effective_uid": os.geteuid() if hasattr(os, "geteuid") else None,
    }
    try:
        import pwd  # pylint: disable=import-outside-toplevel

        evidence["known_users"] = sorted({entry.pw_name for entry in pwd.getpwall() if entry.pw_name})
    except Exception as exc:
        evidence["known_users"] = []
        evidence["known_users_error"] = exc.__class__.__name__
    return evidence


def _tailnet_identity(context: ProbeContext) -> dict[str, Any]:
    command = ["tailscale", "status", "--json"]
    try:
        completed = context.run(command)
        returncode = _returncode(completed)
    except Exception as exc:
        return {"command": command, "status": "unavailable", "error": exc.__class__.__name__, "reachable_peers": []}
    if returncode != 0:
        return {"command": command, "status": "absent", "returncode": returncode, "reachable_peers": []}
    try:
        payload = json.loads(_stdout(completed) or "{}")
    except json.JSONDecodeError as exc:
        return {
            "command": command,
            "status": "unparseable",
            "error": exc.__class__.__name__,
            "reachable_peers": [],
        }
    self_info = payload.get("Self") if isinstance(payload, dict) else None
    peers = payload.get("Peer") if isinstance(payload, dict) else None
    reachable: list[str] = []
    if isinstance(peers, Mapping):
        for peer in peers.values():
            if not isinstance(peer, Mapping) or peer.get("Online") is not True:
                continue
            label = peer.get("DNSName") or peer.get("HostName") or peer.get("ID")
            if isinstance(label, str) and label:
                reachable.append(label.rstrip("."))
    return {
        "command": command,
        "status": "present",
        "self": {
            "dns_name": self_info.get("DNSName", "").rstrip(".") if isinstance(self_info, Mapping) else "",
            "host_name": self_info.get("HostName", "") if isinstance(self_info, Mapping) else "",
            "tailnet_ips": sorted(self_info.get("TailscaleIPs", [])) if isinstance(self_info, Mapping) else [],
        },
        "reachable_peers": sorted(set(reachable)),
    }


def _gpu_identity(context: ProbeContext) -> dict[str, Any]:
    command = ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"]
    try:
        completed = context.run(command)
        returncode = _returncode(completed)
    except Exception as exc:
        return {"command": command, "status": "unavailable", "error": exc.__class__.__name__, "devices": []}
    if returncode != 0:
        return {"command": command, "status": "absent", "returncode": returncode, "devices": []}
    devices = sorted(line.strip() for line in _stdout(completed).splitlines() if line.strip())
    return {"command": command, "status": "present" if devices else "absent", "devices": devices}


def _self_identity(context: ProbeContext) -> ProbeResult:
    env = context.environ()
    env_hostname = str(env.get("HOSTNAME", "")).strip()
    try:
        socket_hostname = socket.gethostname()
    except Exception:
        socket_hostname = ""
    runtime_name = env_hostname or socket_hostname
    arch = platform.machine() or platform.processor()
    os_users = _local_os_users(env)
    tailnet = _tailnet_identity(context)
    gpu = _gpu_identity(context)
    evidence = {
        "arch": arch,
        "gpu": gpu,
        "os_users": os_users,
        "reachable_peers": tailnet.get("reachable_peers", []),
        "runtime_name": runtime_name,
        "socket_hostname": socket_hostname,
        "sources": {
            "arch": "platform.machine",
            "gpu": "nvidia-smi",
            "os_users": "os/getpass/pwd",
            "runtime_name": "env.HOSTNAME or socket.gethostname",
            "tailnet": "tailscale status --json",
        },
        "tailnet_self": tailnet,
    }
    verdict: Verdict = "present" if runtime_name and arch and os_users.get("current_user") else "unknown"
    return _result(SELF_IDENTITY_PROBE, verdict, evidence)


def _worker_spawn_runtime_support(context: ProbeContext) -> ProbeResult:
    evidence: dict[str, Any] = {
        "module": "creator_engine_validator.worker_spawn",
        "required_entrypoints": ["plan_worker_spawn", "spawn_worker"],
    }
    try:
        module = importlib.import_module("creator_engine_validator.worker_spawn")
    except Exception as exc:
        evidence["module_error"] = exc.__class__.__name__
        return _result("worker_spawn_runtime_support", "absent", evidence)
    missing_entrypoints = [
        name for name in evidence["required_entrypoints"] if not callable(getattr(module, name, None))
    ]
    evidence["missing_entrypoints"] = missing_entrypoints
    git_path = shutil.which("git")
    evidence["git_available"] = git_path is not None
    if git_path is None:
        return _result("worker_spawn_runtime_support", "absent", evidence)
    command = [git_path, "-C", str(context.root()), "worktree", "list", "--porcelain"]
    evidence["worktree_command"] = command
    try:
        completed = context.run(command)
        returncode = _returncode(completed)
    except Exception as exc:
        evidence["worktree_error"] = exc.__class__.__name__
        return _result("worker_spawn_runtime_support", "unknown", evidence)
    evidence["worktree_returncode"] = returncode
    verdict: Verdict = "present" if not missing_entrypoints and returncode == 0 else "absent"
    return _result("worker_spawn_runtime_support", verdict, evidence)


PROBES: dict[str, ProbeFn] = {
    "codex_fan_out_surfaces": _codex_fan_out_surfaces,
    "codex_pretooluse_hook": _codex_pretooluse_hook,
    "gh_authenticated": _gh_authenticated,
    "harness_fan_out": _harness_fan_out,
    "merge_group_trigger": _merge_group_trigger,
    "pr_preflight_ci_parity": _pr_preflight_ci_parity,
    "pr_preflight_clean_tree_guard": _pr_preflight_clean_tree_guard,
    "pr_preflight_scrubs_credential_env": _pr_preflight_scrubs_credential_env,
    SELF_IDENTITY_PROBE: _self_identity,
    "wheelhouse_matches_source": _wheelhouse_matches_source,
    "worker_spawn_runtime_support": _worker_spawn_runtime_support,
}


def probe(name: str, context: ProbeContext | None = None) -> ProbeResult:
    ctx = context or ProbeContext()
    injected = ctx.probes or {}
    fn = injected.get(name) or PROBES.get(name)
    if fn is None:
        return _unknown(name, reason="unknown_probe")
    try:
        result = fn(ctx)
    except Exception as exc:
        return _unknown(name, reason="probe_error", error=exc)
    if not isinstance(result, ProbeResult):
        return _unknown(name, reason="invalid_probe_result")
    if result.verdict not in _VERDICTS:
        return _unknown(name, reason="invalid_probe_verdict")
    if result.name != name:
        return ProbeResult(name=name, verdict=result.verdict, evidence=result.evidence)
    return result


def probe_all(context: ProbeContext | None = None) -> list[ProbeResult]:
    ctx = context or ProbeContext()
    return [probe(name, ctx) for name in sorted(PROBES)]


def record_probe_name(record: Mapping[str, Any]) -> str | None:
    verification_method = record.get("verification_method")
    if isinstance(verification_method, Mapping):
        method_type = verification_method.get("type")
        if method_type in {"static", "manual-attested"}:
            return None
        if method_type == "probe":
            probe = verification_method.get("probe")
            if isinstance(probe, str) and probe:
                return probe
    elif isinstance(verification_method, str):
        if verification_method in {"static", "manual-attested"}:
            return None
    evidence_ref = record.get("evidence_ref")
    if not isinstance(evidence_ref, str) or not evidence_ref.startswith(PROBE_EVIDENCE_PREFIX):
        return None
    name = evidence_ref.removeprefix(PROBE_EVIDENCE_PREFIX)
    return name or None


def record_expected_verdict(record: Mapping[str, Any]) -> Verdict | None:
    claim = record.get("claim")
    if not isinstance(claim, Mapping):
        return None
    verdict = claim.get("verdict")
    if verdict in _VERDICTS:
        return verdict  # type: ignore[return-value]
    return None


def mapping_get_path(value: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = value
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def record_expected_self_identity_evidence(record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    claim = record.get("claim")
    if not isinstance(claim, Mapping):
        return None
    expected = claim.get(SELF_IDENTITY_EXPECTED_EVIDENCE_KEY)
    return expected if isinstance(expected, Mapping) else None


def _scope_declared_seat(scope: Any) -> str | None:
    if not isinstance(scope, Mapping):
        return None
    for key in SELF_IDENTITY_SEAT_SCOPE_KEYS:
        value = scope.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def self_identity_declared_seat(record: Mapping[str, Any]) -> str | None:
    scoped = _scope_declared_seat(record.get("scope"))
    if scoped is not None:
        return scoped
    expected = record_expected_self_identity_evidence(record)
    if expected is None:
        return None
    value = expected.get("current_user")
    return value if isinstance(value, str) and value.strip() else None


def self_identity_current_seat(
    observed: ProbeResult,
    *,
    requested_scope: str | Mapping[str, Any] | None = None,
) -> str | None:
    scoped = _scope_declared_seat(requested_scope)
    if scoped is not None:
        return scoped
    value = mapping_get_path(observed.evidence, ("os_users", "current_user"))
    return value if isinstance(value, str) and value.strip() else None


def self_identity_record_applies_to_current_seat(
    record: Mapping[str, Any],
    observed: ProbeResult,
    *,
    requested_scope: str | Mapping[str, Any] | None = None,
) -> bool:
    declared = self_identity_declared_seat(record)
    if declared is None:
        return True
    current = self_identity_current_seat(observed, requested_scope=requested_scope)
    return current == declared
