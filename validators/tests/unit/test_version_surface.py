"""ce-ops#25 — the derived ``<semver>+<short-sha>`` CE version surface.

Covers the shared version API (live-git-wins, the per-process cache, the baked
fallback, fail-closed), the build-file generator (render + refusals), and every
product surface (``ce``/``cev3 --version``, ``ce doctor``, the Cockpit JSON +
L3 header, the governed session) exposing ONE token for one checkout/install.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from creator_engine_validator import ce_version as top_level_ce_version
from creator_engine_validator import version as ver
from creator_engine_validator import doctor_runtime, v3_session
from creator_engine_validator.runner import cockpit_demo_seed, cockpit_readmodel

_HAS_TEXTUAL = importlib.util.find_spec("textual") is not None


@pytest.fixture(autouse=True)
def _clear_version_cache():
    """Each test resolves the token fresh (the resolver is process-cached)."""
    ver._resolve_short_sha.cache_clear()
    yield
    ver._resolve_short_sha.cache_clear()


def _init_git_repo(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(path), "init", "-q"], check=True, env={**_os_environ(), **env})
    (path / "f.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True, env={**_os_environ(), **env})
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True,
                   env={**_os_environ(), **env})
    out = subprocess.run(["git", "-C", str(path), "rev-parse", "--short=8", "HEAD"],
                         check=True, capture_output=True, text=True)
    return out.stdout.strip()


def _os_environ() -> dict:
    import os

    return dict(os.environ)


# --- shared version API -----------------------------------------------------


def test_ce_version_token_shape():
    token = ver.ce_version()
    assert token == f"{ver.SEMVER}+{ver._resolve_short_sha(None)}"
    semver, _, short = token.partition("+")
    assert semver == ver.SEMVER == ver.__version__
    assert len(short) == 8 and all(c in "0123456789abcdef" for c in short)


def test_top_level_export_matches():
    assert top_level_ce_version() == ver.ce_version()


def test_live_git_wins_in_source_mode(tmp_path: Path):
    short = _init_git_repo(tmp_path / "repo")
    token = ver.ce_version(tmp_path / "repo")
    assert token == f"{ver.SEMVER}+{short}"
    # the live checkout's HEAD is NOT the baked sha — proves git won, not fallback
    assert short != ver._baked_short()


def test_cache_does_not_rerun_git_within_one_process(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    calls = {"n": 0}
    real = ver._git_short_head

    def _counting(cwd):
        calls["n"] += 1
        return real(cwd)

    monkeypatch.setattr(ver, "_git_short_head", _counting)
    key = str((repo).resolve())
    first = ver.ce_version(repo)
    after_first = calls["n"]
    second = ver.ce_version(repo)
    assert first == second
    assert calls["n"] == after_first, "git re-ran on a cache hit (must resolve once per root)"


def test_baked_sha_wins_when_git_unavailable(monkeypatch):
    monkeypatch.setattr(ver, "_git_short_head", lambda cwd: None)
    token = ver.ce_version()
    assert token == f"{ver.SEMVER}+{ver._baked_short()}"


def test_fail_closed_when_no_git_and_no_baked(monkeypatch):
    monkeypatch.setattr(ver, "_git_short_head", lambda cwd: None)
    monkeypatch.setattr(ver, "_BAKED_BUILD_GIT_SHA", None)
    with pytest.raises(ver.VersionDerivationError):
        ver.ce_version()


# --- the build-file generator ----------------------------------------------


def test_render_build_file_is_constants_only():
    body = ver.render_build_file("0.2.0", "a" * 40)
    assert 'SEMVER = "0.2.0"' in body
    assert f'BUILD_GIT_SHA = "{"a" * 40}"' in body
    # the generated module is import-clean (no executable logic / imports)
    ns: dict = {}
    exec(compile(body, "<gen>", "exec"), ns)
    assert ns["SEMVER"] == "0.2.0" and ns["BUILD_GIT_SHA"] == "a" * 40


def test_generator_writes_to_out_path(tmp_path: Path):
    repo = tmp_path / "repo"
    short = _init_git_repo(repo)
    (repo / "validators").mkdir()
    (repo / "validators" / "pyproject.toml").write_text(
        '[project]\nname = "creator-engine-validator"\nversion = "0.2.0"\n', encoding="utf-8"
    )
    out = tmp_path / "out_version.py"
    written = ver.write_build_file(repo, allow_dirty=True, out_path=out)
    assert written == out
    text = out.read_text(encoding="utf-8")
    assert 'SEMVER = "0.2.0"' in text
    # baked full sha starts with the live short sha of the repo
    assert short in text


def test_generator_refuses_missing_semver(tmp_path: Path):
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    with pytest.raises(ver.VersionDerivationError):
        ver.write_build_file(repo, allow_dirty=True, out_path=tmp_path / "x.py")


def test_generator_refuses_dirty_tree(tmp_path: Path):
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "validators").mkdir()
    (repo / "validators" / "pyproject.toml").write_text(
        '[project]\nname = "creator-engine-validator"\nversion = "0.2.0"\n', encoding="utf-8"
    )
    # the new untracked pyproject makes the tree dirty
    with pytest.raises(ver.VersionDerivationError):
        ver.write_build_file(repo, out_path=tmp_path / "x.py")


# --- surfaces: one token everywhere ----------------------------------------


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_cli(module: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=REPO_ROOT,
        env={**_os_environ(), "PYTHONPATH": str(REPO_ROOT / "validators")},
        capture_output=True,
        text=True,
    )


def test_ce_version_flag_prints_exactly_one_line():
    proc = _run_cli("creator_engine_validator.ce_cli", "--version")
    assert proc.returncode == 0
    assert proc.stdout.count("\n") == 1
    token = proc.stdout.strip()
    semver, _, short = token.partition("+")
    assert semver == ver.SEMVER and len(short) == 8


def test_cev3_version_flag_prints_token_before_session():
    proc = _run_cli("creator_engine_validator.v3_cli", "--version")
    assert proc.returncode == 0
    token = proc.stdout.strip()
    # exactly the token, NOT the default session banner
    assert proc.stdout.count("\n") == 1
    assert token.startswith(ver.SEMVER + "+")
    assert "governed session" not in proc.stdout


def test_doctor_json_and_human_carry_version():
    report = doctor_runtime.run_doctor(REPO_ROOT, check_packaging=False)
    assert report.payload["ce_version"] == ver.ce_version(REPO_ROOT)
    human = doctor_runtime.render_human(report)
    assert f"version={report.payload['ce_version']}" in human.splitlines()[0]


def test_cockpit_demo_and_live_expose_same_token():
    token = ver.ce_version()
    demo = cockpit_readmodel.fold_snapshot(demo=True, ce_version=token, **cockpit_demo_seed.seed())
    live = cockpit_readmodel.snapshot_from_roots(REPO_ROOT / ".ce" / "state", ce_version=token)
    assert demo["source"]["ce_version"] == token
    assert live["source"]["ce_version"] == token
    # demo still carries its watermark; the additive field did not bump the shape
    assert demo["source"]["watermark"]
    assert demo["snapshot_version"] == cockpit_readmodel.SNAPSHOT_VERSION == 2
    assert live["snapshot_version"] == 2


def test_cockpit_snapshot_is_json_round_trippable():
    token = ver.ce_version()
    snap = cockpit_readmodel.fold_snapshot(demo=True, ce_version=token, **cockpit_demo_seed.seed())
    assert json.loads(json.dumps(snap))["source"]["ce_version"] == token


def test_session_banner_and_json_carry_token():
    token = ver.ce_version()
    banner = v3_session.render_banner(version=token)
    assert token in banner
    lines = v3_session.render_session({}, version=token)
    assert any(token in line for line in lines)
    # absent a token the banner is unchanged (no fabricated identity)
    assert "Creator Engine ·" in v3_session.render_banner()


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_cockpit_l3_header_renders_token_with_app_title_prefix():
    from creator_engine_validator import v3_cockpit

    token = ver.ce_version()
    snap = cockpit_readmodel.fold_snapshot(demo=True, ce_version=token, **cockpit_demo_seed.seed())
    app = v3_cockpit.CockpitApp(snap)
    assert app.title == f"{v3_cockpit.APP_TITLE} · {token}"
    # fallback: no token -> APP_TITLE preserved
    snap_no_ver = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())
    assert v3_cockpit.CockpitApp(snap_no_ver).title == v3_cockpit.APP_TITLE
