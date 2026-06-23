"""CE v3.1-B.8 — the Operator-notify feed (PURE edge-detection fold + narrow I/O edges).

This is the Tier-1 *product delivery layer* for ce-ops#31: the v3 runtime emits a
notification when an escalation enters or exits the AWAITING-OPERATOR queue, fans it
out to pluggable sinks, and ties clearing to escalation resolution so no alert goes
stale. It is the delivery layer over an existing, well-defined surface — NOT a queue
(ce-ops#10 owns that), NOT Web-Push/mobile (#28-M2), NOT a cockpit UI change, NOT a
Ring-1/hook/governance-authority change.

**The hardest question — where does edge-detection state live?** The L2 cockpit fold
is pure by hard law and recomputes open-ness statelessly per fold; an in-memory daemon
diff loses its memory on restart (→ re-alert storm or a swallowed exit). The answer is
a durable, append-only, *notifier-private* delivery ledger
(``<root>/notifications/ledger.ndjson``) owned by this composition root. Edge detection
itself stays a **pure fold of two L1-shaped inputs**:

    fold_notify_feed(escalations, ledger_records, config) -> {pending_events, counts, sinks}

with identity ``(escalation_id, event_kind, sink_id)`` ⇒ idempotent across restarts and
re-folds by construction (no clock cursor, no consecutive-snapshot diffing). This is not
a purity violation: the ledger is *delivery* state, not *governance* state — the
notifier never touches ``escalations/``, ``scopes/``, chains, or the pane registry; it
appends only to its own ``notifications/`` subdir, exactly as chains enter
``fold_cost_meter`` as input data.

**PURE core.** :func:`fold_notify_feed`, :func:`shape_payload`, and
:func:`parse_notify_config` do NO I/O — no disk, no subprocess, no socket, no
wall-clock, no rng. The disk/subprocess touches live ONLY in the narrow edges
(:func:`load_ledger` / :func:`append_delivery` / :func:`load_config` /
:func:`dispatch_desktop` / :func:`dispatch_exec` / :func:`run_once`), mirroring the
``usage_tap`` "pure core + I/O edge" shape. It REUSES
``cockpit_readmodel.load_escalations`` — never a parallel loader — and imports neither
``textual`` nor any v1 module.

Defensive only — it alerts the Creator Engine's own Operator; never offensive.

See:
  - ``runner/cockpit_readmodel.py`` (``load_escalations`` / ``_fold_escalations``)
  - ``schemas/escalation-record.schema.yaml`` (the value-free escalation record)
  - ``docs/architecture/cockpit.md`` (the Operator-alerting section)
"""

from __future__ import annotations

import http.client
import json
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .. import seat_sentinel
from . import spend_gate
from .cockpit_readmodel import load_escalations

#: Notifier-private delivery-state subdir under the v3 local-state ``--root``. The
#: ONLY directory this module writes — never ``escalations/``/``scopes/``/chains.
NOTIFICATIONS_SUBDIR = "notifications"
#: The append-only delivery ledger (NDJSON, tolerant read).
LEDGER_NAME = "ledger.ndjson"
#: The instance-local config, beside ``scopes/`` and ``escalations/``.
CONFIG_NAME = "notify.yaml"

#: The two MVP event kinds, each carrying a class + a desktop urgency.
EVENT_ENTRY = "awaiting_operator_entry"
EVENT_EXIT = "awaiting_operator_exit"
EVENT_STATUS_REPORT = "status_report"
CLASS_RATIFY_NEEDED = "ratify-needed"
CLASS_CLEAR = "clear"
CLASS_STATUS_SUMMARY = "status-summary"
_EVENT_CLASS = {
    EVENT_ENTRY: CLASS_RATIFY_NEEDED,
    EVENT_EXIT: CLASS_CLEAR,
    EVENT_STATUS_REPORT: CLASS_STATUS_SUMMARY,
}
_CLASS_URGENCY = {
    CLASS_RATIFY_NEEDED: "critical",
    CLASS_CLEAR: "normal",
    CLASS_STATUS_SUMMARY: "normal",
}

RUNTIME_RUN_OUTCOME_RECORD_TYPE = "runtime_run_outcome"

