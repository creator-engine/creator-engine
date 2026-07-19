"""Closed, value-free Codex configuration for one attested worker HOME.

This is deliberately a small filesystem boundary.  It accepts an attested,
canonical allocated worktree and produces the sole CDX-D-6 configuration that
worker spawning may use; it neither consumes ambient configuration nor accepts
caller supplied Codex arguments.
"""
from __future__ import annotations

import hashlib
import os
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path


class WorkerConfigRefused(ValueError):
    """The managed worker configuration boundary failed closed."""


@dataclass
class _AttestedDirectoryPin:
    """A single-owner directory descriptor retained through worker launch."""

    _fd: int | None

    def fstat(self) -> os.stat_result:
        if self._fd is None:
            raise OSError("allocated worktree attestation has been released")
        return os.fstat(self._fd)

    def proc_path(self) -> Path:
        if self._fd is None:
            raise OSError("allocated worktree attestation has been released")
        return Path(f"/proc/self/fd/{self._fd}")

    def close(self) -> None:
        fd, self._fd = self._fd, None
        if fd is None:
            return
        try:
            os.close(fd)
        except OSError:
            pass


@dataclass(frozen=True)
class AllocatedWorktreeAttestation:
    path: Path
    path_sha256: str
    owner_uid: int
    device: int
    inode: int
    directory_pin: _AttestedDirectoryPin


@dataclass(frozen=True)
class WorkerConfigTemplate:
    text: str
    sha256: str
    attestation: AllocatedWorktreeAttestation


@dataclass(frozen=True)
class WorkerConfigReceipt:
    path: Path
    sha256: str
    attestation: AllocatedWorktreeAttestation
    device: int
    inode: int


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_directory(path: Path | str, *, label: str) -> Path:
    supplied_path = os.fspath(path)
    if (
        not os.path.isabs(supplied_path)
        or supplied_path.startswith("//")
        or supplied_path != os.path.normpath(supplied_path)
    ):
        raise WorkerConfigRefused(f"{label} must be an absolute, lexically canonical directory")
    candidate = Path(supplied_path)
    try:
        component_path = Path(candidate.anchor)
        details = os.lstat(component_path)
        for component in candidate.parts[1:]:
            component_path /= component
            details = os.lstat(component_path)
            if stat.S_ISLNK(details.st_mode):
                raise WorkerConfigRefused(f"{label} must not contain symlink components")
    except OSError as exc:
        raise WorkerConfigRefused(f"cannot stat {label}") from exc
    if not stat.S_ISDIR(details.st_mode):
        raise WorkerConfigRefused(f"{label} must be canonical and a directory")
    if details.st_uid != os.geteuid():
        raise WorkerConfigRefused(f"{label} has unexpected owner")
    return candidate


def attest_allocated_worktree(worktree: Path | str) -> AllocatedWorktreeAttestation:
    """Create the narrow, value-free trust token for a canonical worktree."""
    path = _canonical_directory(worktree, label="allocated worktree")
    directory_fd: int | None = None
    try:
        directory_fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        details = os.fstat(directory_fd)
        return AllocatedWorktreeAttestation(
            path=path,
            path_sha256=_sha256(str(path)),
            owner_uid=os.geteuid(),
            device=details.st_dev,
            inode=details.st_ino,
            directory_pin=_AttestedDirectoryPin(directory_fd),
        )
    except OSError as exc:
        if directory_fd is not None:
            os.close(directory_fd)
        raise WorkerConfigRefused("cannot open allocated worktree without following links") from exc


def _close_attestation(attestation: object) -> None:
    if not isinstance(attestation, AllocatedWorktreeAttestation):
        return
    attestation.directory_pin.close()


def _validate_attestation(attestation: AllocatedWorktreeAttestation) -> Path:
    if not isinstance(attestation, AllocatedWorktreeAttestation):
        raise WorkerConfigRefused("missing allocated worktree attestation")
    path = _canonical_directory(attestation.path, label="attested worktree")
    try:
        details = path.stat(follow_symlinks=False)
        pinned_details = attestation.directory_pin.fstat()
    except OSError as exc:
        raise WorkerConfigRefused("cannot revalidate allocated worktree attestation") from exc
    if (
        attestation.owner_uid != os.geteuid()
        or attestation.path_sha256 != _sha256(str(path))
        or attestation.device != details.st_dev
        or attestation.inode != details.st_ino
        or (pinned_details.st_dev, pinned_details.st_ino) != (attestation.device, attestation.inode)
        or (details.st_dev, details.st_ino) != (pinned_details.st_dev, pinned_details.st_ino)
    ):
        raise WorkerConfigRefused("stale or tampered allocated worktree attestation")
    return path


