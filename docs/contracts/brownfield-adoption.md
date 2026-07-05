# Contract: Brownfield Project Adoption (E3)

> **Not the same as joining an already-CE repo.** Brownfield *adoption* takes a
> **non-CE** project into CE via a governance **join PR** (the E3 adoption-apply
> layer) — gated default-OFF behind a dual ENV escalation (see *Apply*
> below); unauthorized, it stays deferred. A new dev joining a repo that is
> **already** CE-governed is a *plain-join* (E2, auto-detected) — see
> `plain-join.md`. `install --apply` auto-detects already-CE and
> routes to plain-join; only an existing repo that is **not** already-CE reaches
> the brownfield adoption path described here.

## Purpose

Brownfield adoption lets `ce install` connect CE to an existing project without
forking the installer engine or adding a second apply path. The same loop stays
load-bearing:

```bash
ce install --spec llms-install.md --inventory
# prepare ce-install.answers.yaml with the operator
ce install --spec llms-install.md --answers ce-install.answers.yaml --plan
ce install --spec llms-install.md --answers ce-install.answers.yaml --apply
```

`--inventory` and `--plan` are read-only. They inspect source-controlled project
metadata, produce value-free summaries, and emit an E2 handoff plan. They do not
write files, run scanners, call GitHub mutation APIs, rewrite history, delete
branches, or weaken protections.

## Inventory

The brownfield inputs live in `schemas/install-answers.schema.yaml` under the
single operator inventory as exactly these step-5 rows:

- `brownfield.enabled`
- `brownfield.project_root`
- `brownfield.inventory_depth`
- `brownfield.ci.adopt_existing_workflows`
- `brownfield.ci.required_checks_strategy`
- `brownfield.tests.required_commands`
- `brownfield.history.mode`
- `brownfield.conventions.branch_pattern`
- `brownfield.conventions.commit_style`
- `brownfield.secrets.preflight`
- `brownfield.secrets.waivers`

Detected facts use the existing precedence rule:
`interactive > answers-file > detected > default`. A file value that contradicts
detected reality is a conflict and refuses non-interactive mode until the
operator resolves it.

## Plan

`ce install --plan` adds `brownfield_adoption` to the JSON payload. It includes:

- a canonical value-free `inventory_sha256`;
- existing workflows and checks to preserve;
- the CE validate check as an additive check when missing;
- detected test commands, or an empty list when unknown;
- history mode and value-free history summaries;
- advisory branch and commit conventions;
- a secrets-scrub preflight plan;
- a first Scope seed and two project skill artifacts;
- ordered E2 apply step descriptors.

The project skill artifact paths are:

- `.ce/skills/project-conventions.md`
- `.ce/skills/project-validation.md`

The first Scope seed references those paths through `skill_refs` and binds to
the inventory hash. It is a seed only; normal Scope ratification still happens
through the existing Scope flow.

## Refusals

Normal adoption blocks when:

- no Git history is present (`needs_baseline_capture`);
- tracked working-tree changes make the inventory stale (`blocked_dirty_tree`);
- a required secrets scanner is known unavailable;
- scanner findings are unwaived;
- a waiver lacks `{ratified_prompt_sha, approver_ref, educate_acknowledged: true}`;
- detected-vs-file conflicts remain unresolved;
- the plan would drop existing workflows, checks, reviewers, or protections.

No synthetic history is generated. History rewrite, force push, branch deletion,
workflow deletion, check removal, raw secret persistence, and branch-protection
weakening are outside this gate.

## Apply — the governance join PR (E3 adoption-apply)

