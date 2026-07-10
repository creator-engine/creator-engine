"""Tests for ``ce verify-install`` post-install provenance checks."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from pathlib import Path

from creator_engine_validator import ce_cli, ce_provenance

_WHEEL_FILENAME = "creator_engine_validator-0.2.0-py3-none-any.whl"
_WHEEL_URL = (
    "https://creator-engine.dev/downloads/0.2.0/"
    "creator_engine_validator-0.2.0-py3-none-any.whl"
)
_SHA256S_URL = "https://creator-engine.dev/downloads/0.2.0/SHA256SUMS"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_digest(data: bytes) -> str:
    raw = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii")
    return "sha256=" + raw.rstrip("=")


def _build_wheel(record_text: str, files: dict[str, bytes]) -> bytes:
    """Build a minimal wheel zip carrying ``files`` plus the dist-info RECORD."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for arcname, payload in files.items():
            archive.writestr(arcname, payload)
        archive.writestr(
            "creator_engine_validator-0.2.0.dist-info/RECORD", record_text
        )
    return buffer.getvalue()


def _url_opener(mapping: dict[str, bytes]):
    def _open(url: str) -> bytes:
        try:
            return mapping[url]
        except KeyError as exc:  # pragma: no cover - defensive
            raise AssertionError(f"unexpected fetch: {url}") from exc

    return _open


def _manifest(sha256s_text: str, *, wheel_sha: str | None = None) -> str:
    sha256s_sha = _sha256(sha256s_text.encode("utf-8"))
    if wheel_sha is None:
        wheel_sha = _sha256(b"published wheel bytes")
    return f"""artifact_manifest:
  artifact_manifest_version: 1
  package_name: creator-engine-validator
  package_version: 0.2.0
  python_requires: >=3.14
  artifact_base_url: https://creator-engine.dev/downloads/0.2.0
  sha256s_url: https://creator-engine.dev/downloads/0.2.0/SHA256SUMS
  sha256s_sha256: {sha256s_sha}
  install_sh_url: https://creator-engine.dev/install.sh
  install_sh_sha256s_entry: install.sh
  answers_schema_url: https://creator-engine.dev/install-answers.schema.yaml
  answers_schema_sha256: {"1" * 64}
  app_wheel: creator_engine_validator-0.2.0-py3-none-any.whl
  required_wheels:
    - filename: creator_engine_validator-0.2.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
      sha256: {wheel_sha}
      platforms: all
  python_acquisition:
    - platform: linux-x86_64-cp314
      tool: uv
      version: 0.11.21
      url: https://creator-engine.dev/downloads/0.2.0/uv.tar.gz
      sha256: {"2" * 64}
      command: uv python install 3.14
"""


