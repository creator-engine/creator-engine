"""Tests for Docker build wiring to surfaces/manifest.yaml."""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
from pathlib import Path


MANIFEST_ARG_DEFAULTS = (
    "DEBIAN_COMMIT_OR_DIGEST",
    "DEBIAN_SOURCE",
    "DEBIAN_VERSION",
    "HERDR_COMMIT_OR_DIGEST",
    "HERDR_SOURCE",
    "OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST",
    "OCI_CPYTHON_BASE_IMAGE_SOURCE",
    "OCI_CPYTHON_BASE_IMAGE_VERSION",
    "RUST_COMMIT_OR_DIGEST",
    "RUST_SOURCE",
    "RUST_VERSION",
    "ZIG_TOOLCHAIN_LINUX_AARCH64_SHA256",
    "ZIG_TOOLCHAIN_LINUX_X86_64_SHA256",
    "ZIG_TOOLCHAIN_SOURCE",
    "ZIG_TOOLCHAIN_VERSION",
)

NON_OCI_BUILD_SCRIPTS = {
    "deploy/vps-runsc/build-image.sh": {
        "dockerfile": "deploy/vps-runsc/Dockerfile",
        "image": "creator-engine/codex-runsc:x86_64",
        "context": ".",
        "user_arg": "CE_VPS_USER=",
    },
    "deploy/dgx-runsc/build-image.sh": {
        "dockerfile": "deploy/dgx-runsc/Dockerfile",
        "image": "creator-engine/codex-runsc:0.141.0-aarch64",
        "context": "deploy/dgx-runsc",
        "user_arg": "CE_DGX_USER=",
    },
    "deploy/dgx-controller-runsc/build-image.sh": {
        "dockerfile": "deploy/dgx-controller-runsc/Dockerfile",
        "image": "creator-engine/claude-controller-runsc:c1",
        "context": ".",
        "user_arg": "CE_DGX_USER=",
    },
}


def _text(repo_root: Path, relative: str) -> str:
    return (repo_root / relative).read_text(encoding="utf-8")


def test_oci_build_dry_run_uses_rendered_surface_build_args(repo_root: Path):
    result = subprocess.run(
        ["bash", "deploy/oci/build-image.sh", "--dry-run"],
        cwd=repo_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    expected = subprocess.run(
        [sys.executable, "surfaces/render.py", "build-args"],
        cwd=repo_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.splitlines()

    for rendered_arg in expected:
        assert rendered_arg in result.stdout


def test_dockerfiles_use_unset_defaults_for_manifest_controlled_inputs(repo_root: Path):
    dockerfiles = [
        "deploy/oci/Dockerfile",
        "deploy/vps-runsc/Dockerfile",
        "deploy/dgx-runsc/Dockerfile",
        "deploy/dgx-controller-runsc/Dockerfile",
    ]

    for relative in dockerfiles:
        text = _text(repo_root, relative)
        for arg_name in MANIFEST_ARG_DEFAULTS:
            if re.search(rf"\b{re.escape(arg_name)}\b", text):
                assert f"ARG {arg_name}=UNSET" in text

        from_lines = [line for line in text.splitlines() if line.startswith("FROM ")]
        assert not any(re.search(r"@sha256:[0-9a-f]{64}", line) for line in from_lines)


def test_non_oci_build_wrappers_use_rendered_surface_build_args(repo_root: Path):
    expected = subprocess.run(
        [sys.executable, "surfaces/render.py", "build-args"],
        cwd=repo_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.splitlines()

    for script, contract in NON_OCI_BUILD_SCRIPTS.items():
        syntax = subprocess.run(["bash", "-n", script], cwd=repo_root, text=True, capture_output=True)
        assert syntax.returncode == 0, f"{script}: {syntax.stderr}"

        result = subprocess.run(
            ["bash", script, "--dry-run"],
            cwd=repo_root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        argv = shlex.split(result.stdout)

        assert argv[:2] == ["docker", "build"]
        assert argv[argv.index("--file") + 1] == str(repo_root / contract["dockerfile"])
        assert argv[argv.index("--tag") + 1] == contract["image"]
        assert argv[-1] == str(repo_root / contract["context"])
        assert any(arg.startswith(contract["user_arg"]) for arg in argv)
        for rendered_arg in expected:
            flag, assignment = rendered_arg.split(" ", 1)
            assert flag in argv
            assert assignment in argv


def test_published_non_oci_build_docs_use_wrappers(repo_root: Path):
    docs = {
        "deploy/vps-runsc/README.md": "deploy/vps-runsc/build-image.sh",
        "deploy/dgx-runsc/README.md": "deploy/dgx-runsc/build-image.sh",
        "deploy/dgx-controller-runsc/README.md": "deploy/dgx-controller-runsc/build-image.sh",
    }

    for relative, wrapper in docs.items():
        text = _text(repo_root, relative)
        assert wrapper in text
        assert "docker build \\" not in text