Brownfield apply is the **join-PR layer**: it extends E2's `onboard_apply` leg
pipeline (it is **not** a second executor) with seven mode-gated adoption legs
that convert the `brownfield_deferred` refuse — for a genuine non-CE repo — into a
**non-destructive governance join PR** (a feature branch carrying the CE scaffold +
a real PR against the repo's default branch). It never direct-pushes the default
branch, never force-pushes, never mutates branch protection, and is idempotent
(a re-run reconciles to the same stable branch + the same PR).

The adoption legs (the canonical `BROWNFIELD_APPLY_STEP_IDS`):

1. `brownfield_inventory_drift_check` — recompute the inventory hash over a fresh
   read-only inventory and compare to the plan's `inventory_sha256`; mismatch
   refuses `brownfield_inventory_drift`.
2. `brownfield_secret_preflight` — the **hard, affirmatively fail-closed** scrub
   (see below).
3. `brownfield_build_scaffold` — local checkout → on a stable adoption branch
   write the value-free scaffold (`.ce/skills/*`, the scope seed, and
   `.github/workflows/ce-validate.yml` at the pinned digest) → local commit.
4. `brownfield_push_branch` — push the adoption branch via `forge.push_change`
   (never force; a non-fast-forward refuses `brownfield_push_refused`).
5. `brownfield_open_join_pr` — open exactly one PR via `forge.open_change`
   (idempotent — a re-run claims the existing PR).
6. `brownfield_verify_preserved_checks` — read the live checks and confirm the
   join PR drops none (`brownfield_protection_loss` otherwise).
7. `brownfield_record_apply_evidence` — append the value-free adoption record.

### Authorization (default-OFF, dual escalation)

The adoption **write** path is a real authority escalation beyond the zero-write
plain-join posture, so it is gated behind **two** explicit, default-OFF, host
ENV flags (not answers-schema keys — no ce-root-v1 re-sign cascade):
`CE_FORGE_LIVE_FORGE=1` **and** `CE_FORGE_ADOPTION_WRITE=1`. With either absent,
`install --apply` keeps today's `e2_brownfield_seam_unavailable` refuse byte for
byte (status quo). No auto-merge: the PR is opened and the run stops (a human
merges). Live runs are the VPS Mode-A rehearsal only.

### Two-token model

Reads and writes ride **separate** least-privilege installation tokens:

- **READ token** (the inherited Phase-1 ceiling `{metadata:read, contents:read,
  administration:read}`, no escalation) serves the drift check, the scrub, the
  local clone, and the preserved-checks read (`administration:read` gates the
  branch-protection read).
- **WRITE token** (`{metadata:read, contents:write, workflows:write,
  pull_requests:write}`, binding the `(contents,write)`+`(workflows,write)`
  Tier-2 escalation; `pull_requests:write` is Tier-3 baseline) is minted for the
  push + open-PR legs **only** and **revoked immediately after**.
  `administration:write` is deliberately excluded — branch protection is never
  mutated (the PR body only *recommends* the union).

### Secrets scrub — affirmatively fail-closed

The `brownfield_secret_preflight` leg requires an **affirmative** zero-exit **and**
a parsed empty-findings list from **both** sha256-pinned scanners (Gitleaks **and**
TruffleHog). The absence of parsed findings is **not** clean: any finding, scanner
non-zero exit, exec error, timeout, unparseable output, or a missing scanner
report raises `ApplyRefused` (`brownfield_secret_findings` /
`brownfield_secret_scanner_unavailable`) **before** any branch is built, pushed, or
PR'd. A finding passes only with a complete ratified per-finding waiver. Scanner
reports and waiver ids are value-free (no secret value is ever printed, stored, or
copied into an artifact/PR).

The live scrub surface is the full mutation surface declared by the plan:
`[".", *scaffold_paths]`. Before invoking pinned scanners, the driver materializes a
temporary scan tree from the existing checkout and overlays every scaffold artifact
that `brownfield_build_scaffold` would commit. The original tree is not mutated, and
scanner clean means pre-existing bytes plus scaffold bytes are clean.

Live Mode-A scanner binaries are supplied by sha256-pinned host configuration, not
by committing unverified binaries. `resolve_live_config` reads
`CE_FORGE_GITLEAKS_URL` + `CE_FORGE_GITLEAKS_SHA256` and
`CE_FORGE_TRUFFLEHOG_URL` + `CE_FORGE_TRUFFLEHOG_SHA256` (optional version labels:
`CE_FORGE_GITLEAKS_VERSION`, `CE_FORGE_TRUFFLEHOG_VERSION`) and threads them into
the adoption driver. Missing, partial, or invalid pins keep the default live scrub
fail-closed (`ran: false`) until the VPS rehearsal supplies verified pins.
