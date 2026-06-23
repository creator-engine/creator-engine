---
slug: ce207-channel-emission
date: 2026-06-23
kind: added
scope: runner / notify-feed (contact-on-need channel emission)
issue: ce-ops#207
---

**Add a first-class `webhook` notify sink so CE's delegate-first contact-on-need
reaches Discord/Slack/NanoClaw without an `exec`→`curl` shim.**

The ~95% of CE users in strangeLoop / CEO mode do not watch agents work — they want
CE to CONTACT them only when it needs input, on the channel they chose. The notify
feed (`runner.notify_feed`) already edge-detects AWAITING-OPERATOR entry/exit and
fans out to pluggable sinks; this lands `webhook` as a peer of `desktop`/`exec`.

- **`SINK_WEBHOOK` sink kind** — config `{ id, kind: webhook, url, payload }`. The
  `url` is REQUIRED and restricted to `http(s)` at config-parse (no `file://`/SSRF
  surface); `payload` defaults to `pointer` (confidential-by-default off-host).
- **`dispatch_webhook`** POSTs the SAME `shape_payload` event JSON the `exec` sink
  emits (`Content-Type: application/json`) — it **widens nothing** that already
  leaves CE. A 2xx ⇒ `ok`; a non-2xx, transport error, or down endpoint ⇒
  `ok: false` (recorded, retried) — one sick webhook never crashes the feed. The
  HTTP poster is an injectable seam (default stdlib `urllib.request`; no new
  dependency), so the unit suite never touches the network.
- **Redaction guardrail** — two secret-leak tests assert an injected secret in
  escalation prose / extra record fields never reaches the webhook wire (`pointer`
  strips all prose; even `full` emits only the `shape_payload` allow-list).

Additive within an existing v3 module — no `_versions.py` change, no new CLI group,
no wheel rebuild. The CEO-mode run-outcome + spend report-fold is a noted follow-up.
