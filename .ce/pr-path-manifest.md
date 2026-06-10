# PR path manifest — feat(v3.5-B): Cockpit MVP wave (B.1 + B.3 + B.4 + B.2 + B.6, one combined branch)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: the **v3.5-B Cockpit MVP wave** — the five Operator-ratified gates of the
cluster doc `~/Documents/ce-cockpit-b-gates-20260609T182642Z.md`, executed in the
ratified order **B.1 → B.3 → B.4 → B.2 → B.6** on ONE combined branch (the #185
lesson), each gate committed at its own full green. This carrier is the UNION of
the five gates' closed manifests.

- **B.1 — `ce cockpit` skeleton (the L1/L2/L3 split = THE deliverable).**
  `runner/cockpit_readmodel.py` *(NEW — L2 = the harness-paper F1, the pure
  JSON-serializable snapshot fold)* · `runner/cockpit_demo_seed.py` *(NEW — Fork
  F-b: the `CE_DEMO=1` schema-true, spine-chained seed)* · `v3_cockpit.py` *(NEW —
  L3 Textual view, binds only)* · `v3_cli.py` cockpit subparser w/ lazy textual
  import + `--json` (the textual-free future-GUI seam) · Fork F-a: `cockpit`
  optional extra (textual==8.2.7 + watchfiles==1.2.0) + the 12-wheel pinned
  closure vendored in `wheelhouse-dev/` + `requirements-dev.txt` so CI's offline
  dev-install exercises it · `docs/architecture/cockpit.md` reconciled to the
  live build-input doc · tests `test_cockpit_readmodel.py` + `test_v3_cockpit.py`.
