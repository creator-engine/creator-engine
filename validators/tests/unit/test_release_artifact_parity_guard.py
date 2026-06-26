from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.release_artifact_parity_guard import (
    CHECK_NAME,
    CODE_MISMATCH,
    CODE_MISSING,
    CODE_SHA256SUMS,
    run,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_release(root: Path) -> Path:
    docs = root / "docs"
    release_dir = docs / "downloads" / "0.2.0"
    release_dir.mkdir(parents=True)
    install = docs / "install.sh"
    install.write_text("#!/usr/bin/env bash\necho install\n", encoding="utf-8")
    shutil.copy2(install, release_dir / "install.sh")
    (release_dir / "SHA256SUMS").write_text(
        f"{_sha256(install)}  install.sh\n"
        f"{hashlib.sha256(b'wheel').hexdigest()}  package.whl\n",
        encoding="utf-8",
    )
    return release_dir


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_release_artifact_parity_guard_is_registered():
    assert CHECK_NAME in registered_checks()


def test_release_artifact_parity_guard_accepts_matching_served_mirror_and_sums(tmp_path: Path):
    _write_release(tmp_path)

    result = run([tmp_path])

    assert result.ok


def test_release_artifact_parity_guard_rejects_stale_mirrored_installer(tmp_path: Path):
    release_dir = _write_release(tmp_path)
    (release_dir / "install.sh").write_text("#!/usr/bin/env bash\necho stale\n", encoding="utf-8")

    result = run([tmp_path])

    assert _codes(result) == {CODE_MISMATCH}
    assert "docs/install.sh=" in result.errors[0].message
    assert "SHA256SUMS[install.sh]=" in result.errors[0].message


def test_release_artifact_parity_guard_rejects_stale_sha256s_entry(tmp_path: Path):
    release_dir = _write_release(tmp_path)
    (release_dir / "SHA256SUMS").write_text(f"{'0' * 64}  install.sh\n", encoding="utf-8")

    result = run([tmp_path])

    assert _codes(result) == {CODE_MISMATCH}


def test_release_artifact_parity_guard_rejects_missing_install_entry(tmp_path: Path):
    release_dir = _write_release(tmp_path)
    (release_dir / "SHA256SUMS").write_text(f"{hashlib.sha256(b'wheel').hexdigest()}  package.whl\n", encoding="utf-8")

    result = run([tmp_path])

    assert _codes(result) == {CODE_MISSING}


def test_release_artifact_parity_guard_rejects_malformed_sha256s(tmp_path: Path):
    release_dir = _write_release(tmp_path)
    (release_dir / "SHA256SUMS").write_text("not-a-digest  install.sh\n", encoding="utf-8")

    result = run([tmp_path])

    assert CODE_SHA256SUMS in _codes(result)