def _expected_text(path: Path) -> str:
    return (
        'approval_policy = "never"\n'
        'sandbox_mode = "danger-full-access"\n'
        f'[projects."{path}"]\n'
        'trust_level = "trusted"\n'
    )


def render_worker_config(
    worktree: Path | str, attestation: AllocatedWorktreeAttestation
) -> WorkerConfigTemplate:
    """Render exactly one trusted project entry from verified worktree trust."""
    try:
        attested_path = _validate_attestation(attestation)
        supplied_path = _canonical_directory(worktree, label="worktree")
        if supplied_path != attested_path:
            raise WorkerConfigRefused("worktree does not match allocated worktree attestation")
        text = _expected_text(attested_path)
        return WorkerConfigTemplate(text=text, sha256=_sha256(text), attestation=attestation)
    except WorkerConfigRefused:
        _close_attestation(attestation)
        raise


def parse_worker_config(text: str, attestation: AllocatedWorktreeAttestation) -> WorkerConfigTemplate:
    """Parse and require the sole canonical managed config representation."""
    try:
        path = _validate_attestation(attestation)
        parsed = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        _close_attestation(attestation)
        raise WorkerConfigRefused("managed config is not valid TOML") from exc
    except WorkerConfigRefused:
        _close_attestation(attestation)
        raise
    expected = _expected_text(path)
    if text != expected or parsed != {
        "approval_policy": "never",
        "sandbox_mode": "danger-full-access",
        "projects": {str(path): {"trust_level": "trusted"}},
    }:
        _close_attestation(attestation)
        raise WorkerConfigRefused("managed config is noncanonical or tampered")
    return WorkerConfigTemplate(text=text, sha256=_sha256(text), attestation=attestation)


def _check_owned_mode(details: os.stat_result, *, mode: int, label: str, regular: bool = False) -> None:
    kind_ok = stat.S_ISREG(details.st_mode) if regular else stat.S_ISDIR(details.st_mode)
    if not kind_ok or details.st_uid != os.geteuid() or stat.S_IMODE(details.st_mode) != mode:
        raise WorkerConfigRefused(f"{label} has unexpected type, owner, or mode")


