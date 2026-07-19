---
kind: decision-record
record_type: adr
schema_version: "1"
id: DEC-0017
title: "MC1 docs_envelope arming: arm the pre-delegated docs-envelope merge tier under ADR-0016"
status: accepted
date: "2026-07-19"
decision_makers: ["chmod735 (Operator)"]
consulted: ["delegated-operator controller"]
informed: []
review_by: "2026-10-19"
mutation_class: governance
evidence_refs:
  - kind: adr
    ref: "docs/decisions/ADR-0016-pre-delegated-merge-classes.md — MC1 predicate set (§2), tier arming via governance PR (§2.d), kill-switch contract (§2.d), rollout Phase 2 conditions (§5)"
    tag: adr-0016
  - kind: code
    ref: "deploy/automerge/policy-declaration.yaml — governed source for .ce/state/automerge/policy.json; sets run_mode=ceo, docs class true, docs_envelope tier true"
    tag: policy-declaration
  - kind: code
    ref: "deploy/automerge/materialize-automerge-policy.py — fail-closed materializer script; validates declaration and writes policy state atomically"
    tag: materializer-script
  - kind: pr
    ref: "PR #1041 (ce-619) — docs_envelope file-extension allow-list: non-markdown executables removed from MC1 qualifying path set"
    tag: pr-1041-ce-619
  - kind: pr
    ref: "PR #1043 (ce-621) — docs/decisions/**, docs/adr/**, docs/governance/** classified as governance class, blocking ADR records from zero-gesture merge"
    tag: pr-1043-ce-621
  - kind: code
    ref: "validators/creator_engine_validator/forge/automerge_policy.py — AUTOMERGE_ARMING_RUN_MODES, _AUTOMERGE_TIERS, AutoMergePolicyState (class_flag, tier_flag), save_automerge_policy_state, automerge_policy_state_path"
    tag: automerge-policy-engine
  - kind: code
    ref: "validators/creator_engine_validator/forge/automerge_actuator.py — dual-layer kill-switch re-verification, live policy reload before actuation"
    tag: automerge-actuator
ratification:
  ratified_by: "chmod735"
  ratified_at: "2026-07-19"
  ratification_prompt_sha: "d99b5dea8268df79e9c95e8a550b20fabae73a1c7ffe68299b43a1eeff5bb0f8"
  quorum: n1_solo
---

# MC1 docs_envelope arming

## 1. Decision

MC1 (`docs_envelope`) is hereby armed under the authority granted by
ADR-0016's Operator ratification on 2026-07-19
(ratification_prompt_sha
`d99b5dea8268df79e9c95e8a550b20fabae73a1c7ffe68299b43a1eeff5bb0f8`).

The governed policy materialization is created in this PR:

- `deploy/automerge/policy-declaration.yaml` — single governed source for
  `.ce/state/automerge/policy.json`; sets `run_mode: ceo`,
  `classes.docs.auto_merge: true`, `tiers.docs_envelope.auto_merge: true`,
  all other mutation classes and tiers `false`, and
  `enabling_decision_ref` citing this ADR-0016 ratification.
- `deploy/automerge/materialize-automerge-policy.py` — fail-closed
  deployment script that reads the declaration, validates it strictly, and
  writes the state atomically via `save_automerge_policy_state`.

No direct edit of `.ce/state/automerge/policy.json` is authorized (ADR-0016 §2.d).

## 2. Prerequisites satisfied

The two prerequisites required before arming MC1 (ADR-0016 §5 Phase 2)
are both merged:

| PR | Branch slug | Effect |
|---|---|---|
| PR #1041 | `ce-619-docs-envelope-allowlist` | File-extension allow-list on `docs/**` paths: non-markdown executables (`*.py`, `*.sh`, YAML, Makefile) no longer qualify for the docs_envelope tier, closing the residual risk identified in ADR-0016 §7 Class 1 threat table. |
| PR #1043 | `ce-621-decisions-governance-class` | `docs/decisions/**`, `docs/adr/**`, `docs/governance/**` reclassified from `docs` to `governance` mutation class. ADR records now route to GESTURE regardless of tier flags (ADR-0016 §8 non-goal 8). |

## 3. What changes at actuation time

After the controller runs the materializer (`python3
deploy/automerge/materialize-automerge-policy.py --repo-root <root>`),
the automerge decision engine will:

1. Return `AUTO` for a qualifying `docs_envelope` PR when all predicates
   P1–P15 (ADR-0016 §2.b) are simultaneously satisfied.
2. Require the fresh-context Key-2 reviewer subagent for every MC1 PR
   (P7, P8). What is removed is the post-approval merge trigger only.
3. Re-verify the live policy kill switch before actuation (fail-closed).

The activation procedure is:

1. Merge this PR.
2. Controller runs the materializer on the live host:
   `python3 deploy/automerge/materialize-automerge-policy.py --repo-root <root>`
3. Verify effective state: `ce automerge-status`.
4. Process the first zero-gesture docs-envelope PR through the full
   predicate set; inspect the decision JSON in
   `.ce/state/automerge/decisions/`.
5. Conduct kill-switch drill: `ce automerge-kill-switch on` then
   `ce automerge-kill-switch off`; verify GESTURE is returned during
   the on window.

## 4. Defense-in-depth hardening

Additional actuator hardening (fail-closed path predicate re-verification
at actuation time for the docs_envelope tier) is tracked as a
follow-up. See: tracked actuator hardening follow-up.

The hardening work does not block this arming decision; the existing
dual-layer kill-switch re-verification in `automerge_actuator.py` provides
defense in depth until the follow-up ships.

## 5. Disarm paths

**Per-tier disarm via governance PR:**

Update `deploy/automerge/policy-declaration.yaml` to set
`tiers.docs_envelope.auto_merge: false`, then re-materialize. This is a
governance-class two-key PR (ADR-0016 §2.d).

**Global kill switch (immediate, no PR required):**

```bash
ce automerge-kill-switch on
```

Implemented in `ce_cli.py:_automerge_kill_switch`; reads and writes
`.ce/state/automerge/policy.json` directly. Takes effect before the next
actuation cycle; the actuator re-reads the live policy state before every
actuation.

## 6. Authority summary

| Role | Authority |
|---|---|
| Operator | Ratified ADR-0016 (2026-07-19); ratified this arming decision; may arm or disarm the global kill switch at any time |
| Controller | Maintains Key 1 (byte-verify + non-author approval); dispatches Key-2 reviewer for every MC1 PR; runs the materializer after merge |
| Queue daemon | Actuates enqueue only; never approves; never extends authority beyond the predicate set |
| Machine predicate | Verifies P1–P15 at decision time; re-verifies kill switch and path predicate at actuation time |
