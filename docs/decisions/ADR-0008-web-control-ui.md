---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0008
title: "Web control UI — the web L3 over the cockpit read-model"
status: accepted
date: 2026-06-20
decision_makers: ["ce-ui-architect"]
consulted: []
informed: []
review_by: 2026-12-20
mutation_class: governance
ratification:
  ratified_by: chmod735
  ratified_at: "2026-06-20"
  ratification_prompt_sha: "654ccb5b91c1e7ee1dfce2fa923f88e12c2ed4a18365c6d6a617d53d5b1e54bb"
  quorum: n1_solo
  # N=1 native mode: this privileged, accepted governance record was ratified by
  # the sole resolved human (chmod735), with a distinct agent author
  # (ce-ui-architect) — honest solo quorum. Anchor = sha256 of the
  # Operator-ratified brief ce-briefs/web-control-ui-adr.md.
evidence_refs:
  - kind: doc
    ref: "ce-briefs/web-control-ui-adr.md — Operator-ratified brief (Operator, 2026-06-20)"
    tag: ratified-brief
  - kind: issue
    ref: "ce-ops#28 — mobile / web-L3 home ticket (names cockpit-serve + the tailnet perimeter)"
    tag: web-l3-home
  - kind: issue
    ref: "ce-ops#45 — journey-cockpit five requirements (the panel set, source of the CEO face)"
    tag: journey-five
  - kind: doc
    ref: "validators/creator_engine_validator/runner/cockpit_readmodel.py — fold_snapshot() pure L2 read-model (snapshot_version 2)"
    tag: l2-readmodel
  - kind: doc
    ref: "validators/creator_engine_validator/v3_cockpit.py — `ce cockpit --serve` security spine (loopback bind, token-then-cookie, Host-header gate, aiohttp middleware) + Control-Room Violet THEME"
    tag: cockpit-serve
  - kind: doc
    ref: "validators/creator_engine_validator/v3_cli.py — `cockpit --json` parity surface + `_cmd_escalation_open/_resolve` write seams"
    tag: json-parity
  - kind: doc
    ref: "openclaw/openclaw (MIT) ui/ — Vite+Lit+TS SPA, single-port WS-RPC gateway, hand-rolled SW, Tailscale Serve identity (docs.openclaw.ai/web/control-ui)"
    tag: openclaw-ref
  - kind: doc
    ref: "docs/architecture/stage-vocabulary.md — Frame→Shape→Build→Review→Ship canon (no third vocabulary)"
    tag: stage-canon
  - kind: adr
    ref: "docs/decisions/ADR-0007-egress-gateway-publish-broker.md — the forge-egress gateway twin (this UI gateway must never become a push path)"
    tag: egress-twin
---

# Web control UI — the web L3 over the cockpit read-model

> **Path note.** The ratified brief named `docs/architecture/adr/ADR-00NN-…`;
> the repo's validated home for new Decision Records is
> `docs/decisions/ADR-NNNN-*.md` (the path the `decision_record` check scans and
> where ADR-0007 landed). This ADR follows the validated convention. `ADR-0007`
> is the highest existing number, so this is **ADR-0008**.

## Context and Problem Statement

The Operator wants a **web-based control UI for CE, modeled on OpenClaw's** — a
phone- or browser-reachable surface to see what CE is doing and to discharge the
one act CE reserves for a human: ratification. CE's UI core was deliberately
designed front-end-agnostic in three layers — **L1** the governance spine, **L2**
a pure JSON read-model that does *all* computation, **L3** a thin view that only
renders. The Textual TUI is today's L3. This ADR decides the **web L3**: the
same read-model, rendered in a browser, actuating the same gates.

