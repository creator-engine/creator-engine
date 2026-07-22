"""Static/offline checks for the ce-ops#208 CE validator OCI image."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OCI_DIR = REPO_ROOT / "deploy" / "oci"
DOCKERFILE = OCI_DIR / "Dockerfile"
BUILD_SCRIPT = OCI_DIR / "build-image.sh"
README = OCI_DIR / "README.md"
DGX_README = REPO_ROOT / "deploy" / "dgx-runsc" / "README.md"
VPS_README = REPO_ROOT / "deploy" / "vps-runsc" / "README.md"
PYPROJECT = REPO_ROOT / "validators" / "pyproject.toml"
TEST_CONTEXT = Path("/tmp/ce-oci-context-test")


def _dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _run_shell_commands(text: str) -> list[str]:
    """Return uncommented shell commands from Dockerfile RUN instructions."""
    blocks = re.findall(r"(?ms)^RUN\s+(.*?)(?=^[A-Z]+(?:\s|$)|\Z)", text)
    commands: list[str] = []
    for block in blocks:
        uncommented = "\n".join(
            line.split("#", 1)[0]
            for line in block.splitlines()
            if not line.lstrip().startswith("#")
        )
        commands.extend(
            command.strip()
            for command in re.split(
                r";(?=(?:[^\"']|\"(?:[^\"\\\\]|\\\\.)*\"|'(?:[^'\\\\]|\\\\.)*')*$)",
                uncommented.replace("\\\n", " "),
            )
            if command.strip()
        )
    return commands


def _run_command_has_tokens(text: str, required: list[str]) -> bool:
    for command in _run_shell_commands(text):
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        normalised = [token.rstrip(";") for token in tokens]
        for start in range(len(normalised) - len(required) + 1):
            if start and not tokens[start - 1].endswith(";"):
                continue
            if required[:4] == ["apt-get", "install", "-y", "--no-install-recommends"]:
                command_end = next(
                    (index for index in range(start, len(tokens)) if tokens[index].endswith(";")),
                    len(tokens),
                )
                if (
                    normalised[start : start + 4] == required[:4]
                    and required[4] in normalised[start + 4 : command_end]
                ):
                    return True
            if normalised[start : start + len(required)] == required:
                return True
    return False


def _dry_run(*args: str) -> list[list[str]]:
    env = os.environ.copy()
    env.update(
        {
            "CE_OCI_IMAGE": "creator-engine/ce-validator:test",
            "CE_OCI_PLATFORM": "linux/arm64",
            "CE_OCI_CONTEXT_DIR": str(TEST_CONTEXT),
        }
    )
    result = subprocess.run(
        ["bash", str(BUILD_SCRIPT), "--dry-run", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return [shlex.split(line) for line in result.stdout.splitlines() if line.strip()]


def test_oci_dockerfile_builds_first_party_wheel_from_repo_source() -> None:
    text = _dockerfile()

    assert "ARG OCI_CPYTHON_BASE_IMAGE_SOURCE=UNSET" in text
    assert "ARG OCI_CPYTHON_BASE_IMAGE_VERSION=UNSET" in text
    assert "ARG OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST=UNSET" in text
    assert (
        "FROM --platform=$BUILDPLATFORM "
        "${OCI_CPYTHON_BASE_IMAGE_SOURCE}:${OCI_CPYTHON_BASE_IMAGE_VERSION}@sha256:${OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST} "
        "AS wheel-builder"
    ) in text
    assert "COPY validators/pyproject.toml validators/pyproject.toml" in text
    assert "COPY validators/creator_engine_validator validators/creator_engine_validator" in text
    assert "COPY validators/wheelhouse-dev /opt/build-tools" in text
    assert _run_command_has_tokens(
        text,
        [
            "python",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links=/opt/build-tools",
            "setuptools",
        ],
    )
    assert "SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}" in text
    assert "python -m pip wheel" in text
    assert "--no-deps" in text
    assert "--no-build-isolation" in text
    assert "/src/validators" in text
    assert "creator_engine_validator-*.whl" in text


def test_oci_dockerfile_installs_wheelhouse_offline_and_exposes_cli() -> None:
    text = _dockerfile()

    assert "COPY validators/requirements.txt /opt/creator-engine/requirements.txt" in text
    assert "COPY validators/requirements-dev.txt /opt/creator-engine/requirements-dev.txt" in text
    assert "COPY validators/wheelhouse /opt/creator-engine/wheelhouse" in text
    assert "COPY validators/wheelhouse-dev /opt/creator-engine/wheelhouse-dev" in text
    assert "COPY --from=wheel-builder /out/*.whl /opt/creator-engine/app/" in text
    assert _run_command_has_tokens(
        text,
        [
            "python",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links=/opt/creator-engine/wheelhouse",
            "-r",
            "/opt/creator-engine/requirements.txt",
        ],
    )
    assert _run_command_has_tokens(
        text,
        [
            "python",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links=/opt/creator-engine/wheelhouse",
            "--find-links=/opt/creator-engine/wheelhouse-dev",
            "-r",
            "/opt/creator-engine/requirements-dev.txt",
        ],
    )
    assert _run_command_has_tokens(
        text,
        [
            "python",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links=/opt/creator-engine/wheelhouse",
            "--find-links=/opt/creator-engine/app",
            "creator-engine-validator",
        ],
    )
    assert "creator-engine-validator" in text
    for package in ("openssh-client", "libsodium23"):
        assert _run_command_has_tokens(
            text, ["apt-get", "install", "-y", "--no-install-recommends", package]
        )
    for tool in ("ce", "creator-engine-validator", "ssh-keygen"):
        assert _run_command_has_tokens(text, ["command", "-v", tool])
    assert _run_command_has_tokens(text, ["python", "-c", "import pytest, xdist"])
    assert _run_command_has_tokens(
        text,
        [
            "python",
            "-c",
            "import ctypes.util; assert ctypes.util.find_library('sodium'), 'libsodium not resolvable'",
        ],
    )
    assert "ce --help" in text
    assert "creator-engine-validator --help" in text


def test_oci_instruction_contracts_reject_comments_and_adjacent_tokens() -> None:
    adversarial = """\
