"""CE v3.1-B.8 — Operator-notify feed tests (pure fold + sinks + config + CLI + boundary).

Covers the §6 test plan: the edge-detection fold matrix, payload confidentiality
(key-absence, not emptiness), config validation incl. the ``digest`` loud refusal,
the desktop/exec sinks with a fake runner, the ``cev3 notify once|status`` CLI
end-to-end, the cross-host sync leg with a stubbed gh runner, and the version-boundary
+ no-v1-import packaging invariants.
"""
from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import _versions as ver
from creator_engine_validator import v3_cli
from creator_engine_validator.runner import notify_feed
from creator_engine_validator.runner.notify_feed import (
    EVENT_ENTRY,
    EVENT_EXIT,
    NotifyConfig,
    NotifyConfigError,
    SinkConfig,
    fold_notify_feed,
    parse_notify_config,
    shape_payload,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _esc(esc_id, *, resolved=False, created_at="2026-06-12T08:00:00+00:00", **extra):
    record = {
        "kind": "escalation-record",
        "record_type": "escalation",
        "schema_version": "1",
        "escalation_id": esc_id,
        "title": f"title-{esc_id}",
        "decision_needed": f"decide-{esc_id}",
        "recommendation": f"recommend-{esc_id}",
        "created_at": created_at,
    }
    record.update(extra)
    if resolved:
        record["resolved_at"] = "2026-06-12T09:00:00+00:00"
    return record


def _delivery(esc_id, event, sink_id, *, ok=True):
    return {"escalation_id": esc_id, "event": event, "sink_id": sink_id, "ok": ok}


def _desktop_cfg(*sink_ids):
    sinks = [SinkConfig(id=s, kind="desktop", payload="full") for s in (sink_ids or ("desktop",))]
    return NotifyConfig(
        classes={"ratify-needed": "immediate", "clear": "immediate"}, sinks=tuple(sinks)
    )


def _webhook_cfg(url="https://hook/x", payload="pointer"):
    return NotifyConfig(
        classes={"ratify-needed": "immediate", "clear": "immediate"},
        sinks=(SinkConfig(id="hook", kind="webhook", payload=payload, url=url),),
    )


class _Recorder:
    """A fake subprocess runner recording argv + kwargs, returning a fixed rc."""

    def __init__(self, returncode=0, raises=None):
        self.calls: list[tuple[list[str], dict]] = []
        self.returncode = returncode
        self.raises = raises

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        if self.raises is not None:
            raise self.raises
        return subprocess.CompletedProcess(list(argv), self.returncode, stdout="", stderr="")


# ---------------------------------------------------------------------------
# Pure fold — the core matrix
# ---------------------------------------------------------------------------
def test_open_no_ledger_entry_pending_per_sink():
    fold = fold_notify_feed([_esc("esc-a")], [], _desktop_cfg("desktop", "exec2"))
    events = fold["pending_events"]
    assert {(e["event"], e["sink_id"]) for e in events} == {
        (EVENT_ENTRY, "desktop"),
        (EVENT_ENTRY, "exec2"),
    }
    assert fold["counts"]["pending_entry"] == 2
    assert fold["counts"]["open_count"] == 1


def test_delivered_entry_is_idempotent_on_refold():
    cfg = _desktop_cfg("desktop")
    ledger = [_delivery("esc-a", EVENT_ENTRY, "desktop", ok=True)]
    fold = fold_notify_feed([_esc("esc-a")], ledger, cfg)
    assert fold["pending_events"] == []
    assert fold["counts"]["delivered"] == 1


def test_resolved_with_entry_delivered_yields_exit_then_settles():
    cfg = _desktop_cfg("desktop")
    ledger = [_delivery("esc-a", EVENT_ENTRY, "desktop", ok=True)]
    fold = fold_notify_feed([_esc("esc-a", resolved=True)], ledger, cfg)
    assert [(e["event"], e["sink_id"]) for e in fold["pending_events"]] == [
        (EVENT_EXIT, "desktop")
    ]
    # After the exit delivery is recorded ⇒ fully settled.
    ledger.append(_delivery("esc-a", EVENT_EXIT, "desktop", ok=True))
    settled = fold_notify_feed([_esc("esc-a", resolved=True)], ledger, cfg)
    assert settled["pending_events"] == []


def test_resolved_before_ever_notified_pings_nothing():
    # Resolved with NO entry delivery in the ledger ⇒ neither entry nor exit pending.
    fold = fold_notify_feed([_esc("esc-a", resolved=True)], [], _desktop_cfg("desktop"))
    assert fold["pending_events"] == []
    assert fold["counts"]["pending_entry"] == 0
    assert fold["counts"]["pending_exit"] == 0


def test_dial_off_filters_class():
    cfg = NotifyConfig(
        classes={"ratify-needed": "off", "clear": "immediate"},
        sinks=(SinkConfig(id="desktop", kind="desktop", payload="full"),),
    )
    fold = fold_notify_feed([_esc("esc-a")], [], cfg)
    assert fold["pending_events"] == []


def test_two_sinks_one_already_delivered_only_other_pending():
    cfg = _desktop_cfg("desktop", "exec2")
    ledger = [_delivery("esc-a", EVENT_ENTRY, "desktop", ok=True)]
    fold = fold_notify_feed([_esc("esc-a")], ledger, cfg)
    assert [(e["event"], e["sink_id"]) for e in fold["pending_events"]] == [
        (EVENT_ENTRY, "exec2")
    ]


def test_failed_delivery_stays_pending_for_retry():
    cfg = _desktop_cfg("desktop")
    ledger = [_delivery("esc-a", EVENT_ENTRY, "desktop", ok=False)]
    fold = fold_notify_feed([_esc("esc-a")], ledger, cfg)
    assert [(e["event"], e["sink_id"]) for e in fold["pending_events"]] == [
        (EVENT_ENTRY, "desktop")
    ]
    assert fold["counts"]["failed"] == 1
    assert fold["counts"]["failed_by_sink"] == {"desktop": 1}


def test_fold_is_pure_deterministic_and_json_serializable():
    cfg = _desktop_cfg("desktop", "exec2")
    escs = [_esc("esc-b", created_at="2026-06-12T08:05:00+00:00"), _esc("esc-a")]
    first = fold_notify_feed(escs, [], cfg)
    second = fold_notify_feed(escs, [], cfg)
    assert first == second
    assert json.loads(json.dumps(first, sort_keys=True)) == first
    # input-preserving (no mutation)
    assert escs[0]["escalation_id"] == "esc-b"


# ---------------------------------------------------------------------------
# Payload confidentiality — assert KEY ABSENCE, not emptiness
# ---------------------------------------------------------------------------
def test_pointer_payload_strips_all_confidential_prose():
    esc = _esc("esc-a", source_ref="https://forge/issues/7")
    payload = shape_payload(esc, EVENT_ENTRY, "pointer", open_count=3)
    for forbidden in ("title", "decision_needed", "recommendation", "host", "hostname"):
        assert forbidden not in payload, f"pointer must not carry {forbidden!r}"
    assert set(payload) == {
        "event", "class", "escalation_id", "created_at", "source_ref", "open_count"
    }
    assert payload["open_count"] == 3
    assert json.loads(json.dumps(payload)) == payload


def test_full_payload_carries_prose():
    esc = _esc("esc-a")
    payload = shape_payload(esc, EVENT_ENTRY, "full", open_count=1)
    assert payload["title"] == "title-esc-a"
    assert payload["decision_needed"] == "decide-esc-a"
    assert payload["recommendation"] == "recommend-esc-a"
    assert json.loads(json.dumps(payload)) == payload


def test_pending_event_wrapper_for_pointer_sink_has_no_prose():
    cfg = NotifyConfig(
        classes={"ratify-needed": "immediate", "clear": "immediate"},
        sinks=(SinkConfig(id="ntfy", kind="exec", payload="pointer", argv=("true",)),),
    )
    fold = fold_notify_feed([_esc("esc-a")], [], cfg)
    event = fold["pending_events"][0]
    blob = json.dumps(event)
    assert "decide-esc-a" not in blob and "title-esc-a" not in blob


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------
def test_absent_config_is_single_desktop_full():
    cfg = parse_notify_config(None)
    assert [(s.id, s.kind, s.payload) for s in cfg.sinks] == [("desktop", "desktop", "full")]
    assert cfg.dial("ratify-needed") == "immediate"
    assert cfg.dial("clear") == "immediate"


def test_digest_dial_is_loudly_refused():
    with pytest.raises(NotifyConfigError) as exc:
        parse_notify_config({"classes": {"ratify-needed": "digest"}})
    assert "digest" in str(exc.value)


@pytest.mark.parametrize(
    "doc",
    [
        {"classes": {"clear": "bogus"}},
        {"sinks": [{"id": "x", "kind": "smoke"}]},
        {"sinks": [{"id": "x", "kind": "desktop", "payload": "weird"}]},
        {"sinks": [{"id": "x", "kind": "exec"}]},  # exec needs argv
        {"sinks": [{"id": "x", "kind": "exec", "argv": "echo hi"}]},  # argv must be a list
        {"sinks": [{"id": "a", "kind": "desktop"}, {"id": "a", "kind": "desktop"}]},  # dup id
        {"kind": "not-notify-config"},
        {"schema_version": "2"},
    ],
)
def test_malformed_config_refused(doc):
    with pytest.raises(NotifyConfigError):
        parse_notify_config(doc)


def test_per_kind_payload_defaults():
    cfg = parse_notify_config(
        {
            "sinks": [
                {"id": "desktop", "kind": "desktop"},
                {"id": "ntfy", "kind": "exec", "argv": ["curl", "-d", "@-", "http://x"]},
            ]
        }
    )
    by_id = {s.id: s for s in cfg.sinks}
    assert by_id["desktop"].payload == "full"  # local transport default
    assert by_id["ntfy"].payload == "pointer"  # confidential-by-default off-host
    assert by_id["ntfy"].argv == ("curl", "-d", "@-", "http://x")


# ---------------------------------------------------------------------------
# Sinks (fake runner)
# ---------------------------------------------------------------------------
def test_desktop_argv_shape_and_urgency_mapping():
    rec = _Recorder(returncode=0)
    entry_payload = shape_payload(_esc("esc-a"), EVENT_ENTRY, "full", 1)
    assert notify_feed.dispatch_desktop(entry_payload, "ratify-needed", runner=rec) is True
    argv = rec.calls[0][0]
    assert argv[0] == "notify-send"
    assert "--app-name=CE" in argv
    assert "--urgency=critical" in argv  # ratify-needed → critical

    rec2 = _Recorder(returncode=0)
    exit_payload = shape_payload(_esc("esc-a", resolved=True), EVENT_EXIT, "full", 0)
    notify_feed.dispatch_desktop(exit_payload, "clear", runner=rec2)
    assert "--urgency=normal" in rec2.calls[0][0]  # clear → normal


def test_desktop_missing_binary_is_ok_false_not_raise():
    rec = _Recorder(raises=FileNotFoundError("notify-send not found"))
    payload = shape_payload(_esc("esc-a"), EVENT_ENTRY, "full", 1)
    assert notify_feed.dispatch_desktop(payload, "ratify-needed", runner=rec) is False


def test_exec_receives_event_json_on_stdin_no_shell():
    rec = _Recorder(returncode=0)
    cfg = NotifyConfig(
        classes={"ratify-needed": "immediate", "clear": "immediate"},
        sinks=(SinkConfig(id="ntfy", kind="exec", payload="pointer", argv=("curl", "@-")),),
    )
    event = fold_notify_feed([_esc("esc-a")], [], cfg)["pending_events"][0]
    assert notify_feed.dispatch_exec(("curl", "@-"), event, runner=rec) is True
    argv, kw = rec.calls[0]
    assert argv == ["curl", "@-"]  # argv-list, no shell string
    assert kw.get("shell") is not True
    assert json.loads(kw["input"]) == event


def test_exec_nonzero_exit_is_ok_false():
    rec = _Recorder(returncode=7)
    assert notify_feed.dispatch_exec(("false",), {"x": 1}, runner=rec) is False


# ---------------------------------------------------------------------------
# run_once composition root (ledger durability + idempotency)
# ---------------------------------------------------------------------------
def test_run_once_dispatches_then_records_and_is_idempotent(tmp_path):
    rec = _Recorder(returncode=0)
    cfg = _desktop_cfg("desktop")
    esc = _esc("esc-a")
    first = notify_feed.run_once(tmp_path, config=cfg, escalations=[esc], runner=rec)
    assert first["dispatched"] == 1 and first["ok"] == 1 and first["failed"] == 0
    ledger = notify_feed.load_ledger(tmp_path)
    assert len(ledger) == 1 and ledger[0]["ok"] is True and "recorded_at" in ledger[0]
    # second pass over the same state ⇒ no-op (ledger memory blocks re-alert)
    second = notify_feed.run_once(tmp_path, config=cfg, escalations=[esc], runner=rec)
    assert second["dispatched"] == 0


def test_run_once_fires_exit_after_resolution(tmp_path):
    rec = _Recorder(returncode=0)
    cfg = _desktop_cfg("desktop")
    notify_feed.run_once(tmp_path, config=cfg, escalations=[_esc("esc-a")], runner=rec)
    out = notify_feed.run_once(
        tmp_path, config=cfg, escalations=[_esc("esc-a", resolved=True)], runner=rec
    )
    assert out["dispatched"] == 1
    last = notify_feed.load_ledger(tmp_path)[-1]
    assert last["event"] == EVENT_EXIT


def test_run_once_failed_dispatch_stays_pending(tmp_path):
    rec = _Recorder(returncode=1)
    cfg = _desktop_cfg("desktop")
    out = notify_feed.run_once(tmp_path, config=cfg, escalations=[_esc("esc-a")], runner=rec)
    assert out["failed"] == 1
    # ok:false ledger record does NOT block ⇒ still pending next pass
    rec2 = _Recorder(returncode=0)
    again = notify_feed.run_once(tmp_path, config=cfg, escalations=[_esc("esc-a")], runner=rec2)
    assert again["dispatched"] == 1


def test_load_ledger_skips_malformed_lines(tmp_path):
    path = tmp_path / notify_feed.NOTIFICATIONS_SUBDIR / notify_feed.LEDGER_NAME
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(_delivery("esc-a", EVENT_ENTRY, "desktop")) + "\n"
        + "{ this is not json\n"
        + json.dumps(_delivery("esc-b", EVENT_ENTRY, "desktop")) + "\n",
        encoding="utf-8",
    )
    records = notify_feed.load_ledger(tmp_path)
    assert [r["escalation_id"] for r in records] == ["esc-a", "esc-b"]