This is **not greenfield** — roughly 80% already exists. `fold_snapshot()`
(`cockpit_readmodel.py`) is the pure L2 read-model; `ce cockpit --json` already
emits it verbatim as the future-GUI seam; `ce cockpit --serve` already carries a
hardened serve spine (loopback bind, Jupyter token-then-cookie gate, Host-header
anti-rebinding, aiohttp middleware on every route); the journey-cockpit (#45)
already computes the CEO face (the Frame→Ship arc, the where-am-I marker, the
plain-language decision feed). What is missing is: a browser SPA, a **live-push +
RPC** transport (the TUI binds the fold in-process; a browser needs it over the
wire), and a **programmatic seam to actuate the canonical ratification gate** (the
TUI is observation-only today; only escalation open/resolve write seams exist).

The hard question is the boundary. A web client is the easiest place to
accidentally grow a second brain — to compute a status the read-model didn't, or
to write governance state down a path that skips the gate. The L3 law must hold
*over the wire*, enforced by CI and review, not by good intentions.

## Decision Drivers

- **Front-end-agnostic core is a HARD rule** (`ce-cockpit-frontend-agnostic-core`):
  L2 computes everything; L3 only renders; swapping L3 must not touch L1/L2.
- **Dogfood-grade, not MVP** (`ce-no-mvp-quality-from-day-1`): design for the
  real product, not a minimum.
- **Ground in the actual reference** (`agent-research-discipline`): mirror what
  OpenClaw *really* does (read 2026-06-20), not a remembered sketch.
- **No new public perimeter**: the fleet is tailnet-native; reuse that perimeter.
- **Automate the push, human-gate the ratify** (`ce-push-deploy-authority-model`):
  the web UI may *carry* a ratification, never *be* the authority; authority
  attaches to the ratification **form**, not the input modality
  (`ce-authority-attaches-to-form`).
- **Containment doctrine** (`ce-mandatory-containment-decision`, ADR-0007): the
  read-model gateway must not become a forge-egress or arbitrary-mutation hole.
- **Plain-language law** (`ce-positioning-ease-not-governance`): zero jargon in
  CEO-facing text; the UI sells *ease*, governance is the invisible engine.
- **Reuse, don't reinvent**: ~80% exists; the decision is mostly *how to expose
  what already computes*, not what to build new.

## Considered Options

**Stack.** (1) **Vite + Lit + TypeScript** — mirrors the reference; standards-based
web components are portable and PWA-native, and match the "L3 is replaceable"
rule (web components survive a future host swap). (2) React/Next — heavier, a
framework runtime and router we don't need for a read-model mirror; SSR fights a
live-push model. (3) Svelte/SvelteKit — fine and light, but diverges from the
reference and is less component-portable than custom elements. (4) Server-rendered
HTMX — clean for request/response, awkward for a continuously-pushed read-model.

**Gateway.** (1) **Evolve `ce cockpit --serve`** — keep its security spine, swap
the payload from `textual_serve` (which serves the *TUI* in a browser) to static
SPA serving + a WS endpoint. (2) A brand-new gateway service — throws away a
hardened, reviewed auth spine. (3) Reuse `textual-web`/`textual-serve` to ship
the TUI-in-browser as "the web UI" — explicitly rejected upstream
(`textual-web` is already rejected in `v3_cockpit.py`); it is the TUI piped
through a canvas, not a real web L3, and can't be a PWA or go mobile-native.

**Auth.** (1) **Tailscale Serve identity, token-then-cookie fallback** — matches
the tailnet fleet and OpenClaw's path, no new public perimeter. (2) A public
ingress + new IdP — a new attack surface and custody burden for a solo/small-team
product. (3) Token-only — works on loopback, but has no per-user identity for an
audited ratification.

**Write path.** (1) **Form-echo over an enumerated, server-validated RPC allowlist
that wraps the *existing* canonical seams** — the binding act is the same act the
CLI performs, re-rendered. (2) A generic "write any record" RPC — exactly the
bypass containment forbids. (3) Web stays read-only forever — fails the #28 goal
(discharge from your phone).

## Decision Outcome

Adopt **the read-model-mirror web L3**: a Vite + Lit + TypeScript SPA served by an
evolved `cockpit-serve` gateway over a single port, authenticated by Tailscale
Serve identity (token-then-cookie fallback), rendering the L2 fold live and
actuating gates only through a small, server-validated, form-echoed RPC allowlist
that wraps the existing canonical seams. Per-decision:

1. **Stack — Vite + Lit + TypeScript** (Option 1). The reference is real and
   proven (verified: Lit 3.3.3, Vite 8, TS, `@noble/ed25519` for in-browser
   device identity, MIT-licensed). Web components keep L3 swappable and PWA-native.
   Mirror OpenClaw's **hand-rolled service worker** (Cache API, no Workbox
   dependency) rather than inherit a framework's PWA layer — lighter, and we
   control the cache-exclusion list (critical: never cache the RPC/event path).

