"""Regression coverage for the private AF_UNIX temporary-root fixture."""

from __future__ import annotations

from collections.abc import Generator
import importlib.util
import os
from pathlib import Path
import stat
from typing import get_type_hints

import pytest


def _load_conftest_module():
    path = Path(__file__).resolve().parents[1] / "conftest.py"
    spec = importlib.util.spec_from_file_location("ce_fixture_conftest", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unix_socket_tmp_path_removes_root_when_setup_validation_refuses(monkeypatch):
    conftest = _load_conftest_module()
    real_lstat = conftest.os.lstat
    roots: list[Path] = []

    def unsafe_first_lstat(path, *args, **kwargs):
        result = real_lstat(path, *args, **kwargs)
        if not roots:
            roots.append(Path(path))
            return os.stat_result((stat.S_IFLNK | 0o700, *result[1:]))
        return result

    monkeypatch.setattr(conftest.os, "lstat", unsafe_first_lstat)
    fixture = conftest.unix_socket_tmp_path.__wrapped__()

    with pytest.raises(RuntimeError, match="refusing unsafe AF_UNIX temporary directory"):
        next(fixture)

    assert roots
    assert not roots[0].exists()


def test_unix_socket_tmp_path_has_generator_annotation():
    conftest = _load_conftest_module()

    assert get_type_hints(conftest.unix_socket_tmp_path.__wrapped__)["return"] == Generator[Path, None, None]
