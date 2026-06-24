"""Offline source-clone bootstrap for a controller/seat venv.

The source checkout deliberately does not commit a first-party application
wheel.  This runtime therefore installs runtime dependencies from the vendored
wheelhouse with ``uv`` or pip, then links the checked-out ``validators/`` source
into the target interpreter and writes the expected console scripts.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from . import install_prereqs


SOURCE_PTH = "creator_engine_validator_source.pth"
FAIL_NO_TARGET_PYTHON = "CE-BOOTSTRAP-NO-TARGET-PYTHON"
FAIL_NO_INSTALLER = "CE-BOOTSTRAP-NO-INSTALLER"
FAIL_INSTALL_FAILED = "CE-BOOTSTRAP-INSTALL-FAILED"
FAIL_LAYOUT = "CE-BOOTSTRAP-LAYOUT"
FAIL_VERIFY = "CE-BOOTSTRAP-VERIFY"
FAIL_PREREQ = "CE-BOOTSTRAP-PREREQ"
DOCTOR_CLAUSE = "CE-SEAT-ENV"
DOCTOR_CHECK_NAME = "controller-seat-app-install"

CONSOLE_SCRIPTS = {
    "creator-engine-validator": "creator_engine_validator.cli:main",
    "ce": "creator_engine_validator.ce_cli:main",
    "cev3": "creator_engine_validator.v3_cli:main",
}


@dataclass(frozen=True)
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "argv": self.argv,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass(frozen=True)
class BootstrapResult:
    ok: bool
    target_python: str
    repo_root: str
    installer: str | None
    changed: bool
    commands: tuple[CommandResult, ...] = field(default_factory=tuple)
    scripts: dict[str, str] = field(default_factory=dict)
    site_packages: str | None = None
    reason: str | None = None
    remediation: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "target_python": self.target_python,
            "repo_root": self.repo_root,
            "installer": self.installer,
            "changed": self.changed,
            "commands": [c.to_dict() for c in self.commands],
            "scripts": self.scripts,
            "site_packages": self.site_packages,
            "reason": self.reason,
            "remediation": self.remediation,
            "detail": self.detail,
        }


def default_target_python(repo_root: Path | str) -> Path:
    env = os.environ.get("CE_VALIDATOR_PYTHON")
    if env:
        return Path(env)
    return Path(repo_root) / ".venv" / "bin" / "python"


def _run(argv: Sequence[str], *, env: dict[str, str] | None = None) -> CommandResult:
    proc = subprocess.run(
        [str(a) for a in argv],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return CommandResult(
        argv=[str(a) for a in argv],
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _publish_tool_path(tool_path: str) -> None:
    os.environ.update(install_prereqs.env_with_tool_on_path(tool_path))


def _ensure_uv_available(*, prefer_uv: bool) -> tuple[str | None, list[CommandResult], str | None]:
    if not prefer_uv:
        return None, [], None
    uv = install_prereqs.find_uv()
    if uv:
        _publish_tool_path(uv)
        return uv, [], None
    install_dir = install_prereqs.default_uv_install_dir()
    if install_dir is None:
        return None, [], "HOME is not set. " + install_prereqs.uv_install_remediation()
    if shutil.which("curl") is None or shutil.which("sh") is None:
        return None, [], install_prereqs.uv_install_remediation()
    install_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["UV_INSTALL_DIR"] = str(install_dir)
    command = _run(["sh", "-c", install_prereqs.UV_INSTALL_SNIPPET], env=env)
    if command.returncode != 0:
        detail = (command.stderr or command.stdout or "uv installer failed").strip()
        return None, [command], f"{install_prereqs.uv_install_remediation(env)}. Installer detail: {detail}"
    uv = install_prereqs.find_uv(env=env)
    if not uv:
        return None, [command], (
            "official uv installer completed but uv is not discoverable. "
            + install_prereqs.uv_install_remediation(env)
        )
    _publish_tool_path(uv)
    return uv, [command], None


def _ensure_python314_with_uv(uv: str, target: Path) -> tuple[list[CommandResult], str | None]:
    commands: list[CommandResult] = []
    find = _run([uv, "python", "find", install_prereqs.PYTHON_VERSION])
    commands.append(find)
    if find.returncode != 0:
        install = _run([uv, "python", "install", install_prereqs.PYTHON_VERSION])
        commands.append(install)
        if install.returncode != 0:
            detail = (install.stderr or install.stdout or "uv python install failed").strip()
            return commands, f"{install_prereqs.python314_remediation(target)}. Installer detail: {detail}"
        find = _run([uv, "python", "find", install_prereqs.PYTHON_VERSION])
        commands.append(find)
    if find.returncode != 0:
        detail = (find.stderr or find.stdout or "uv could not resolve Python 3.14").strip()
        return commands, f"{install_prereqs.python314_remediation(target)}. Resolver detail: {detail}"
    return commands, None


def _create_target_venv_with_uv(uv: str, target: Path) -> tuple[list[CommandResult], str | None]:
    commands, failure = _ensure_python314_with_uv(uv, target)
    if failure is not None:
        return commands, failure
    venv_dir = install_prereqs.venv_dir_for_target_python(target)
    if venv_dir is None:
        return commands, (
            f"Target interpreter {target} is not a venv bin/python path. "
            f"{install_prereqs.python314_remediation(target)}."
        )
    venv = _run([uv, "venv", "--python", install_prereqs.PYTHON_VERSION, str(venv_dir)])
    commands.append(venv)
    if venv.returncode != 0:
        detail = (venv.stderr or venv.stdout or "uv venv failed").strip()
        return commands, f"Create the target venv with: uv venv --python 3.14 {venv_dir}. Detail: {detail}"
    if not target.is_file():
        return commands, f"uv venv completed but target interpreter is still missing: {target}"
    return commands, None


def _offline_env(wheelhouse: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PIP_NO_INDEX": "1",
            "PIP_FIND_LINKS": str(wheelhouse),
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "UV_PYTHON_DOWNLOADS": "never",
        }
    )
    return env


def _target_probe_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return env


def _target_paths(target_python: Path) -> tuple[Path, Path]:
    code = (
        "import json, sysconfig; "
        "print(json.dumps({'purelib': sysconfig.get_path('purelib'), "
        "'scripts': sysconfig.get_path('scripts')}))"
    )
    proc = subprocess.run(
        [str(target_python), "-c", code],
        check=False,
        capture_output=True,
        text=True,
        env=_target_probe_env(),
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "target interpreter path probe failed").strip())
    data = json.loads(proc.stdout)
    return Path(data["purelib"]), Path(data["scripts"])


def _pip_available(target_python: Path) -> bool:
    return _run([str(target_python), "-m", "pip", "--version"]).returncode == 0


def _ensure_pip(target_python: Path) -> CommandResult | None:
    if _pip_available(target_python):
        return None
    result = _run([str(target_python), "-m", "ensurepip", "--upgrade"])
    if result.returncode != 0 or not _pip_available(target_python):
        return result
    return result


def _installer_command(
    target_python: Path,
    validators_root: Path,
    wheelhouse: Path,
    *,
    prefer_uv: bool = True,
) -> tuple[str | None, list[str] | None, CommandResult | None]:
    requirements = validators_root / "requirements.txt"
    uv = install_prereqs.find_uv() if prefer_uv else None
    if uv:
        return (
            "uv",
            [
                uv,
                "pip",
                "install",
                "--python",
                str(target_python),
                "--no-index",
                "--find-links",
                str(wheelhouse),
                "-r",
                str(requirements),
            ],
            None,
        )
    ensure = _ensure_pip(target_python)
    if ensure is not None and ensure.returncode != 0:
        return (None, None, ensure)
    return (
        "pip",
        [
            str(target_python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            "-r",
            str(requirements),
        ],
        ensure,
    )


def _entrypoint_script(target_python: Path, module_func: str) -> str:
    module, _, func = module_func.partition(":")
    shebang_python = os.path.abspath(target_python)
    return (
        f"#!{shebang_python}\n"
        "import sys\n"
        f"from {module} import {func}\n\n"
        "if __name__ == '__main__':\n"
        f"    raise SystemExit({func}())\n"
    )


def _write_text_if_changed(path: Path, content: str, *, mode: int | None = None) -> bool:
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    changed = old != content
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if mode is not None:
        current = stat.S_IMODE(path.stat().st_mode)
        if current != mode:
            path.chmod(mode)
            changed = True
    return changed


def _install_source_link(
    *,
    validators_root: Path,
    target_python: Path,
) -> tuple[bool, Path, Path, dict[str, str]]:
    site_packages, scripts_dir = _target_paths(target_python)
    site_packages.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    changed = _write_text_if_changed(site_packages / SOURCE_PTH, f"{validators_root}\n")
    scripts: dict[str, str] = {}
    for name, entrypoint in CONSOLE_SCRIPTS.items():
        script_path = scripts_dir / name
        scripts[name] = str(script_path)
        changed = (
            _write_text_if_changed(script_path, _entrypoint_script(target_python, entrypoint), mode=0o755)
            or changed
        )
    return changed, site_packages, scripts_dir, scripts


def inspect_target_env(target_python: Path | str) -> dict[str, Any]:
    target = Path(target_python)
    payload: dict[str, Any] = {
        "target_python": str(target),
        "target_python_exists": target.is_file(),
        "package_importable": False,
        "scripts_dir": None,
        "scripts": {},
        "missing_scripts": list(CONSOLE_SCRIPTS),
        "ok": False,
        "remediation": f"Run ce bootstrap --python {target}",
    }
    if not target.is_file():
        payload["detail"] = f"target interpreter not found: {target}"
        return payload
    try:
        _site_packages, scripts_dir = _target_paths(target)
    except Exception as exc:  # noqa: BLE001 - surfaced as doctor detail.
        payload["detail"] = f"target interpreter probe failed: {exc}"
        return payload
    payload["scripts_dir"] = str(scripts_dir)
    script_paths = {name: str(scripts_dir / name) for name in CONSOLE_SCRIPTS}
    payload["scripts"] = script_paths
    missing = [name for name, path in script_paths.items() if not Path(path).is_file()]
    payload["missing_scripts"] = missing
    proc = subprocess.run(
        [
            str(target),
            "-c",
            "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('creator_engine_validator') else 1)",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=_target_probe_env(),
    )
    payload["package_importable"] = proc.returncode == 0
    payload["ok"] = payload["package_importable"] and not missing
    if payload["ok"]:
        payload["detail"] = "creator-engine-validator import target and console scripts are present"
    else:
        bits = []
        if not payload["package_importable"]:
            bits.append("package not importable in target interpreter")
        if missing:
            bits.append(f"missing console scripts: {', '.join(missing)}")
        payload["detail"] = "; ".join(bits)
    return payload


def doctor_check(
    target_python: Path | str,
    *,
    applicable: bool,
) -> dict[str, Any]:
    if not applicable:
        return {
            "clause": DOCTOR_CLAUSE,
            "name": DOCTOR_CHECK_NAME,
            "applicable": False,
            "ok": True,
            "detail": "no target controller/seat interpreter requested or discovered",
            "target_python": str(target_python),
            "remediation": f"Run ce bootstrap --python {target_python}",
        }
    inspection = inspect_target_env(target_python)
    return {
        "clause": DOCTOR_CLAUSE,
        "name": DOCTOR_CHECK_NAME,
        "applicable": True,
        "ok": bool(inspection["ok"]),
        "detail": inspection["detail"],
        "target_python": inspection["target_python"],
        "target_python_exists": inspection["target_python_exists"],
        "package_importable": inspection["package_importable"],
        "scripts_dir": inspection["scripts_dir"],
        "scripts": inspection["scripts"],
        "missing_scripts": inspection["missing_scripts"],
        "remediation": inspection["remediation"],
    }


def bootstrap(
    repo_root: Path | str,
    target_python: Path | str | None = None,
    *,
    prefer_uv: bool = True,
) -> BootstrapResult:
    root = Path(repo_root).resolve()
    target = Path(target_python) if target_python is not None else default_target_python(root)
    validators_root = root / "validators"
    wheelhouse = validators_root / "wheelhouse"
    if not validators_root.is_dir() or not wheelhouse.is_dir():
        return BootstrapResult(
            ok=False,
            target_python=str(target),
            repo_root=str(root),
            installer=None,
            changed=False,
            reason=FAIL_LAYOUT,
            remediation="Run ce bootstrap from a Creator Engine source checkout with validators/wheelhouse present.",
            detail=f"missing validators source or wheelhouse under {root}",
        )
    uv, prereq_commands, uv_failure = _ensure_uv_available(prefer_uv=prefer_uv)
    commands: list[CommandResult] = list(prereq_commands)
    if uv_failure is not None:
        return BootstrapResult(
            ok=False,
            target_python=str(target),
            repo_root=str(root),
            installer=None,
            changed=False,
            commands=tuple(commands),
            reason=FAIL_PREREQ,
            remediation=uv_failure,
            detail="uv is required but is not available and could not be auto-provisioned",
        )
    if not target.is_file():
        if uv is None:
            return BootstrapResult(
                ok=False,
                target_python=str(target),
                repo_root=str(root),
                installer=None,
                changed=False,
                commands=tuple(commands),
                reason=FAIL_NO_TARGET_PYTHON,
                remediation=(
                    f"Create the target venv first, for example: python3.14 -m venv {target.parent.parent}; "
                    f"then run ce bootstrap --python {target}"
                ),
                detail=f"target interpreter not found: {target}",
            )
        venv_commands, venv_failure = _create_target_venv_with_uv(uv, target)
        commands.extend(venv_commands)
        if venv_failure is not None:
            return BootstrapResult(
                ok=False,
                target_python=str(target),
                repo_root=str(root),
                installer=None,
                changed=False,
                commands=tuple(commands),
                reason=FAIL_NO_TARGET_PYTHON,
                remediation=venv_failure,
                detail=f"target interpreter not found and auto-provision failed: {target}",
            )

    installer, argv, ensure = _installer_command(target, validators_root, wheelhouse, prefer_uv=prefer_uv)
    if ensure is not None:
        commands.append(ensure)
    if argv is None or installer is None:
        return BootstrapResult(
            ok=False,
            target_python=str(target),
            repo_root=str(root),
            installer=None,
            changed=False,
            commands=tuple(commands),
            reason=FAIL_NO_INSTALLER,
            remediation=(
                "Install uv on PATH or use a target interpreter with pip/ensurepip support, "
                f"then run ce bootstrap --python {target}."
            ),
            detail="no supported offline installer is available for the target interpreter",
        )
    install = _run(argv, env=_offline_env(wheelhouse))
    commands.append(install)
    if install.returncode != 0:
        return BootstrapResult(
            ok=False,
            target_python=str(target),
            repo_root=str(root),
            installer=installer,
            changed=False,
            commands=tuple(commands),
            reason=FAIL_INSTALL_FAILED,
            remediation=(
                "Verify validators/wheelhouse contains the pinned cp314 dependency wheels "
                f"and rerun ce bootstrap --python {target}."
            ),
            detail=(install.stderr or install.stdout or "offline dependency install failed").strip(),
        )
    try:
        source_changed, site_packages, _scripts_dir, scripts = _install_source_link(
            validators_root=validators_root,
            target_python=target,
        )
    except Exception as exc:  # noqa: BLE001 - converted to named CLI refusal.
        return BootstrapResult(
            ok=False,
            target_python=str(target),
            repo_root=str(root),
            installer=installer,
            changed=False,
            commands=tuple(commands),
            reason=FAIL_LAYOUT,
            remediation=f"Check write permissions for the target venv and rerun ce bootstrap --python {target}.",
            detail=str(exc),
        )
    inspection = inspect_target_env(target)
    if not inspection["ok"]:
        return BootstrapResult(
            ok=False,
            target_python=str(target),
            repo_root=str(root),
            installer=installer,
            changed=source_changed,
            commands=tuple(commands),
            scripts=scripts,
            site_packages=str(site_packages),
            reason=FAIL_VERIFY,
            remediation=f"Run ce bootstrap --python {target} again after resolving: {inspection['detail']}",
            detail=inspection["detail"],
        )
    return BootstrapResult(
        ok=True,
        target_python=str(target),
        repo_root=str(root),
        installer=installer,
        changed=source_changed,
        commands=tuple(commands),
        scripts=scripts,
        site_packages=str(site_packages),
        detail="offline dependencies installed; source checkout linked; console scripts present",
    )


def _target_from_cli(args: argparse.Namespace) -> Path | None:
    if args.target_python:
        return Path(args.target_python)
    if args.venv:
        venv = Path(args.venv)
        if not venv.is_absolute():
            venv = Path(args.repo_root) / venv
        return venv / "bin" / "python"
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m creator_engine_validator.bootstrap_runtime",
        description="Provision a source-clone controller/seat venv offline",
    )
    parser.add_argument("command", nargs="?", default="bootstrap", choices=("bootstrap",))
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--venv", default=None)
    parser.add_argument("--python", dest="target_python", default=None)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    result = bootstrap(args.repo_root, _target_from_cli(args))
    if args.json_output:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif result.ok:
        changed = "updated" if result.changed else "already provisioned"
        print(f"ce bootstrap: {changed} ({result.target_python})")
    else:
        print(
            f"ERROR: ce bootstrap refused [{result.reason}]: {result.detail}\n"
            f"remediation: {result.remediation}",
            file=sys.stderr,
        )
    return 0 if result.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