- **B.3 ★ keystone — governance/authority panel + the refusal-record spine seam.**
  `hook_check.py` *(the wave's ONLY v1 edit)*: governed hard-deny paths
  (restricted-mechanic + secret-path) now append a
  `runtime_agent_action{classification: denied}` record to the instance-local
  refusal chain via the **shared** `runtime_evidence_spine` (V1→shared = allowed;
  `evidence_sink` (v3) is never imported — zero v1↔v3 crossings, enforced green);
  decide-first-record-after; the deny stands if the append fails. Panel
  projections (envelope matrix off the existing `envelope_ref`, ★ REFUSED feed,
  attribution, posture) in L2; right-rail binding in L3; tests
  `test_hook_check.py` (extended) + `test_cockpit_governance_panel.py` *(NEW)*.
- **B.4 — unified resource/health meter strip.** Pure REUSE of the shipped
  metering (`fleet_spend_meter` / `fleet_token_rate` / `context_meter` — no
  parallel math) folded into the snapshot with mandatory
  MEASURED/ESTIMATED/UNAVAILABLE honesty badges; the subscription-headroom tile
  is the labelled ESTIMATED placeholder, never a number; soft/hard breach
  banners; test `test_cockpit_meters.py` *(NEW)*.
- **B.2 — ops board + seat detail.** Board cards across the canon five stages
  (`PHASE_BY_STATE` — never a third vocabulary), all/mine/live filters, blocked
  cards name their refusal inline; seat-detail tabs Stream (Temporal-style
  collapsed spans + retry badges) / Diffs / Evidence-trail (truthful
  `verify_chain` badge) / Waterfall / Outcome — every projection in L2, `--json`
  parity; test `test_cockpit_board.py` *(NEW)*.
- **B.6 — `--serve` browser mode + Control-Room Violet polish.** The hands-on
  serve-library precondition was verified BEFORE building: textual-serve 1.1.3
  delivers 127.0.0.1-only bind + token gate + Host-header validation without
  forking (public-class subclass + one appended aiohttp middleware; textual-web
  never used). Pure `ServeConfig` builder (loud non-loopback refusal, ≥32-char
  token floor) + pure per-request decision (Host first — anti-DNS-rebinding —
  then the Jupyter token-then-cookie model); `cockpit-serve` extra
  (textual-serve==1.1.3) + the 12-wheel pinned serve closure vendored for CI's
  offline exercise; serve is additive (TUI/`--json` never import it). The live
  site tokens land VERBATIM as the Textual theme (refusals gate-red, verified
  chains spark-lime, ESTIMATED amber, authority violet) — `docs/index.html` was
  READ for the hexes and is NOT in this diff; test `test_v3_cockpit_serve.py`
  *(NEW)*. The shipped `wheelhouse/creator_engine_validator` wheel + `SHA256SUMS`
  were rebuilt from the combined source (cluster §0.8).
- **`.ce/pr-path-manifest.md`** *(this carrier)*.

**Version-boundary impact (the wave's declared end-state):** new `@register`
checks **0** — the check registry stays **47** and `--list-checks` is
byte-identical; **V3_RUNTIME 28 → 31** (B.1's `runner.cockpit_readmodel` +
`runner.cockpit_demo_seed` + `v3_cockpit`; B.3/B.4/B.2/B.6 are all +0), with all
three `_versions.py` entries landing together with their module files. No schema
edits, no spine edits; the single v1 edit is B.3's append-only observability seam
in `hook_check.py` (zero decision-behavior change; `version_boundary` +
`test_hard_invariant_zero_v1_v3_crossings` green). The core install surface
(PyYAML + jsonschema) is unchanged — all new deps are optional extras
(`cockpit`, `cockpit-serve`), dev-vendored offline.

- **base:** `ea1eea6` (current `main`).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=44

AUTHORIZED_PATHS_SHA256=5d4fd56370536f3a7b7bf08b2035d2a521ea8c27623dce5015ccc65892d71161

```text
.ce/pr-path-manifest.md
docs/architecture/cockpit.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/runner/cockpit_demo_seed.py
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_cockpit.py
validators/pyproject.toml
validators/requirements-dev.txt
validators/tests/unit/test_cockpit_board.py
validators/tests/unit/test_cockpit_governance_panel.py
validators/tests/unit/test_cockpit_meters.py
validators/tests/unit/test_cockpit_readmodel.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_v3_cockpit.py
validators/tests/unit/test_v3_cockpit_serve.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse-dev/aiohappyeyeballs-2.6.2-py3-none-any.whl
validators/wheelhouse-dev/aiohttp-3.14.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
validators/wheelhouse-dev/aiohttp_jinja2-1.6-py3-none-any.whl
validators/wheelhouse-dev/aiosignal-1.4.0-py3-none-any.whl
validators/wheelhouse-dev/anyio-4.13.0-py3-none-any.whl
validators/wheelhouse-dev/attrs-26.1.0-py3-none-any.whl
validators/wheelhouse-dev/frozenlist-1.8.0-cp314-cp314-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl
validators/wheelhouse-dev/idna-3.18-py3-none-any.whl
validators/wheelhouse-dev/jinja2-3.1.6-py3-none-any.whl
validators/wheelhouse-dev/linkify_it_py-2.1.0-py3-none-any.whl
validators/wheelhouse-dev/markdown_it_py-4.2.0-py3-none-any.whl
validators/wheelhouse-dev/markupsafe-3.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
validators/wheelhouse-dev/mdit_py_plugins-0.6.1-py3-none-any.whl
validators/wheelhouse-dev/mdurl-0.1.2-py3-none-any.whl
validators/wheelhouse-dev/multidict-6.7.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
validators/wheelhouse-dev/platformdirs-4.10.0-py3-none-any.whl
validators/wheelhouse-dev/propcache-0.5.2-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
validators/wheelhouse-dev/rich-15.0.0-py3-none-any.whl
validators/wheelhouse-dev/textual-8.2.7-py3-none-any.whl
validators/wheelhouse-dev/textual_serve-1.1.3-py3-none-any.whl
validators/wheelhouse-dev/typing_extensions-4.15.0-py3-none-any.whl
validators/wheelhouse-dev/uc_micro_py-2.0.0-py3-none-any.whl
validators/wheelhouse-dev/watchfiles-1.2.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
validators/wheelhouse-dev/yarl-1.24.2-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
