from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from creator_engine_validator import _versions
from creator_engine_validator import state_root_probe as probe


def _private_root(tmp_path: Path) -> Path:
    tmp_path.chmod(0o700)
    root = tmp_path / "state"
    root.mkdir(mode=0o700)
    return root


def _refusal(root: Path, *, expected_uid: int | None = None) -> probe.StateRootProbeRefused:
    with pytest.raises(probe.StateRootProbeRefused) as caught:
        probe.probe_state_root(
            root,
            expected_uid=os.geteuid() if expected_uid is None else expected_uid,
            mode="writable-boot",
        )
    return caught.value


def test_clean_empty_root_proves_nonce_and_is_repeatable(tmp_path: Path):
    root = _private_root(tmp_path)

    first = probe.probe_state_root(root, expected_uid=os.geteuid(), mode="writable-boot")
    second = probe.probe_state_root(root, expected_uid=os.geteuid(), mode="writable-boot")

    assert first.status == second.status == "pass"
    assert first.writable_durability == second.writable_durability == "proven"
    assert first.error_codes == second.error_codes == ()
    assert first.same_filesystem is True
    assert first.nonce_created is True
    assert first.nonce_fsynced is True
    assert first.nonce_verified is True
    assert first.nonce_unlinked is True
    assert first.directory_fsynced_after_unlink is True
    assert list(root.iterdir()) == []


def test_missing_root_is_not_created(tmp_path: Path):
    tmp_path.chmod(0o700)
    root = tmp_path / "missing"

    refusal = _refusal(root)

    assert refusal.result.error_codes == ("SRP-MISSING",)
    assert not root.exists()


@pytest.mark.parametrize("kind", ["symlink", "file"])
def test_root_must_be_real_directory(tmp_path: Path, kind: str):
    tmp_path.chmod(0o700)
    root = tmp_path / "state"
    if kind == "symlink":
        target = tmp_path / "external"
        target.mkdir(mode=0o700)
        root.symlink_to(target, target_is_directory=True)
    else:
        root.write_text("not a directory", encoding="utf-8")
        root.chmod(0o600)

    refusal = _refusal(root)

    assert "SRP-NOT-REAL-DIR" in refusal.result.error_codes


def test_intermediate_symlink_is_refused_without_following(tmp_path: Path):
    tmp_path.chmod(0o700)
    external = tmp_path / "external"
    external.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(external, target_is_directory=True)

    refusal = _refusal(link / "state")

    assert "SRP-NOT-REAL-DIR" in refusal.result.error_codes
    assert list(external.iterdir()) == []


@pytest.mark.parametrize("mode", [0o750, 0o770, 0o701, 0o1700])
def test_directory_modes_are_private_exactly(tmp_path: Path, mode: int):
    root = _private_root(tmp_path)
    child = root / "child"
    child.mkdir(mode=0o700)
    child.chmod(mode)

    refusal = _refusal(root)

    assert "SRP-MODE" in refusal.result.error_codes
    assert "SRP-FOREIGN-WRITER" in refusal.result.error_codes


@pytest.mark.parametrize("mode,accepted", [(0o600, True), (0o700, True), (0o644, False), (0o660, False), (0o601, False), (0o4600, False)])
def test_regular_file_modes(tmp_path: Path, mode: int, accepted: bool):
    root = _private_root(tmp_path)
    state_file = root / "record"
    state_file.write_bytes(b"state")
    state_file.chmod(mode)

    if accepted:
        result = probe.probe_state_root(root, expected_uid=os.geteuid(), mode="writable-boot")
        assert result.status == "pass"
    else:
        assert "SRP-MODE" in _refusal(root).result.error_codes


