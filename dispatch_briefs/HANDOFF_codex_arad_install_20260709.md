# HANDOFF — governed codex controller — Arad/Mythos CE 0.3.4 install — 2026-07-09

## Mission
Install CE **0.3.4** on Arad's machine and walk it to a verified first governed session.
Operator is PHYSICALLY PRESENT with Arad — this run doubles as the **Decision-15
Fresh-Tenant Rehearsal made live**: every stage produces evidence (format below). You are a
GOVERNED controller seat: Ring-1 hooks are active on you; act within this brief only.

## Machine + access
- Target: `aradsky-vostro-3400` = tailnet `100.74.214.78` (FQDN aradsky-vostro-3400.tail7370ba.ts.net),
  Ubuntu 24.04. SSH: `ssh aradsky@100.74.214.78` (key auth already registered from the 0.3.1 install).
- ⚠️ NOT a pristine machine: CE **0.3.1** was installed 2026-07-03 (signed install, live governed
  session ran) and her welcome package sits at `~/ce-welcome`. FIRST ACT = inventory: existing CE
  install location/version, `~/.ce-secrets` (HER App PEM — do not touch), repo checkout state of
  `chmod735-dor/mythos`. Decide upgrade-in-place vs clean per what `docs/install.sh` (0.3.4) supports;
  prefer the path the installer itself documents. Record the inventory as evidence stage 0.

## Identities (SSOT = ce-ops:infra/identity-registry.yaml — registry WINS over this brief)
- Arad's seat identity: **mythos-arad** App `4159494` / installation `142925881`, PEM in HER
  `~/.ce-secrets` — **her custody; never read, move, or copy it** (app-auth two-lane doctrine).
- Infra/adoption identity: **mythos-ce** App `4103119` / client `Iv23liuJp6OxfCWvwfSl` /
  installation `141552951` (per-ACCOUNT, covers all chmod735-dor repos). PEM (controller custody,
  on the DGX): `~/.ce-keys/mythos-ce.2026-06-20.private-key.pem`; env mirror `~/.ce-keys/mythos-ce-app.env`.
  If you must mint an installation token: stage PEM to /dev/shm, shred after. gh CLI cannot do
  App-JWT auth — use the HTTPS-Bearer flow.
- Org-scope credential: the **mythos-overwatch PAT** (in `~/.ce-keys/` on the DGX) is the ONLY
  standing credential for the chmod735-dor org. **NEVER use ce-overwatch / ce-dev-* / any ce-*
  fleet identity in the tenant org.**
- Repo: `chmod735-dor/mythos`. Branch protection UNENFORCED (free org) — **PRs-only discipline**;
  reviewer floor `aradSmith`. Her git pushes ride her own SSH key, not your credentials.

## Interaction doctrine (ratified)
- Arad = CEO-mode user. She supplies **intent and natural-language authorization**; agents drive
  every command. NEVER ask her to type a shell/ce command. The Operator relays her ratifications.
- User-facing vocabulary: Goal / Done-when / Change-type. No "bet", no "budget".

## Install path (canonical, verified on origin/main 2026-07-09)
1. Prereqs on her machine: git, curl, a coding-agent CLI available (check what's installed; Claude
   Code expected from the 0.3.1 session — verify, record version).
2. Install: signed one-liner `curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash`
   (user-local, sha256-verified, inventory-only) — or drive the agent-playbook path per
   `docs/llms-install.md` (same ceremony). Confirm installed version reports 0.3.4.
3. `ce doctor` — record output.
4. Onboard `chmod735-dor/mythos`: **KNOWN 0.3.4 GOTCHA** — `ce onboard` hard-requires the legacy
   `.hermes` gitignore entry (fix is creator-engine PR #918, merged to main AFTER the 0.3.4 cut,
   not in her wheel). When onboard refuses, add the single gitignore line it demands — expected,
   not breakage. NOTE: 0.3.4's refusal guidance may name a wrong bootstrap command (`ce init`);
   the working sequence if state-layout is the complaint: `ce brain init` creates `.ce/state/`.
5. First launch: `ce launch` with the **HOST backend** (the quickstart default). Do NOT attempt the
   contained backend — open bug ce-ops#490 (three stacked plan-time gaps on fresh tenants).
6. First-hour journey: her stating a Goal/Done-when, the governed session shaping it, her
   natural-language ratification. Record each step.

## Prior-failure history (what the evidence must prove is fixed)
- Send-1 failure: #494 — broken generated workflow at onboard.
- Send-2 failure: docs taught `ce inbox`, an unshipped verb (docs fixed on main via #906/#910;
  her INSTALLED 0.3.4 CLI has no `ce inbox` — do not use it, and flag any doc she sees that does).
- Adoption workflow template merge_group trigger: landed via #859 — VERIFY the 0.3.4-generated
  workflow includes `merge_group:` when onboard renders it; if absent, record it (wheel may predate).

## Evidence bundle (Decision 15 — this IS the rehearsal record)
Follow the evidence format at `deploy/rehearsal/evidence-format.md` (on main, PR #914). One JSON
record per stage (inventory, install, doctor, onboard, launch, first-journey), pass/fail + raw
output refs. Write locally during the run, then copy the bundle to
`/home/cedev2/creator-engine/.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/` and keep a
running status file at `/home/cedev2/creator-engine/.ce/state/research/ARAD_INSTALL_STATUS_20260709.md`
(update after EVERY stage — the persistent controller and Operator read it).

## Stop lines (absolute)
- You NEVER sign anything (no ce-root-v1, no release ops). No merge/approve/gate authority anywhere.
- No creator-engine repo pushes; product defects you hit get RECORDED in the status file (the
  persistent controller tickets them) — do NOT improvise product fixes on her machine.
- Her `~/.ce-secrets` and her App PEM are untouchable. No fleet credentials on her machine — ever.
- Any ambiguity or scope question → the Operator is standing right there: ASK HIM, then record his
  answer in the status file.
- If a stage hard-fails: capture evidence, mark the stage FAILED in the status file, STOP and
  surface to the Operator. A failed rehearsal is a VALID outcome — do not force a green.