RUN set -eux; \\
    # python -m pip install --no-index --find-links=/opt/creator-engine/wheelhouse -r /opt/creator-engine/requirements.txt; \\
    echo libsodium23; \\
    command -v creator-engine-validator-shadow
"""

    assert not _run_command_has_tokens(
        adversarial,
        [
            "python",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links=/opt/creator-engine/wheelhouse",
            "-r",
            "/opt/creator-engine/requirements.txt",
        ],
    )
    assert not _run_command_has_tokens(
        adversarial, ["apt-get", "install", "-y", "--no-install-recommends", "libsodium23"]
    )
    assert not _run_command_has_tokens(
        adversarial, ["command", "-v", "creator-engine-validator"]
    )


def test_oci_dockerfile_installs_gate_daemon_runtime_dependencies_from_pinned_repos() -> None:
    text = _dockerfile()

    assert 'urlopen("https://cli.github.com/packages/githubcli-archive-keyring.gpg", timeout=30)' in text
    assert "chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg" in text
    assert (
        "deb [arch=$(dpkg --print-architecture) "
        "signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] "
        "https://cli.github.com/packages stable main"
    ) in text
    assert "      gh \\" in text
    assert "      git \\" in text
    assert "command -v gh" in text
    assert "command -v git" in text
    assert text.index("command -v gh") < text.index("ce --help")
    assert text.index("command -v git") < text.index("ce --help")


def test_oci_dockerfile_is_non_root_and_multi_arch_friendly() -> None:
    text = _dockerfile()

    assert (
        "FROM --platform=$TARGETPLATFORM "
        "${OCI_CPYTHON_BASE_IMAGE_SOURCE}:${OCI_CPYTHON_BASE_IMAGE_VERSION}@sha256:${OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST} "
        "AS runtime"
    ) in text
    assert "ARG TARGETARCH" in text
    assert "arm64|amd64|unknown" in text
    assert "FROM --platform=linux/amd64" not in text
    assert "FROM --platform=linux/arm64" not in text
    assert "ARG CE_UID=10001" in text
    assert "ARG CE_GID=10001" in text
    assert "useradd --uid" in text
    assert "USER ${CE_UID}:${CE_GID}" in text
    assert "WORKDIR /workspace/creator-engine" in text
    assert 'ENTRYPOINT ["/usr/bin/tini", "--"]' in text
    assert 'CMD ["ce", "--help"]' in text


def test_oci_build_script_shell_syntax_and_dry_run_contract() -> None:
    syntax = subprocess.run(
        ["bash", "-n", str(BUILD_SCRIPT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert syntax.returncode == 0, syntax.stderr

    commands = _dry_run()
    docker_cmd = next(cmd for cmd in commands if cmd[:3] == ["docker", "buildx", "build"])
    run_cmd = next(cmd for cmd in commands if cmd[:3] == ["docker", "run", "--rm"])
    copy_sources = {cmd[2] for cmd in commands if cmd[:2] == ["cp", "-R"]}

    assert not any("python3" in cmd and "pip" in cmd and "wheel" in cmd for cmd in commands)
    assert ["cp", str(REPO_ROOT / "validators" / "pyproject.toml"), str(TEST_CONTEXT / "validators" / "pyproject.toml")] in commands
    assert ["cp", str(REPO_ROOT / "validators" / "requirements.txt"), str(TEST_CONTEXT / "validators" / "requirements.txt")] in commands
    assert ["cp", str(REPO_ROOT / "validators" / "requirements-dev.txt"), str(TEST_CONTEXT / "validators" / "requirements-dev.txt")] in commands
    assert str(REPO_ROOT / "validators" / "creator_engine_validator") in copy_sources
    assert str(REPO_ROOT / "validators" / "wheelhouse") in copy_sources
    assert str(REPO_ROOT / "validators" / "wheelhouse-dev") in copy_sources

    assert "--file" in docker_cmd
    assert str(DOCKERFILE) in docker_cmd
    assert "--platform" in docker_cmd
    assert docker_cmd[docker_cmd.index("--platform") + 1] == "linux/arm64"
    assert "--build-arg" in docker_cmd
    assert "OCI_CPYTHON_BASE_IMAGE_SOURCE=docker.io/library/python" in docker_cmd
    assert "OCI_CPYTHON_BASE_IMAGE_VERSION=3.14-slim-bookworm" in docker_cmd
    assert any(re.fullmatch(r"OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST=[0-9a-f]{64}", arg) for arg in docker_cmd)
    assert "SOURCE_DATE_EPOCH=946684800" in docker_cmd
    assert "--tag" in docker_cmd
    assert "creator-engine/ce-validator:test" in docker_cmd
    assert "--load" in docker_cmd
    assert docker_cmd[-1] == str(TEST_CONTEXT)

    assert run_cmd[-3:] == ["creator-engine/ce-validator:test", "ce", "--help"]


def test_oci_build_script_preflights_buildx_for_real_builds(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    assert bash is not None
    dirname = shutil.which("dirname")
    assert dirname is not None
    (tmp_path / "dirname").symlink_to(dirname)

    env = os.environ.copy()
    env.update(
        {
            "PATH": str(tmp_path),
            "CE_OCI_CONTEXT_DIR": str(tmp_path / "context"),
        }
    )
    result = subprocess.run(
        [bash, str(BUILD_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 127
    assert "docker buildx is required" in result.stderr
    assert "Use --dry-run to inspect the build command" in result.stderr
    assert not (tmp_path / "context").exists()


def test_oci_build_script_requires_push_for_multi_platform_load() -> None:
    result = subprocess.run(
        ["bash", str(BUILD_SCRIPT), "--dry-run", "--platform", "linux/arm64,linux/amd64"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "multi-platform builds require --push" in result.stderr


def test_oci_build_script_supports_multi_platform_push() -> None:
    commands = _dry_run("--platform", "linux/arm64,linux/amd64", "--push")
    docker_cmd = next(cmd for cmd in commands if cmd[:3] == ["docker", "buildx", "build"])

    assert docker_cmd[docker_cmd.index("--platform") + 1] == "linux/arm64,linux/amd64"
    assert "--push" in docker_cmd
    assert "--load" not in docker_cmd


def test_oci_image_console_scripts_match_packaging_metadata() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    text = _dockerfile()

    assert scripts["ce"] == "creator_engine_validator.ce_cli:main"
    assert scripts["creator-engine-validator"] == "creator_engine_validator.cli:main"
    assert data["project"]["requires-python"] == ">=3.14"
    assert "command -v ce" in text
    assert "command -v creator-engine-validator" in text


def test_oci_docs_tie_image_to_runsc_deployments() -> None:
    readme = _readme()
    dgx = DGX_README.read_text(encoding="utf-8")
    vps = VPS_README.read_text(encoding="utf-8")

    assert "deploy/oci/build-image.sh" in readme
    assert "docker run --rm" in readme
    assert "linux/arm64,linux/amd64" in readme
    assert "deploy/dgx-runsc" in readme
    assert "deploy/vps-runsc" in readme
    assert "runsc-gvproxy-ptrace" in readme
    assert "deploy/oci" in dgx
    assert "deploy/oci" in vps
    assert "creator-engine-validator" in dgx
    assert "creator-engine-validator" in vps
