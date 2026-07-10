"""Post-install provenance verifier for CE release installs.

The verifier is intentionally read-only: it checks the install-state pin,
validates installed files against wheel RECORD digests, and in online mode
compares the install's signed SHA256SUMS pin with the live release manifest.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen as _stdlib_urlopen

from .bootstrap_manifest import BootstrapManifest, parse_bootstrap_manifest, parse_sha256s

PUBLISHED_INSTALL_SPEC_URL = "https://creator-engine.dev/llms-install.md"

UrlOpen = Callable[[str], Any]


@dataclass(frozen=True)
class VerifyInstallResult:
    ok: bool
    status: str
    reason: str
    install_root: str
    state: dict[str, str] = field(default_factory=dict)
    manifest: dict[str, str] = field(default_factory=dict)
    sha256s: dict[str, str] = field(default_factory=dict)
    venv: dict[str, Any] = field(default_factory=dict)
    problems: tuple[str, ...] = ()

    @property
    def header(self) -> str:
        return f"checking root: {self.install_root}"

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "reason": self.reason,
            "header": self.header,
            "install_root": self.install_root,
            "state": dict(self.state),
            "manifest": dict(self.manifest),
            "sha256s": dict(self.sha256s),
            "venv": dict(self.venv),
            "problems": list(self.problems),
        }


def default_install_root() -> Path:
    if os.environ.get("CE_INSTALL_ROOT"):
        return Path(os.environ["CE_INSTALL_ROOT"])
    base = os.environ.get("CE_HOME")
    if base:
        return Path(base) / "bootstrap"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "creator-engine" / "bootstrap"
    return Path.home() / ".local" / "share" / "creator-engine" / "bootstrap"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_state(path: Path) -> dict[str, str]:
    state: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        key, sep, value = raw.partition("=")
        if sep:
            state[key.strip()] = value.strip()
    return state


def _as_bytes(response: Any) -> bytes:
    if isinstance(response, bytes):
        return response
    if isinstance(response, str):
        return response.encode("utf-8")
    with response:
        return response.read()


def _fetch(url: str, opener: UrlOpen) -> bytes:
    return _as_bytes(opener(url))


def _decode_record_digest(value: str) -> str | None:
    if not value.startswith("sha256="):
        return None
    encoded = value.split("=", 1)[1]
    padding = "=" * (-len(encoded) % 4)
    try:
        raw = base64.urlsafe_b64decode((encoded + padding).encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return None
    return raw.hex()


def _path_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _parse_record_rows(record_text: str) -> list[tuple[str, str, str]]:
    """Parse RECORD CSV text into ``(relpath, digest, size)`` rows with a hash."""
    rows: list[tuple[str, str, str]] = []
    for row in csv.reader(io.StringIO(record_text)):
        if len(row) < 3 or not row[1]:
            continue
        rows.append((row[0], row[1], row[2]))
    return rows


def _trusted_record_text_from_wheel(
    wheel_bytes: bytes, package_version: str
) -> str | None:
    """Extract the dist-info RECORD from the trusted published wheel bytes.

    The wheel is a zip; its RECORD is the published release's own file
    manifest. Anchoring installed-file verification here (rather than the
    venv's self-referential RECORD) is what defeats a tampered-file-plus-
    tampered-RECORD attack.
    """
    arcname = f"creator_engine_validator-{package_version}.dist-info/RECORD"
    try:
        with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
            return archive.read(arcname).decode("utf-8")
    except (KeyError, zipfile.BadZipFile, UnicodeDecodeError):
        return None


def _verify_record(
    venv_target: Path,
    package_version: str,
    *,
    trusted_record_text: str | None,
) -> tuple[list[str], dict[str, Any]]:
    """Verify installed venv bytes against trusted RECORD digests.

    Online (``trusted_record_text`` provided): the digests come from the
    published wheel's RECORD (trust anchored in the signed SHA256SUMS chain);
    the installed RECORD is used only as a file map. Offline: the only available
    source is the installed RECORD, which is a *reduced-assurance* check — it can
    only attest "matches local install-state", never "matches the published
    release". Path containment is validated against the VENV ROOT so legitimate
    venv-owned console scripts (e.g. ``../../../bin/ce``) are accepted.
    """
    problems: list[str] = []
    record_glob = f"creator_engine_validator-{package_version}.dist-info/RECORD"
    records = sorted(venv_target.glob(f"**/{record_glob}"))
    if not records:
        return ["venv_record_missing"], {
            "target": str(venv_target),
            "record_files_checked": 0,
            "anchor": "published_wheel" if trusted_record_text else "installed_record",
            "assurance": "published_release" if trusted_record_text else "local_install_state_only",
        }
    record = records[0]
    site_packages = record.parent.parent
    # site_packages == <venv>/lib/pythonX.Y/site-packages → venv root is 3 up.
    venv_root = site_packages.parent.parent.parent

    if trusted_record_text is not None:
        anchor = "published_wheel"
        assurance = "published_release"
        rows = _parse_record_rows(trusted_record_text)
    else:
        anchor = "installed_record"
        assurance = "local_install_state_only"
        rows = _parse_record_rows(record.read_text(encoding="utf-8"))

    checked = 0
    for rel, digest, size in rows:
        installed = site_packages / rel
        # Console scripts and other venv-owned files legitimately resolve
        # outside site-packages (e.g. <venv>/bin/ce). Validate containment
        # against the venv root, only flagging a TRUE escape.
        if not _path_inside(installed, venv_root):
            problems.append("venv_record_path_escape")
            continue
        if not installed.is_file():
            problems.append("venv_record_file_missing")
            continue
        expected = _decode_record_digest(digest)
        if expected is None:
            problems.append("venv_record_digest_unsupported")
            continue
        data = installed.read_bytes()
        if _sha256_bytes(data) != expected:
            problems.append("venv_record_hash_mismatch")
        if size and size.isdigit() and len(data) != int(size):
            problems.append("venv_record_size_mismatch")
        checked += 1
    if checked == 0:
        problems.append("venv_record_empty")
    return problems, {
        "target": str(venv_target),
        "record": str(record),
        "record_files_checked": checked,
        "anchor": anchor,
        "assurance": assurance,
    }


def _manifest_from_local_repo() -> bytes | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "llms-install.md"
        if candidate.is_file():
            return candidate.read_bytes()
    return None


def _load_manifest_bytes(
    *,
    manifest_bytes: bytes | str | None,
    offline: bool,
    opener: UrlOpen,
) -> bytes | None:
    if isinstance(manifest_bytes, str):
        return manifest_bytes.encode("utf-8")
    if manifest_bytes is not None:
        return manifest_bytes
    if offline:
        return None
    local = _manifest_from_local_repo()
    if local is not None:
        return local
    return _fetch(PUBLISHED_INSTALL_SPEC_URL, opener)


def _fetch_trusted_wheel_record(
    *,
    manifest: BootstrapManifest,
    sums: dict[str, str],
    opener: UrlOpen,
    problems: list[str],
) -> str | None:
    """Fetch the published app wheel, verify it against the trusted SHA256SUMS
    digest, then return its RECORD text as the file-verification trust anchor.

    The wheel bytes are reproduced from the publisher, hashed locally, and only
    accepted when the hash matches the (signed-manifest-pinned, live-verified)
    SHA256SUMS entry. Never transcribe a stored hash — re-derive it.
    """
    app_wheel = manifest.wheel_by_filename().get(manifest.app_wheel)
    if app_wheel is None:
        problems.append("manifest_app_wheel_missing")
        return None
    trusted_digest = sums.get(app_wheel.filename)
    if not trusted_digest or trusted_digest != app_wheel.sha256:
        problems.append("live_sha256s_entry_mismatch")
        return None
    wheel_bytes = _fetch(app_wheel.url, opener)
    if _sha256_bytes(wheel_bytes) != trusted_digest:
        problems.append("published_wheel_hash_mismatch")
        return None
    record_text = _trusted_record_text_from_wheel(wheel_bytes, manifest.package_version)
    if record_text is None:
        problems.append("published_wheel_record_missing")
        return None
    return record_text


def _verify_manifest_and_sha256s(
    *,
    state: dict[str, str],
    manifest_bytes: bytes | str | None,
    offline: bool,
    opener: UrlOpen,
) -> tuple[list[str], dict[str, str], dict[str, str], str | None]:
    """Returns ``(problems, manifest_info, sha_info, trusted_record_text)``.

    ``trusted_record_text`` is the published wheel's RECORD (the file-level
    trust anchor) and is only ever populated in online mode after the wheel is
    fetched and verified against the signed SHA256SUMS chain.
    """
    problems: list[str] = []
    manifest_payload = _load_manifest_bytes(
        manifest_bytes=manifest_bytes,
        offline=offline,
        opener=opener,
    )
    if manifest_payload is None:
        return problems, {}, {"mode": "offline", "status": "offline_skipped"}, None

    manifest = parse_bootstrap_manifest(manifest_payload)
    manifest_info = {
        "package_version": manifest.package_version,
        "sha256s_sha256": manifest.sha256s_sha256,
        "sha256s_url": manifest.sha256s_url,
    }
    if state.get("package_version") != manifest.package_version:
        problems.append("package_version_mismatch")
    if state.get("sha256s_sha256") != manifest.sha256s_sha256:
        problems.append("sha256s_pin_mismatch")
    if offline:
        return problems, manifest_info, {"mode": "offline", "status": "offline_skipped"}, None

    live = _fetch(manifest.sha256s_url, opener)
    live_digest = _sha256_bytes(live)
    sha_info = {"mode": "online", "status": "verified", "digest": live_digest}
    if live_digest != manifest.sha256s_sha256:
        problems.append("live_sha256s_hash_mismatch")
        sha_info["status"] = "mismatch"
    sums = parse_sha256s(live.decode("utf-8"))
    expected_wheels = manifest.wheel_by_filename()
    for filename, wheel in expected_wheels.items():
        if sums.get(filename) != wheel.sha256:
            problems.append("live_sha256s_entry_mismatch")
            sha_info["status"] = "mismatch"
            break
    # Anchor installed-file verification in the trusted published wheel only
    # when the SHA256SUMS chain itself verified clean.
    trusted_record_text: str | None = None
    if sha_info["status"] == "verified":
        trusted_record_text = _fetch_trusted_wheel_record(
            manifest=manifest,
            sums=sums,
            opener=opener,
            problems=problems,
        )
    return problems, manifest_info, sha_info, trusted_record_text


def verify_install(
    install_root: str | Path | None = None,
    *,
    offline: bool = False,
    manifest_bytes: bytes | str | None = None,
    urlopen: UrlOpen | None = None,
) -> VerifyInstallResult:
    root = Path(install_root) if install_root is not None else default_install_root()
    state_path = root / "install-state"
    if not state_path.is_file():
        return VerifyInstallResult(
            ok=False,
            status="refuse",
            reason="missing install-state",
            install_root=str(root),
            problems=("missing_install_state",),
        )
    state = _read_state(state_path)
    problems: list[str] = []
    for key in ("sha256s_sha256", "package_version"):
        if not state.get(key):
            problems.append(f"install_state_missing_{key}")
    sha_pin = state.get("sha256s_sha256", "")
    version = state.get("package_version", "")
    expected_target_name = f"venv-{version}-{sha_pin}" if version and sha_pin else ""
    raw_target = state.get("venv_target") or str(root / expected_target_name)
    target = Path(raw_target)
    if not target.is_absolute():
        target = root / target
    if expected_target_name and target.name != expected_target_name:
        problems.append("venv_target_pin_mismatch")
    target_in_root = _path_inside(target, root)
    if not target_in_root:
        problems.append("venv_target_outside_install_root")
    elif not target.is_dir():
        problems.append("venv_target_missing")

    live_venv = root / "venv"
    if live_venv.exists() and not _path_inside(live_venv, root):
        problems.append("live_venv_outside_install_root")
    elif (
        live_venv.exists()
        and target_in_root
        and target.exists()
        and live_venv.resolve() != target.resolve()
    ):
        problems.append("live_venv_not_pinned")
    elif not live_venv.exists():
        problems.append("live_venv_missing")

    # Resolve the trust anchor (published wheel RECORD, online) BEFORE verifying
    # installed bytes, so file verification is rooted in trusted bytes — not the
    # mutable installed RECORD.
    opener = urlopen or _stdlib_urlopen
    trusted_record_text: str | None = None
    try:
        manifest_problems, manifest_info, sha_info, trusted_record_text = (
            _verify_manifest_and_sha256s(
                state=state,
                manifest_bytes=manifest_bytes,
                offline=offline,
                opener=opener,
            )
        )
        problems.extend(manifest_problems)
    except Exception as exc:  # network/parser failures are refusals, not tracebacks
        manifest_info = {}
        sha_info = {"mode": "offline" if offline else "online", "status": "error"}
        problems.append(f"manifest_or_sha256s_unavailable:{exc.__class__.__name__}")

    venv_info: dict[str, Any] = {
        "target": str(target),
        "record_files_checked": 0,
        "anchor": "published_wheel" if trusted_record_text else "installed_record",
        "assurance": "published_release" if trusted_record_text else "local_install_state_only",
    }
    if target_in_root and target.is_dir() and version:
        record_problems, venv_info = _verify_record(
            target, version, trusted_record_text=trusted_record_text
        )
        problems.extend(record_problems)

    unique_problems = tuple(dict.fromkeys(problems))
    ok = not unique_problems
    return VerifyInstallResult(
        ok=ok,
        status="pass" if ok else "refuse",
        reason="verified" if ok else "install provenance refused",
        install_root=str(root),
        state={k: state[k] for k in sorted(state) if k in {"package_version", "sha256s_sha256", "venv_path", "venv_target"}},
        manifest=manifest_info,
        sha256s=sha_info,
        venv=venv_info,
        problems=unique_problems,
    )