def _install_root(tmp_path: Path, *, root: Path | None = None):
    """Build a genuine install tree + the trusted published wheel + SHA256SUMS.

    Returns ``(root, sha256s_text, manifest_text, wheel_bytes)`` so online tests
    can serve the *trusted* wheel bytes (the real anchor) at the wheel URL and
    the live SHA256SUMS at its URL.
    """
    package_bytes = b"print('genuine ce')\n"
    record_text = (
        "creator_engine_validator/__init__.py,"
        f"{_record_digest(package_bytes)},{len(package_bytes)}\n"
        "creator_engine_validator-0.2.0.dist-info/RECORD,,\n"
    )
    wheel_bytes = _build_wheel(
        record_text,
        {"creator_engine_validator/__init__.py": package_bytes},
    )
    wheel_sha = _sha256(wheel_bytes)
    sha256s_text = f"{wheel_sha}  {_WHEEL_FILENAME}\n"
    sha256s_sha = _sha256(sha256s_text.encode("utf-8"))
    root = root or tmp_path / "install"
    target = root / f"venv-0.2.0-{sha256s_sha}"
    package = target / "lib" / "python3.14" / "site-packages" / "creator_engine_validator"
    dist = target / "lib" / "python3.14" / "site-packages" / "creator_engine_validator-0.2.0.dist-info"
    package.mkdir(parents=True)
    dist.mkdir(parents=True)
    (package / "__init__.py").write_bytes(package_bytes)
    (dist / "RECORD").write_text(record_text, encoding="utf-8")
    (root / "venv").symlink_to(target.name)
    (root / "install-state").write_text(
        "\n".join(
            [
                f"sha256s_sha256={sha256s_sha}",
                "package_version=0.2.0",
                f"venv_path={root / 'venv'}",
                f"venv_target={target}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return root, sha256s_text, _manifest(sha256s_text, wheel_sha=wheel_sha), wheel_bytes


def _configured_default_root(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.delenv("CE_INSTALL_ROOT", raising=False)
    monkeypatch.delenv("CE_HOME", raising=False)
    xdg_data = tmp_path / "xdg-data"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data))
    return xdg_data / "creator-engine" / "bootstrap"


def test_genuine_match_passes_online_with_live_sha256s(tmp_path: Path):
    root, sha256s_text, manifest, wheel_bytes = _install_root(tmp_path)

    result = ce_provenance.verify_install(
        root,
        manifest_bytes=manifest.encode("utf-8"),
        urlopen=_url_opener(
            {
                _SHA256S_URL: sha256s_text.encode("utf-8"),
                _WHEEL_URL: wheel_bytes,
            }
        ),
    )

    assert result.ok is True
    payload = result.to_json()
    assert payload["status"] == "pass"
    assert payload["sha256s"]["status"] == "verified"
    assert payload["venv"]["record_files_checked"] == 1
    # Online full-assurance: file digests are anchored in the trusted wheel,
    # not the installed venv's own RECORD.
    assert payload["venv"]["assurance"] == "published_release"
    assert payload["venv"]["anchor"] == "published_wheel"


def test_tampered_installed_bytes_refuse(tmp_path: Path):
    root, _sha256s_text, manifest, _wheel_bytes = _install_root(tmp_path)
    package_file = next(root.glob("venv-*/lib/python3.14/site-packages/creator_engine_validator/__init__.py"))
    package_file.write_bytes(b"print('tampered')\n")

    result = ce_provenance.verify_install(
        root,
        offline=True,
        manifest_bytes=manifest.encode("utf-8"),
    )

    assert result.ok is False
    assert result.to_json()["status"] == "refuse"
    assert "venv_record_hash_mismatch" in result.to_json()["problems"]


def test_tampered_file_and_record_refused_online(tmp_path: Path):
    """Issue 1: a tampered file WITH a matching tampered installed RECORD must
    still be REFUSED online, proving the trust anchor is the published wheel
    (signed SHA256SUMS chain), not the mutable installed RECORD."""
    root, sha256s_text, manifest, wheel_bytes = _install_root(tmp_path)
    package_file = next(
        root.glob("venv-*/lib/python3.14/site-packages/creator_engine_validator/__init__.py")
    )
    tampered = b"print('tampered')\n"
    package_file.write_bytes(tampered)
    # Attacker also rewrites the installed RECORD to match the tampered bytes,
    # so any check rooted in the installed RECORD would (wrongly) pass.
    record_file = next(root.glob("venv-*/**/creator_engine_validator-0.2.0.dist-info/RECORD"))
    record_file.write_text(
        "creator_engine_validator/__init__.py,"
        f"{_record_digest(tampered)},{len(tampered)}\n"
        "creator_engine_validator-0.2.0.dist-info/RECORD,,\n",
        encoding="utf-8",
    )

    result = ce_provenance.verify_install(
        root,
        manifest_bytes=manifest.encode("utf-8"),
        urlopen=_url_opener(
            {
                _SHA256S_URL: sha256s_text.encode("utf-8"),
                _WHEEL_URL: wheel_bytes,
            }
        ),
    )

    assert result.ok is False
    assert result.to_json()["status"] == "refuse"
    assert "venv_record_hash_mismatch" in result.to_json()["problems"]


def test_legitimate_venv_owned_console_script_accepted(tmp_path: Path):
    """Issue 2: a RECORD entry for a venv-owned console script (``../../../bin/ce``)
    resolves inside the venv root, not site-packages — it must be ACCEPTED, not
    flagged as a path escape."""
    root, sha256s_text, manifest, wheel_bytes = _install_root(tmp_path)
    target = next(root.glob("venv-0.2.0-*"))
    bin_dir = target / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script_bytes = b"#!/usr/bin/env python\n# console script ce\n"
    (bin_dir / "ce").write_bytes(script_bytes)

    record_file = next(root.glob("venv-*/**/creator_engine_validator-0.2.0.dist-info/RECORD"))
    package_bytes = b"print('genuine ce')\n"
    new_record = (
        "creator_engine_validator/__init__.py,"
        f"{_record_digest(package_bytes)},{len(package_bytes)}\n"
        f"../../../bin/ce,{_record_digest(script_bytes)},{len(script_bytes)}\n"
        "creator_engine_validator-0.2.0.dist-info/RECORD,,\n"
    )
    record_file.write_text(new_record, encoding="utf-8")
    # Rebuild the trusted wheel so its RECORD also carries the console-script
    # entry (the published release's RECORD is the anchor).
    wheel_bytes = _build_wheel(
        new_record,
        {
            "creator_engine_validator/__init__.py": package_bytes,
            "../../../bin/ce": script_bytes,
        },
    )
    wheel_sha = _sha256(wheel_bytes)
    sha256s_text = f"{wheel_sha}  {_WHEEL_FILENAME}\n"
    sha256s_sha = _sha256(sha256s_text.encode("utf-8"))
    manifest = _manifest(sha256s_text, wheel_sha=wheel_sha)
    # Re-pin install-state + rename the venv target to the new sha256s pin.
    new_target = root / f"venv-0.2.0-{sha256s_sha}"
    target.rename(new_target)
    (root / "venv").unlink()
    (root / "venv").symlink_to(new_target.name)
    (root / "install-state").write_text(
        "\n".join(
            [
                f"sha256s_sha256={sha256s_sha}",
                "package_version=0.2.0",
                f"venv_path={root / 'venv'}",
                f"venv_target={new_target}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = ce_provenance.verify_install(
        root,
        manifest_bytes=manifest.encode("utf-8"),
        urlopen=_url_opener(
            {
                _SHA256S_URL: sha256s_text.encode("utf-8"),
                _WHEEL_URL: wheel_bytes,
            }
        ),
    )

    assert "venv_record_path_escape" not in result.to_json()["problems"]
    assert result.ok is True
    assert result.to_json()["venv"]["record_files_checked"] == 2


def test_true_path_escape_outside_venv_root_refused(tmp_path: Path):
    """A RECORD entry resolving OUTSIDE the venv root entirely is still a true
    escape and must be flagged."""
    root, _sha256s_text, manifest, _wheel_bytes = _install_root(tmp_path)
    record_file = next(root.glob("venv-*/**/creator_engine_validator-0.2.0.dist-info/RECORD"))
    package_bytes = b"print('genuine ce')\n"
    record_file.write_text(
        "creator_engine_validator/__init__.py,"
        f"{_record_digest(package_bytes)},{len(package_bytes)}\n"
        "../../../../../../../../etc/passwd,sha256=deadbeef,1\n"
        "creator_engine_validator-0.2.0.dist-info/RECORD,,\n",
        encoding="utf-8",
    )

    result = ce_provenance.verify_install(
        root,
        offline=True,
        manifest_bytes=manifest.encode("utf-8"),
    )

    assert "venv_record_path_escape" in result.to_json()["problems"]
    assert result.ok is False


def test_offline_degrades_to_local_only_without_network(tmp_path: Path):
    root, _sha256s_text, manifest, _wheel_bytes = _install_root(tmp_path)

    result = ce_provenance.verify_install(
        root,
        offline=True,
        manifest_bytes=manifest.encode("utf-8"),
        urlopen=lambda _url: (_ for _ in ()).throw(AssertionError("network used")),
    )

    assert result.ok is True
    payload = result.to_json()
    assert payload["sha256s"]["status"] == "offline_skipped"
    # Offline is reduced assurance: it can only attest "matches local
    # install-state", never "matches the published release".
    assert payload["venv"]["assurance"] == "local_install_state_only"
    assert payload["venv"]["anchor"] == "installed_record"


def test_missing_install_state_refuses(tmp_path: Path):
    root = tmp_path / "install"
    root.mkdir()

    result = ce_provenance.verify_install(root, offline=True, manifest_bytes=_manifest("").encode("utf-8"))

    assert result.ok is False
    assert result.to_json()["problems"] == ["missing_install_state"]


def test_non_default_root_does_not_probe_populated_default_root(monkeypatch, tmp_path: Path):
    default_root = _configured_default_root(monkeypatch, tmp_path)
    default_root, _sha256s_text, manifest, _wheel_bytes = _install_root(
        tmp_path, root=default_root
    )
    default_target = next(default_root.glob("venv-0.2.0-*"))
    custom_root = tmp_path / "custom-install"
    custom_root.mkdir()
    (custom_root / "install-state").write_text(
        (default_root / "install-state").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (custom_root / "venv").symlink_to(default_target)

    result = ce_provenance.verify_install(
        custom_root,
        offline=True,
        manifest_bytes=manifest.encode("utf-8"),
    )

    payload = result.to_json()
    assert result.ok is False
    assert payload["install_root"] == str(custom_root)
    assert "venv_target_outside_install_root" in payload["problems"]
    assert "live_venv_outside_install_root" in payload["problems"]


def test_non_default_root_missing_does_not_fall_back_to_default(monkeypatch, tmp_path: Path):
    default_root = _configured_default_root(monkeypatch, tmp_path)
    _install_root(tmp_path, root=default_root)
    custom_root = tmp_path / "missing-custom-install"

    result = ce_provenance.verify_install(
        custom_root,
        offline=True,
        manifest_bytes=_manifest("").encode("utf-8"),
    )

    payload = result.to_json()
    assert result.ok is False
    assert payload["install_root"] == str(custom_root)
    assert payload["problems"] == ["missing_install_state"]


def test_ce_verify_install_cli_json(monkeypatch, tmp_path: Path, capsys):
    root, _sha256s_text, _manifest_text, _wheel_bytes = _install_root(tmp_path)

    rc = ce_cli.main(["verify-install", "--install-root", str(root), "--offline", "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
    assert payload["header"] == f"checking root: {root}"
