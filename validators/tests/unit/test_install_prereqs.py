"""Focused prerequisite remediation decisions for clean-room install paths."""
from __future__ import annotations

import os
from pathlib import Path

from creator_engine_validator import install_prereqs as prereqs


def _which(names: set[str]):
    return lambda name: f"/usr/bin/{name}" if name in names else None


def test_find_uv_discovers_off_path_user_install(tmp_path: Path):
    home = tmp_path / "home"
    uv = home / ".local" / "bin" / "uv"
    uv.parent.mkdir(parents=True)
    uv.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    uv.chmod(0o755)

    assert prereqs.find_uv(which=lambda _name: None, env={"HOME": str(home), "PATH": ""}) == str(uv)


def test_env_with_tool_on_path_prepends_install_dir(tmp_path: Path):
    uv = tmp_path / "bin" / "uv"
    env = prereqs.env_with_tool_on_path(uv, {"PATH": os.pathsep.join(["/usr/bin", "/bin"])})

    assert env["PATH"].split(os.pathsep)[0] == str(uv.parent)


def test_uv_remediation_is_exact_official_installer_line(tmp_path: Path):
    remediation = prereqs.uv_install_remediation({"HOME": str(tmp_path)})

    assert "curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh | sh" in remediation
    assert f'export PATH="{tmp_path / ".local" / "bin"}:$PATH"' in remediation


def test_python314_remediation_uses_uv_and_target_path():
    remediation = prereqs.python314_remediation("/repo/.venv/bin/python")

    assert "uv python install 3.14" in remediation
    assert "ce bootstrap --python /repo/.venv/bin/python" in remediation


def test_venv_dir_for_standard_target_python():
    assert prereqs.venv_dir_for_target_python(Path("/repo/.venv/bin/python")) == Path("/repo/.venv")
    assert prereqs.venv_dir_for_target_python(Path("/repo/python")) is None


def test_ssh_keygen_package_plans_are_precise():
    assert prereqs.ssh_keygen_package_plan(which=_which({"apt-get"})).command == (
        "sudo apt-get update && sudo apt-get install -y openssh-client"
    )
    assert prereqs.ssh_keygen_package_plan(which=_which({"dnf"})).command == (
        "sudo dnf install -y openssh-clients"
    )
    assert prereqs.ssh_keygen_package_plan(which=_which({"apk"})).command == (
        "sudo apk add openssh-client"
    )
    assert prereqs.ssh_keygen_package_plan(which=_which(set())) is None