2. **Gateway — evolve `cockpit-serve`** (Option 1). Keep verbatim its security
   spine from `v3_cockpit.py`: loopback-default bind discipline (`_LOOPBACK_BINDS`),
   the token-then-cookie gate (`generate_token`, `TOKEN_COOKIE`,
   `_MIN_TOKEN_LENGTH`, constant-time `hmac.compare_digest`), Host-header
   anti-rebinding (`allowed_hosts`), and the aiohttp middleware that runs the gate
   on **every** route. Replace the `textual_serve` payload with two route groups
   on the **same port**: (a) static SPA assets; (b) a WebSocket carrying the
   read-model stream + the RPC allowlist. Deps stay lazy-imported on the serve
   path; no daemon by default (daemonizing — e.g. the VPS `:8200` deployment — is
   an ops concern, not in the binary). This is "evolve from cockpit-serve, not a
   new service."

3. **Auth — Tailscale Serve identity, token fallback** (Option 1). Primary:
   `tailscale serve` terminates HTTPS on the tailnet and forwards identity; the
   gateway **verifies** it via the local `tailscaled` (`tailscale whois` on the
   forwarded address, matched to the `tailscale-user-login` header) — never trust
   the header alone — and only when an `allow_tailscale` config is set. This
   yields a real per-user identity for an audited ratification with **no new
   public perimeter**. Fallback: the existing token-then-cookie gate for loopback
   / non-tailnet. Adopt OpenClaw's stated **trusted-host** caveat (disable the
   tokenless tailnet path if untrusted local code may share the host). In-browser
   **ed25519 device identity** (OpenClaw's third layer) is a strong future
   hardening for the mobile/PWA case — see Open Questions — but is **not** MVP.

4. **L3 boundary (HARD LAW).** The web computes nothing and reads no source.
   - **Read:** the SPA's *only* data input is the fold JSON (`snapshot_version: 2`).
     Every datum rendered must be a key already present in `ce cockpit --json`. No
     second data path, no client-side recomputation, no direct file or spine read.
   - **Write:** the gateway exposes *only* (a) the read-model stream and (b) a
     **closed, enumerated RPC allowlist**, each method a thin wrapper over an
     existing canonical seam (escalation resolve today; ratify when its seam
     exists — see Slice Web-B). No generic write RPC. Every write is **form-echoed**
     (§Write path below) and **re-validated server-side** against the canonical
     schema before it touches state.
   - **Enforcement (CI + review), so the law holds over the wire:**
     - *Parity test:* the set of fold keys the SPA binds is asserted ⊆ the golden
       `ce cockpit --json` output; fold-vs-UI drift fails CI (the `--json` surface
       is the contract, not an afterthought).
     - *No-compute lint/review:* the SPA package may not import or re-implement any
       L2 logic; reviewers reject any client-side derivation of governance state.
     - *Closed RPC allowlist:* the method set is a reviewed constant; adding a write
       method is a `governance`-class change reviewed **separately** (as the TUI
       Slice-2 write-seam was), never folded into a render PR.
     - *Server-side form-echo + schema re-validation:* the gateway rejects any
       write whose echoed form ≠ the canonical form, or that fails the same
       validator the CLI/record uses.

5. **Panel set** — the #45 five requirements as web views, each bound 1:1 to a
   fold key (no new computation), in two faces:
   - **CEO face (default):** *process picture* → `journey.arc` (the
     Frame→Shape→Build→Review→Ship belt); *where-am-I* → `journey.now`;
     *what-needs-me* decision-inbox → `journey.needs_attention`; *plain-language
     decision-detail* → `journey.need_details[ref]`.
   - **Dev face (toggle):** *visual dev-arc/roadmap* → `board`
     (columns/cards/`phase_counts`), plus the governance posture
     (`governance.posture`, `governance.seats`) and the honest resource envelope
     (`meters`: spend, token-rate, context, subscription-headroom — with the
     MEASURED/ESTIMATED/UNAVAILABLE badges). These come *for free* from the fold.
   - **The discharge-binding-act seam (Web-B)** lives on the decision-detail screen.
   Vocabulary is fixed to the canon (Frame→Shape→Build→Review→Ship; Goal / Done-when
   / Budget / Change-type / Ready) — **no third vocabulary**; CEO-text comes from the
   fold's pre-scrubbed plain-language fields (`journey.need_details`,
   `stage_labels`), never re-authored in the client.