#: Per-class verbosity dial values. ``digest`` is a RESERVED enum the validator
#: REFUSES loudly (it ships with the #28-M2/email rung) — an alerting system must
#: never silently degrade its own promise by treating it as ``off``.
DIAL_IMMEDIATE = "immediate"
DIAL_OFF = "off"
DIAL_DIGEST = "digest"
_VALID_DIALS = frozenset({DIAL_IMMEDIATE, DIAL_OFF})

SINK_DESKTOP = "desktop"
SINK_EXEC = "exec"
#: v3.5 — the first-class contact-on-need webhook sink: POSTs the already-shaped,
#: confidential-by-default notify event JSON to a configured URL, so Discord/Slack/
#: NanoClaw fan-out is first-class (no exec→curl shim). It widens NOTHING the desktop/
#: exec sinks don't already emit — it reuses :func:`shape_payload` byte-for-byte.
SINK_WEBHOOK = "webhook"
_VALID_SINK_KINDS = frozenset({SINK_DESKTOP, SINK_EXEC, SINK_WEBHOOK})

PAYLOAD_POINTER = "pointer"
PAYLOAD_FULL = "full"
_VALID_PAYLOADS = frozenset({PAYLOAD_POINTER, PAYLOAD_FULL})

#: Confidential-by-default per-kind payload default: local D-Bus desktop = full
#: (content never leaves the host); off-host exec/webhook = pointer (CE cannot see
#: where the command/URL forwards the payload).
_DEFAULT_PAYLOAD = {
    SINK_DESKTOP: PAYLOAD_FULL,
    SINK_EXEC: PAYLOAD_POINTER,
    SINK_WEBHOOK: PAYLOAD_POINTER,
}

#: The only URL schemes a webhook sink may target (no ``file://``/``gopher://`` SSRF
#: surface — a webhook is an off-host HTTP delivery edge, nothing else).
_WEBHOOK_SCHEMES = ("https://", "http://")


class NotifyConfigError(Exception):
    """Loud fail-closed refusal for a malformed ``notify.yaml`` (CLI exit 2).

    A half-applied alerting config is a missed alert wearing a green light — there is
    never a silent fallback to defaults on a malformed (present) config.
    """


@dataclass(frozen=True)
class SinkConfig:
    """One enabled delivery sink (PURE value)."""

    id: str
    kind: str
    payload: str
    argv: tuple[str, ...] | None = None
    url: str | None = None


@dataclass(frozen=True)
class NotifyConfig:
    """The validated notify configuration (PURE value)."""

    classes: Mapping[str, str]
    sinks: tuple[SinkConfig, ...]

    def dial(self, event_class: str) -> str:
        """The dial for a class; absent ⇒ ``immediate`` (the working default)."""
        return self.classes.get(event_class, DIAL_IMMEDIATE)


def default_config() -> NotifyConfig:
    """Zero-config defaults: one desktop sink (full), both classes ``immediate``."""
    return NotifyConfig(
        classes={
            CLASS_RATIFY_NEEDED: DIAL_IMMEDIATE,
            CLASS_CLEAR: DIAL_IMMEDIATE,
            CLASS_STATUS_SUMMARY: DIAL_IMMEDIATE,
        },
        sinks=(SinkConfig(id=SINK_DESKTOP, kind=SINK_DESKTOP, payload=PAYLOAD_FULL),),
    )


