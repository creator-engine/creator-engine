"""Tests for ``ce verify-install`` post-install provenance checks."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from creator_engine_validator import ce_cli, ce_provenance


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_digest(data: bytes) -> str:
    raw = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii")
    return "sha256=" + raw.rstrip("=")


def _manifest(sha256s_text: str) -> str:
    sha256s_sha = _sha256(sha256s_text.encode("utf-8"))
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


def _install_root(tmp_path: Path) -> tuple[Path, str, str]:
    package_bytes = b"print('genuine ce')\n"
    wheel_sha = _sha256(b"published wheel bytes")
    sha256s_text = f"{wheel_sha}  creator_engine_validator-0.2.0-py3-none-any.whl\n"
    sha256s_sha = _sha256(sha256s_text.encode("utf-8"))
    root = tmp_path / "install"
    target = root / f"venv-0.2.0-{sha256s_sha}"
    package = target / "lib" / "python3.14" / "site-packages" / "creator_engine_validator"
    dist = target / "lib" / "python3.14" / "site-packages" / "creator_engine_validator-0.2.0.dist-info"
    package.mkdir(parents=True)
    dist.mkdir(parents=True)
    (package / "__init__.py").write_bytes(package_bytes)
    (dist / "RECORD").write_text(
        "creator_engine_validator/__init__.py,"
        f"{_record_digest(package_bytes)},{len(package_bytes)}\n"
        "creator_engine_validator-0.2.0.dist-info/RECORD,,\n",
        encoding="utf-8",
    )
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
    return root, sha256s_text, _manifest(sha256s_text)


def test_genuine_match_passes_online_with_live_sha256s(tmp_path: Path):
    root, sha256s_text, manifest = _install_root(tmp_path)

    result = ce_provenance.verify_install(
        root,
        manifest_bytes=manifest.encode("utf-8"),
        urlopen=lambda _url: sha256s_text.encode("utf-8"),
    )

    assert result.ok is True
    payload = result.to_json()
    assert payload["status"] == "pass"
    assert payload["sha256s"]["status"] == "verified"
    assert payload["venv"]["record_files_checked"] == 1


def test_tampered_installed_bytes_refuse(tmp_path: Path):
    root, _sha256s_text, manifest = _install_root(tmp_path)
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


def test_offline_degrades_to_local_only_without_network(tmp_path: Path):
    root, _sha256s_text, manifest = _install_root(tmp_path)

    result = ce_provenance.verify_install(
        root,
        offline=True,
        manifest_bytes=manifest.encode("utf-8"),
        urlopen=lambda _url: (_ for _ in ()).throw(AssertionError("network used")),
    )

    assert result.ok is True
    assert result.to_json()["sha256s"]["status"] == "offline_skipped"


def test_missing_install_state_refuses(tmp_path: Path):
    root = tmp_path / "install"
    root.mkdir()

    result = ce_provenance.verify_install(root, offline=True, manifest_bytes=_manifest("").encode("utf-8"))

    assert result.ok is False
    assert result.to_json()["problems"] == ["missing_install_state"]


def test_ce_verify_install_cli_json(monkeypatch, tmp_path: Path, capsys):
    root, _sha256s_text, _manifest_text = _install_root(tmp_path)

    rc = ce_cli.main(["verify-install", "--install-root", str(root), "--offline", "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
