"""Install prerequisite detection and remediation decisions.

The functions here are intentionally small and side-effect free where possible:
the shell installer and source-clone bootstrap both need exact, testable
remediation text for clean-room hosts.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

PYTHON_VERSION = "3.14"
UV_INSTALLER_URL = "https://astral.sh/uv/install.sh"
UV_INSTALL_SNIPPET = f"curl --proto '=https' --tlsv1.2 -LsSf {UV_INSTALLER_URL} | sh"


@dataclass(frozen=True)
class PackageInstallPlan:
    tool: str
    package: str
    command: str


def default_uv_install_dir(env: Mapping[str, str] | None = None) -> Path | None:
    env = env if env is not None else os.environ
    explicit = env.get("UV_INSTALL_DIR")
    if explicit:
        return Path(explicit)
    home = env.get("HOME")
    if home:
        return Path(home) / ".local" / "bin"
    return None


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def find_uv(
    *,
    which: Callable[[str], str | None] = shutil.which,
    env: Mapping[str, str] | None = None,
) -> str | None:
    env = env if env is not None else os.environ
    found = which("uv")
    if found:
        return found
    candidates: list[Path] = []
    for key in ("UV_INSTALL_DIR", "XDG_BIN_HOME"):
        value = env.get(key)
        if value:
            candidates.append(Path(value) / "uv")
    home = env.get("HOME")
    if home:
        candidates.extend([Path(home) / ".local" / "bin" / "uv", Path(home) / ".cargo" / "bin" / "uv"])
    for candidate in candidates:
        if _is_executable(candidate):
            return str(candidate)
    return None


def env_with_tool_on_path(tool_path: str | Path, env: Mapping[str, str] | None = None) -> dict[str, str]:
    result = dict(env if env is not None else os.environ)
    tool_dir = str(Path(tool_path).parent)
    path = result.get("PATH", "")
    parts = [part for part in path.split(os.pathsep) if part]
    if tool_dir not in parts:
        result["PATH"] = os.pathsep.join([tool_dir, *parts])
    return result


def uv_install_remediation(env: Mapping[str, str] | None = None) -> str:
    install_dir = default_uv_install_dir(env)
    path_note = f'export PATH="{install_dir}:$PATH"; ' if install_dir is not None else ""
    return f"Install uv, then rerun: {UV_INSTALL_SNIPPET}; {path_note}uv --version"


def python314_remediation(target_python: Path | str | None = None) -> str:
    target = f"; then rerun ce bootstrap --python {target_python}" if target_python else ""
    return f"Install CPython {PYTHON_VERSION}: uv python install {PYTHON_VERSION}{target}"


def venv_dir_for_target_python(target_python: Path | str) -> Path | None:
    target = Path(target_python)
    if target.parent.name == "bin" and target.name.startswith("python"):
        return target.parent.parent
    return None


def ssh_keygen_package_plan(
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> PackageInstallPlan | None:
    if which("apt-get"):
        return PackageInstallPlan(
            tool="apt-get",
            package="openssh-client",
            command="sudo apt-get update && sudo apt-get install -y openssh-client",
        )
    if which("dnf"):
        return PackageInstallPlan(
            tool="dnf",
            package="openssh-clients",
            command="sudo dnf install -y openssh-clients",
        )
    if which("yum"):
        return PackageInstallPlan(
            tool="yum",
            package="openssh-clients",
            command="sudo yum install -y openssh-clients",
        )
    if which("apk"):
        return PackageInstallPlan(
            tool="apk",
            package="openssh-client",
            command="sudo apk add openssh-client",
        )
    if which("pacman"):
        return PackageInstallPlan(
            tool="pacman",
            package="openssh",
            command="sudo pacman -Sy --needed openssh",
        )
    if which("brew"):
        return PackageInstallPlan(
            tool="brew",
            package="openssh",
            command="brew install openssh",
        )
    return None