def parse_notify_config(doc: Any) -> NotifyConfig:
    """Validate a ``notify.yaml`` mapping into a :class:`NotifyConfig` (PURE).

    ``doc is None`` ⇒ :func:`default_config`. Any structural defect raises
    :class:`NotifyConfigError` with the concrete reasons — never a silent fallback.
    The reserved ``digest`` dial is REFUSED loudly (Fork 6).
    """
    if doc is None:
        return default_config()
    if not isinstance(doc, Mapping):
        raise NotifyConfigError("notify config must be a mapping")
    errors: list[str] = []

    kind = doc.get("kind")
    if kind is not None and kind != "notify-config":
        errors.append(f"kind must be 'notify-config' (got {kind!r})")
    version = doc.get("schema_version")
    if version is not None and str(version) != "1":
        errors.append(f"schema_version must be '1' (got {version!r})")

    classes: dict[str, str] = dict(default_config().classes)
    raw_classes = doc.get("classes")
    if raw_classes is not None:
        if not isinstance(raw_classes, Mapping):
            errors.append("classes must be a mapping of class -> dial")
        else:
            for cls, dial in raw_classes.items():
                if dial == DIAL_DIGEST:
                    errors.append(
                        f"class {cls!r} dial 'digest' is not yet shipped — "
                        "see ce-ops#31 follow-up (#28-M2/email rung); use 'immediate' or 'off'"
                    )
                elif dial not in _VALID_DIALS:
                    errors.append(
                        f"class {cls!r} dial {dial!r} invalid — must be 'immediate' or 'off'"
                    )
                else:
                    classes[str(cls)] = str(dial)

    sinks: list[SinkConfig] = []
    raw_sinks = doc.get("sinks")
    if raw_sinks is None:
        sinks = list(default_config().sinks)
    elif not isinstance(raw_sinks, list):
        errors.append("sinks must be a list")
    else:
        seen_ids: set[str] = set()
        for idx, raw in enumerate(raw_sinks):
            if not isinstance(raw, Mapping):
                errors.append(f"sink #{idx} must be a mapping")
                continue
            sink_id = raw.get("id")
            sink_kind = raw.get("kind")
            if not sink_id or not isinstance(sink_id, str):
                errors.append(f"sink #{idx} missing a string 'id'")
                continue
            if sink_id in seen_ids:
                errors.append(f"duplicate sink id {sink_id!r}")
                continue
            seen_ids.add(sink_id)
            if sink_kind not in _VALID_SINK_KINDS:
                errors.append(
                    f"sink {sink_id!r} kind {sink_kind!r} invalid — "
                    "must be 'desktop', 'exec', or 'webhook'"
                )
                continue
            payload = raw.get("payload", _DEFAULT_PAYLOAD[sink_kind])
            if payload not in _VALID_PAYLOADS:
                errors.append(
                    f"sink {sink_id!r} payload {payload!r} invalid — must be 'pointer' or 'full'"
                )
                continue
            argv: tuple[str, ...] | None = None
            url: str | None = None
            if sink_kind == SINK_EXEC:
                raw_argv = raw.get("argv")
                if not isinstance(raw_argv, list) or not raw_argv or not all(
                    isinstance(a, str) for a in raw_argv
                ):
                    errors.append(
                        f"exec sink {sink_id!r} requires a non-empty argv LIST of strings "
                        "(never a shell string — no shell, no injection surface)"
                    )
                    continue
                argv = tuple(raw_argv)
            elif sink_kind == SINK_WEBHOOK:
                raw_url = raw.get("url")
                if not raw_url or not isinstance(raw_url, str):
                    errors.append(
                        f"webhook sink {sink_id!r} requires a string 'url' "
                        "(the configured Discord/Slack/NanoClaw endpoint)"
                    )
                    continue
                if not raw_url.startswith(_WEBHOOK_SCHEMES):
                    errors.append(
                        f"webhook sink {sink_id!r} url {raw_url!r} must be an http(s) URL "
                        "(no file:// or other scheme — a webhook is an HTTP delivery edge)"
                    )
                    continue
                url = raw_url
            sinks.append(
                SinkConfig(id=sink_id, kind=sink_kind, payload=str(payload), argv=argv, url=url)
            )

    if errors:
        raise NotifyConfigError("; ".join(errors))
    return NotifyConfig(classes=classes, sinks=tuple(sinks))


def _ledger_key(record: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("escalation_id") or ""),
        str(record.get("event") or record.get("event_kind") or ""),
        str(record.get("sink_id") or ""),
    )


def _json_number(value: Any) -> float | int | None:
    if value is None:
        return None
    as_float = float(value)
    return int(as_float) if as_float.is_integer() else as_float


