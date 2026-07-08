# PR path manifest - ce-docs-cli-parity

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-docs-cli-parity` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=29e075bab61493e56fd4d42ac9505611d77779f43c6f6378a0391f944be028c0

```text
.ce/changelog/ce-docs-cli-parity.md
.ce/pr-manifests/ce-docs-cli-parity.md
docs/guide/quickstart.md
docs/guide/welcome.md
docs/guide/zero-to-governed-seat-quickstart.md
```

## PR Body Evidence

Summary:
- Welcome is now orientation-only and points install-seekers to Quickstart.
- Quickstart now contains the install one-liner, install-handoff material, and
  first-run `ce onboard` step once.
- The governed-seat quickstart no longer instructs users to add the retired
  local-state gitignore entry.
- Depends on ce-hermes-retirement for the gitignore requirement removal; CI will
  verify compatibility.

CLI reference sweep:

```console
VERIFIED docs/guide/brain-ingest-refresh.md:16:`ce brain ingest` default. The default state root is `.ce/state`.
VERIFIED docs/guide/brain-ingest-refresh.md:23:`ce brain ingest`.
VERIFIED docs/guide/brain-ingest-refresh.md:5:It wraps the existing `ce brain ingest` command; it does not add a new gate,
VERIFIED docs/guide/complete-walkthrough.md:224:through the agent's normal terminal UI. When in doubt, run `ce drive --help` to
VERIFIED docs/guide/complete-walkthrough.md:244:**What you see.** A sample `ce report` render looks like:
VERIFIED docs/guide/complete-walkthrough.md:294:1. Launch your governed pane with `ce launch --backend host`.
VERIFIED docs/guide/complete-walkthrough.md:46:`ce onboard` checks the host, verifies the installed CE surface, initializes
VERIFIED docs/guide/contributing-to-ce.md:101:`ce validate-pr` is the canonical local preflight. It is a superset of the individual pytest and validator commands above, resolves the committed comparison base, and prints one final `GREEN` or `FAIL` summary (`docs/contracts/authoring-a-governed-pr.md:18-61`, `validators/creator_engine_validator/pr_preflight.py:175-180`). Use the single preflight as the final local evidence pass before push.
VERIFIED docs/guide/contributing-to-ce.md:106:If `ce validate-pr` or `ce brain verify`, `ce brain correct`, or `ce brain sync` refuses because the installed `creator-engine-validator` wheel is older than the source checkout, reinstall or update the wheel before treating the result as durable. For a deliberate one-off override, set `CE_ALLOW_STALE_WHEEL=1`; the literal value `1` is required, and CE logs that the command is proceeding by explicit override.
VERIFIED docs/guide/contributing-to-ce.md:157:- Paste validation evidence, including `ce validate-pr` and the focused local checks above when they apply.
VERIFIED docs/guide/first-value-mythos.md:100:2. `ce ratify` records the human-only front-gate digest.
VERIFIED docs/guide/first-value-mythos.md:101:3. `ce drive --spawn` launches the governed author seat.
VERIFIED docs/guide/first-value-mythos.md:102:4. `ce pr --apply` pushes the authored branch and opens the PR with the
VERIFIED docs/guide/first-value-mythos.md:104:5. `ce review --spawn` launches a distinct reviewer venue.
VERIFIED docs/guide/first-value-mythos.md:105:6. `ce collect` folds the reviewer run, then the author run, into runtime
VERIFIED docs/guide/first-value-mythos.md:107:7. `ce merge --apply` performs the gated merge.
VERIFIED docs/guide/first-value-mythos.md:108:8. `ce report` emits the completion report.
VERIFIED docs/guide/first-value-mythos.md:38:- Completion report rendered by `ce report`
VERIFIED docs/guide/first-value-mythos.md:57:Alternatively, provide an existing `ce pr --app-config` JSON:
VERIFIED docs/guide/first-value-mythos.md:99:1. `ce scope` files the first-value Scope.
VERIFIED docs/guide/onboarding-macos-container.md:175:working directory before your first `ce launch`; otherwise, `ce launch` refuses
VERIFIED docs/guide/onboarding-macos-container.md:188:If `ce onboard` reports RED-G-4 for an ungoverned state path, follow the
VERIFIED docs/guide/onboarding-macos-container.md:189:actionable guidance it prints: gitignore `.hermes/`, run `ce init`, then re-run
VERIFIED docs/guide/onboarding-macos-container.md:190:`ce onboard`.
VERIFIED docs/guide/onboarding-macos-container.md:198:`ce hud` is documented as an alias for the same launcher. The full governed
VERIFIED docs/guide/onboarding-macos-container.md:199:pilot path also documents `ce session` after its plan/apply setup, but the
VERIFIED docs/guide/onboarding-macos-container.md:200:solo container path should start with the everyday `ce launch` flow.
VERIFIED docs/guide/onboarding-macos-container.md:214:- `ce launch` spawns a Claude Code (`claude`) session, so that harness must be
VERIFIED docs/guide/pilot-runbook.md:113:`project.scaffold.kind: minimal` in the answers file. `ce install --plan` then
VERIFIED docs/guide/pilot-runbook.md:119:For an existing repo, `ce install --inventory` and `--plan` also report
VERIFIED docs/guide/pilot-runbook.md:157:`ce session` starts the governed launcher around your coding-agent terminal. The
VERIFIED docs/guide/pilot-runbook.md:171:   When the card reads **Ready ✓**, ratify the Scope: `ce ratify <scope>`.
VERIFIED docs/guide/pilot-runbook.md:172:3. **Build** — `ce drive <scope>` dispatches one governed, boxed run (the front
VERIFIED docs/guide/pilot-runbook.md:174:4. **Review** — read the **◆ CE Completion Report**: `ce report <scope>`:
VERIFIED docs/guide/pilot-runbook.md:193:`ce artifacts <run>` and `ce show <scope>` enumerate every artifact (PR · Scope ·
VERIFIED docs/guide/pilot-runbook.md:195:For the plain-language tour, run `ce guide`.
VERIFIED docs/guide/pilot-runbook.md:200:`ce install --spec llms-install.md --answers ce-install.answers.yaml --plan`,
VERIFIED docs/guide/pilot-runbook.md:207:Authorize the App when prompted, then run `ce session` from the repo terminal.
VERIFIED docs/guide/pilot-runbook.md:209:Build, review the PR in a distinct venue, and merge through `ce merge --apply`.
VERIFIED docs/guide/pilot-runbook.md:4:App, open a governed terminal session with `ce session`, file work as a Scope,
VERIFIED docs/guide/quickstart.md:57:`ce onboard` is the quick one-shot that gets you to a working governed session
VERIFIED docs/guide/quickstart.md:60:human-approved `ce install --plan` / `ce install --apply` flow covered in
VERIFIED docs/guide/solo-ceo-onboarding.md:125:> You can inspect any Scope before ratifying with `ce show <scope-id>`, and
VERIFIED docs/guide/solo-ceo-onboarding.md:126:> see what is queued with `ce status`.
VERIFIED docs/guide/solo-ceo-onboarding.md:220:3. **Ratify** — `ce ratify <id> --approver-ref 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef` — your "yes, build this."
VERIFIED docs/guide/solo-ceo-onboarding.md:223:6. **Gate the merge** — `ce merge <id> --run <run-id> --apply`.
VERIFIED docs/guide/solo-ceo-onboarding.md:224:7. **Read the report** — `ce report <id> --run-id <run-id>` — capture the evidence, move on.
VERIFIED docs/guide/solo-ceo-onboarding.md:238:| **Ratifying** the Scope (`ce ratify <id> --approver-ref 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef`) | Running the build inside the ratified envelope |
VERIFIED docs/guide/solo-ceo-onboarding.md:241:| The **gated merge** (`ce merge <id> --run <run-id> --apply`) | Opening the PR and reading the merge gate |
VERIFIED docs/guide/solo-ceo-onboarding.md:28:| **Shape** | You drive the Scope/Shape loop with `ce scope <id> --goal ... --change-type ...` and `ce shape <id>` — see [`solo-dev-onboarding.md`](./solo-dev-onboarding.md) | The agent drives the Scope/Shape loop; it assembles the Scope and presents it to you for review |
VERIFIED docs/guide/solo-ceo-onboarding.md:31:| **Ship** | You run `ce merge <id> --run <run-id> --apply` | Same — `ce merge <id> --run <run-id> --apply` is the human-gated finish |
VERIFIED docs/guide/solo-ceo-onboarding.md:44:first. Once installed, `ce launch --backend host` is your daily entry point.
VERIFIED docs/guide/solo-ceo-onboarding.md:49:`ce scope <id> --goal ... --change-type ...` and `ce shape <id>` yourself, you tell it *what you want to build*, in
VERIFIED docs/guide/solo-dev-onboarding.md:139:`ce onboard` is the quick first-run rail for getting a governed local session.
VERIFIED docs/guide/solo-dev-onboarding.md:20:2. Run `ce onboard`.
VERIFIED docs/guide/solo-dev-onboarding.md:22:4. Return later with `ce launch --backend host`.
VERIFIED docs/guide/solo-dev-onboarding.md:60:`ce onboard` performs the first-run sequence: it verifies the local install,
VERIFIED docs/guide/solo-dev-onboarding.md:72:`ce onboard` is a general recovery command for partially reused state.
VERIFIED docs/guide/solo-dev-onboarding.md:84:`ce launch --backend host` opens or attaches the visible governed terminal
VERIFIED docs/guide/understanding-ce.md:18:CE is CLI-anchored. The everyday path is `ce brain init` once, then
VERIFIED docs/guide/understanding-ce.md:19:`ce launch --backend host` to open your governed agent session. Contained launch
VERIFIED docs/guide/welcome.md:37:first `ce onboard` run, `ce launch` opens **your own coding agent in its normal
VERIFIED docs/guide/welcome.md:40:session, not a replacement for it. (`ce hud` is just another name for the same
VERIFIED docs/guide/zero-to-governed-seat-quickstart.md:38:`ce onboard` is the first CE command on a new host. It verifies the local
```

Mismatches: none.

Welcome restructure:
- Removed `origin/main:docs/guide/welcome.md` lines 64-177, the "Day One as a
  new user: install, launch, use it" block.
- Added the orientation pointer at `docs/guide/welcome.md` lines 64-70.
- Landed install and handoff material at `docs/guide/quickstart.md` lines
  13-62.
- Removed the retired gitignore prerequisite from
  `docs/guide/zero-to-governed-seat-quickstart.md` lines 7-10.

External heading links: checked with repository grep for `welcome.md#`,
`welcome#`, and the removed heading slug; no external links targeted the removed
heading.
