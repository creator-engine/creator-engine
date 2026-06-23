# PR path manifest — ce-ops#207 · v3.5 contact-on-need: the first-class `webhook` notify sink

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce207-channel-emission
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Base:
`4956994d1731185fa8fcf76c265caea250ad5cfe` (origin/main).

## What this lands (additive, low-risk — no refactor of the existing sinks)

The delegate-first ~95% of CE users (strangeLoop + CEO mode) do NOT watch agents
work — they want CE to CONTACT them only when it needs input, on the channel they
chose (Discord/Slack/NanoClaw). The notify-feed spine (`runner.notify_feed`) already
edge-detects AWAITING-OPERATOR entry/exit and fans out to pluggable sinks
(`desktop`, `exec`) with confidential-by-default payload shaping. This PR adds a
**first-class `webhook` sink** so contact-on-need is first-class instead of needing
an `exec`→`curl` shim.

The webhook sink **widens nothing**: it POSTs the SAME `shape_payload` event JSON the
`exec` sink already writes to stdin (`pointer` by default — no confidential prose
off-host). The URL is restricted to `http(s)` at config-parse (no `file://`/SSRF), a
down/erroring endpoint is recorded `ok: false` and retried (never crashes the feed),
and the HTTP poster is an injectable seam (default stdlib `urllib.request`, no new
dependency) so the unit suite never touches the network.

**Redaction guardrail (NON-NEGOTIABLE).** Two secret-leak tests assert that an
injected secret in escalation prose / extra record fields NEVER reaches the webhook
wire — `pointer` strips all prose, and even `full` emits ONLY the `shape_payload`
allow-list (no raw escalation record can smuggle a secret-bearing field out).

`runner.notify_feed` is an existing v3 module — no `_versions.py` / version-boundary
change (the webhook sink is additive WITHIN it). No new top-level `ce` CLI group.
The dev wheelhouse carries no first-party app wheel (the wheel-built-surface gate
builds from source), so no wheel rebuild is in scope.

The CEO-mode "here's what happened" report-fold (run-outcomes + spend into periodic
status events) is a NOTED FOLLOW-UP (ce-ops#207), split out to keep this unit clean.

Per-file purpose (the closed path-set — 5 paths; carrier self-inclusive):
- **`.ce/pr-manifests/ce207-channel-emission.md`** *(A)* — this carrier (self-inclusive).
- **`docs/architecture/cockpit.md`** *(M)* — the "Operator alerting" sink contract:
  the `webhook` sink (first-class contact-on-need), its `url`/`http(s)`-only rule,
  the confidential-by-default `webhook = pointer` payload default, and a config example.
- **`validators/creator_engine_validator/runner/notify_feed.py`** *(M)* — the
  `SINK_WEBHOOK` kind + `url` field on `SinkConfig` + config parse/validation (url
  required, `http(s)`-only) + the `dispatch_webhook` I/O edge (injectable `WebhookPoster`
  seam, default stdlib `urllib.request`, 2xx⇒ok, transport-error⇒ok=false) wired into
  `_dispatch_event` / `run_once`. REUSES `shape_payload` byte-for-byte (no widening).
- **`validators/tests/unit/test_notify_feed.py`** *(M)* — webhook config-parse
  (url-required, http(s)-only, pointer default), the `dispatch_webhook` sink (fake
  poster: 2xx⇒ok, non-2xx⇒ok=false, down-endpoint⇒ok=false-never-raises), `run_once`
  webhook dispatch, and the two REDACTION secret-leak tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=22166c70bd31da21d29f6abec2bc9ede890d6ef96404f05cf61925f48dbc6402

```text
.ce/changelog/ce207-channel-emission.md
.ce/pr-manifests/ce207-channel-emission.md
docs/architecture/cockpit.md
validators/creator_engine_validator/runner/notify_feed.py
validators/tests/unit/test_notify_feed.py
```
