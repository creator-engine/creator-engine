from __future__ import annotations

import dataclasses
import os
from pathlib import Path

import pytest

from creator_engine_validator import codex_worker_config as config


def _home_fd(home: Path) -> int:
    home.mkdir(mode=0o700)
    return os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)


def test_render_is_canonical_and_bound_to_the_attested_worktree(tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    attestation = config.attest_allocated_worktree(worktree)

    template = config.render_worker_config(worktree, attestation)

    assert template.text == (
        'approval_policy = "never"\n'
        'sandbox_mode = "danger-full-access"\n'
        f'[projects."{worktree}"]\n'
        'trust_level = "trusted"\n'
    )
    assert config.parse_worker_config(template.text, attestation) == template
    with pytest.raises(config.WorkerConfigRefused):
        config.render_worker_config(worktree / ".", dataclasses.replace(attestation, path=tmp_path / "other"))


def test_materializer_writes_reloads_and_receipts_a_mode_checked_config(tmp_path):
    worktree = tmp_path / "worktree"
    home = tmp_path / "home"
    worktree.mkdir()
    template = config.render_worker_config(worktree, config.attest_allocated_worktree(worktree))
    fd = _home_fd(home)
    try:
        receipt = config.materialize_worker_config(fd, template, template.attestation)
    finally:
        os.close(fd)

    path = home / ".codex" / "config.toml"
    assert path.read_text(encoding="utf-8") == template.text
    assert path.stat().st_mode & 0o777 == 0o600
    assert (home / ".codex").stat().st_mode & 0o777 == 0o700
    assert receipt.path == path
    assert receipt.sha256 == template.sha256
    assert config.load_worker_config(path, template.attestation) == template
    assert config.revalidate_worker_config_receipt(receipt) == template
    config.release_worker_config_receipt(receipt)
    with pytest.raises(OSError):
        template.attestation.directory_pin.fstat()
    path.chmod(0o644)
    with pytest.raises(config.WorkerConfigRefused):
        config.load_worker_config(path, template.attestation)


def test_receipt_revalidation_refuses_tampered_stale_or_mismatched_config(tmp_path):
    worktree = tmp_path / "worktree"
    home = tmp_path / "home"
    worktree.mkdir()
    template = config.render_worker_config(worktree, config.attest_allocated_worktree(worktree))
    fd = _home_fd(home)
    try:
        receipt = config.materialize_worker_config(fd, template, template.attestation)
    finally:
        os.close(fd)

    with pytest.raises(config.WorkerConfigRefused):
        config.revalidate_worker_config_receipt(dataclasses.replace(receipt, sha256="0" * 64))
    (home / ".codex" / "config.toml").write_text(template.text + "# tampered\n", encoding="utf-8")
    with pytest.raises(config.WorkerConfigRefused):
        config.revalidate_worker_config_receipt(receipt)


def test_attestation_refuses_a_recreated_stale_worktree(tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    attestation = config.attest_allocated_worktree(worktree)

    worktree.rmdir()
    worktree.mkdir()

    with pytest.raises(config.WorkerConfigRefused):
        config.render_worker_config(worktree, attestation)


def test_receipt_revalidation_pins_and_refuses_a_recreated_worktree(tmp_path):
    worktree = tmp_path / "worktree"
    home = tmp_path / "home"
    worktree.mkdir()
    attestation = config.attest_allocated_worktree(worktree)
    original = attestation.directory_pin.fstat()
    template = config.render_worker_config(worktree, attestation)
    fd = _home_fd(home)
    try:
        receipt = config.materialize_worker_config(fd, template, attestation)
    finally:
        os.close(fd)

    try:
        worktree.rmdir()
        worktree.mkdir()

        pinned = attestation.directory_pin.fstat()
        assert (pinned.st_dev, pinned.st_ino) == (original.st_dev, original.st_ino)
        with pytest.raises(config.WorkerConfigRefused, match="stale or tampered allocated worktree attestation"):
            config.revalidate_worker_config_receipt(receipt)
        with pytest.raises(OSError):
            attestation.directory_pin.fstat()
    finally:
        config._close_attestation(attestation)


def test_attestation_pin_is_single_owner_and_idempotent_after_fd_number_reuse(tmp_path):
    worktree = tmp_path / "worktree"
    home = tmp_path / "home"
    unrelated = tmp_path / "unrelated"
    worktree.mkdir()
    unrelated.mkdir()
    attestation = config.attest_allocated_worktree(worktree)
    template = config.render_worker_config(worktree, attestation)
    home_fd = _home_fd(home)
    try:
        receipt = config.materialize_worker_config(home_fd, template, attestation)
    finally:
        os.close(home_fd)
    pin = receipt.attestation.directory_pin
    original_fd = pin._fd
    assert original_fd is not None

    config.release_worker_config_receipt(receipt)
    replacement_fd = os.open(unrelated, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    if replacement_fd != original_fd:
        os.dup2(replacement_fd, original_fd)
        os.close(replacement_fd)
    try:
        config._close_attestation(attestation)
        assert os.fstat(original_fd).st_ino == unrelated.stat().st_ino
        with pytest.raises(config.WorkerConfigRefused):
            config.revalidate_worker_config_receipt(receipt)
        assert os.fstat(original_fd).st_ino == unrelated.stat().st_ino
    finally:
        os.close(original_fd)


def test_materializer_refuses_symlinked_config_and_tampered_template(tmp_path):
    worktree = tmp_path / "worktree"
    home = tmp_path / "home"
    worktree.mkdir()
    template = config.render_worker_config(worktree, config.attest_allocated_worktree(worktree))
    fd = _home_fd(home)
    try:
        (home / ".codex").mkdir(mode=0o700)
        target = tmp_path / "target.toml"
        target.write_text(template.text, encoding="utf-8")
        (home / ".codex" / "config.toml").symlink_to(target)
        with pytest.raises(config.WorkerConfigRefused):
            config.materialize_worker_config(fd, template, template.attestation)
        with pytest.raises(config.WorkerConfigRefused):
            config.materialize_worker_config(
                fd, dataclasses.replace(template, text=template.text + "# tampered\n"), template.attestation
            )
    finally:
        os.close(fd)
