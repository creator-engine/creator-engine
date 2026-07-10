# BRIEF — dev-1 — 2026-07-08 — IaC singleton redeploy + Ring-1 launch-wired provenance (2 units)

Two units authorised by Operator decisions in `.ce/state/decisions/DECISIONS_20260708.md`.
Branch every unit off a fresh `git fetch origin && git checkout -b <branch> origin/main`.
Self-push lane: run FULL `ce validate-pr` green locally, then push, open a PR, and report
`READY <branch> <sha> PR#<n>` in the pane. Carrier slug must equal the branch name exactly.
Preflight is non-negotiable before every push — do not discover gates via CI.
Resource rules on VPS: serialise full suites; TMPDIR=$HOME/tmp; -n 4 pytest cap; clean pytest
temp dirs after each run.

---

## U1 — branch `ce-iac-singleton-redeploy` (work class: story) — Operator decision 1, 2026-07-08

**Substance.** Decision 1 of DECISIONS_20260708.md ratified the efficient-singleton design
on condition that a one-click IaC redeploy mechanism exists to recover a dead singleton
daemon from the VPS without manual steps. This is the hard PRECONDITION for arming any new
singleton authority. There is currently no such script. The queue daemon (ce-queue-daemon) is
the concrete singleton to cover first; the Option A materializer is the forward-looking second
target (stub only — it does not exist yet).

**Existing pattern to follow.** Deploy tooling is pure shell + systemd, no Terraform.
Canonical adapter: `deploy/daemons/run-daemon-container.sh`. Existing systemd unit:
`deploy/queue-daemon/ce-queue-daemon.service` (already installed on VPS under
`/etc/systemd/system/` with `Restart=always`, `RestartSec=5`, `User=ce-dev-1`,
`EnvironmentFile=/etc/creator-engine/ce-queue-daemon.env`). Install pattern exemplar:
`deploy/systemd/install-gate-daemons-systemd.sh`. Smoke pattern exemplar:
`deploy/daemons/smoke-daemon-container.sh`. Follow those conventions; do not invent a new
framework.

**Goal.** Create the following under `deploy/singleton-redeploy/`:

1. `redeploy-singleton.sh` — idempotent, shellcheck-clean bash script that:
   - Accepts `--daemon <name>` (required; supported values: `queue-daemon`, with
     `option-a-materializer` accepted but stubbed-out with a clear TODO and exit 0 in
     dry-run or a clear "not yet deployed" message in live mode).
   - Accepts `--dry-run` flag: prints every action it would take without executing any
     write or restart. Must not require root for dry-run.
   - Accepts `--repo-root <path>` (default: auto-resolved relative to the script, same
     pattern as `install-gate-daemons-systemd.sh`).
   - Accepts `--env-file <path>` (for queue-daemon: default `/etc/creator-engine/ce-queue-daemon.env`).
   - For `queue-daemon` (live mode):
     a. Verifies the env file exists (mode 0600) and fails closed if absent; prints a
        copy-pasteable remediation referencing `deploy/queue-daemon/RELOCATION.md`.
     b. Installs (or updates) the systemd unit from the checkout to `/etc/systemd/system/`
        using `install -m 0644`, skipping if unchanged (same `cmp -s` idiom used in the
        install exemplar).
     c. Runs `systemctl daemon-reload` then `systemctl enable --now ce-queue-daemon.service`.
        If the service was already active, uses `systemctl restart ce-queue-daemon.service`.
     d. Waits up to 30 s for the service to reach `active (running)` state, polling with
        `systemctl is-active`, then runs the health probe:
        `deploy/queue-daemon/launch-queue-daemon.sh --health`.
        Exits non-zero on any failure.
   - Uses `set -euo pipefail` and `die()` / `usage()` helpers consistent with the existing
     launcher scripts.
   - Requires `sudo` only for the actual write steps (install, daemon-reload, enable,
     restart); structure it so a passwordless-sudo operator can run it end-to-end in a
     single invocation.

2. `smoke-singleton-redeploy.sh` — host-operator smoke test that exercises the `--dry-run`
   path for `queue-daemon` without touching the live service. Must exit 0 when dry-run
   produces the expected output lines (grep for "Would install", "Would reload", etc.) and
   non-zero when a required env file path is passed that does not exist. This smoke is
   analogous to `deploy/daemons/smoke-daemon-container.sh` — self-contained, no external
   deps beyond what is already on the VPS. Also add a minimal `--help` assertion.

**Runbook doc.** Add `docs/operations/SINGLETON_DAEMON_REDEPLOY_RUNBOOK.md` containing:
- Purpose and scope (decision 1 rationale, singleton precondition).
- Prerequisites (env file, passwordless sudo, Docker on VPS).
- One-click redeploy procedure (copy-pasteable commands).
- Dry-run verification step.
- Smoke test invocation.
- Rollback note (pointing to `deploy/queue-daemon/RELOCATION.md` § "Rollback To DGX").
- Forward-looking section: Option A materializer placeholder with a note that the
  `--daemon option-a-materializer` stub will be fleshed out when that daemon is committed.
Public-docs lens: no internal topology identifiers (no host names, user names, tailnet IPs,
etc.) in the doc; use generic role labels (`VPS controller host`, `state root`, etc.).

