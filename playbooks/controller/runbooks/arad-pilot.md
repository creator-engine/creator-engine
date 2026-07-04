# Pilot Co-Drive Runbook

Durable, reusable procedure for taking a **new pilot user** from a cold machine
to their first governed, Operator-ratified PR. Written for the Arad pilot on
`chmod735-dor/mythos`, but the shape is repo-agnostic: swap the pilot repo, the
App env file, and the reviewer login and it drives the next pilot just the same.

> **Internal-only.** This runbook names internal mechanics (the pilot repo, the
> reviewer login, an App cred path). It lives in `playbooks/**`, which is NOT in
> the public-docs confidentiality scan surface (the guard scans `README.md` +
> `docs/**` only). It must never be relocated into `docs/**`. It references
> credentials by path/name only — never embed a token, PEM, or digest value.

## Roles

- **Pilot user** (e.g. Arad) — runs the self-serve install and the governed
  onboard on their own machine, sees the governance frame, and supplies nothing
  secret. The whole point is that the pilot does the visible work themselves.
- **Operator** — the human who holds the ratification flip. The only irreducible
  Operator gesture in the whole sequence is supplying the approver-ref for the
  first live PR (see Phase 3). Everything else is build-and-arm.
- **Controller** — preps the host (cred placement, workdir, seat env), watches
  the spawned venues during the live run, and never substitutes its own judgment
  for the Operator's ratification gesture.

## What the pilot needs

- A coding agent they already use (Claude Code or Codex) — CE governs *their*
  agent, it does not replace it.
- A GitHub repository CE will drive work on (the pilot repo). For the Arad pilot
  the App is already provisioned on `chmod735-dor/mythos`.
- Permission to install dependencies (sudo) and to authorize a GitHub App.

---

## Phase 1 — Self-serve install (pilot runs this)

The pilot installs CE themselves from the signed one-liner. This is confirmed
current and safe (four-way artifact hash match incl. the release-artifact parity
guard).

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
source ~/.profile
command -v ce      # must resolve — this is the PATH check; do not proceed until it does
```

If `command -v ce` does not resolve after sourcing the profile, the install did
not land `ce` on PATH; stop and fix PATH before any onboard step.

---

## Phase 2 — Self-serve governed onboard (pilot runs this; sees governance)

Still the pilot, on their own machine. This is where the pilot first *sees* the
governance frame — provenance verification and a governed plan they approve.

```bash
ce verify-install     # provenance: confirms the installed CE matches signed artifacts
ce onboard            # governed onboarding plan the pilot reviews and approves
```

> User-facing commands are `ce …`. `ce verify-install` and `ce onboard` are the
> real kernel commands for this pilot path; do not ask a pilot to use legacy
> version-stamped commands.

---

## Phase 3 — Operator co-drives the live first PR

This is the co-drive: the controller has armed the host, the pilot's CE is
installed and onboarded, and the Operator now supplies the one human gesture
that turns the first governed PR live.

### 3a. Pre-session ops prep (controller, before the Operator joins)

Build-and-arm everything so the live run blocks only on the Operator's
approver-ref. None of these are secret values written into this doc — they are
host-local placements the controller performs:

- **App PEM** at `/dev/shm/mythos-ce-app.pem` — tmpfs, so it does **not** survive
  a reboot. Re-place it if the host rebooted since last session.
- **`MYTHOS_CE_WORKDIR`** — the cloned pilot-repo checkout the script drives.
- **`MYTHOS_CE_SEAT_ENV_FILE`** — the reviewer-seat env file.
- App identity for the live run comes from the App env file, sourced (not
  embedded) at run time:

  ```bash
  set -a; source ~/.ce-keys/mythos-ce-app.env; set +a
  ```

  That env file supplies the repo, installation id, client id, and PEM path. The
  script never prints PATs, PEM contents, or secret values, and exits before the
  first mutating command if a required live value is absent or malformed.

### 3b. Dry run (credential-free, mutation-free)

Always dry-run first when changing the target checkout, scope id, branch, or
manifest path:

```bash
bash scripts/first-value.sh --dry-run
```

This prints the full 8-step governed command plan and the expected evidence for
each step (Scope record, ratification fields, author dispatch, target PR +
manifest, reviewer dispatch + authority envelope, runtime evidence chains, merge
evidence, completion report).

### 3c. Live run (the Operator gesture)

```bash
set -a; source ~/.ce-keys/mythos-ce-app.env; set +a
bash scripts/first-value.sh
```

The **only irreducible Operator gesture** is supplying `MYTHOS_CE_APPROVER_REF`:
a value-free 64-hex ratification digest the Operator generates fresh —

```bash
openssl rand -hex 32
```

It is the human-holds-the-flip gesture (it ratifies; it carries no secret
content). It is distinct from the reviewer identity:

- **Reviewer** = `ubuntuaws745-cmyk` — the distinct human-review login.
- **Merging App-bot** = `mythos-ce[bot]` — the App identity that performs the
  gated merge. The reviewer and the merging bot are deliberately different
  identities; never collapse them.

The script then runs the canonical governed sequence in order: `ce scope` ->
`ce ratify` (records the approver-ref) -> `ce drive --spawn` (author seat) ->
`ce pr --apply` (push branch + open PR with the declared manifest) ->
`ce review --spawn` (distinct reviewer venue) -> `ce collect` (fold reviewer
then author runs into runtime evidence) -> `ce merge --apply` (gated merge) ->
`ce report` (completion report).

The controller watches the spawned venues and confirms the pilot repo's manifest
path matches the actual first-value PR diff before the merge step lands.

---

## Reuse for the next pilot

To drive a different pilot user/repo, change only:

1. the **pilot repo** (`MYTHOS_CE_REPO` / installation id in the App env file);
2. the **App env file** path you source (`~/.ce-keys/<pilot>-ce-app.env`);
3. the **reviewer login** supplied as the reviewer actor;
4. the **workdir / seat env** placements in 3a.

Phases 1 and 2 are identical for every pilot — they are the product's self-serve
path. Phase 3's only human-irreducible step is, and remains, the Operator's
fresh approver-ref.
