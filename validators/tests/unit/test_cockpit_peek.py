"""Unit tests for ce-ops#226 cockpit peek mode gating and trigger surface."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.runner import cockpit_readmodel

_HAS_TEXTUAL = importlib.util.find_spec("textual") is not None


def _pane(
    lane_id: str,
    *,
    terminal: dict,
    status: str = "active",
) -> dict:
    return {
        "kind": "pane-registry-record",
        "record_type": "pane_identity",
        "schema_version": "1",
        "controller_id": "controller-a",
        "lane_id": lane_id,
        "role": "implementer",
        "status": status,
        "terminal": terminal,
    }


def _herdr_pane(lane_id: str = "lane-herdr") -> dict:
    return _pane(
        lane_id,
        terminal={
            "kind": "herdr",
            "surface_ref": "herdr-surface-abc123",
            "pane_id": "pane-1",
            "pid": 4242,
        },
    )


def _headless_pane(lane_id: str = "lane-headless", *, with_input: bool = False) -> dict:
    terminal = {
        "kind": "headless",
        "surface_ref": "/state/headless/surface.json",
        "stream_ref": "/state/headless/stream.log",
        "pid": 31337,
    }
    if with_input:
        terminal["input_ref"] = "/state/headless/input.fifo"
    return _pane(
        lane_id,
        terminal=terminal,
    )


def test_peek_mode_gate_defaults_and_overrides() -> None:
    dev = cockpit_readmodel.fold_snapshot(
        panes=[_herdr_pane()],
        operating_mode="dev",
    )["peek"]
    assert dev["enabled"] is True
    assert dev["default_enabled"] is True
    assert dev["policy"]["never_locked_out"] is True
    assert dev["seats"][0]["can_attach"] is True
    assert dev["seats"][0]["can_send"] is True

    dev_opt_out = cockpit_readmodel.fold_snapshot(
        panes=[_herdr_pane()],
        operating_mode="dev",
        peek_opt_in=False,
    )["peek"]
    assert dev_opt_out["enabled"] is False
    assert dev_opt_out["seats"][0]["can_attach"] is False
    assert (
        dev_opt_out["seats"][0]["capabilities"]["visual_inspect"]["state"]
        == "mode_disabled"
    )

    ceo = cockpit_readmodel.fold_snapshot(
        panes=[_herdr_pane()],
        operating_mode="ceo",
    )["peek"]
    assert ceo["enabled"] is False
    assert ceo["default_enabled"] is False
    assert ceo["policy"]["can_enable"] is True

    strange_loop = cockpit_readmodel.fold_snapshot(
        panes=[_herdr_pane()],
        operating_mode="strangeLoop",
    )["peek"]
    assert strange_loop["enabled"] is False
    assert strange_loop["default_enabled"] is False

    ceo_opt_in = cockpit_readmodel.fold_snapshot(
        panes=[_herdr_pane()],
        operating_mode="CEO",
        peek_opt_in=True,
    )["peek"]
    assert ceo_opt_in["mode"] == "ceo"
    assert ceo_opt_in["enabled"] is True
    assert ceo_opt_in["seats"][0]["can_send"] is True


def test_peek_herdr_target_carries_attach_and_send_triggers() -> None:
    snapshot = cockpit_readmodel.fold_snapshot(panes=[_herdr_pane()])
    peek = snapshot["peek"]
    target = peek["seats"][0]

    assert json.loads(json.dumps(peek, sort_keys=True)) == peek
    assert target["state"] == "ok"
    assert target["terminal_kind"] == "herdr"
    assert target["pane_id"] == "pane-1"
    assert target["surface_ref"] == "herdr-surface-abc123"
    assert target["pid"] == 4242
    visual = target["capabilities"]["visual_inspect"]
    send = target["capabilities"]["send_input"]
    assert visual["available"] is True
    assert send["available"] is True
    assert visual["trigger"]["kind"] == "herdr_attach"
    assert send["trigger"]["kind"] == "herdr_send_input"
    assert visual["trigger"]["driver"] == "HerdrSession"


def test_peek_headless_target_can_visually_inspect_without_tailing_logs() -> None:
    target = cockpit_readmodel.fold_snapshot(panes=[_headless_pane()])["peek"]["seats"][0]

    assert target["terminal_kind"] == "headless"
    assert target["can_attach"] is True
    assert target["can_send"] is False
    assert target["blocked_reason"]
    assert "input seam" in target["blocked_reason"]
    visual = target["capabilities"]["visual_inspect"]
    assert visual["available"] is True
    assert visual["trigger"]["kind"] == "headless_visual_inspect"
    assert visual["trigger"]["driver"] == "HeadlessSurface"
    assert visual["trigger"]["stream_ref"] == "/state/headless/stream.log"
    assert target["capabilities"]["send_input"]["trigger"] is None
    assert target["capabilities"]["send_input"]["state"] == "unavailable"


def test_peek_headless_target_with_input_ref_can_send() -> None:
    target = cockpit_readmodel.fold_snapshot(
        panes=[_headless_pane(with_input=True)],
        operating_mode="dev",
    )["peek"]["seats"][0]

    assert target["state"] == "ok"
    assert target["can_attach"] is True
    assert target["can_send"] is True
    send = target["capabilities"]["send_input"]
    assert json.loads(json.dumps(target, sort_keys=True)) == target
    assert send["trigger"]["kind"] == "headless_send_input"
    assert send["trigger"]["driver"] == "HeadlessSurface"
    assert send["trigger"]["input_ref"] == "/state/headless/input.fifo"


def test_peek_mode_and_opt_in_resolve_from_environment(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    ledger_root = tmp_path / "ledger"
    pane_dir = ledger_root / "panes" / "controller-a"
    pane_dir.mkdir(parents=True)
    (pane_dir / "lane-herdr.yaml").write_text(
        yaml.safe_dump(_herdr_pane(), sort_keys=True),
        encoding="utf-8",
    )

    snapshot = cockpit_readmodel.snapshot_from_roots(
        state_root,
        environ={
            cockpit_readmodel.COCKPIT_MODE_ENV: "strange-loop",
            cockpit_readmodel.COCKPIT_PEEK_ENV: "yes",
            cockpit_readmodel.LEDGER_ROOT_ENV: str(ledger_root),
        },
    )

    assert snapshot["peek"]["mode"] == "strangeLoop"
    assert snapshot["peek"]["default_enabled"] is False
    assert snapshot["peek"]["enabled"] is True
    assert snapshot["peek"]["seats"][0]["can_attach"] is True


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed")
def test_l3_peek_request_routes_herdr_and_headless_by_capability() -> None:
    from creator_engine_validator import v3_cockpit

    snapshot = cockpit_readmodel.fold_snapshot(
        panes=[
            _herdr_pane(),
            _headless_pane(),
            _headless_pane("lane-headless-input", with_input=True),
        ],
    )

    attach = v3_cockpit.build_peek_request(
        snapshot,
        "lane-herdr",
        action="visual_inspect",
    )
    send = v3_cockpit.build_peek_request(
        snapshot,
        "lane-herdr",
        action="send_input",
        data="status\n",
    )
    headless_inspect = v3_cockpit.build_peek_request(
        snapshot,
        "lane-headless",
        action="visual_inspect",
    )
    headless_blocked_send = v3_cockpit.build_peek_request(
        snapshot,
        "lane-headless",
        action="send_input",
        data="status\n",
    )
    headless_send = v3_cockpit.build_peek_request(
        snapshot,
        "lane-headless-input",
        action="send_input",
        data="status\n",
    )

    assert attach["routed"] is True
    assert attach["trigger"]["kind"] == "herdr_attach"
    assert send["routed"] is True
    assert send["trigger"]["kind"] == "herdr_send_input"
    assert send["data"] == "status\n"
    assert headless_inspect["routed"] is True
    assert headless_inspect["trigger"]["kind"] == "headless_visual_inspect"
    assert headless_blocked_send["routed"] is False
    assert "input seam" in headless_blocked_send["reason"]
    assert headless_send["routed"] is True
    assert headless_send["trigger"]["kind"] == "headless_send_input"
    assert headless_send["data"] == "status\n"


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed")
def test_l3_peek_binding_uses_injected_handler() -> None:
    import asyncio

    from creator_engine_validator import v3_cockpit

    snapshot = cockpit_readmodel.fold_snapshot(
        panes=[_herdr_pane("scope-a")],
        scopes=[
            {
                "kind": "scope-record",
                "record_type": "scope",
                "schema_version": "1",
                "scope_id": "scope-a",
                "intent": "ship peek",
                "mutation_class": "code",
            }
        ],
    )
    requests: list[dict] = []

    async def go() -> dict:
        app = v3_cockpit.CockpitApp(snapshot, peek_handler=requests.append)
        async with app.run_test() as pilot:
            await pilot.press("p")
            return app._last_peek_request or {}

    request = asyncio.run(go())
    assert requests == [request]
    assert request["routed"] is True
    assert request["lane_id"] == "scope-a"
    assert request["trigger"]["kind"] == "herdr_attach"