**Artefacts.** Changelog fragment at `.ce/changelog/ce-iac-singleton-redeploy.md`. Carrier
at `.ce/pr-manifests/ce-iac-singleton-redeploy.md` (slug == branch). PR body must include:
- `- **Declared work class:** story`
- `Operator decision: decision 1, .ce/state/decisions/DECISIONS_20260708.md`
- Path manifest listing every new and modified path.

**Allowed paths (U1 only):**
- `deploy/singleton-redeploy/` (new directory; all files within)
- `docs/operations/SINGLETON_DAEMON_REDEPLOY_RUNBOOK.md` (new file)
- `.ce/changelog/ce-iac-singleton-redeploy.md`
- `.ce/pr-manifests/ce-iac-singleton-redeploy.md`

No changes to `deploy/queue-daemon/launch-queue-daemon.sh`, `deploy/daemons/run-daemon-container.sh`, any systemd unit file, or any file under `validators/`.

---

## U2 — branch `ce-ring1-launch-provenance` (work class: tiny) — Operator decision 4a, 2026-07-08

**Substance.** Decision 4a of DECISIONS_20260708.md authorises updating the harness matrix
launch-wired provenance for the codex Ring 1 row. Currently
`validators/creator_engine_validator/harness_matrix.py` (function `_codex_rows`, the
`_row("codex", "Ring 1", ...)` block) carries:

```python
launch_wired=_yellow("deferred pending containment acceptance; promotion evidence packet = ticket 480"),
```

The blocking condition has been resolved: containment acceptance was declared by Operator
decision 3 (C5 promotion) in the same DECISIONS_20260708.md file. This is a surgical
provenance update only — `live_proven` and `promotion_approved` remain RED and are not in
scope.

**Goal.** Make exactly the following targeted changes:

1. `validators/creator_engine_validator/harness_matrix.py` — in `_codex_rows`, update the
   codex Ring 1 `launch_wired` cell from `_yellow(...)` to `_green(...)` with a provenance
   string of the form:
   `"Operator-authorized pre-act: decision 4, DECISIONS_20260708.md; containment accepted per decision 3 (C5); promotion evidence packet still pending = ticket 480"`
   (exact wording is the seat's to finalise, but it must cite DECISIONS_20260708.md decisions 3 and 4, and retain the ticket 480 reference).

2. `validators/tests/unit/test_harness_matrix.py` — update
   `test_codex_ring0_is_full_but_ring1_waits_for_promotion_packet`: change the single
   assertion `ring1.cells["launch-wired"].value == hm.YELLOW` to `== hm.GREEN`. All other
   assertions in that test (live-proven=RED, promotion-approved=RED, gate_capable=GATE_NO,
   "ticket 480" in live-proven provenance) stay exactly as they are.

3. `docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md` — regenerate the rendered
   markdown from the updated matrix so `test_doc_is_rendered_from_the_matrix` stays green.
   Use whatever existing CLI or module path already renders this file (look for the
   `harness-matrix` subcommand in `ce_cli`/`v3_cli`, or call
   `creator_engine_validator.harness_matrix.render_markdown` directly). Do not hand-edit
   this file.

Run `pytest validators/tests/unit/test_harness_matrix.py -v` (and the full `ce validate-pr`
before push) to confirm all three tests pass: the updated Ring 1 assertion, the JSON-safe
payload test, and `test_doc_is_rendered_from_the_matrix`.

**Artefacts.** Changelog fragment at `.ce/changelog/ce-ring1-launch-provenance.md`. Carrier
at `.ce/pr-manifests/ce-ring1-launch-provenance.md` (slug == branch). PR body must include:
- `- **Declared work class:** tiny`
- `Operator-authorized: decision 4, DECISIONS_20260708.md`
- Path manifest listing every changed path (harness_matrix.py, test file,
  rendered doc, changelog, carrier).

**Allowed paths (U2 only):**
- `validators/creator_engine_validator/harness_matrix.py` (codex Ring 1 `launch_wired` cell in `_codex_rows` only)
- `validators/tests/unit/test_harness_matrix.py` (the single `hm.YELLOW` → `hm.GREEN` assertion in the Ring 1 test only)
- `docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md` (regenerated rendered output only; no hand edits)
- `.ce/changelog/ce-ring1-launch-provenance.md`
- `.ce/pr-manifests/ce-ring1-launch-provenance.md`

No changes to Ring 2, containment, any other harness row, or any file outside the above list.

---

## Standing preflight directive (ce-ops#303)

Run FULL `ce validate-pr` green locally before every push. Do not push to unblock a failing
gate; fix it or raise a BLOCKED line. VPS is non-contained, so do not use `--profile contained-seat`.

## Signal format

Report each unit on completion as:
`READY <branch> <full-head-sha> PR#<n>`

## BLOCKED line format

`BLOCKED <branch> <reason> — awaiting controller`

## STOP LINE

No gate acts, no signing, no approve, no merge, no scope creep beyond the named paths per
unit. U1 must not touch any Python under `validators/`. U2 must not alter `live_proven`,
`promotion_approved`, Ring 2, containment, or any other row. Both units: do not open PRs
against each other's branch, do not co-mingle commits. Each branch has exactly one PR.
