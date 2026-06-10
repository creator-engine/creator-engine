"""Unit tests for v3.5-B.6 — ``ce cockpit --serve`` + Control-Room Violet polish.

The gate's green-def (cluster §B.6), in testable form:

* the serve-config builder is PURE + correct: it binds loopback only; the
  token is required + unguessable; a bad/absent ``Host`` header is rejected
  (anti-DNS-rebinding); ``0.0.0.0`` (or any non-loopback bind) is refused
  with a loud error;
* the theme constants equal the live site hex values VERBATIM
  (``docs/index.html`` — read, never edited; the site lane is separate);
* the semantic mapping (refusal -> gate, verified -> spark,
  estimated -> amber) is asserted via L2 snapshot styling hints — the
  palette NAMES travel in the snapshot; the view only maps name -> hex;
* serve is ADDITIVE: the TUI path and the ``--json`` path never import
  ``textual_serve``/``aiohttp``;
* the governed middleware enforces token + Host on a live in-process
  aiohttp app (``skipif``-absent guard for minimal local envs only — CI
  installs the ``cockpit-serve`` extra and RUNS this).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

VALIDATORS_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = VALIDATORS_DIR.parent
SITE_FILE = REPO_ROOT / "docs" / "index.html"

_HAS_TEXTUAL = importlib.util.find_spec("textual") is not None
_HAS_SERVE = importlib.util.find_spec("textual_serve") is not None

#: The live site tokens, verbatim (docs/index.html:35-41) — the test pins the
#: exact hexes so any drift in EITHER direction (theme or site) is loud.
SITE_HEX = {
    "ink-900": "#08090F",
    "ink-850": "#0B0D15",
    "ink-800": "#0F1220",
    "fg": "#E9EAF5",
    "violet": "#A06BFF",
    "spark": "#9BE34F",
    "gate": "#FF4D6D",
    "amber": "#F4B740",
}

GOOD_TOKEN = "t" * 43  # token_urlsafe(32)-shaped


def _run(code: str, *, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(VALIDATORS_DIR), **(extra_env or {})}
    return subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )


def _config(**overrides):
    from creator_engine_validator import v3_cockpit

    kwargs = {"command": "demo-command", "token": GOOD_TOKEN, "port": 8000}
    kwargs.update(overrides)
    return v3_cockpit.build_serve_config(**kwargs)


# --- the PURE serve-config builder -------------------------------------------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_build_serve_config_defaults_to_loopback():
    config = _config()
    assert config.host == "127.0.0.1"
    assert config.port == 8000
    assert config.token == GOOD_TOKEN
    assert "127.0.0.1:8000" in config.allowed_hosts
    assert "localhost:8000" in config.allowed_hosts


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_build_serve_config_refuses_non_loopback_loudly():
    with pytest.raises(ValueError, match="(?i)refus.*loopback|loopback.*refus"):
        _config(host="0.0.0.0")
    with pytest.raises(ValueError, match="(?i)loopback"):
        _config(host="192.168.1.7")
    with pytest.raises(ValueError, match="(?i)loopback"):
        _config(host="example.com")


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_build_serve_config_requires_a_strong_token():
    with pytest.raises(ValueError, match="(?i)token"):
        _config(token="")
    with pytest.raises(ValueError, match="(?i)token"):
        _config(token="short")


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_generated_token_is_unguessable_shaped():
    from creator_engine_validator import v3_cockpit

    one = v3_cockpit.generate_token()
    two = v3_cockpit.generate_token()
    assert one != two
    assert len(one) >= 32
    assert all(c.isalnum() or c in "-_" for c in one), "token must be URL-safe"


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_tokened_url_carries_the_token():
    from creator_engine_validator import v3_cockpit

    config = _config()
    assert v3_cockpit.tokened_url(config) == f"http://127.0.0.1:8000/?token={GOOD_TOKEN}"


# --- the PURE request decision (token gate + Host validation) ----------------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_evaluate_request_token_then_cookie_model():
    from creator_engine_validator import v3_cockpit

    config = _config()
    ok_host = "127.0.0.1:8000"

    via_query = v3_cockpit.evaluate_request(
        config, host_header=ok_host, query_token=GOOD_TOKEN, cookie_token=None
    )
    assert via_query.allowed and via_query.set_cookie

    via_cookie = v3_cockpit.evaluate_request(
        config, host_header=ok_host, query_token=None, cookie_token=GOOD_TOKEN
    )
    assert via_cookie.allowed and not via_cookie.set_cookie

    bare = v3_cockpit.evaluate_request(
        config, host_header=ok_host, query_token=None, cookie_token=None
    )
    assert not bare.allowed
    assert "token" in bare.reason

    wrong = v3_cockpit.evaluate_request(
        config, host_header=ok_host, query_token="WRONG", cookie_token="WRONG"
    )
    assert not wrong.allowed


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_evaluate_request_rejects_bad_or_absent_host():
    from creator_engine_validator import v3_cockpit

    config = _config()

    absent = v3_cockpit.evaluate_request(
        config, host_header=None, query_token=GOOD_TOKEN, cookie_token=None
    )
    assert not absent.allowed
    assert "host" in absent.reason.lower()

    # a forged Host with a VALID token is still rejected (anti-DNS-rebinding)
    forged = v3_cockpit.evaluate_request(
        config, host_header="evil.example:8000", query_token=GOOD_TOKEN, cookie_token=None
    )
    assert not forged.allowed
    assert "host" in forged.reason.lower()


# --- Control-Room Violet: verbatim site hexes + the semantic mapping ---------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_theme_tokens_equal_the_site_hexes_verbatim():
    from creator_engine_validator import v3_cockpit

    assert v3_cockpit.THEME == SITE_HEX


@pytest.mark.skipif(not SITE_FILE.exists(), reason="site file absent (wheel-installed env)")
def test_site_hexes_are_still_live_on_the_site():
    """Cross-check the pinned hexes against docs/index.html (READ-only)."""
    site = SITE_FILE.read_text(encoding="utf-8")
    for name, hex_value in SITE_HEX.items():
        assert f"--{name}:{hex_value}" in site, (
            f"site token --{name} drifted from the pinned {hex_value}"
        )


def test_semantic_palette_names_travel_in_the_l2_snapshot():
    """The styling HINTS live in L2 (palette names), never computed in widgets."""
    from creator_engine_validator.runner import cockpit_demo_seed, cockpit_readmodel

    assert cockpit_readmodel._CLASS_COLORS == {
        "allowed": "spark",
        "denied": "gate",
        "escalate": "amber",
    }
    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())
    colors = {
        group["color"]
        for detail in snapshot["seat_detail"].values()
        for group in (detail.get("stream") or {}).get("groups", [])
        if group.get("kind") == "actions"
    }
    assert colors, "the demo stream must carry styling hints"
    assert colors <= {"spark", "gate", "amber"}


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_view_maps_palette_names_to_site_hexes():
    from creator_engine_validator import v3_cockpit

    assert v3_cockpit.SEMANTIC_HEX == {
        "gate": SITE_HEX["gate"],
        "spark": SITE_HEX["spark"],
        "amber": SITE_HEX["amber"],
        "violet": SITE_HEX["violet"],
    }
    # honesty badges: ESTIMATED renders amber (pending/soft semantics)
    assert v3_cockpit.BADGE_HEX["ESTIMATED"] == SITE_HEX["amber"]
    # evidence badges: verified chains spark-lime, tampered chains gate-red
    assert v3_cockpit.EVIDENCE_BADGE_HEX["clean"] == SITE_HEX["spark"]
    assert v3_cockpit.EVIDENCE_BADGE_HEX["findings"] == SITE_HEX["gate"]


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_refusal_feed_renders_gate_red_and_app_css_is_violet():
    from creator_engine_validator import v3_cockpit

    chain_entry = {
        "source": "refusal-chain",
        "recorded_at": "2026-06-10T00:00:00Z",
        "run_id": "lane-x",
        "tool": "Bash",
        "target": "git push",
        "deny_kind": "explicit",
        "deciding_clause": "G2.007.2",
    }
    rendered = "\n".join(v3_cockpit._refusal_lines(chain_entry))
    assert SITE_HEX["gate"] in rendered, "refusal-chain entries must render gate-red"

    css = v3_cockpit.CockpitApp.CSS
    for token in ("ink-900", "fg", "violet", "amber"):
        assert SITE_HEX[token] in css, f"app CSS must carry the {token} site hex"


# --- serve is ADDITIVE (the TUI/json paths never touch the serve deps) -------

def test_json_path_never_imports_serve_deps(tmp_path):
    code = (
        "import sys\n"
        "from creator_engine_validator import v3_cli\n"
        f"rc = v3_cli.main(['cockpit', '--json', '--root', {str(tmp_path)!r}])\n"
        "assert rc == 0, rc\n"
        "assert 'textual_serve' not in sys.modules\n"
        "assert 'aiohttp' not in sys.modules\n"
    )
    proc = _run(code, extra_env={"CE_DEMO": "1"})
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["source"]["demo"] is True


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_tui_module_import_never_imports_serve_deps():
    code = (
        "import sys\n"
        "from creator_engine_validator import v3_cockpit\n"
        "assert 'textual_serve' not in sys.modules, 'serve must be additive'\n"
        "assert 'aiohttp' not in sys.modules, 'serve must be additive'\n"
    )
    proc = _run(code)
    assert proc.returncode == 0, proc.stderr


# --- the CLI surface: --serve flags + the loud non-loopback refusal ----------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_cli_serve_refuses_non_loopback_bind_loudly(tmp_path):
    code = (
        "from creator_engine_validator import v3_cli\n"
        "rc = v3_cli.main(['cockpit', '--serve', '--host', '0.0.0.0', "
        f"'--root', {str(tmp_path)!r}])\n"
        "raise SystemExit(rc)\n"
    )
    proc = _run(code, extra_env={"CE_DEMO": "1"})
    assert proc.returncode == 2, (proc.returncode, proc.stderr)
    assert "loopback" in proc.stderr.lower()
    assert "0.0.0.0" in proc.stderr


# --- the governed middleware on a live in-process aiohttp app ----------------

@pytest.mark.skipif(not _HAS_SERVE, reason="cockpit-serve extra not installed (minimal local env)")
def test_governed_middleware_enforces_token_and_host_live():
    import asyncio

    from aiohttp.test_utils import TestClient, TestServer

    from creator_engine_validator import v3_cockpit

    config = _config()
    server = v3_cockpit._build_server(config)
    ok_host = {"Host": "127.0.0.1:8000"}

    async def go():
        app = await server._make_app()
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            # denials FIRST — once a valid token lands, the client's jar holds
            # the session cookie (which is exactly the designed behavior).
            bare = await client.get("/", headers=ok_host)
            forged_host = await client.get(
                "/", params={"token": GOOD_TOKEN}, headers={"Host": "evil.example:8000"}
            )
            wrong_token = await client.get("/", params={"token": "WRONG"}, headers=ok_host)
            via_cookie = await client.get(
                "/",
                headers={**ok_host, "Cookie": f"{v3_cockpit.TOKEN_COOKIE}={GOOD_TOKEN}"},
            )
            with_token = await client.get("/", params={"token": GOOD_TOKEN}, headers=ok_host)
            set_cookie = with_token.headers.get("Set-Cookie", "")
            return (
                with_token.status,
                set_cookie,
                bare.status,
                forged_host.status,
                wrong_token.status,
                via_cookie.status,
            )
        finally:
            await client.close()

    ok, set_cookie, bare, forged, wrong, cookie_ok = asyncio.run(go())
    assert ok == 200
    assert v3_cockpit.TOKEN_COOKIE in set_cookie, "first tokened request must set the cookie"
    assert bare == 403
    assert forged == 403, "a forged Host with a valid token must still be rejected"
    assert wrong == 403
    assert cookie_ok == 200, "the cookie session must carry subsequent requests"
