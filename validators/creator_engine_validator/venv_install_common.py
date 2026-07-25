"""Shared, fail-closed helpers for promoted CE installer virtual environments."""
from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path


class LiveSymlinkVerifyFailed(RuntimeError):
    """The promoted live ``cev3`` link could not execute successfully."""


class InstallLock:
    """Exclusive installer lock whose refusal type belongs to the caller."""

    def __init__(self, root: Path, refusal: Callable[[str], Exception]):
        self.path = root / "install.lock"
        self._refusal = refusal

    def __enter__(self) -> "InstallLock":
        try:
            self.path.mkdir()
        except FileExistsError as exc:
            raise self._refusal(f"install_lock_held: lock already exists at {self.path}") from exc
        (self.path / "pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            (self.path / "pid").unlink()
        except FileNotFoundError:
            pass
        try:
            self.path.rmdir()
        except OSError:
            pass


def venv_target_ok(target: Path) -> bool:
    ce = target / "bin" / "ce"
    cev3 = target / "bin" / "cev3"
    return ce.is_file() and os.access(ce, os.X_OK) and cev3.is_file() and os.access(cev3, os.X_OK)


def build_venv_target(
    target: Path,
    *,
    python_executable: str,
    populate_wheelhouse: Callable[[Path], None],
    requirement: str,
) -> None:
    """Build and target-verify a venv from a caller-provided wheelhouse."""
    wheelhouse = target.parent / f".{target.name}.wheelhouse.{os.getpid()}"
    if target.exists():
        shutil.rmtree(target)
    if wheelhouse.exists():
        shutil.rmtree(wheelhouse)
    try:
        wheelhouse.mkdir(parents=True)
        populate_wheelhouse(wheelhouse)
        subprocess.run([python_executable, "-m", "venv", str(target)], check=True)
        subprocess.run(
            [
                str(target / "bin" / "python"),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(wheelhouse),
                requirement,
            ],
            check=True,
        )
        subprocess.run(
            [str(target / "bin" / "ce"), "--help"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        subprocess.run(
            [str(target / "bin" / "cev3"), "--help"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(wheelhouse, ignore_errors=True)


def verify_live_cev3(live: Path) -> None:
    """Verify the promoted link itself, rather than its resolved target."""
    try:
        subprocess.run(
            [str(live / "bin" / "cev3"), "--help"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise LiveSymlinkVerifyFailed(
            "live_cev3_reverify_failed: promoted venv cev3 --help failed"
        ) from exc


def write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def promote_and_write_state(root: Path, target: Path, write_state: Callable[[], None]) -> None:
    """Promote, live-link verify, and write state with the established rollback semantics."""
    live = root / "venv"
    link_tmp = root / f"venv.link.{os.getpid()}"
    backup = root / f"venv.previous.{os.getpid()}"
    if link_tmp.exists() or link_tmp.is_symlink():
        link_tmp.unlink()
    if backup.exists() or backup.is_symlink():
        if backup.is_dir() and not backup.is_symlink():
            shutil.rmtree(backup)
        else:
            backup.unlink()
    previous_symlink_target = os.readlink(live) if live.is_symlink() else None
    link_tmp.symlink_to(target.name)
    moved_dir = False
    promoted = False
    try:
        if live.exists() and not live.is_symlink():
            os.replace(live, backup)
            moved_dir = True
        os.replace(link_tmp, live)
        promoted = True
        verify_live_cev3(live)
        write_state()
    except Exception:
        if link_tmp.exists() or link_tmp.is_symlink():
            link_tmp.unlink()
        if promoted:
            if live.exists() or live.is_symlink():
                if live.is_dir() and not live.is_symlink():
                    shutil.rmtree(live)
                else:
                    live.unlink()
            if previous_symlink_target is not None:
                live.symlink_to(previous_symlink_target)
        if moved_dir and backup.exists() and not live.exists():
            os.replace(backup, live)
        raise
    if backup.exists():
        if backup.is_dir() and not backup.is_symlink():
            shutil.rmtree(backup)
        else:
            backup.unlink()
