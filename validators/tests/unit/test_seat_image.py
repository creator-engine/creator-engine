"""Static/offline checks for the canonical CE tenant seat image publish surface."""

from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SEAT_DIR = REPO_ROOT / "deploy" / "seat-image"
DOCKERFILE = SEAT_DIR / "Dockerfile"
README = SEAT_DIR / "README.md"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish-seat-image.yml"
SURFACES = REPO_ROOT / "surfaces" / "manifest.yaml"


def _dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _surfaces() -> dict:
    return yaml.safe_load(SURFACES.read_text(encoding="utf-8"))


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


def test_seat_dockerfile_derives_from_digest_pinned_runtime_arg() -> None:
    text = _dockerfile()

    assert (
        "ARG CE_CANONICAL_RUNTIME_IMAGE="
        "ghcr.io/creator-engine/creator-engine/ce-runtime@sha256:UNSET"
    ) in text
    assert "FROM ${CE_CANONICAL_RUNTIME_IMAGE}" in text
    assert "FROM --platform=linux/amd64" not in text
    assert "FROM --platform=linux/arm64" not in text
    assert "FROM --platform=$TARGETPLATFORM" not in text


def test_seat_dockerfile_installs_both_agent_clis_with_version_pins() -> None:
    text = _dockerfile()

    assert "ARG NODE_MAJOR=22" in text
    assert "https://deb.nodesource.com/node_${NODE_MAJOR}.x" in text
    assert "ARG CODEX_CLI_VERSION=0.142.4" in text
    assert "Keep this default in sync with the claude-code surface pin." in text
    assert "ARG CLAUDE_CODE_CLI_VERSION=2.1.201" in text
    assert '"@openai/codex@${CODEX_CLI_VERSION}"' in text
    assert '"@anthropic-ai/claude-code@${CLAUDE_CODE_CLI_VERSION}"' in text
    assert "node --version | grep -E '^v22\\.'" in text
    assert "command -v codex" in text
    assert "command -v claude" in text
    assert "codex --version" in text
    assert "claude --version" in text


def test_seat_dockerfile_preserves_non_root_ce_uid_runtime() -> None:
    text = _dockerfile()

    assert "ARG CE_UID=10001" in text
    assert "ARG CE_GID=10001" in text
    assert "USER root" in text
    assert "USER ${CE_UID}:${CE_GID}" in text
    assert 'test "$(id -u)" = "${CE_UID}"' in text
    assert "WORKDIR /workspace/creator-engine" in text
    assert 'ENTRYPOINT ["/usr/bin/tini", "--"]' in text


def test_seat_dockerfile_excludes_fleet_only_artifacts() -> None:
    text = _dockerfile().lower()

    assert "herdr" not in text
    assert "broker" not in text
    assert "runsc" not in text


def test_publish_seat_workflow_triggers_only_manual_and_release_tags() -> None:
    on = _on_block(_workflow())

    assert set(on) == {"workflow_dispatch", "push"}
    assert on["push"]["tags"] == ["release/v*.*.*"]
    assert on["workflow_dispatch"]["inputs"]["version"]["required"] is True
    assert "branches" not in on["push"]


def test_publish_seat_workflow_uses_least_privilege_package_publish_permissions() -> None:
    doc = _workflow()

    assert doc["permissions"] == {"contents": "read"}
    assert doc["jobs"]["publish"]["permissions"] == {
        "contents": "read",
        "packages": "write",
    }


def test_publish_seat_workflow_builds_multi_arch_from_runtime_manifest_digest() -> None:
    doc = _workflow()
    run = _all_run_text(doc)
    runtime = _step_named(doc, "Resolve runtime manifest-list digest")["run"]
    build = _step_named(doc, "Build and push multi-arch seat image")["run"]
    digest = _step_named(doc, "Surface manifest-list digest")["run"]

    assert _step_named(doc, "Set up QEMU")["uses"] == "docker/setup-qemu-action@c7c53464625b32c7a7e944ae62b3e17d2b600130"
    assert _step_named(doc, "Set up QEMU")["with"]["platforms"] == "arm64"
    assert _step_named(doc, "Set up Docker Buildx")["uses"] == "docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f"
    assert "ghcr.io/${repository}/ce-seat" in run
    assert "ghcr.io/${repository}/ce-runtime" in run
    assert "docker login ghcr.io" in run
    assert "github.token" in str(_step_named(doc, "Login to GHCR")["env"])
    assert "docker buildx imagetools inspect \"${RUNTIME_IMAGE}:${VERSION}\"" in runtime
    assert "runtime_digest_ref=\"${RUNTIME_IMAGE}@${runtime_digest}\"" in runtime
    assert "--file deploy/seat-image/Dockerfile" in build
    assert "--platform linux/amd64,linux/arm64" in build
    assert "--build-arg CE_CANONICAL_RUNTIME_IMAGE=\"${CE_CANONICAL_RUNTIME_IMAGE}\"" in build
    assert "--push" in build
    assert "--tag \"${IMAGE}:${VERSION}\"" in build
    assert "--tag \"${IMAGE}:${GIT_SHA}\"" in build
    assert "docker buildx imagetools inspect" in digest
    assert "{{.Manifest.Digest}}" in digest
    assert "Consumers must pin the manifest-list digest" in digest


def test_seat_readme_documents_contract_and_deliberate_exclusions() -> None:
    text = _readme()

    assert "FROM ${CE_CANONICAL_RUNTIME_IMAGE}" in text
    assert "manifest-list digest" in text
    assert "Do not pin" in text
    assert "`amd64` or `arm64`" in text
    assert "child manifest digest" in text
    assert "linux/amd64" in text
    assert "linux/arm64" in text
    assert "no credentials" in text
    assert "herdr" in text
    assert "broker" in text
    assert "runsc" in text
    assert "runtime mounts" in text
    assert "ce-ops" not in text.lower()


def test_surfaces_manifest_records_pinned_seat_image_digest() -> None:
    doc = _surfaces()
    seat = next(
        surface for surface in doc["surfaces"] if surface["name"] == "CE seat image"
    )

    assert seat["version"] == "0.3.3"
    assert seat["commit_or_digest"] == (
        "sha256:1def5b0cd1e5e465cb42fa73934bc6ee4b1c93fe005bbd7d111a4589dc96b698"
    )
    assert seat["source"] == "ghcr.io/creator-engine/creator-engine/ce-seat"
    assert "manifest-list digest" in seat["update_policy"]
    assert "UNSET until published" not in seat["update_policy"]


def test_surfaces_manifest_tracks_claude_code_cli_pin() -> None:
    doc = _surfaces()
    claude_code = next(
        surface for surface in doc["surfaces"] if surface["name"] == "claude-code"
    )

    assert claude_code["version"] == "2.1.201"
    assert claude_code["commit_or_digest"] == "UNSET"
    assert claude_code["source"] == "npm:@anthropic-ai/claude-code"
    assert claude_code["custody"] == "rented"
    assert claude_code["update_policy"] == "downstream digest capture pending"
