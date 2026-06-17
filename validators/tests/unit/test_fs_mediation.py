"""Unit tests for Ring-1 Section-8c filesystem mediation (``fs_mediation``).

Host-portable: the Landlock-unavailable / capability-shape / config-guard paths
are exercised here via monkeypatch (no kernel dependency). The LIVE deny/allow
enforcement proof lives in ``tests/integration/test_fs_mediation_landlock.py``,
gated on real Landlock availability.
"""

from __future__ import annotations

import pytest

from creator_engine_validator import fs_mediation as fm
from creator_engine_validator.secret_paths import CREDENTIAL_PATH_RULE_CLASSES


# --- config guard: reuse of the single source of truth ----------------------

def test_confinement_rejects_credential_shaped_read_root():
    # Reuses secret_paths.is_secret_path: you cannot allow-list a credential
    # store back into the runner's read surface.
    with pytest.raises(ValueError, match="credential-shaped read root"):
        fm.RunnerFsConfinement(workspace_read_roots=("/home/seat/.ssh",))
    with pytest.raises(ValueError, match="credential-shaped read root"):
        fm.RunnerFsConfinement(workspace_read_roots=("/srv/app/.env",))


def test_confinement_requires_at_least_one_root():
    with pytest.raises(ValueError, match="at least one workspace read root"):
        fm.RunnerFsConfinement(workspace_read_roots=())


def test_confinement_rejects_empty_root():
    with pytest.raises(ValueError, match="non-empty path"):
        fm.RunnerFsConfinement(workspace_read_roots=("  ",))


def test_resolved_roots_include_system_python_and_workspace():
    conf = fm.RunnerFsConfinement(workspace_read_roots=("/work/seat",))
    roots = conf.resolved_read_roots()
    assert "/work/seat" in roots
    for sysroot in fm.DEFAULT_SYSTEM_READ_ROOTS:
        assert sysroot in roots
    # de-duplicated, stable tuple
    assert len(roots) == len(set(roots))
    assert isinstance(roots, tuple)


def test_resolved_roots_can_drop_system_and_python():
    conf = fm.RunnerFsConfinement(
        workspace_read_roots=("/work/seat",),
        include_system_roots=False,
        include_python_roots=False,
    )
    assert conf.resolved_read_roots() == ("/work/seat",)


# --- honest fallback: fail-closed vs advisory -------------------------------

def _conf():
    return fm.RunnerFsConfinement(workspace_read_roots=("/work/seat",))


def test_unavailable_landlock_fails_closed_when_required(monkeypatch):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: None)
    with pytest.raises(fm.FsMediationUnavailable, match="fail-closed"):
        fm.build_runner_fs_capability(_conf(), require_enforcement=True)


def test_unavailable_landlock_advisory_declares_not_enforced(monkeypatch):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: None)
    cap = fm.build_runner_fs_capability(_conf(), require_enforcement=False)
    assert cap.sandbox_fs_enforced is False
    assert cap.mechanism == fm.MECHANISM_NONE
    assert cap.landlock_abi is None
    assert cap.handled_access == ()
    # The honest non-coverage declaration is always present.
    assert cap.non_coverage == fm.NON_COVERAGE
    assert cap.recognized_credential_classes == CREDENTIAL_PATH_RULE_CLASSES


def test_available_landlock_declares_enforced(monkeypatch):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: 4)
    cap = fm.build_runner_fs_capability(_conf(), require_enforcement=True)
    assert cap.sandbox_fs_enforced is True
    assert cap.mechanism == fm.MECHANISM_LANDLOCK
    assert cap.landlock_abi == 4
    assert cap.handled_access == ("read_file",)
    assert "/work/seat" in cap.allow_read_roots


def test_apply_read_confinement_unavailable_raises(monkeypatch):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: None)
    with pytest.raises(fm.FsMediationUnavailable):
        fm.apply_read_confinement(("/usr",))


def test_run_confined_unavailable_required_fails_closed(monkeypatch):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: None)
    with pytest.raises(fm.FsMediationUnavailable):
        fm.run_confined(["/bin/true"], _conf(), require_enforcement=True)


def test_run_confined_composes_caller_preexec_under_enforcement(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(fm, "landlock_abi_version", lambda: 8)
    monkeypatch.setattr(fm, "landlock_preexec", lambda confinement: lambda: calls.append("landlock"))

    def fake_run(argv, **kwargs):
        preexec = kwargs.get("preexec_fn")
        assert callable(preexec)
        preexec()
        return fm.subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(fm.subprocess, "run", fake_run)

    fm.run_confined(
        ["/bin/true"],
        _conf(),
        require_enforcement=True,
        preexec_fn=lambda: calls.append("caller"),
    )

    assert calls == ["landlock", "caller"]


# --- capability serialization ------------------------------------------------

def test_capability_to_dict_round_trip(monkeypatch):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: 8)
    cap = fm.build_runner_fs_capability(_conf(), require_enforcement=True)
    d = cap.to_dict()
    assert d["sandbox_fs_enforced"] is True
    assert d["landlock_abi"] == 8
    assert d["mechanism"] == fm.MECHANISM_LANDLOCK
    assert d["handled_access"] == ["read_file"]
    assert isinstance(d["allow_read_roots"], list)
    assert isinstance(d["non_coverage"], list) and d["non_coverage"]
    assert isinstance(d["recognized_credential_classes"], list)


def test_abi_probe_returns_int_or_none():
    abi = fm.landlock_abi_version()
    assert abi is None or (isinstance(abi, int) and abi >= 1)
    assert fm.fs_mediation_available() is (abi is not None)
