"""Unit tests for the rented-surface manifest completeness check."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import surfaces_manifest as chk


def _surface(name: str, *, version: str | None = "1.0.0", commit_or_digest: object = "a" * 64) -> dict[str, object]:
    return {
        "name": name,
        "version": version,
        "commit_or_digest": commit_or_digest,
        "source": f"test:{name}",
        "custody": "test",
        "update_policy": "test updates by manifest change",
        "last_evaluated": "2026-06-26",
    }


def _complete_doc() -> dict[str, object]:
    return {
        "surfaces": [
            _surface("codex", version="0.141.0", commit_or_digest=None),
            _surface("herdr", version=None, commit_or_digest="ff924966"),
            _surface(
                "Zig toolchain",
                version="0.15.2",
                commit_or_digest={
                    "linux-aarch64": {
                        "sha256": "958ed7d1e00d0ea76590d27666efbf7a932281b3d7ba0c6b01b0ff26498f667f"
                    },
                    "linux-x86_64": {
                        "sha256": "02aa270f183da276e5b5920b1dac44a63f1a49e55050ebde3aecc9eb82f93239"
                    },
                },
            ),
            _surface("PyYAML", version="6.0.3", commit_or_digest=None),
            _surface("jsonschema", version="4.26.0", commit_or_digest=None),
            _surface("textual", version="8.2.7", commit_or_digest=None),
            _surface("OpenBao", version=None, commit_or_digest=None),
            _surface("gVisor/runsc", version=None, commit_or_digest=None),
            _surface("gvproxy", version=None, commit_or_digest=None),
        ]
    }


def _consistent_doc() -> dict[str, object]:
    doc = _complete_doc()
    digests = {
        "codex": "1" * 64,
        "PyYAML": "2" * 64,
        "jsonschema": "3" * 64,
        "textual": "4" * 64,
    }
    for surface in doc["surfaces"]:  # type: ignore[index]
        name = surface["name"]  # type: ignore[index]
        if name in digests:
            surface["commit_or_digest"] = digests[name]  # type: ignore[index]
        if name in {"OpenBao", "gVisor/runsc", "gvproxy"}:
            surface["source"] = f"host:{name}"  # type: ignore[index]
            surface["custody"] = "host-only"  # type: ignore[index]
            surface["update_policy"] = "host inventory required before pinning"  # type: ignore[index]
    return doc


def _write_manifest(root: Path, doc: dict[str, object]) -> Path:
    path = root / "surfaces" / "manifest.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    (root / "validators" / "creator_engine_validator" / "checks").mkdir(parents=True)
    return path


def _write_consistent_repo(root: Path, doc: dict[str, object] | None = None) -> None:
    _write_manifest(root, doc or _consistent_doc())
    dockerfile = root / "deploy" / "vps-runsc" / "Dockerfile"
    dockerfile.parent.mkdir(parents=True, exist_ok=True)
    dockerfile.write_text(
        "\n".join(
            [
                "FROM --platform=linux/amd64 rust:1-bookworm@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa AS herdr-builder",
                "ARG HERDR_SOURCE_REF=ff924966bd789afabec1a52d74f24392f45838ef",
                "ARG ZIG_VERSION=0.15.2",
                "FROM debian:bookworm-slim@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb AS runtime",
                "",
            ]
        ),
        encoding="utf-8",
    )
    runner = root / "deploy" / "vps-runsc" / "run-vps-runsc.sh"
    runner.write_text(
        'CE_VPS_IMAGE="${CE_VPS_IMAGE:-creator-engine/codex-runsc:0.141.0-x86_64}"\n',
        encoding="utf-8",
    )
    validators = root / "validators"
    validators.mkdir(exist_ok=True)
    (validators / "requirements.txt").write_text("jsonschema==4.26.0\npyyaml==6.0.3\n", encoding="utf-8")
    (validators / "requirements-dev.txt").write_text("textual==8.2.7\n", encoding="utf-8")


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_surfaces_manifest_complete_is_registered():
    assert chk.CHECK_NAME in registered_checks()


def test_surfaces_manifest_consistent_is_registered():
    assert chk.CONSISTENT_CHECK_NAME in registered_checks()


def test_complete_manifest_passes_with_python_digest_warnings(tmp_path: Path):
    _write_manifest(tmp_path, _complete_doc())

    result = chk.run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]
    assert {warning.code for warning in result.warnings} == {chk.CODE_PYTHON_DIGEST_WARNING}


def test_missing_required_field_fails(tmp_path: Path):
    doc = _complete_doc()
    first = doc["surfaces"][0]  # type: ignore[index]
    del first["custody"]  # type: ignore[index]
    _write_manifest(tmp_path, doc)

    result = chk.run([tmp_path])

    assert chk.CODE_MISSING_FIELD in _codes(result)
    assert any(".custody" in error.path for error in result.errors)


def test_pinnable_surface_missing_digest_fails(tmp_path: Path):
    doc = _complete_doc()
    doc["surfaces"][1]["commit_or_digest"] = None  # type: ignore[index]
    _write_manifest(tmp_path, doc)

    result = chk.run([tmp_path])

    assert _codes(result) >= {chk.CODE_PINNABLE_MISSING_DIGEST}
    assert any("herdr.commit_or_digest" in error.path for error in result.errors)


def test_host_only_null_versions_and_digests_are_permitted(tmp_path: Path):
    _write_manifest(tmp_path, _complete_doc())

    result = chk.run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]
    assert not any("OpenBao" in error.path or "gVisor" in error.path or "gvproxy" in error.path for error in result.errors)


def test_consistent_manifest_and_repo_files_pass(tmp_path: Path):
    _write_consistent_repo(tmp_path)

    result = registered_checks()[chk.CONSISTENT_CHECK_NAME].run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_consistent_manifest_missing_dockerfile_digest_fails(tmp_path: Path):
    _write_consistent_repo(tmp_path)
    dockerfile = tmp_path / "deploy" / "vps-runsc" / "Dockerfile"
    dockerfile.write_text(
        "\n".join(
            [
                "FROM creator-engine/codex-runsc:0.141.0 AS runtime",
                "ARG HERDR_SOURCE_REF=ff924966bd789afabec1a52d74f24392f45838ef",
                "ARG ZIG_VERSION=0.15.2",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = registered_checks()[chk.CONSISTENT_CHECK_NAME].run([tmp_path])

    assert chk.CODE_DOCKERFILE_FROM_MISSING_DIGEST in _codes(result)


def test_consistent_manifest_mismatched_dockerfile_digest_fails(tmp_path: Path):
    _write_consistent_repo(tmp_path)
    dockerfile = tmp_path / "deploy" / "vps-runsc" / "Dockerfile"
    dockerfile.write_text(
        "\n".join(
            [
                "FROM creator-engine/codex-runsc:0.141.0@sha256:9999999999999999999999999999999999999999999999999999999999999999 AS runtime",
                "ARG HERDR_SOURCE_REF=ff924966bd789afabec1a52d74f24392f45838ef",
                "ARG ZIG_VERSION=0.15.2",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = registered_checks()[chk.CONSISTENT_CHECK_NAME].run([tmp_path])

    assert chk.CODE_DOCKERFILE_FROM_DIGEST_MISMATCH in _codes(result)


def test_consistent_manifest_mismatched_arg_version_and_ref_fail(tmp_path: Path):
    _write_consistent_repo(tmp_path)
    dockerfile = tmp_path / "deploy" / "vps-runsc" / "Dockerfile"
    dockerfile.write_text(
        "\n".join(
            [
                "FROM rust:1-bookworm@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "ARG HERDR_CE_REF=deadbeef",
                "ARG ZIG_VERSION=0.15.1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = registered_checks()[chk.CONSISTENT_CHECK_NAME].run([tmp_path])

    assert chk.CODE_ARG_MISMATCH in _codes(result)
    assert any("HERDR_CE_REF" in error.message for error in result.errors)
    assert any("ZIG_VERSION" in error.message for error in result.errors)


def test_consistent_manifest_mismatched_requirements_pin_fails(tmp_path: Path):
    _write_consistent_repo(tmp_path)
    (tmp_path / "validators" / "requirements.txt").write_text(
        "jsonschema==4.26.0\npyyaml==6.0.2\n",
        encoding="utf-8",
    )

    result = registered_checks()[chk.CONSISTENT_CHECK_NAME].run([tmp_path])

    assert chk.CODE_REQUIREMENTS_PIN_MISMATCH in _codes(result)
    assert any("pyyaml" in error.message for error in result.errors)


def test_consistent_manifest_pinnable_null_digest_fails(tmp_path: Path):
    doc = _consistent_doc()
    doc["surfaces"][1]["commit_or_digest"] = None  # type: ignore[index]
    _write_consistent_repo(tmp_path, doc)

    result = registered_checks()[chk.CONSISTENT_CHECK_NAME].run([tmp_path])

    assert chk.CODE_CONSISTENCY_PINNABLE_MISSING_DIGEST in _codes(result)
    assert any("herdr.commit_or_digest" in error.path for error in result.errors)


def test_consistent_manifest_phase1_pending_null_digests_pass(tmp_path: Path):
    doc = _consistent_doc()
    for surface in doc["surfaces"]:  # type: ignore[index]
        if surface["name"] in {"codex", "PyYAML", "jsonschema", "textual"}:  # type: ignore[index]
            surface["commit_or_digest"] = None  # type: ignore[index]
    _write_consistent_repo(tmp_path, doc)

    result = registered_checks()[chk.CONSISTENT_CHECK_NAME].run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_current_repo_surfaces_manifest_consistent_passes():
    repo_root = Path(__file__).resolve().parents[3]

    result = registered_checks()[chk.CONSISTENT_CHECK_NAME].run([repo_root])

    assert result.ok, [error.format() for error in result.errors]