def _open_dir_at(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    return os.open(name, flags, dir_fd=parent_fd)


def _ensure_codex_dir(home_fd: int) -> int:
    try:
        home_details = os.fstat(home_fd)
        if not stat.S_ISDIR(home_details.st_mode):
            raise WorkerConfigRefused("worker HOME descriptor is not a directory")
        try:
            os.mkdir(".codex", 0o700, dir_fd=home_fd)
        except FileExistsError:
            pass
        codex_fd = _open_dir_at(home_fd, ".codex")
        _check_owned_mode(os.fstat(codex_fd), mode=0o700, label=".codex")
        return codex_fd
    except OSError as exc:
        raise WorkerConfigRefused("cannot create or open managed .codex directory") from exc


def _existing_config_is_safe(codex_fd: int) -> None:
    try:
        details = os.stat("config.toml", dir_fd=codex_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise WorkerConfigRefused("cannot inspect existing managed config") from exc
    _check_owned_mode(details, mode=0o600, label="existing managed config", regular=True)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short write while materializing managed config")
        view = view[written:]


def load_worker_config(path: Path | str, attestation: AllocatedWorktreeAttestation) -> WorkerConfigTemplate:
    """No-follow reload plus exact parser check for the pre-launch receipt."""
    target = Path(path)
    try:
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise WorkerConfigRefused("cannot open managed config without following links") from exc
    try:
        _check_owned_mode(os.fstat(fd), mode=0o600, label="managed config", regular=True)
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as fh:
            text = fh.read()
    except (OSError, UnicodeError) as exc:
        raise WorkerConfigRefused("cannot reload managed config") from exc
    finally:
        os.close(fd)
    return parse_worker_config(text, attestation)


def revalidate_worker_config_receipt(receipt: WorkerConfigReceipt) -> WorkerConfigTemplate:
    """Require the materialized config to still be the exact received file."""
    if not isinstance(receipt, WorkerConfigReceipt):
        raise WorkerConfigRefused("missing managed config receipt")
    attestation = receipt.attestation
    try:
        details = os.stat(receipt.path, follow_symlinks=False)
        _check_owned_mode(details, mode=0o600, label="managed config receipt", regular=True)
        if details.st_dev != receipt.device or details.st_ino != receipt.inode:
            raise WorkerConfigRefused("stale or tampered managed config receipt")
        loaded = load_worker_config(receipt.path, attestation)
        if loaded.sha256 != receipt.sha256 or loaded.attestation != attestation:
            raise WorkerConfigRefused("managed config receipt does not match config")
        return loaded
    except WorkerConfigRefused:
        _close_attestation(attestation)
        raise
    except OSError as exc:
        _close_attestation(attestation)
        raise WorkerConfigRefused("cannot stat managed config receipt") from exc


def pinned_worktree_launch_path(receipt: WorkerConfigReceipt) -> Path:
    """Revalidate and expose the still-live directory pin to the launch primitive."""
    if not isinstance(receipt, WorkerConfigReceipt):
        raise WorkerConfigRefused("missing managed config receipt")
    try:
        _validate_attestation(receipt.attestation)
        return receipt.attestation.directory_pin.proc_path()
    except WorkerConfigRefused:
        _close_attestation(receipt.attestation)
        raise
    except OSError as exc:
        _close_attestation(receipt.attestation)
        raise WorkerConfigRefused("cannot retain allocated worktree identity for launch") from exc


def release_worker_config_receipt(receipt: WorkerConfigReceipt | None) -> None:
    """Release the receipt's single-owner directory pin exactly once."""
    if isinstance(receipt, WorkerConfigReceipt):
        _close_attestation(receipt.attestation)


def materialize_worker_config(
    home_fd: int, template: WorkerConfigTemplate, attestation: AllocatedWorktreeAttestation
) -> WorkerConfigReceipt:
    """Atomically install, fsync, and reload a descriptor-relative config file."""
    if not isinstance(template, WorkerConfigTemplate) or template.attestation != attestation:
        _close_attestation(attestation)
        raise WorkerConfigRefused("template is not bound to the supplied worktree attestation")
    codex_fd: int | None = None
    temp_name = f".config.toml.tmp.{os.getpid()}.{os.urandom(16).hex()}"
    try:
        parsed = parse_worker_config(template.text, attestation)
        if template.sha256 != parsed.sha256:
            raise WorkerConfigRefused("managed config template digest mismatch")
        codex_fd = _ensure_codex_dir(home_fd)
        _existing_config_is_safe(codex_fd)
        temp_fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=codex_fd)
        try:
            _write_all(temp_fd, template.text.encode("utf-8"))
            os.fchmod(temp_fd, 0o600)
            os.fsync(temp_fd)
        finally:
            os.close(temp_fd)
        os.replace(temp_name, "config.toml", src_dir_fd=codex_fd, dst_dir_fd=codex_fd)
        os.fsync(codex_fd)
        config_path = Path(os.readlink(f"/proc/self/fd/{codex_fd}")) / "config.toml"
        loaded = load_worker_config(config_path, attestation)
        if loaded != parsed:
            raise WorkerConfigRefused("managed config reload mismatch")
        details = os.stat(config_path, follow_symlinks=False)
        _check_owned_mode(details, mode=0o600, label="materialized managed config", regular=True)
        return WorkerConfigReceipt(
            path=config_path,
            sha256=loaded.sha256,
            attestation=attestation,
            device=details.st_dev,
            inode=details.st_ino,
        )
    except (OSError, WorkerConfigRefused) as exc:
        _close_attestation(attestation)
        raise WorkerConfigRefused("cannot atomically materialize managed config") from exc
    finally:
        if codex_fd is not None:
            try:
                os.unlink(temp_name, dir_fd=codex_fd)
            except FileNotFoundError:
                pass
            finally:
                os.close(codex_fd)