def _shape_report(report: Mapping[str, Any]) -> dict[str, Any]:
    spend = report.get("spend") if isinstance(report.get("spend"), Mapping) else {}
    shaped_spend = {
        "unit": spend.get("unit"),
        "amount": _json_number(spend.get("amount")),
        "record_count": int(spend.get("record_count") or 0),
        "run_count": int(spend.get("run_count") or 0),
        "spend_per_hour": _json_number(spend.get("spend_per_hour")),
    }
    return {
        "report_id": str(report.get("report_id") or ""),
        "report_key": str(report.get("report_key") or ""),
        "since": report.get("since"),
        "until": report.get("until"),
        "completed_runs": int(report.get("completed_runs") or 0),
        "outcomes": dict(sorted((report.get("outcomes") or {}).items())),
        "spend": shaped_spend,
    }


def shape_payload(
    escalation: Mapping[str, Any],
    event: str,
    payload_mode: str,
    open_count: int,
) -> dict[str, Any]:
    """Shape the per-event payload (PURE). ``pointer`` strips all confidential prose.

    ``pointer`` carries ONLY ``event``/``class``/``escalation_id``/``created_at``/
    ``source_ref``/``open_count`` — NO ``title``, ``decision_needed``,
    ``recommendation`` or hostname key (the confidential-by-default off-host shape).
    ``full`` adds the prose fields (for a local-only desktop banner).
    """
    payload: dict[str, Any] = {
        "event": event,
        "class": _EVENT_CLASS[event],
        "escalation_id": escalation.get("escalation_id"),
        "created_at": escalation.get("created_at"),
        "source_ref": escalation.get("source_ref"),
        "open_count": open_count,
    }
    if event == EVENT_STATUS_REPORT:
        report = escalation.get("report")
        if isinstance(report, Mapping):
            payload["report"] = _shape_report(report)
        return payload
    if payload_mode == PAYLOAD_FULL:
        payload["title"] = escalation.get("title")
        payload["decision_needed"] = escalation.get("decision_needed")
        payload["recommendation"] = escalation.get("recommendation")
    return payload


