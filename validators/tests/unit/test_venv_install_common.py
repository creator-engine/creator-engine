from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator import venv_install_common


def test_promote_verifies_the_live_symlink_before_writing_state(monkeypatch, tmp_path: Path):
    root = tmp_path / "install-root"
    root.mkdir()
    target = root / "venv-new"
    target.mkdir()
    seen: list[Path] = []
    states: list[str] = []

    monkeypatch.setattr(venv_install_common, "verify_live_cev3", lambda live: seen.append(live))

    venv_install_common.promote_and_write_state(root, target, lambda: states.append("written"))

    assert seen == [root / "venv"]
    assert (root / "venv").is_symlink()
    assert (root / "venv").resolve() == target
    assert states == ["written"]


def test_promote_live_symlink_refusal_rolls_back_before_state_write(monkeypatch, tmp_path: Path):
    root = tmp_path / "install-root"
    root.mkdir()
    previous = root / "venv-old"
    previous.mkdir()
    live = root / "venv"
    live.symlink_to(previous.name)
    target = root / "venv-new"
    target.mkdir()
    states: list[str] = []

    def refuse(_live: Path) -> None:
        raise RuntimeError("live_cev3_reverify_failed: promoted venv cev3 --help failed")

    monkeypatch.setattr(venv_install_common, "verify_live_cev3", refuse)

    with pytest.raises(RuntimeError, match="live_cev3_reverify_failed"):
        venv_install_common.promote_and_write_state(root, target, lambda: states.append("written"))

    assert live.is_symlink()
    assert live.resolve() == previous
    assert states == []
