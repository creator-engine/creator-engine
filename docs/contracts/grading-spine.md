# Contract: Spine-First Grading

Validator modules:
`creator_engine_validator.grading_spine`,
`creator_engine_validator.grading_policy`

## Purpose

Creator Engine grading is a stack. The deterministic spine is the
primary counting grader. A semantic grade is secondary and MUST NOT
count unless the spine verdict is green.

## Deterministic Spine

The spine verdict aggregates these deterministic signals:

| Signal | Required green condition |
|---|---|
| `ci_validators` | CI and validator result is green. |
| `ring1_refusal` | Ring-1/refusal gate did not block the change. |
| `require_carrier` | `--require-carrier` manifest and changelog carrier are present and valid. |
| `baseline_diff` | Baseline diff reports zero new failures. |
| `tests_build` | Required focused tests/build evidence is green. |

Missing required signals are red. Any red signal makes the spine
verdict red. Semantic or LLM-produced grades MAY be retained as
advisory evidence, but they have zero counting weight while the spine
is red.

## Mode Policy

The policy scaffold is keyed by `(run_mode, risk_tier,
available_model_diversity)`, where `run_mode` is one of `dev` or
`strangeLoop`. It selects reviewer-independence requirements only; it
does not merge, deploy, mutate settings, or actuate any privileged
operation.

`dev` mode keeps human opted-in review as the irreducible boundary.
Medium and higher risk require reviewer model separation from the
author model. High and critical risk add authorship obfuscation;
critical risk also requires an adversarial prompt.

`strangeLoop` mode treats review as delegated and requires the maximum
available model diversity. Medium and higher risk also require
authorship obfuscation and an adversarial prompt.

## Review Evidence Attestation

Review evidence records include:

- `reviewer_model`
- `authorship_obfuscated`
- `adversarial_prompt`

These fields are evidence attestations for mode-aware independence.
They are not normative upstream bindings to any product, provider,
account, runner, bot, or deployment harness.

## Approval Capability Binding

Approval capability `policy_sha` values used for this grading wall MUST
be derived from a canonical payload that includes the active `run_mode`
and `risk_tier`. A capability minted under a permissive mode or tier
therefore fails verification when replayed against a stricter mode or
tier because the verifier observes a `policy_mismatch`.