def fold_notify_feed(
    escalations: Iterable[Mapping[str, Any]] | None,
    ledger_records: Iterable[Mapping[str, Any]] | None,
    config: NotifyConfig,
) -> dict[str, Any]:
    """Fold escalations + the delivery ledger into pending events + counts (PURE).

    Edge-detection by construction, per ``(escalation_id, event_kind, sink_id)``:

    * an ENTRY event is pending iff the escalation is OPEN, its class dial is not
      ``off``, and the ledger holds no successful entry delivery for that sink;
    * an EXIT event is pending iff ``resolved_at`` is set, an entry WAS delivered for
      that sink, the ``clear`` dial is not ``off``, and no exit delivery is recorded.

    Resolved-before-ever-notified ⇒ NOTHING pending (no orphan "resolved" ping). A
    failed delivery (``ok: false``) does NOT block re-pending (retry next tick).
    Idempotent across re-folds: a successful delivery permanently settles its event.
    """
    records = [e for e in (escalations or []) if isinstance(e, Mapping)]
    ledger = [r for r in (ledger_records or []) if isinstance(r, Mapping)]

    delivered: set[tuple[str, str, str]] = set()
    failed_by_sink: dict[str, int] = {}
    failed_count = 0
    for record in ledger:
        if record.get("ok") is True:
            delivered.add(_ledger_key(record))
        else:
            failed_count += 1
            sink_id = str(record.get("sink_id") or "")
            failed_by_sink[sink_id] = failed_by_sink.get(sink_id, 0) + 1

    open_records = [e for e in records if not e.get("resolved_at")]
    open_count = len(open_records)
    resolved_count = len(records) - open_count

    pending_events: list[dict[str, Any]] = []
    pending_entry = 0
    pending_exit = 0

    def _sorted(recs: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        return sorted(recs, key=lambda e: str(e.get("created_at") or ""))

    for escalation in _sorted(records):
        esc_id = str(escalation.get("escalation_id") or "")
        if not esc_id:
            continue
        is_open = not escalation.get("resolved_at")
        for sink in config.sinks:
            entry_key = (esc_id, EVENT_ENTRY, sink.id)
            exit_key = (esc_id, EVENT_EXIT, sink.id)
            entry_delivered = entry_key in delivered
            # ENTRY pending: open, class on, no successful entry delivery yet.
            if (
                is_open
                and config.dial(CLASS_RATIFY_NEEDED) != DIAL_OFF
                and not entry_delivered
            ):
                pending_events.append(
                    _pending_event(escalation, EVENT_ENTRY, sink, open_count)
                )
                pending_entry += 1
            # EXIT pending: resolved, entry WAS delivered, clear on, no exit delivery.
            if (
                not is_open
                and entry_delivered
                and config.dial(CLASS_CLEAR) != DIAL_OFF
                and exit_key not in delivered
            ):
                pending_events.append(
                    _pending_event(escalation, EVENT_EXIT, sink, open_count)
                )
                pending_exit += 1

    return {
        "pending_events": pending_events,
        "counts": {
            "open_count": open_count,
            "resolved_count": resolved_count,
            "pending_entry": pending_entry,
            "pending_exit": pending_exit,
            "pending_total": len(pending_events),
            "delivered": len(delivered),
            "failed": failed_count,
            "failed_by_sink": dict(sorted(failed_by_sink.items())),
        },
        "sinks": [sink.id for sink in config.sinks],
    }


def _parse_report_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _inside_report_window(recorded_at: Any, since: str | None, until: str | None) -> bool:
    since_dt = _parse_report_ts(since)
    until_dt = _parse_report_ts(until)
    if since_dt is None and until_dt is None:
        return True
    recorded_dt = _parse_report_ts(recorded_at)
    if recorded_dt is None:
        return False
    if since_dt is not None and recorded_dt < since_dt:
        return False
    if until_dt is not None and recorded_dt > until_dt:
        return False
    return True


def _report_id(report_key: str) -> str:
    return f"status-report:{report_key}"


def _report_record(
    outcome_records: Iterable[Mapping[str, Any]] | None,
    spend_records: Iterable[Mapping[str, Any]] | None,
    *,
    report_key: str,
    since: str | None,
    until: str | None,
    fleet_id: str | None,
    unit: str,
) -> dict[str, Any]:
    outcomes_by_run: dict[str, str] = {}
    for record in outcome_records or []:
        if not isinstance(record, Mapping):
            continue
        if record.get("record_type") != RUNTIME_RUN_OUTCOME_RECORD_TYPE:
            continue
        outcome = str(record.get("outcome") or "")
        run_id = str(record.get("run_id") or "")
        if outcome not in seat_sentinel.OUTCOME_ENUM or not run_id:
            continue
        if not _inside_report_window(record.get("recorded_at"), since, until):
            continue
        outcomes_by_run[run_id] = outcome

    outcome_counts: dict[str, int] = {}
    for outcome in outcomes_by_run.values():
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    meter = spend_gate.fleet_spend_meter(
        spend_records,
        fleet_id=fleet_id,
        unit=unit,
        since=since,
        until=until,
    )
    spend = {
        "unit": meter.unit,
        "amount": meter.spend,
        "record_count": meter.record_count,
        "run_count": meter.run_count,
        "spend_per_hour": meter.spend_per_hour,
    }
    rid = _report_id(report_key)
    return {
        "escalation_id": rid,
        "created_at": until or since or report_key,
        "source_ref": None,
        "report": {
            "report_id": rid,
            "report_key": report_key,
            "since": since,
            "until": until,
            "completed_runs": len(outcomes_by_run),
            "outcomes": outcome_counts,
            "spend": spend,
        },
    }


def fold_report_notify_feed(
    outcome_records: Iterable[Mapping[str, Any]] | None,
    spend_records: Iterable[Mapping[str, Any]] | None,
    ledger_records: Iterable[Mapping[str, Any]] | None,
    config: NotifyConfig,
    *,
    report_key: str,
    since: str | None = None,
    until: str | None = None,
    fleet_id: str | None = None,
    unit: str = "$",
) -> dict[str, Any]:
    """Fold run outcomes + spend into one idempotent status-report notify event (PURE)."""
    ledger = [r for r in (ledger_records or []) if isinstance(r, Mapping)]
    delivered: set[tuple[str, str, str]] = set()
    failed_by_sink: dict[str, int] = {}
    failed_count = 0
    for record in ledger:
        if record.get("ok") is True:
            delivered.add(_ledger_key(record))
        else:
            failed_count += 1
            sink_id = str(record.get("sink_id") or "")
            failed_by_sink[sink_id] = failed_by_sink.get(sink_id, 0) + 1

    report = _report_record(
        outcome_records,
        spend_records,
        report_key=report_key,
        since=since,
        until=until,
        fleet_id=fleet_id,
        unit=unit,
    )
    pending_events: list[dict[str, Any]] = []
    if config.dial(CLASS_STATUS_SUMMARY) != DIAL_OFF:
        for sink in config.sinks:
            key = (report["escalation_id"], EVENT_STATUS_REPORT, sink.id)
            if key not in delivered:
                pending_events.append(_pending_event(report, EVENT_STATUS_REPORT, sink, 0))

    return {
        "pending_events": pending_events,
        "counts": {
            "pending_report": len(pending_events),
            "pending_total": len(pending_events),
            "delivered": len(delivered),
            "failed": failed_count,
            "failed_by_sink": dict(sorted(failed_by_sink.items())),
            "completed_runs": report["report"]["completed_runs"],
        },
        "sinks": [sink.id for sink in config.sinks],
    }


def _pending_event(
    escalation: Mapping[str, Any], event: str, sink: SinkConfig, open_count: int
) -> dict[str, Any]:
    """Build one pending-event wrapper (PURE). The wrapper carries NO confidential
    prose itself — all content lives in ``payload``, shaped per the sink's mode."""
    return {
        "escalation_id": str(escalation.get("escalation_id") or ""),
        "event": event,
        "class": _EVENT_CLASS[event],
        "sink_id": sink.id,
        "payload_mode": sink.payload,
        "payload": shape_payload(escalation, event, sink.payload, open_count),
    }


# ---------------------------------------------------------------------------
# I/O edges — ledger read/append + sink dispatch + the once composition root.
# ---------------------------------------------------------------------------

#: The injectable subprocess runner shape (mirrors ``subprocess.run``).
Runner = Callable[..., Any]

#: The injectable HTTP-poster shape ``(url, body, headers) -> status_int``. Tests
#: inject a fake poster so the unit suite never touches the network; the default
#: rides stdlib ``urllib.request`` (no third-party dependency).
WebhookPoster = Callable[[str, bytes, Mapping[str, str]], int]


def _ledger_path(root: Path) -> Path:
    return Path(root) / NOTIFICATIONS_SUBDIR / LEDGER_NAME


def load_ledger(root: Path) -> list[dict[str, Any]]:
    """Read the delivery ledger (NDJSON, tolerant). Missing file ⇒ ``[]`` (I/O edge).

    A malformed line is skipped (it can at worst cause a benign duplicate, never a
    lost alert) — the at-least-once discipline.
    """
    path = _ledger_path(root)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


def append_delivery(root: Path, record: Mapping[str, Any]) -> None:
    """Append one delivery record to the ledger (I/O edge, the only governance-free write)."""
    path = _ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def load_config(root: Path) -> NotifyConfig:
    """Read ``<root>/notify.yaml`` → :class:`NotifyConfig` (I/O edge).

    Absent ⇒ defaults. Present-but-malformed ⇒ :class:`NotifyConfigError` (LOUD).
    """
    path = Path(root) / CONFIG_NAME
    if not path.is_file():
        return default_config()
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise NotifyConfigError(f"could not read {path}: {exc}") from exc
    return parse_notify_config(doc)


def _default_runner(argv: list[str], **kwargs: Any) -> Any:
    return subprocess.run(argv, **kwargs)


def _desktop_summary_body(payload: Mapping[str, Any]) -> tuple[str, str]:
    """Compose a desktop (summary, body) from a shaped payload (PURE helper)."""
    event = payload.get("event")
    esc_id = payload.get("escalation_id")
    if event == EVENT_STATUS_REPORT:
        report = payload.get("report") if isinstance(payload.get("report"), Mapping) else {}
        spend = report.get("spend") if isinstance(report.get("spend"), Mapping) else {}
        summary = f"CE · status report {report.get('report_key') or esc_id}"
        body = (
            f"completed runs: {report.get('completed_runs') or 0}; "
            f"spend: {spend.get('amount') or 0} {spend.get('unit') or ''}".strip()
        )
        return summary, body
    elif event == EVENT_EXIT:
        head = f"CE · resolved {esc_id}"
    else:
        head = f"CE · AWAITING-OPERATOR {esc_id}"
    if "title" in payload:  # full mode
        title = payload.get("title") or ""
        summary = f"{head}: {title}".strip()
        body_lines = []
        if payload.get("decision_needed"):
            body_lines.append(f"Decision: {payload['decision_needed']}")
        if payload.get("recommendation"):
            body_lines.append(f"Recommend: {payload['recommendation']}")
        body = "\n".join(body_lines) or f"open escalations: {payload.get('open_count')}"
    else:  # pointer mode — no prose
        summary = head
        body = f"open escalations: {payload.get('open_count')}"
    return summary, body


def dispatch_desktop(
    payload: Mapping[str, Any],
    event_class: str,
    *,
    runner: Runner | None = None,
) -> bool:
    """Fire a ``notify-send`` desktop notification (I/O edge). Returns ``ok``.

    ``critical`` urgency for ``ratify-needed``, ``normal`` for ``clear``. A non-zero
    exit or a missing ``notify-send`` ⇒ ``ok=False`` (recorded, retried) — never raises.
    """
    run = runner or _default_runner
    urgency = _CLASS_URGENCY.get(event_class, "normal")
    summary, body = _desktop_summary_body(payload)
    argv = ["notify-send", "--app-name=CE", f"--urgency={urgency}", summary, body]
    try:
        completed = run(argv, capture_output=True, text=True)
    except (OSError, ValueError):
        return False
    return getattr(completed, "returncode", 1) == 0


def dispatch_exec(
    argv: Iterable[str],
    event: Mapping[str, Any],
    *,
    runner: Runner | None = None,
) -> bool:
    """Fire a generic exec-hook sink (I/O edge). Returns ``ok``.

    The user-supplied ``argv`` LIST is invoked with NO shell (no injection surface);
    the event JSON is written to the child's stdin. A non-zero exit ⇒ ``ok=False``
    (recorded, retried) — never raises, so one sick sink never crashes the loop.
    """
    run = runner or _default_runner
    body = json.dumps(event, sort_keys=True)
    try:
        completed = run(list(argv), input=body, capture_output=True, text=True)
    except (OSError, ValueError):
        return False
    return getattr(completed, "returncode", 1) == 0


def _default_poster(url: str, body: bytes, headers: Mapping[str, str]) -> int:
    """Default stdlib HTTP POST (I/O edge; no third-party dependency).

    Returns the HTTP status code. Network/transport failure raises (caught by the
    caller, recorded ``ok: false``) — a down endpoint never crashes the feed.
    """
    # Scheme is restricted to http(s) at config-parse — no file:///SSRF surface here.
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        return int(getattr(response, "status", None) or response.getcode() or 0)


def dispatch_webhook(
    url: str,
    event: Mapping[str, Any],
    *,
    poster: WebhookPoster | None = None,
) -> bool:
    """POST the (already-shaped) notify event JSON to a webhook URL (I/O edge). Returns ``ok``.

    The body is EXACTLY the same pending-event wrapper the exec sink writes to stdin —
    it widens nothing (it reuses :func:`shape_payload`'s confidential-by-default shape;
    a ``pointer`` sink carries no confidential prose at all). A non-2xx status, a
    transport error, a down endpoint, or a malformed-but-prefix-valid URL (which makes
    stdlib raise :class:`http.client.InvalidURL`/``HTTPException``) ⇒ ``ok=False``
    (recorded, retried) — never raises, so one sick webhook never crashes the loop.
    """
    post = poster or _default_poster
    body = json.dumps(event, sort_keys=True).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    try:
        status = post(url, body, headers)
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
        return False
    return 200 <= int(status) < 300


def _dispatch_event(
    event: Mapping[str, Any],
    sink: SinkConfig,
    *,
    runner: Runner | None,
    poster: WebhookPoster | None = None,
) -> bool:
    if sink.kind == SINK_DESKTOP:
        return dispatch_desktop(event["payload"], str(event.get("class")), runner=runner)
    if sink.kind == SINK_EXEC and sink.argv:
        return dispatch_exec(sink.argv, event, runner=runner)
    if sink.kind == SINK_WEBHOOK and sink.url:
        return dispatch_webhook(sink.url, event, poster=poster)
    return False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_once(
    root: Path,
    *,
    config: NotifyConfig | None = None,
    escalations: Iterable[Mapping[str, Any]] | None = None,
    runner: Runner | None = None,
    poster: WebhookPoster | None = None,
    clock: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """One fold → dispatch → record pass (the composition root; the testable unit).

    **Deliver-then-record, at-least-once** (Fork 7): a crash between dispatch and
    ledger append can duplicate a notification (benign); the inverse order could
    silently LOSE the alert this gate exists to prevent. A failed dispatch is recorded
    ``ok: false`` (so ``status`` surfaces sick sinks) and stays pending — retried next
    tick. REUSES ``cockpit_readmodel.load_escalations``; never a parallel loader.
    """
    root = Path(root)
    cfg = config if config is not None else load_config(root)
    by_id = {s.id: s for s in cfg.sinks}
    recs = list(escalations) if escalations is not None else (load_escalations(root) or [])
    ledger = load_ledger(root)
    fold = fold_notify_feed(recs, ledger, cfg)
    now = clock or _utc_now_iso

    dispatched = 0
    ok_count = 0
    failed = 0
    for event in fold["pending_events"]:
        sink = by_id.get(event["sink_id"])
        if sink is None:  # pragma: no cover - fold only emits configured sinks
            continue
        ok = _dispatch_event(event, sink, runner=runner, poster=poster)
        dispatched += 1
        ok_count += 1 if ok else 0
        failed += 0 if ok else 1
        append_delivery(
            root,
            {
                "escalation_id": event["escalation_id"],
                "event": event["event"],
                "sink_id": event["sink_id"],
                "payload_mode": event["payload_mode"],
                "ok": ok,
                "recorded_at": now(),
            },
        )

    return {
        "dispatched": dispatched,
        "ok": ok_count,
        "failed": failed,
        "counts": fold["counts"],
        "sinks": fold["sinks"],
    }


def run_report_once(
    root: Path,
    *,
    config: NotifyConfig | None = None,
    outcome_records: Iterable[Mapping[str, Any]] | None = None,
    spend_records: Iterable[Mapping[str, Any]] | None = None,
    report_key: str,
    since: str | None = None,
    until: str | None = None,
    fleet_id: str | None = None,
    unit: str = "$",
    runner: Runner | None = None,
    poster: WebhookPoster | None = None,
    clock: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """One status-report fold → dispatch → record pass.

    The live evidence readers are intentionally not invented here: callers inject
    runtime run-outcome and spend-ledger records from the existing evidence/spend
    surfaces. Delivery idempotency reuses the notifier ledger with the report id as
    the event identity, so the same period does not re-emit after a successful send.
    """
    root = Path(root)
    cfg = config if config is not None else load_config(root)
    by_id = {s.id: s for s in cfg.sinks}
    ledger = load_ledger(root)
    fold = fold_report_notify_feed(
        outcome_records,
        spend_records,
        ledger,
        cfg,
        report_key=report_key,
        since=since,
        until=until,
        fleet_id=fleet_id,
        unit=unit,
    )
    now = clock or _utc_now_iso

    dispatched = 0
    ok_count = 0
    failed = 0
    for event in fold["pending_events"]:
        sink = by_id.get(event["sink_id"])
        if sink is None:  # pragma: no cover - fold only emits configured sinks
            continue
        ok = _dispatch_event(event, sink, runner=runner, poster=poster)
        dispatched += 1
        ok_count += 1 if ok else 0
        failed += 0 if ok else 1
        append_delivery(
            root,
            {
                "escalation_id": event["escalation_id"],
                "event": event["event"],
                "sink_id": event["sink_id"],
                "payload_mode": event["payload_mode"],
                "ok": ok,
                "recorded_at": now(),
            },
        )

    return {
        "dispatched": dispatched,
        "ok": ok_count,
        "failed": failed,
        "counts": fold["counts"],
        "sinks": fold["sinks"],
    }