# ---------------------------------------------------------------------------
# CLI (tmp root) — end-to-end via cev3 notify
# ---------------------------------------------------------------------------
def _write_config(root: Path, doc: str) -> None:
    (root / notify_feed.CONFIG_NAME).write_text(doc, encoding="utf-8")


def test_cli_once_fires_both_sinks_and_writes_ledger(tmp_path, capsys, monkeypatch):
    rec = _Recorder(returncode=0)
    monkeypatch.setattr(notify_feed.subprocess, "run", rec)
    _write_config(
        tmp_path,
        "kind: notify-config\n"
        "schema_version: \"1\"\n"
        "sinks:\n"
        "  - id: desktop\n    kind: desktop\n    payload: full\n"
        "  - id: ntfy\n    kind: exec\n    argv: [\"true\"]\n    payload: pointer\n",
    )
    v3_cli.main([
        "escalation", "open", "--id", "esc-a", "--title", "t",
        "--decision", "d", "--recommend", "r", "--root", str(tmp_path),
    ])
    capsys.readouterr()
    code = v3_cli.main(["notify", "once", "--root", str(tmp_path), "--json"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["dispatched"] == 2 and out["ok"] == 2
    assert len(rec.calls) == 2
    ledger = notify_feed.load_ledger(tmp_path)
    assert len(ledger) == 2
    # second once = no-op
    code2 = v3_cli.main(["notify", "once", "--root", str(tmp_path), "--json"])
    assert code2 == 0
    assert json.loads(capsys.readouterr().out)["dispatched"] == 0


def test_cli_once_absent_config_uses_desktop_default(tmp_path, capsys, monkeypatch):
    rec = _Recorder(returncode=0)
    monkeypatch.setattr(notify_feed.subprocess, "run", rec)
    v3_cli.main([
        "escalation", "open", "--id", "esc-a", "--title", "t",
        "--decision", "d", "--recommend", "r", "--root", str(tmp_path),
    ])
    capsys.readouterr()
    v3_cli.main(["notify", "once", "--root", str(tmp_path), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["sinks"] == ["desktop"] and out["dispatched"] == 1
    assert rec.calls[0][0][0] == "notify-send"


def test_cli_malformed_config_exits_2_with_reasons(tmp_path, capsys):
    _write_config(
        tmp_path,
        "kind: notify-config\nclasses:\n  ratify-needed: digest\n",
    )
    code = v3_cli.main(["notify", "once", "--root", str(tmp_path), "--json"])
    assert code == 2
    out = json.loads(capsys.readouterr().out)
    assert out["error"] == "notify_config_invalid"
    assert "digest" in out["detail"]


def test_cli_status_json_shape(tmp_path, capsys):
    v3_cli.main([
        "escalation", "open", "--id", "esc-a", "--title", "t",
        "--decision", "d", "--recommend", "r", "--root", str(tmp_path),
    ])
    capsys.readouterr()
    code = v3_cli.main(["notify", "status", "--root", str(tmp_path), "--json"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["action"] == "notify_status"
    assert out["counts"]["open_count"] == 1
    assert out["counts"]["pending_entry"] == 1
    assert out["sinks"] == ["desktop"]


def test_cli_once_sync_leg_mirrors_then_fires(tmp_path, capsys, monkeypatch):
    rec = _Recorder(returncode=0)
    issue = {
        "number": 5,
        "title": "Awaiting operator #5",
        "url": "https://github.com/example/repo/issues/5",
        "body": "Decision needed: choose path\nRecommendation: choose safe path\n",
        "createdAt": "2026-06-12T09:05:00Z",
        "closedAt": None,
        "state": "OPEN",
    }

    def fake_run(argv, **kw):
        if argv[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps([issue]), stderr="")
        return rec(argv, **kw)

    monkeypatch.setattr(notify_feed.subprocess, "run", fake_run)
    monkeypatch.setattr(v3_cli.subprocess, "run", fake_run)
    code = v3_cli.main([
        "notify", "once", "--root", str(tmp_path),
        "--sync-repo", "example/repo", "--json",
    ])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sync"]["ok"] is True and out["sync"]["written"] == 1
    assert out["dispatched"] == 1  # the mirrored escalation fired


def test_cli_once_sync_failure_is_tolerated(tmp_path, capsys, monkeypatch):
    def fake_run(argv, **kw):
        if argv[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="offline")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(notify_feed.subprocess, "run", fake_run)
    monkeypatch.setattr(v3_cli.subprocess, "run", fake_run)
    code = v3_cli.main([
        "notify", "once", "--root", str(tmp_path),
        "--sync-repo", "example/repo", "--json",
    ])
    assert code == 0  # forge downtime never blocks local alerting
    out = json.loads(capsys.readouterr().out)
    assert out["sync"]["ok"] is False
    assert out["dispatched"] == 0  # nothing local to fire


# ---------------------------------------------------------------------------
# Webhook sink (v3.5 — contact-on-need first-class; Discord/Slack/NanoClaw)
# ---------------------------------------------------------------------------
class _WebhookRecorder:
    """A fake HTTP poster recording (url, body, headers), returning a fixed status."""

    def __init__(self, status=204, raises=None):
        self.calls: list[tuple[str, bytes, dict]] = []
        self.status = status
        self.raises = raises

    def __call__(self, url, body, headers):
        self.calls.append((url, body, dict(headers)))
        if self.raises is not None:
            raise self.raises
        return self.status


def test_webhook_sink_parses_with_url_and_defaults_pointer():
    cfg = parse_notify_config(
        {
            "sinks": [
                {"id": "discord", "kind": "webhook", "url": "https://discord/webhooks/x"},
            ]
        }
    )
    sink = cfg.sinks[0]
    assert sink.kind == "webhook"
    assert sink.url == "https://discord/webhooks/x"
    # confidential-by-default off-host transport ⇒ pointer
    assert sink.payload == "pointer"


def test_webhook_sink_requires_a_url():
    with pytest.raises(NotifyConfigError) as exc:
        parse_notify_config({"sinks": [{"id": "x", "kind": "webhook"}]})
    assert "url" in str(exc.value)


def test_webhook_sink_rejects_non_http_url():
    with pytest.raises(NotifyConfigError) as exc:
        parse_notify_config(
            {"sinks": [{"id": "x", "kind": "webhook", "url": "file:///etc/passwd"}]}
        )
    assert "http" in str(exc.value).lower()


def test_webhook_posts_event_json_and_returns_ok_on_2xx():
    rec = _WebhookRecorder(status=204)
    event = fold_notify_feed([_esc("esc-a")], [], _webhook_cfg())["pending_events"][0]
    assert notify_feed.dispatch_webhook("https://hook/x", event, poster=rec) is True
    url, body, headers = rec.calls[0]
    assert url == "https://hook/x"
    assert json.loads(body.decode("utf-8")) == event
    assert headers.get("Content-Type") == "application/json"


def test_webhook_non_2xx_is_ok_false_not_raise():
    rec = _WebhookRecorder(status=500)
    assert notify_feed.dispatch_webhook("https://hook/x", {"x": 1}, poster=rec) is False


def test_webhook_down_endpoint_is_ok_false_never_crashes_feed():
    import urllib.error

    rec = _WebhookRecorder(raises=urllib.error.URLError("connection refused"))
    assert notify_feed.dispatch_webhook("https://hook/x", {"x": 1}, poster=rec) is False


def test_webhook_event_for_pointer_sink_carries_no_prose():
    cfg = _webhook_cfg()  # pointer by default
    event = fold_notify_feed([_esc("esc-a")], [], cfg)["pending_events"][0]
    blob = json.dumps(event)
    assert "decide-esc-a" not in blob and "title-esc-a" not in blob


def test_run_once_dispatches_webhook_sink(tmp_path):
    poster = _WebhookRecorder(status=200)
    cfg = _webhook_cfg()
    out = notify_feed.run_once(
        tmp_path, config=cfg, escalations=[_esc("esc-a")], poster=poster
    )
    assert out["dispatched"] == 1 and out["ok"] == 1
    assert len(poster.calls) == 1
    assert json.loads(poster.calls[0][1].decode("utf-8"))["escalation_id"] == "esc-a"


# ---------------------------------------------------------------------------
# REDACTION GUARDRAIL — a webhook is a live secret-leak surface (NON-NEGOTIABLE)
# ---------------------------------------------------------------------------
_SECRET = "ghp_SUPERSECRETtoken_must_never_leave_CE_0123456789"


def test_webhook_payload_never_carries_injected_secret(tmp_path):
    """An escalation whose confidential prose contains a secret value must NOT reach
    the webhook (pointer sink default): the body posted to the wire carries no secret.
    """
    poster = _WebhookRecorder(status=204)
    esc = _esc(
        "esc-a",
        title=f"deploy with token {_SECRET}",
        decision_needed=f"approve secret {_SECRET}",
        recommendation=f"use {_SECRET}",
        source_ref="https://forge/issues/7",
    )
    notify_feed.run_once(tmp_path, config=_webhook_cfg(), escalations=[esc], poster=poster)
    assert poster.calls, "webhook must have fired"
    wire = poster.calls[0][1].decode("utf-8")
    assert _SECRET not in wire, "the injected secret leaked onto the webhook wire"


def test_webhook_full_mode_still_shapes_only_known_fields(tmp_path):
    """Even a `full`-payload webhook must emit ONLY the shape_payload fields — never a
    raw escalation record (no extra keys can smuggle a secret-bearing field out)."""
    poster = _WebhookRecorder(status=204)
    esc = _esc("esc-a", secret_blob=_SECRET, internal_token=_SECRET)
    cfg = NotifyConfig(
        classes={"ratify-needed": "immediate", "clear": "immediate"},
        sinks=(SinkConfig(id="hook", kind="webhook", payload="full", url="https://hook/x"),),
    )
    notify_feed.run_once(tmp_path, config=cfg, escalations=[esc], poster=poster)
    wire = json.loads(poster.calls[0][1].decode("utf-8"))
    # the wire is a pending-event wrapper; its payload keys are the shaped allow-list
    assert "secret_blob" not in json.dumps(wire)
    assert "internal_token" not in json.dumps(wire)
    assert _SECRET not in json.dumps(wire)


# ---------------------------------------------------------------------------
# Boundary / packaging invariants
# ---------------------------------------------------------------------------
def test_notify_feed_classified_v3():
    assert ver.classify("runner.notify_feed") == ver.V3
    assert "runner.notify_feed" in ver.V3_RUNTIME


def test_notify_feed_imports_no_v1_module():
    src = Path(notify_feed.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    referenced: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                referenced.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                referenced.add(node.module.split(".")[0])
            if node.level and node.module is None:
                for alias in node.names:
                    referenced.add(alias.name.split(".")[0])
    assert referenced & ver.V1_RUNTIME == set()