6. **PWA / mobile (#28).** Ship a web app manifest (install-to-homescreen) and a
   hand-rolled service worker mirroring OpenClaw's policy: cache-first for hashed
   assets, network-first for HTML, and **never cache the RPC/event path** (the
   `/rpc` + WS routes — auth- and freshness-sensitive). **Web Push (VAPID)** fires
   on a new `⏸️ AWAITING-OPERATOR` item (a fold `journey.needs_attention` arrival);
   the notification deep-links to that decision-detail. Web Push requires a secure
   context — **Tailscale Serve's HTTPS magicDNS provides it**, so the mobile thesis
   is exactly: phone on the tailnet → install the PWA → receive the ⏸️ push →
   open the decision → discharge it (Web-B). The loopback/token path stays a
   desktop convenience (no push without TLS).

7. **Visual design direction — "Control-Room Violet," shared with the live site /
   #37 docs portal.** Full token system, typography, signature element, and
   low-fi wireframes in §Visual design direction below; rendered mockups in
   `tmp/webui-shots/` for the Operator's visual checkpoint.

## L1 / L2 / L3 mapping

```
                          ┌──────────────────────────────────────────┐
  L1  GOVERNANCE SPINE    │ scopes · runs · escalations · refusal-     │
      (source of truth)   │ chain · envelopes · ledger · claims        │
                          └───────────────────┬──────────────────────┘
                                              │  load seams (file reads ONLY here)
                                              ▼
                          ┌──────────────────────────────────────────┐
  L2  PURE READ-MODEL     │ fold_snapshot()  →  one JSON dict          │
      (ALL computation)   │ snapshot_version: 2                        │
                          │ { source, availability, seats, board,      │
                          │   seat_detail, refusals, escalations,      │
                          │   journey, dispatches, seat_events,        │
                          │   claims, governance, meters, evidence }   │
                          └──────┬───────────────────────────┬────────┘
                                 │ in-process bind            │ `cev3 cockpit --json` (verbatim)
                                 ▼                            ▼
                  ┌───────────────────────┐     ┌──────────────────────────────────┐
  L3  VIEW ONLY   │ Textual TUI (today)   │     │  GATEWAY (evolved cockpit-serve) │
      (renders,   │ render-only           │     │  one port · TS identity / token  │
      computes    └───────────────────────┘     │  ── WS ──► snapshot stream (push)│
      nothing)                                   │  ◄─ RPC ── allowlist (form-echo) │
                                                 └───────────────┬──────────────────┘
                                                                 ▼
                                                   ┌──────────────────────────────┐
                                                   │  WEB L3 — Vite + Lit + TS SPA │
                                                   │  PWA · CEO face / Dev face     │
                                                   │  renders the fold; no compute  │
                                                   └──────────────────────────────┘

  WRITE PATH (Web-B): SPA ─gate.prepare→ canonical form ─human affirms→ gate.commit(echo)
                      → gateway validates echo==form + re-validates schema
                      → calls the SAME canonical seam the CLI calls (escalation resolve / ratify)
                      → L1 state changes → next fold push reflects it.
  The gateway is a READ-MODEL surface, NOT a forge-egress path (cf. ADR-0007).
```

## WS-RPC contract sketch

Single port; static SPA + WebSocket share it (OpenClaw's load-bearing choice).
A **custom frame envelope** (mirrors OpenClaw; simpler than JSON-RPC 2.0 for a
streaming read-model). Three frame types:

```jsonc
// client → server: a request
{ "type": "req", "id": "<uuid>", "method": "<name>", "params": { } }

// server → client: the matching response (correlated by id only)
{ "type": "res", "id": "<uuid>", "ok": true,
  "payload": { },
  "error": { "code": "string", "message": "string", "retryable": false } }

// server → client: an unsolicited push (connect-then-stream; no per-topic subscribe)
{ "type": "event", "event": "snapshot", "seq": 42,
  "snapshotVersion": 2, "payload": { /* the full fold */ } }
```

**Connect-then-stream** (OpenClaw model): after the gate admits the socket, the
server pushes a full `snapshot` event and then re-pushes on change, each with a
monotonic `seq`. The client renders the latest and detects gaps by `seq`. Start
with **full-snapshot pushes** (the fold is small and cheap; honesty over
cleverness); introduce true deltas only if payload size demands it (Open Question).

**Method allowlist (closed set):**

| Method | Slice | Wraps (existing canonical seam) | Notes |
|---|---|---|---|
| `cockpit.snapshot` | Web-A | `snapshot_from_roots()` / demo seed | Pull the current fold (read-only). |
| `cockpit.stream` | Web-A | the push loop | Begin/end the live stream. |
| `gate.prepare` | Web-B | reads `journey.need_details[ref]` | Returns the **canonical form text** + a one-time nonce. No write. |
| `gate.commit` | Web-B | `_cmd_escalation_resolve` (exists); `ce ratify` (seam **must be built**) | Accepts `{ ref, nonce, echoed_form }`; gateway asserts `echoed_form == canonical_form`, re-validates against the record schema, then calls the seam. |

**Form-echo (the binding act).** Authority attaches to the ratification *form*,
not the modality. `gate.prepare` returns the exact canonical text the human must
affirm; the SPA shows it and requires a deliberate confirm; `gate.commit` carries
the **verbatim echo**, which the gateway checks byte-for-byte against the canonical
form before any write. A mismatch is refused, not coerced. This makes the web
ratification "another rendering of the same text," valid only when it validates.

**Honest gap (do not paper over):** there is **no programmatic ratify seam today**.
`_cmd_escalation_open/_resolve` exist (`v3_cli.py`); `ce ratify --scope-id
--approver-ref` exists as a **CLI** path but is not callable as a library API for a
gateway. Web-B therefore **includes building** that seam — extract the canonical
ratify core into a function reused by *both* the CLI and the gateway — and must
**never** invent a web-only write that bypasses it.

## Visual design direction

> Produced with the `frontend-design` plugin. The visual language is **pinned** by
> the brief (Control-Room Violet, shared with the live site / #37 docs portal), so
> the design discipline here is *fidelity + restraint*, not a fresh palette hunt.
> Rendered low-fi mockups: `tmp/webui-shots/index.html`.

**Subject & job.** A control room for a governed agent SDLC. Audience: a solo
builder or small-team CEO who delegates the work and keeps the one decision that's
theirs. The page's single job: **show what CE is doing, and surface the one thing
that needs you — with enough plain-language context to decide.**

**Signature element — the Gate Card.** CE's whole thesis is "automate the push,
human-gate the ratify." The most characteristic moment in CE's world is *the
pause*: CE stops and asks. So the signature is the **Gate Card** on the
decision-detail screen — a violet-edged panel that reads in plain language (What
this means / Why CE paused / If you continue / If you decline / What CE will *not*
do) and ends in the form-echo affirm. Everything else stays quiet so this lands.

**Reuse the live-site token system (`docs/index.html :root`, verbatim):**

```css
/* Control-Room Violet — shared with the live site & #37 docs portal */
--violet:#A06BFF; --violet-bright:#B98CFF; --violet-deep:#6E3CD6;
--violet-soft:rgba(160,107,255,.16);
--ink:#0C0B0A; --panel:#16140F; --panel-2:#191712; --line:rgba(255,255,255,.10);
--paper:#FAF8F1; --muted:#9A968C;
/* semantic status (domain-derived, NOT decorative) */
--spark:#7FB069;  /* go · verified · allowed · MEASURED */
--gate:#E0605C;   /* deny · refusal · hard-breach */
--amber:#E08B4C;  /* pending · soft-breach · ESTIMATED · AWAITING-OPERATOR */
--mono:'SFMono-Regular',ui-monospace,Menlo,Consolas,monospace;
--sans:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
```

These are the same tokens `v3_cockpit.py`'s `THEME` pins to verbatim, so TUI,
web, and the marketing site read as one product. The status triad is the rare
case where "a dark theme with one accent" is wrong: `gate`/`spark`/`amber` each
*mean* something (deny / go / pending) — they are the governance vocabulary made
visible, not mood.

**Typography (2 roles + utility), shared with the live site.**
- *Display & body* — **Inter** (700 for heads, `-0.02em` tracking; 400/500 body at
  `line-height:1.5`). The plain-language law lives here: CEO copy is humanist and
  calm.
- *Utility / data* — **SFMono**: eyebrows (uppercase, `0.18em` tracking, violet),
  scope IDs, run digests, evidence hashes, meter readouts. Mono = "this is a
  machine fact." The mono/violet eyebrow is the live site's signature tic; we keep it.

**Layout & motion.** Warm-ink canvas, one violet radial glow at the top (the live
site's `--violet-soft`), generous whitespace, hairline `--line` dividers. The
**factory belt** (the live site's Frame→Shape→Build→Review→Ship conveyor) is the
process picture — reused, not reinvented, with a live where-am-I marker riding it.
Motion is restrained: the belt marker eases to its station; a new ⏸️ item slides
in once; `prefers-reduced-motion` respected. No ambient animation competing with
the Gate Card.

**Plain-language law.** Every CEO-facing string is a verb the person controls and
recognizes ("Approve the spend," not "Ratify mutation_class=deploy"); the affirm
button keeps its word through to the toast ("Approve" → "Approved"). Jargon
(`scope_id`, `mutation_class`, hashes) is allowed only in mono, in the Dev face or
a decision's *technical source* footer — never in the explanation.

### Wireframe — CEO face (default): journey + where-am-I + what-needs-me

```
┌─ CE ────────────────────────────────────  ◐ CEO | Dev   ⏻ Operator ─┐
│                                                                            │
│  WHERE THINGS ARE                                                          │
│  ●───────●───────◍───────○───────○                                         │
│  Frame   Shape   Build   Review  Ship      ◍ = you are here                │
│                  └ "Adding the web control UI"  ·  on track                │
│                                                                            │
│  ┌─ WHAT NEEDS YOU ───────────────────────────────────────── 2 ─┐         │
│  │ ⏸  Approve $40 for the design research run        Recommend ▸ │         │
│  │     CE paused — this is over your $25 auto-limit               │         │
│  │ ──────────────────────────────────────────────────────────── │         │
│  │ ⏸  Merge "web control UI ADR"?                    Recommend ▸ │         │
│  │     Reviewed and green; needs your go-ahead                    │         │
│  └───────────────────────────────────────────────────────────────┘        │
│                                                                            │
│  Nothing else needs you. CE is working on 3 things.            [ See all ] │
└────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe — Decision detail (the Gate Card · Web-B form-echo) — SIGNATURE

```
┌─ ‹ Back to what needs you ─────────────────────────────────────────────────┐
│                                                                            │
│   ⏸  Approve $40 for the design research run                               │
│   ╒════════════════════════════════ violet edge ═══════════════════════╕ │
│   │ WHAT THIS MEANS                                                        │
│   │   CE wants to spend about $40 of model time researching the           │
│   │   web UI design before it writes any code.                            │
│   │ WHY CE PAUSED                                                         │
│   │   You set a $25 limit for automatic spend. This is over it.          │
│   │ IF YOU APPROVE        CE runs the research now and shows you results. │
│   │ IF YOU DECLINE        CE stops here and asks for a smaller plan.      │
│   │ CE WILL NOT           merge, deploy, or push anything on its own.     │
│   ╘════════════════════════════════════════════════════════════════════╛ │
│                                                                            │
│   CE recommends: Approve — the estimate is within this week's headroom.    │
│                                                                            │
│   To approve, this is what you're affirming:                              │
│   ┌ form-echo ─────────────────────────────────────────────────────────┐ │
│   │ "Approve up to $40 for run ce28-design-research (spend gate)."      │ │
│   └────────────────────────────────────────────────────────────────────┘ │
│                       [  Decline  ]      [  Approve  ]                      │
│   technical source: escalation esc-...  ·  spend_gate                      │
└────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe — Dev face (toggle): board + posture + honest meters

```
┌─ CE ───────────────────────────────────────────  CEO | ◐ Dev   ⏻ Operator ──┐
│ FRAME    SHAPE     BUILD      REVIEW     SHIP        posture: 2 hard-denies │
│ ┌────┐  ┌────┐   ┌──────┐   ┌──────┐   ┌────┐       · governed seat: no push│
│ │ce31│  │ce45│   │ce28  │◍  │ce08  │   │    │       · contained: no egress  │
│ └────┘  └────┘   │ web  │   │ adr  │   └────┘                               │
│                  └──────┘   └──────┘                                        │
│ ── meters ─────────────────────────────────────────────────────────────── │
│ spend  $18 / wk        ▣ MEASURED      context  41%        ▣ MEASURED       │
│ tokens 92k / hr        ▣ ESTIMATED     headroom 38% used   ▣ MEASURED       │
└────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe — Mobile / PWA: the ⏸️ push → discharge

```
   ┌─────────────┐      ┌──────────────────┐      ┌──────────────────┐
   │  9:41    ▮▮▮ │      │ ‹ CE             │      │  ⏸ Approve $40   │
   │ ┌─────────┐ │      │ WHERE THINGS ARE │      │  WHAT THIS MEANS │
   │ │ CE  now │ │ tap  │ ●──●──◍──○──○     │ tap  │  …plain text…    │
   │ │ ⏸ needs │─┼────► │ WHAT NEEDS YOU 1 │────► │  [Decline][Approve]│
   │ │ you: $40│ │      │ ⏸ Approve $40  ▸ │      │  form-echo: ✓    │
   │ └─────────┘ │      │                  │      │                  │
   └─────────────┘      └──────────────────┘      └──────────────────┘
    Web Push (VAPID)     installed to homescreen     Web-B form-echo
    over Tailscale TLS    (tailnet, no public net)    discharges the gate
```

## Sliced build plan

The ADR proposes; **the build is a separate, later, ratified dispatch.**

**Slice 0 — Gateway evolution (shared dependency).** Refactor `cockpit-serve` so
its security spine (`build_serve_config`, `evaluate_request`, token-then-cookie,
Host-header gate, aiohttp middleware) is reusable, and add the two route groups
(static SPA + WS) behind it on one port. Add the **closed RPC allowlist** scaffold
(read methods only). Add Tailscale-identity verification (`tailscaled` whois) as
the primary auth, token fallback retained. No SPA yet — provable with a WS client
that pulls + streams the fold.

**Slice Web-A — read-only live journey mirror.** The Vite + Lit + TS SPA: connect,
authenticate, receive the snapshot stream, render the **CEO face** (journey arc,
where-am-I, what-needs-me, decision-detail *read-only*) and the **Dev face** (board,
posture, meters). PWA shell: manifest + service worker + install-to-homescreen +
Web Push that fires on a new `journey.needs_attention` item and deep-links to its
detail. **Notify → inspect.** Ships the parity test (UI-bound keys ⊆
`cockpit --json`) and the no-compute review rule. *No write path.*

**Slice Web-B — discharge the binding act.** Build the **canonical ratify seam**
(extract `ce ratify`'s core into a callable reused by CLI + gateway) — *if it does
not exist, that is the first task of this slice; never a web-only bypass.* Wire
`gate.prepare`/`gate.commit` with **form-echo** and server-side schema
re-validation; light up the decision-detail affirm. Reviewed under **separate
governance review** (as the TUI Slice-2 write-seam was), not folded into Web-A's
render PR. Start with the escalation-resolve seam (which exists) to prove the
form-echo loop end-to-end, then extend to ratify.

**Out of scope / explicit non-goals.** This gateway is a **read-model + gate
surface only** — never a forge-egress/push path (that is ADR-0007's egress
gateway; keep them distinct). No `textual-web` TUI-in-canvas. No client-side
governance computation, ever.

## Consequences

- **Good:** reuses ~80% (the fold, `--json` parity, the serve spine, the journey
  computation, the design tokens); the L3 law holds over the wire by CI + closed
  allowlist + form-echo; no new public perimeter (tailnet identity); one design
  language across TUI / web / marketing site; the mobile ⏸️→discharge thesis
  (#28) is reachable on the existing fleet.
- **Good:** L3 stays genuinely swappable — a future native or different web host
  consumes the same fold + RPC allowlist; nothing in L1/L2 moves.
- **Trade-off:** an **SPA build needs Node/npm**, which conflicts with the v0.1
  substrate's "fresh clone, offline, Python-only" guarantee (plan.md). The web UI
  is a **separate optional surface**, not part of the validator's offline path;
  built SPA assets may be vendored (like `validators/wheelhouse/`) to preserve an
  offline serve. (Open Question.)
- **Trade-off:** Web Push / device identity / WebCrypto need a **secure context**;
  full mobile capability requires the Tailscale-HTTPS path (loopback/token is
  desktop-only). Acceptable — the fleet is already tailnet-native.
- **Trade-off:** the gateway becomes a **higher-assurance component** the moment
  Web-B lands (it can actuate a binding act). Mitigated by the closed allowlist,
  form-echo, server-side re-validation, and the same containment posture as the
  egress gateway — but it must be hardened and audited, not treated as "just a
  viewer."
- **Trade-off:** mirroring OpenClaw's **custom WS envelope** (not JSON-RPC 2.0)
  trades ecosystem tooling for simpler streaming; revisit if external tooling ever
  needs to speak the protocol.
- **Note (ticket structure):** keep **ce-ops#28** as the umbrella/home (it already
  names cockpit-serve + the tailnet); open **two child build tickets** — *Web-A*
  (read-only mirror, incl. Slice 0 gateway evolution) and *Web-B* (binding-act
  seam, governance-reviewed) — with **ce-ops#45** cross-linked as the panel-set
  requirement source. Do *not* fold Web-B into #45 or #28's render work; its write
  path earns its own ratified scope.