def test_symlink_and_fifo_descendants_are_refused(tmp_path: Path):
    root = _private_root(tmp_path)
    target = tmp_path / "outside"
    target.write_text("sentinel", encoding="utf-8")
    (root / "link").symlink_to(target)
    os.mkfifo(root / "fifo", mode=0o600)

    refusal = _refusal(root)

    assert "SRP-ENTRY-TYPE" in refusal.result.error_codes
    assert target.read_text(encoding="utf-8") == "sentinel"


def test_preexisting_nonce_residue_is_not_deleted(tmp_path: Path):
    root = _private_root(tmp_path)
    residue = root / f"{probe.NONCE_PREFIX}crash"
    residue.write_bytes(b"sentinel-secret")
    residue.chmod(0o600)

    refusal = _refusal(root)

    assert "SRP-NONCE-RESIDUE" in refusal.result.error_codes
    assert residue.read_bytes() == b"sentinel-secret"
    assert "sentinel-secret" not in json.dumps(refusal.result.to_dict(), sort_keys=True)
    assert residue.name not in str(refusal)


def test_read_only_diagnostic_never_mutates_and_never_proves_writable(tmp_path: Path):
    root = _private_root(tmp_path)
    before = tuple(root.iterdir())

    result = probe.probe_state_root(
        root,
        expected_uid=os.geteuid(),
        mode="read-only-diagnostic",
    )

    assert result.status == "not-proven"
    assert result.writable_durability == "not-proven"
    assert result.nonce_created is False
    assert tuple(root.iterdir()) == before


def test_euid_mismatch_refuses_writable_but_diagnostic_remains_not_proven(tmp_path: Path):
    root = _private_root(tmp_path)
    other_uid = os.geteuid() + 1

    refusal = _refusal(root, expected_uid=other_uid)
    diagnostic = probe.probe_state_root(
        root,
        expected_uid=other_uid,
        mode="read-only-diagnostic",
    )

    assert "SRP-OWNER" in refusal.result.error_codes
    assert diagnostic.status == "refused"
    assert diagnostic.writable_durability == "not-proven"
    assert diagnostic.nonce_created is False


def test_unsafe_ancestor_refuses_but_sticky_tmp_rule_is_accepted(tmp_path: Path):
    unsafe = tmp_path / "unsafe"
    unsafe.mkdir(mode=0o700)
    unsafe.chmod(0o777)
    root = unsafe / "state"
    root.mkdir(mode=0o700)
    assert "SRP-ANCESTOR-UNSAFE" in _refusal(root).result.error_codes

    sticky = tmp_path / "sticky"
    sticky.mkdir(mode=0o700)
    sticky.chmod(0o1777)
    sticky_root = sticky / "state"
    sticky_root.mkdir(mode=0o700)
    result = probe.probe_state_root(
        sticky_root,
        expected_uid=os.geteuid(),
        mode="writable-boot",
    )
    assert result.status == "pass"


