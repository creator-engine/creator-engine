"""Unit tests for surfaces.render."""

from __future__ import annotations

from pathlib import Path

import yaml

from surfaces import render


def _surface(name: str, *, version: str | None, commit_or_digest: object, source: str, custody: str = "rented"):
    return {
        "name": name,
        "version": version,
        "commit_or_digest": commit_or_digest,
        "source": source,
        "custody": custody,
        "update_policy": "pin by reviewed manifest change",
        "last_evaluated": "2026-06-26",
    }


def _manifest(tmp_path: Path, surfaces: list[dict[str, object]]) -> Path:
    path = tmp_path / "surfaces" / "manifest.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({"surfaces": surfaces}, sort_keys=False), encoding="utf-8")
    return path


def _happy_surfaces() -> list[dict[str, object]]:
    return [
        _surface(
            "Zig toolchain",
            version="0.15.2",
            commit_or_digest={
                "linux-x86_64": {"sha256": "b" * 64},
                "linux-aarch64": {"sha256": "a" * 64},
            },
            source="https://ziglang.org/download/0.15.2/",
        ),
        _surface(
            "herdr",
            version=None,
            commit_or_digest="ff924966",
            source="https://github.com/creator-engine/herdr-ce.git",
            custody="fork",
        ),
        _surface(
            "rust",
            version="1-bookworm",
            commit_or_digest="sha256:" + "c" * 64,
            source="docker.io/library/rust:1-bookworm",
            custody="docker-base-image",
        ),
    ]


def test_build_args_render_happy_path(tmp_path: Path):
    manifest = _manifest(tmp_path, _happy_surfaces())

    rendered = render.render_build_args(manifest)

    assert render._lines(rendered) == [
        "--build-arg HERDR_COMMIT_OR_DIGEST=ff924966",
        "--build-arg HERDR_SOURCE=https://github.com/creator-engine/herdr-ce.git",
        "--build-arg RUST_COMMIT_OR_DIGEST=" + "c" * 64,
        "--build-arg RUST_SOURCE=docker.io/library/rust",
        "--build-arg RUST_VERSION=1-bookworm",
        "--build-arg ZIG_TOOLCHAIN_LINUX_AARCH64_SHA256=" + "a" * 64,
        "--build-arg ZIG_TOOLCHAIN_LINUX_X86_64_SHA256=" + "b" * 64,
        "--build-arg ZIG_TOOLCHAIN_SOURCE=https://ziglang.org/download/0.15.2/",
        "--build-arg ZIG_TOOLCHAIN_VERSION=0.15.2",
    ]
    assert rendered.warnings == ()


def test_launch_env_render_happy_path(tmp_path: Path):
    manifest = _manifest(tmp_path, _happy_surfaces())

    rendered = render.render_launch_env(manifest)

    assert render._lines(rendered) == [
        "export HERDR_COMMIT_OR_DIGEST=ff924966",
        "export HERDR_SOURCE=https://github.com/creator-engine/herdr-ce.git",
        "export RUST_COMMIT_OR_DIGEST=sha256:" + "c" * 64,
        "export RUST_SOURCE=docker.io/library/rust:1-bookworm",
        "export RUST_VERSION=1-bookworm",
        "export ZIG_TOOLCHAIN_LINUX_AARCH64_SHA256=" + "a" * 64,
        "export ZIG_TOOLCHAIN_LINUX_X86_64_SHA256=" + "b" * 64,
        "export ZIG_TOOLCHAIN_SOURCE=https://ziglang.org/download/0.15.2/",
        "export ZIG_TOOLCHAIN_VERSION=0.15.2",
    ]
    assert rendered.warnings == ()


def test_required_surface_with_null_digest_fails(tmp_path: Path):
    manifest = _manifest(
        tmp_path,
        [
            _surface(
                "herdr",
                version=None,
                commit_or_digest=None,
                source="https://github.com/creator-engine/herdr-ce.git",
                custody="fork",
            )
        ],
    )

    try:
        render.render_build_args(manifest)
    except render.RenderError as exc:
        assert "required pinnable surface" in str(exc)
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("expected RenderError")


def test_host_only_null_digest_warns_without_failing(tmp_path: Path):
    manifest = _manifest(
        tmp_path,
        [
            _surface(
                "OpenBao",
                version=None,
                commit_or_digest=None,
                source="host:openbao",
                custody="host-only",
            )
        ],
    )

    rendered = render.render_launch_env(manifest)

    assert render._lines(rendered) == ["export OPENBAO_SOURCE=host:openbao"]
    assert rendered.warnings == ("OpenBao: commit_or_digest is null; no digest/ref value emitted",)


def test_output_is_deterministic_and_stable(tmp_path: Path):
    first = _manifest(tmp_path / "first", _happy_surfaces())
    second = _manifest(tmp_path / "second", list(reversed(_happy_surfaces())))

    assert render._lines(render.render_build_args(first)) == render._lines(render.render_build_args(second))
