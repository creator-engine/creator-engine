# Auto-Update Mechanism — Research Report (decision-grade) — 2026-06-30

**architect_research (Opus, read-only).** Brief: `.ce/briefs/ce-auto-update-mechanism-research.md`. Status: awaiting Operator ratification.

## Bottom line
Auto-**CHECK + NOTIFY** on the solo end-user path: YES, build it (cheap, matches "don't make Arad hunt for updates"). Auto-**APPLY** silently on startup: **NO, not yet** — opt-in only, never the startup default, until a signed recall/min-version kill-switch + a deeper post-promote self-check exist. Auto-update inside governed/contained/fleet seats: **HARD NO** — already routed through `fleet_rollout.py` and denied at `hook_check.py`; preserve that boundary explicitly.

CE already has a strong verify→stage→apply→rollback self-update engine (`update.py`). Missing: a trigger, a notify UX, a config surface, and — for any auto-apply — a recall floor. Assemble-and-harden, not greenfield.

## Two-axis frame (keeps the carve-out clean)
- **Axis A (what):** A1 = the CE app itself (validator wheels/venv) → `update.py`; A2 = rented toolchain (codex/herdr/rg/zig/deps) → `surfaces/manifest.yaml` + `check_updates.py` + `fleet_rollout.py`.
- **Axis B (where):** B1 = solo end-user install (Arad); B2 = governed/contained fleet seat.
- **A1×B1** = the auto-update candidate (`update.py` is purpose-built). **anything×B2** = MUST flow controller→`fleet_rollout`, never self-update (already enforced). **A2×B1** = rides inside the signed CE release (no separate solo toolchain auto-update).

## Current state (grounded in code)
- `update.py` = strong CE self-updater: `resolve_latest_signed_release()` mirrors `install.sh` (signed spec + `ce-root-v1` trust root + **out-of-band DNS-TXT anchor** via dns.google; SSHSIG verify; refuses same-origin anchor; SHA256SUMS + per-wheel hash + embedded version/sha parity). `VenvSwapper` builds offline (`pip install --no-index`), smoke-tests `ce --help`, **atomic symlink promote w/ restore-on-failure**, lock + state. Downgrade refused. **Not invoked at startup anywhere.**
- `ce update` CLI: `--check` (read-only) / default apply; `--site`, `--trust-anchor-url`, `--json`.
- `surfaces/check_updates.py` = DIFFERENT (A2 upstream version detection for rented surfaces; never mutates).
- `fleet_rollout.py` = governed fleet path; `_refuse_prohibited_command` blocks apt/curl/npm/pip — seats relaunched onto pinned surfaces, never self-install.
- `hook_check.py` = contained-seat guard ALREADY exists: tags `toolchain_self_update` and hard-denies in governed seats; **deliberately exempts `pip install --no-index`** (exactly what VenvSwapper uses) → the carve-out is already encoded at the mechanic level.
- Trust anchor: `docs/install.sh` canonical verify-before-execute; `release_artifact_parity_guard.py` byte-binds install.sh ≡ downloads ≡ SHA256SUMS.

## Why NOT silent auto-apply (residual risks)
1. Rollback protects the SWAP, not a correctly-signed-but-bad release (only gate before promote = `ce --help`).
2. **No recall / min-version / kill-switch** — a bad/malicious signed release (or `ce-root-v1` key compromise) → instant fleet-wide RCE on next startup. DNS anchor rotates the KEY but can't RECALL a release. **Biggest gap before any default apply.**
3. Mid-session code swap hazard for an autonomous SDLC product; contradicts CE's own "never auto-apply" instinct.
4. `update.py.default_fetcher` has **no timeout** → startup check must be time-boxed + fail-open.
5. `check_for_update()` downloads+verifies wheels even for a read-only check → too heavy for startup; need a lightweight spec-only check.
6. Auto-checker must be statically OFF in contained seats (egress-restricted + doctrinally forbidden).

## Channels
- **Stable (Arad on 0.3.x):** auto-update = latest SIGNED release (the only thing `update.py` can verify). Wire notice/opt-in-apply here.
- **main-HEAD (Nitzan/contributors):** git/editable-install workflow; NO signed artifact for arbitrary main → do NOT build "track main" into the signed updater.

## Recommendation
1. Default solo UX = **non-blocking, cached, fail-open startup NOTICE** ("ce 0.3.1 available — run `ce update`") via a NEW lightweight signature-only check (rate-limited).
2. Auto-apply = **explicit opt-in** (`auto_update: notify|apply|off`, default `notify`); even `apply` at a safe boundary w/ confirm-on-consequence + `ce update --auto` for cron — never silent mid-session.
3. **Hard-disable auto-update in governed/contained/fleet seats** (reuse posture predicate + `toolchain_self_update` deny); fleet stays controller→`fleet_rollout`.
4. Gate any default auto-apply behind safety hardening (recall floor + deeper self-check).

## Gaps to close (priority)
1. Signed **recall / min-supported-version** field in `llms-install.md`, client-enforced (prereq for default apply).
2. Lightweight check path in `update.py` (spec-only, no wheel fetch).
3. Fetcher **timeout** + fail-open startup checker.
4. Deeper post-promote self-check (`ce doctor`) + auto-rollback.
5. `auto_update` config + onboarding answer (default `notify`) + local audit record.
6. Posture gate so startup checker is off in governed seats.

## Phasing
- **P0** (cheap): cached fail-open startup NOTICE; off in governed seats; opt-out. (gaps 2,6)
- **P1:** `auto_update` config + onboarding answer; `ce update --auto`; fetcher timeout; audit record.
- **P2** (req before default apply): signed recall/min-version floor + deeper self-check/auto-rollback.
- **P3:** converge solo toolchain pins into the signed release + fleet via fleet_rollout (one manifest, two rollout modes).

## OPEN OPERATOR DECISION
Is **`notify` default** acceptable, or does "updates shouldn't be left to the user" mean **`apply` default**? If apply-default → P2 (recall floor + deeper self-check) becomes a HARD prerequisite, not optional.
