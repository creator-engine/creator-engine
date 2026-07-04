# First Value On chmod735-dor/mythos

This guide is the worked first-value path for the pilot repo
`chmod735-dor/mythos`. It uses [`scripts/first-value.sh`](../../scripts/first-value.sh)
as a thin driver around the canonical governed sequence:

```text
ce scope -> ce ratify <scope> -> ce drive <scope> --spawn
-> ce pr ... --apply -> ce review ... --spawn -> ce collect ...
-> ce merge ... --apply -> ce report ...
```

The bootstrap README, App installation, CI setup, and initial branch are
onboarding evidence only. First value is the first post-scaffold governed PR
that is opened through the forge leg, independently reviewed, collected into
runtime evidence, merged through the gated merge path, and summarized in a
completion report.

## Dry Run

Dry-run mode is credential-free and mutation-free:

```bash
bash scripts/first-value.sh --dry-run
```

The output prints the full governed command plan for the default repo
`chmod735-dor/mythos` and installation id `141552951`. It also names the expected
evidence for each step:

- Scope record under `.ce/state/scopes/`
- Ratification fields on the Scope record
- Author dispatch record under `.ce/state/dispatches/`
- Target PR plus declared manifest paths
- Reviewer dispatch and reviewer authority envelope
- Runtime evidence chains under `.ce/state/runs/`
- Merge evidence appended to the author runtime evidence chain
- Completion report rendered by `ce report`

Use dry-run first whenever changing the target checkout, scope id, branch, or
manifest path.

## Live Configuration

Live mode reads host-local configuration from environment variables and, when
present, an env file such as `~/.ce-keys/mythos-ce-app.env`.

Minimum App identity keys:

```bash
MYTHOS_CE_REPO=chmod735-dor/mythos
MYTHOS_CE_INSTALLATION_ID=141552951
MYTHOS_CE_CLIENT_ID=<github-app-client-id>
MYTHOS_CE_PEM_PATH=/path/to/app-private-key.pem
```

Alternatively, provide an existing `ce pr --app-config` JSON:

```bash
MYTHOS_CE_APP_CONFIG=/path/to/mythos-app-config.json
```

The script never embeds or prints PATs, PEM contents, or secret values. If a
required live value is absent, malformed, or points at a missing file, it exits
before the first mutating command.

Live runs also need first-value governance inputs that cannot be guessed:

```bash
MYTHOS_CE_APPROVER_REF=<64-hex-value-free-human-ratifier-digest>
MYTHOS_CE_REVIEWER_ACTOR=<distinct-reviewer-login>
MYTHOS_CE_WORKDIR=/path/to/chmod735-dor/mythos-checkout
```

Optional live inputs:

```bash
MYTHOS_CE_SCOPE_ID=first-value-mythos
MYTHOS_CE_AUTHOR_BRANCH=ce-first-value-mythos
MYTHOS_CE_MANIFEST_PATHS=.ce/pr-manifests/ce-first-value-mythos.md
MYTHOS_CE_VENUE_ROOT=$HOME/.ce/venues/mythos
MYTHOS_CE_LEDGER_ROOT=$HOME/.ce/active-work
MYTHOS_CE_SEAT_ENV_FILE=/path/to/reviewer-seat.env
```

## Live Run

From this repository, point the script at the Mythos checkout:

```bash
bash scripts/first-value.sh \
  --workdir /path/to/chmod735-dor/mythos \
  --approver-ref "$MYTHOS_CE_APPROVER_REF" \
  --reviewer-actor "$MYTHOS_CE_REVIEWER_ACTOR"
```

The live path runs the commands in this order:

1. `ce scope` files the first-value Scope.
2. `ce ratify` records the human-only front-gate digest.
3. `ce drive --spawn` launches the governed author seat.
4. `ce pr --apply` pushes the authored branch and opens the PR with the
   declared manifest path.
5. `ce review --spawn` launches a distinct reviewer venue.
6. `ce collect` folds the reviewer run, then the author run, into runtime
   evidence.
7. `ce merge --apply` performs the gated merge.
8. `ce report` emits the completion report.

The controller remains responsible for supplying the live Mythos credentials,
watching the spawned venues, and confirming that the target repo's manifest path
matches the actual first-value PR diff.
