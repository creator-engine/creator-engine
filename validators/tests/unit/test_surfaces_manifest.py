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


def _write_manifest(root: Path, doc: dict[str, object]) -> Path:
    path = root / "surfaces" / "manifest.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    (root / "validators" / "creator_engine_validator" / "checks").mkdir(parents=True)
    return path


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_surfaces_manifest_complete_is_registered():
    assert chk.CHECK_NAME in registered_checks()


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