def test_acl_xattr_is_refused(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    real_listxattr = probe.os.listxattr

    def fake_listxattr(target):
        attrs = list(real_listxattr(target))
        try:
            stat_result = os.fstat(target)
        except TypeError:
            return attrs
        if stat_result.st_ino == root.stat().st_ino:
            attrs.append("system.posix_acl_access")
        return attrs

    monkeypatch.setattr(probe.os, "listxattr", fake_listxattr)

    refusal = _refusal(root)

    assert "SRP-ACL" in refusal.result.error_codes


def test_foreign_root_owner_is_refused_before_nonce(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    root_inode = root.stat().st_ino
    real_fstat = probe.os.fstat

    def foreign_root_fstat(fd: int):
        metadata = real_fstat(fd)
        if metadata.st_ino != root_inode:
            return metadata
        values = list(metadata)
        values[4] = os.geteuid() + 1
        return os.stat_result(values)

    monkeypatch.setattr(probe.os, "fstat", foreign_root_fstat)

    refusal = _refusal(root)

    assert "SRP-OWNER" in refusal.result.error_codes
    assert refusal.result.nonce_created is False


def test_violation_digest_is_stable_and_value_free(tmp_path: Path):
    root = _private_root(tmp_path)
    bad = root / "sensitive-relative-name"
    bad.write_bytes(b"sensitive-content")
    bad.chmod(0o644)

    first = probe.probe_state_root(root, expected_uid=os.geteuid(), mode="read-only-diagnostic")
    second = probe.probe_state_root(root, expected_uid=os.geteuid(), mode="read-only-diagnostic")
    serialized = json.dumps(first.to_dict(), sort_keys=True)

    assert first.violation_digest == second.violation_digest
    assert first.violation_digest is not None
    assert "sensitive-relative-name" not in serialized
    assert "sensitive-content" not in serialized


def test_nonce_short_writes_and_reads_are_completed(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    real_write = probe.os.write
    real_read = probe.os.read

    monkeypatch.setattr(probe.os, "write", lambda fd, data: real_write(fd, data[:3]))
    monkeypatch.setattr(probe.os, "read", lambda fd, size: real_read(fd, min(size, 2)))

    result = probe.probe_state_root(root, expected_uid=os.geteuid(), mode="writable-boot")

    assert result.status == "pass"
    assert result.nonce_verified is True
    assert list(root.iterdir()) == []


def test_nonce_device_mismatch_refuses_and_attempts_cleanup(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    real_open = probe.os.open
    real_fstat = probe.os.fstat
    nonce_fds: set[int] = set()

    def record_open(path, flags, mode=0o777, *, dir_fd=None):
        fd = real_open(path, flags, mode, dir_fd=dir_fd)
        if isinstance(path, str) and path.startswith(probe.NONCE_PREFIX):
            nonce_fds.add(fd)
        return fd

    def other_device(fd: int):
        metadata = real_fstat(fd)
        if fd not in nonce_fds:
            return metadata
        values = list(metadata)
        values[2] = metadata.st_dev + 1
        return os.stat_result(values)

    monkeypatch.setattr(probe.os, "open", record_open)
    monkeypatch.setattr(probe.os, "fstat", other_device)
    monkeypatch.setattr(probe, "_require_primitives", lambda: None)

    refusal = _refusal(root)

    assert "SRP-RACE" in refusal.result.error_codes
    assert refusal.result.nonce_unlinked is True
    assert list(root.iterdir()) == []


def test_nonce_fsync_failure_refuses_and_cleans_up(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    real_fsync = probe.os.fsync
    calls = 0

    def fail_first_fsync(fd: int):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected fsync failure")
        return real_fsync(fd)

    monkeypatch.setattr(probe.os, "fsync", fail_first_fsync)

    refusal = _refusal(root)

    assert "SRP-NONCE-FSYNC" in refusal.result.error_codes
    assert refusal.result.nonce_unlinked is True
    assert list(root.iterdir()) == []


def test_nonce_create_write_and_read_failures_use_stable_codes(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    real_open = probe.os.open

    def fail_create(path, flags, mode=0o777, *, dir_fd=None):
        if isinstance(path, str) and path.startswith(probe.NONCE_PREFIX):
            raise OSError("injected create failure")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(probe.os, "open", fail_create)
    monkeypatch.setattr(probe, "_require_primitives", lambda: None)
    assert _refusal(root).result.error_codes == ("SRP-NONCE-CREATE",)
    assert list(root.iterdir()) == []

    monkeypatch.setattr(probe.os, "open", real_open)
    monkeypatch.setattr(
        probe.os,
        "write",
        lambda _fd, _data: (_ for _ in ()).throw(OSError("injected write failure")),
    )
    assert "SRP-NONCE-WRITE" in _refusal(root).result.error_codes
    assert list(root.iterdir()) == []

    monkeypatch.undo()
    monkeypatch.setattr(
        probe.os,
        "read",
        lambda _fd, _size: (_ for _ in ()).throw(OSError("injected read failure")),
    )
    assert "SRP-NONCE-READ" in _refusal(root).result.error_codes
    assert list(root.iterdir()) == []


def test_final_directory_fsync_failure_never_passes(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    real_fsync = probe.os.fsync
    calls = 0

    def fail_final_fsync(fd: int):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("injected final directory fsync failure")
        return real_fsync(fd)

    monkeypatch.setattr(probe.os, "fsync", fail_final_fsync)

    refusal = _refusal(root)

    assert "SRP-NONCE-FSYNC" in refusal.result.error_codes
    assert refusal.result.nonce_unlinked is True
    assert refusal.result.directory_fsynced_after_unlink is False
    assert list(root.iterdir()) == []


def test_unsupported_directory_fsync_refuses_without_downgrade(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    real_fsync = probe.os.fsync
    calls = 0

    def unsupported_directory_fsync(fd: int):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError(getattr(os, "EINVAL", 22), "directory fsync unsupported")
        return real_fsync(fd)

    monkeypatch.setattr(probe.os, "fsync", unsupported_directory_fsync)

    refusal = _refusal(root)

    assert "SRP-UNSUPPORTED" in refusal.result.error_codes
    assert refusal.result.nonce_unlinked is True
    assert list(root.iterdir()) == []


def test_nonce_unlink_failure_never_passes(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    real_unlink = probe.os.unlink

    def fail_nonce_unlink(path, *, dir_fd=None):
        if isinstance(path, str) and path.startswith(probe.NONCE_PREFIX):
            raise OSError("injected unlink failure")
        return real_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(probe.os, "unlink", fail_nonce_unlink)
    monkeypatch.setattr(probe, "_require_primitives", lambda: None)

    refusal = _refusal(root)

    assert "SRP-NONCE-UNLINK" in refusal.result.error_codes
    assert refusal.result.nonce_unlinked is False
    residue = next(root.iterdir())
    real_unlink(residue)


def test_final_lexical_rewalk_detects_component_swap(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    real_stat = probe.os.stat
    final_stats = 0

    def swapped_on_rewalk(path, *args, **kwargs):
        nonlocal final_stats
        metadata = real_stat(path, *args, **kwargs)
        if path != root.name or kwargs.get("dir_fd") is None:
            return metadata
        final_stats += 1
        if final_stats < 2:
            return metadata
        values = list(metadata)
        values[1] = metadata.st_ino + 1
        return os.stat_result(values)

    monkeypatch.setattr(probe.os, "stat", swapped_on_rewalk)
    monkeypatch.setattr(probe, "_require_primitives", lambda: None)

    refusal = _refusal(root)

    assert "SRP-PATH-REVALIDATE" in refusal.result.error_codes
    assert list(root.iterdir()) == []


def test_unsupported_descriptor_primitive_refuses_without_fallback(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    monkeypatch.delattr(probe.os, "O_NOFOLLOW")

    refusal = _refusal(root)

    assert refusal.result.error_codes == ("SRP-UNSUPPORTED",)
    assert list(root.iterdir()) == []


def test_nonce_corruption_refuses_value_free_and_cleans_up(monkeypatch, tmp_path: Path):
    root = _private_root(tmp_path)
    real_read = probe.os.read

    def corrupt_read(fd: int, size: int) -> bytes:
        data = real_read(fd, size)
        if data and size > 1:
            return bytes((data[0] ^ 0xFF,)) + data[1:]
        return data

    monkeypatch.setattr(probe.os, "read", corrupt_read)

    refusal = _refusal(root)

    assert "SRP-NONCE-MISMATCH" in refusal.result.error_codes
    assert list(root.iterdir()) == []
    serialized = json.dumps(refusal.result.to_dict(), sort_keys=True)
    assert probe.NONCE_PREFIX not in serialized


def test_packaged_module_inventory_includes_probe():
    assert "state_root_probe" in _versions.EXPLICIT_SHARED_MODULES
    assert _versions.classify("state_root_probe") == _versions.SHARED
