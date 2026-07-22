"""Static/offline checks for the canonical CE runtime image publish surface."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIR = REPO_ROOT / "deploy" / "runtime-image"
DOCKERFILE = RUNTIME_DIR / "Dockerfile"
README = RUNTIME_DIR / "README.md"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish-runtime-image.yml"


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


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _on_block(doc: dict) -> dict:
    if "on" in doc:
        return doc["on"]
    return doc[True]


def _steps(doc: dict) -> list[dict]:
    return doc["jobs"]["publish"]["steps"]


def _step_named(doc: dict, name: str) -> dict:
    for step in _steps(doc):
        if step.get("name") == name:
            return step
    raise AssertionError(f"missing workflow step: {name}")


def _all_run_text(doc: dict) -> str:
    return "\n".join(str(step.get("run", "")) for step in _steps(doc))


def test_runtime_dockerfile_uses_manifest_pinned_python_base_for_both_arches() -> None:
    text = _dockerfile()

    assert "ARG OCI_CPYTHON_BASE_IMAGE_SOURCE=UNSET" in text
    assert "ARG OCI_CPYTHON_BASE_IMAGE_VERSION=UNSET" in text
    assert "ARG OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST=UNSET" in text
    assert (
        "FROM --platform=$BUILDPLATFORM "
        "${OCI_CPYTHON_BASE_IMAGE_SOURCE}:${OCI_CPYTHON_BASE_IMAGE_VERSION}@sha256:${OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST} "
        "AS wheel-builder"
    ) in text
    assert (
        "FROM --platform=$TARGETPLATFORM "
        "${OCI_CPYTHON_BASE_IMAGE_SOURCE}:${OCI_CPYTHON_BASE_IMAGE_VERSION}@sha256:${OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST} "
        "AS runtime"
    ) in text
    assert "ARG TARGETARCH" in text
    assert "arm64|amd64|unknown" in text
    assert "FROM --platform=linux/amd64" not in text
    assert "FROM --platform=linux/arm64" not in text


def test_runtime_dockerfile_installs_validator_from_wheel_seam_offline() -> None:
    text = _dockerfile()

    assert "COPY validators/pyproject.toml validators/pyproject.toml" in text
    assert "COPY validators/creator_engine_validator validators/creator_engine_validator" in text
    assert "COPY validators/requirements.txt /opt/creator-engine/requirements.txt" in text
    assert "COPY validators/requirements-dev.txt /opt/creator-engine/requirements-dev.txt" in text
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
    assert "python -m pip wheel" in text
    assert "--no-deps" in text
    assert "--no-build-isolation" in text
    assert "ARG CE_VALIDATOR_WHEEL=/opt/creator-engine/app/creator_engine_validator-*.whl" in text
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
    for package in ("openssh-client", "libsodium23"):
        assert _run_command_has_tokens(
            text, ["apt-get", "install", "-y", "--no-install-recommends", package]
        )
    for tool in ("ce", "cev3", "creator-engine-validator", "ssh-keygen"):
        assert _run_command_has_tokens(text, ["command", "-v", tool])
    assert "import pytest, xdist" in text
    assert "find_library('sodium')" in text


def test_runtime_instruction_contracts_reject_comments_and_adjacent_tokens() -> None:
    adversarial = """\
RUN set -eux; \\
    # python -m pip install --no-index --find-links=/opt/creator-engine/wheelhouse -r /opt/creator-engine/requirements.txt; \\
    echo openssh-client; \\
    command -v ce-shadow
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
        adversarial, ["apt-get", "install", "-y", "--no-install-recommends", "openssh-client"]
    )
    assert not _run_command_has_tokens(adversarial, ["command", "-v", "ce"])


def test_runtime_dockerfile_installs_gate_daemon_runtime_dependencies_from_pinned_repos() -> None:
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


def test_runtime_dockerfile_is_non_root_and_engine_agnostic() -> None:
    text = _dockerfile()

    assert "ARG CE_UID=10001" in text
    assert "ARG CE_GID=10001" in text
    assert "useradd --uid" in text
    assert "USER ${CE_UID}:${CE_GID}" in text
    assert "WORKDIR /workspace/creator-engine" in text
    assert 'ENTRYPOINT ["/usr/bin/tini", "--"]' in text
    assert 'CMD ["ce", "--help"]' in text
    assert "--runtime=" not in text
    assert "runsc" not in text
    assert "podman" not in text


def test_runtime_dockerfile_declares_required_oci_labels() -> None:
    text = _dockerfile()

    assert 'org.opencontainers.image.title="Creator Engine canonical runtime"' in text
    assert "org.opencontainers.image.description=" in text
    assert 'org.opencontainers.image.source="https://github.com/creator-engine/creator-engine"' in text
    assert 'org.opencontainers.image.version="${CE_IMAGE_VERSION}"' in text
    assert 'org.opencontainers.image.revision="${CE_IMAGE_REVISION}"' in text


def test_publish_runtime_workflow_triggers_only_manual_and_release_tags() -> None:
    on = _on_block(_workflow())

    assert set(on) == {"workflow_dispatch", "push"}
    assert on["push"]["tags"] == ["release/v*.*.*"]
    assert on["workflow_dispatch"]["inputs"]["version"]["required"] is True
    assert "branches" not in on["push"]


def test_publish_runtime_workflow_uses_least_privilege_package_publish_permissions() -> None:
    doc = _workflow()

    assert doc["permissions"] == {"contents": "read"}
    assert doc["jobs"]["publish"]["permissions"] == {
        "contents": "read",
        "packages": "write",
    }


def test_publish_runtime_workflow_builds_multi_arch_and_surfaces_manifest_digest() -> None:
    doc = _workflow()
    run = _all_run_text(doc)
    build = _step_named(doc, "Build and push multi-arch runtime image")["run"]
    digest = _step_named(doc, "Surface manifest-list digest")["run"]

    assert _step_named(doc, "Set up QEMU")["uses"] == "docker/setup-qemu-action@c7c53464625b32c7a7e944ae62b3e17d2b600130"
    assert _step_named(doc, "Set up QEMU")["with"]["platforms"] == "arm64"
    assert _step_named(doc, "Set up Docker Buildx")["uses"] == "docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f"
    assert "--file deploy/runtime-image/Dockerfile" in build
    assert "--platform linux/amd64,linux/arm64" in build
    assert "--push" in build
    assert "--tag \"${IMAGE}:${VERSION}\"" in build
    assert "--tag \"${IMAGE}:${GIT_SHA}\"" in build
    assert "ghcr.io/${repository}/ce-runtime" in run
    assert "docker login ghcr.io" in run
    assert "github.token" in str(_step_named(doc, "Login to GHCR")["env"])
    assert "docker buildx imagetools inspect" in digest
    assert "{{.Manifest.Digest}}" in digest
    assert "Consumers must pin the manifest-list digest" in digest


def test_runtime_readme_documents_consumer_contract_and_manifest_digest_rule() -> None:
    text = _readme()

    assert "Docker or rootless podman" in text
    assert "FROM ${CE_CANONICAL_RUNTIME_IMAGE}" in text
    assert "manifest-list digest" in text
    assert "Do not pin an amd64 or arm64 child" in text
    assert "exec format error" in text
    assert "linux/amd64" in text
    assert "linux/arm64" in text
    assert "deploy/daemons/Dockerfile" in text
    assert "CE_CANONICAL_RUNTIME_IMAGE" in text
