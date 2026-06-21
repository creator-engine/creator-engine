"""Fresh capability probes for the Knowledge-SSOT brain surface.

Capability probes deliberately interrogate current reality. They do not cache
answers and they never convert an unknown capability into a guessed verdict.
"""

from __future__ import annotations

import os
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Sequence

import yaml

Verdict = Literal["present", "absent", "unknown"]
ProbeFn = Callable[["ProbeContext"], "ProbeResult"]

CODE_PROBE_DISAGREEMENT = "brain_assertion_probe_disagreement"
PROBE_EVIDENCE_PREFIX = "probe:"
_VERDICTS: frozenset[str] = frozenset({"present", "absent", "unknown"})
_TRUE_VALUES = {"1", "true", "yes", "on", "present", "enabled"}
_FALSE_VALUES = {"0", "false", "no", "off", "absent", "disabled"}
_FAN_OUT_ENV_KEYS = (
    "CE_HARNESS_FAN_OUT",
    "CE_MULTI_AGENT_FAN_OUT",
    "CODEX_SUBAGENTS",
)


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
    wheelhouse = root / "validators" / "wheelhouse"
    if not source_root.is_dir():
        return [f"missing validator source tree at {source_root}"]
    if not wheelhouse.is_dir():
        return [f"missing validator wheelhouse at {wheelhouse}"]
    wheels = sorted(wheelhouse.glob("creator_engine_validator-*.whl"))
    if not wheels:
        return [f"missing creator_engine_validator app wheel in {wheelhouse}"]

    source_files = {
        path.relative_to(source_root).as_posix(): path
        for path in source_root.rglob("*.py")
        if path.is_file()
    }
    violations: list[str] = []
    for wheel in wheels:
        try:
            with zipfile.ZipFile(wheel) as zf:
                wheel_files = {
                    name.removeprefix("creator_engine_validator/")
                    for name in zf.namelist()
                    if name.startswith("creator_engine_validator/") and name.endswith(".py")
                }
                for rel in sorted(wheel_files - source_files.keys()):
                    violations.append(f"app wheel {wheel.name} has no source file for {rel}")
                for rel in sorted(source_files.keys() - wheel_files):
                    violations.append(f"app wheel {wheel.name} missing source file {rel}")
                for rel in sorted(source_files.keys() & wheel_files):
                    if zf.read(f"creator_engine_validator/{rel}") != source_files[rel].read_bytes():
                        violations.append(f"app wheel {wheel.name} differs from source file {rel}")
        except zipfile.BadZipFile:
            violations.append(f"invalid app wheel zip archive: {wheel.name}")
    return violations


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


def _gh_authenticated(context: ProbeContext) -> ProbeResult:
    command = ["gh", "auth", "status"]
    try:
        completed = context.run(command)
        returncode = int(getattr(completed, "returncode"))
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


PROBES: dict[str, ProbeFn] = {
    "gh_authenticated": _gh_authenticated,
    "harness_fan_out": _harness_fan_out,
    "merge_group_trigger": _merge_group_trigger,
    "wheelhouse_matches_source": _wheelhouse_matches_source,
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
