# Seat-Side Preflight Design

Status: design-only

## Purpose

Prevent governed seats from handing off stale generated reference artifacts or
malformed PR carriers. Focused author checks and repair tools may run before
push, while the required Validate check on the pushed current head remains the
authoritative validation gate.

The check is a prevention layer in the author loop. It does not replace CI,
review, path-manifest enforcement, or controller harvest. It moves the first
failure point to the seat, while the seat still owns the worktree and can make
the smallest repair.

## Existing Failure Mode

Governed PRs already have downstream checks for generated CLI/schema reference
freshness, declared work class, changelog presence, and path-manifest fidelity.
Those checks are too late for contained seat harvest when the seat emits READY
before it has:

- regenerated checked-in reference docs after changing a registered generated
  surface;
- authored a carrier whose authorized path set matches the real diff;
- included the carrier itself in the authorized path set;
- included the changelog fragment;
- emitted the canonical declared-work-class line in the PR body or carrier.

When any of those are missing, harvest has to do author repair work. That
confuses ownership: controller harvest should collect and route evidence, not
rewrite the seat's deliverable.

## Non-Goals

- No implementation in this design unit.
- No new approval, merge, enqueue, release-signing, or gate authority.
- No bypass of CI or reviewer checks.
- No hand-edited alternate carrier format.
- No replacement for `verify-path-manifest`, autogen sync checks, or public-docs
  confidentiality scanning.
- No exposure of internal host topology, seat identifiers, or local operational
  paths in public-facing documentation.

## Scope

The seat-side preflight applies to implementation seats and other write-capable
authoring lanes that are expected to self-push a governed PR branch. Read-only
review or verification lanes may run the same checks for evidence, but they do
not repair or push.

The source of truth is committed branch state compared to the resolved PR base.
Working-tree-only edits are not READY material. A seat may run focused checks or
an optional full diagnostic while dirty, but gate evidence is the required
Validate result bound to the exact pushed head.

## Validation Contract

### Carrier Shape Versus Real Diff

The preflight validates the branch's per-PR carrier at
`.ce/pr-manifests/<branch-slug>.md` against the actual `base..HEAD` path set.
It must reuse the same canonicalization as the existing path-manifest verifier:

```text
sha256("\n".join(sorted(unique_paths)) + "\n")
```

Required carrier properties:

- The carrier slug equals the branch slug.
- The fenced path list equals the real `base..HEAD` changed path set.
- The list includes `.ce/pr-manifests/<branch-slug>.md` itself.
- The list includes `.ce/changelog/<branch-slug>.md`.
- `AUTHORIZED_PATHS_COUNT` equals the number of sorted unique authorized paths.
- `AUTHORIZED_PATHS_SHA256` equals the canonical digest for that exact set.
- The carrier is parseable by the existing path-manifest parser.

If the carrier is absent, malformed, non-self-inclusive, missing its changelog
fragment, or out of sync with the diff, the seat must regenerate the carrier
using repo-native tooling and recommit before READY.

### Changelog Presence

Every governed PR must carry one changelog fragment at:

```text
.ce/changelog/<branch-slug>.md
```

The preflight treats a missing changelog as a blocking authoring error. It does
not infer that an empty or unrelated changelog is acceptable merely because a
path exists; the fragment must be part of the authorized path set and belong to
the same branch slug.

### Declared Work Class

The PR body or carrier input must contain exactly one canonical declared work
class line:

```text
- **Declared work class:** <class>
```

The accepted canonical vocabulary is:

```text
XS, S, M, L
```

Legacy aliases may be accepted only as input compatibility when existing
validator policy allows them, but the seat-ready artifact should emit the
canonical form. Free-form frontmatter such as `work_class: honest`, prose-only
claims, or multiple conflicting declarations fail closed.

### Autogen Freshness

Generated reference artifacts are checked artifacts. Current registered
generators include:

| Registered surface | Generator | Checked artifact |
| --- | --- | --- |
| CLI reference | `scripts/gen_cli_reference.py --write` | `.ce/reference/cli.generated.md` |
| Schema reference | `scripts/gen_schema_reference.py --write` | `.ce/reference/schemas.generated.md` |

The seat-side preflight must reuse the existing registered freshness checks for
source-surface detection. For the current generators, the profile invokes
`cli_reference_autogen_sync` and `schema_reference_autogen_sync`; it does not
reimplement a separate CLI or schema surface matcher. Those checks own the
source surface rules for CLI command surfaces, validator CLI help text, schema
files, and schema-producing code that can affect the rendered references. When
such a surface changes, the seat-side repair path runs the corresponding
generator with `--write`, stages the generated artifact if it changed, and
recommits before the final READY pass.

The final pass then verifies byte parity by running the registered freshness
checks, not by trusting timestamps. If a generator itself changes, its checked
artifact is treated as suspect and must be regenerated or verified.

Future generators should register the same contract:

- a stable check name;
- a deterministic source-surface matcher;
- a deterministic `--write` repair command;
- a checked artifact path or path set;
- a read-only verify mode used by CI and, optionally, `ce validate-pr`;
- an allow-list decision for public-docs confidentiality scanning.

The seat-side preflight should iterate the registry instead of hard-coding only
the two current artifacts once a registry exists. Until then, the two current
generators are mandatory special cases.

### Public-Docs Lens

Any docs produced or changed by seat repair must remain safe for the intended
audience. Public-facing docs use generic placeholders, role names, and product
concepts. They must not disclose internal hostnames, local account names,
private operational topology, unredacted issue-harvest details, credentials,
tokens, or seat-specific filesystem paths.

The seat-side preflight must run the same public-docs confidentiality scanner
used by the final PR preflight. A failure blocks READY and is repaired by
rewriting the document through the public lens.

## Execution Model

Two command shapes are plausible:

| Option | Shape | Strengths | Weaknesses |
| --- | --- | --- | --- |
| Validate-pr profile | `ce validate-pr --profile seat-ready` | Reuses existing diagnostics, base resolution, work-class parsing, path-manifest checks, autogen checks, and public-docs scanner. | A full local run is expensive and cannot become progression or gate evidence. |

Recommendation: keep `ce validate-pr --profile seat-ready` as an optional
diagnostic, not a READY prerequisite. Authoring automation should invoke the
focused carrier, autogen, work-class, and confidentiality checks it can repair;
the pushed current-head required Validate check remains authoritative.

`seat-ready` is a new successor profile, not a mutation of the existing
`contained-seat` profile. The legacy `contained-seat` profile continues to serve
the harvest-side-carrier flow and may continue to tolerate
`path_manifest_carrier_required` because those carriers are generated after the
seat exits. `seat-ready` is for branches whose authoring seat owns the changelog
and carrier before READY, so it must enforce carrier presence, carrier
self-inclusion, changelog inclusion, digest fidelity, declared work class,
registered autogen freshness, and public-docs confidentiality. This separation
keeps existing harvest-side-carrier users working while giving seat-authored
carriers a fail-closed profile.

## Seat Author Loop

The expected write-capable seat loop is:

1. Build and commit the assigned change inside the allocated worktree.
2. Run any focused tests or docs checks needed for the changed files.
3. Regenerate registered autogen artifacts when touched source surfaces require
   them.
4. Generate the changelog and path-manifest carrier with repo-native tooling.
5. Commit all intended READY artifacts.
6. Optionally run the seat-ready `ce validate-pr` profile as a diagnostic.
7. Push the committed current head and wait for its required Validate result.
8. Repair any failure, regenerate the carrier if the path set changed, recommit,
   push the new head, and wait for the new head's required Validate result.

The seat must not signal READY based on a dirty worktree, an uncommitted carrier
repair, or a local full-suite transcript. READY evidence names the pushed head
SHA and required Validate run URL/status for that exact head.

## Fail-Closed Semantics

Focused author checks fail closed for the artifact they inspect, while only the
required current-head Validate result is load-bearing progression evidence:

- PASS from a local check means only that its focused obligation passed; it is
  optional iteration evidence, not a merge gate.
- FAIL means repair the named obligation before treating the artifact as ready.
- ENV-SKIP is introduced by the implementation slice as an explicit
  classification for checks the host environment cannot run. Carrier fidelity,
  changelog presence, declared work class, registered autogen freshness, and
  confidentiality checks are not optional skips.
- TOOLING ERROR in a focused artifact check is treated as FAIL for that
  obligation. Failure or unavailability of the optional full profile does not,
  by itself, block READY; report it only as diagnostic evidence.

Self-repair happens before push and before READY. Controller harvest does not
repair a stale autogen artifact, missing changelog, malformed carrier, missing
digest block, non-self-inclusive manifest, or invalid work-class declaration.

## Host Resource Rules

An optional full-suite local diagnostic is resource-sensitive and must respect
host bounds:

- Serialize full-suite preflights. A seat should not start a full local preflight
  when another local full-suite or preflight run is active on the same host.
- Use disk-backed temporary storage: `TMPDIR=$HOME/tmp`.
- Bound pytest worker parallelism. The `seat-ready` profile supplies a
  profile-level default test-command override with xdist capped at `-n 4`,
  replacing the generic preflight default that may use `-n auto`. A wrapper may
  pass the same cap explicitly, but it must not widen the profile above `-n 4`.
  Use at most `-n 4`; never use `-n auto` for seat-side full preflight.
- Clean stale pytest directories after the run has completed and no live pytest
  from that run still needs them.

These rules apply only when a seat elects to run the optional full diagnostic.
They keep that diagnostic from becoming a host-resource incident; they do not
make it READY or CI-parity evidence.

## Dispatch-Brief Integration

Implementation briefs for write-capable seats should carry a standing checklist
item before the READY stop line:

```text
- [ ] If this branch touches a registered generated reference surface, run the
      matching generator with --write, commit the checked artifact, and rerun the
      freshness check.
- [ ] Generate the changelog and PR carrier with repo-native tooling. The carrier
      slug must equal the branch slug, include itself, include the changelog, and
      carry AUTHORIZED_PATHS_COUNT and AUTHORIZED_PATHS_SHA256 for the real diff.
- [ ] PR body or carrier input contains exactly one line:
      - **Declared work class:** <XS|S|M|L>
- [ ] Push the committed current head and record the required Validate run
      URL/status for that exact head; local full-suite transcripts do not
      substitute for this evidence.
```

The checklist is not a substitute for tooling. Its purpose is to make the
authoring contract explicit in every dispatch until the profile is enforced by
the normal seat READY flow.

## Acceptance

The design is satisfied when an implementation slice can demonstrate:

- A seat branch that changes a registered CLI or schema surface self-regenerates
  the relevant checked reference artifact before READY.
- The pushed branch passes the CLI/schema freshness gates in the required
  Validate run without controller-side regeneration.
- The path-manifest carrier for the branch is generated from the real diff,
  includes itself and the changelog, and has a valid
  `AUTHORIZED_PATHS_COUNT`/`AUTHORIZED_PATHS_SHA256` block.
- The PR body includes `- **Declared work class:** <class>` using canonical
  vocabulary.
- Controller harvest requires zero carrier or autogen repairs. The controller
  harvest process emits this as a `controller_side_repairs` count in the harvest
  report and mirrors the value into its PR evidence comment. The measurement
  window is the controller harvest of the first pushed head after the seat
  reports READY: from checkout of that head through completion of carrier and
  autogen freshness evaluation. The count is zero only when harvest performs no
  carrier rewrite, changelog insertion, digest repair, generated-reference
  regeneration, or generated-reference staging on behalf of the seat.
- Public-facing docs contain only generic placeholders and no internal topology
  or secret-bearing operational detail.

## Implementation Notes for a Later Slice

A later implementation should prefer small extensions to existing validator
surfaces:

- Keep the seat-ready `ce validate-pr` profile as an optional diagnostic.
- Wire registered autogen repair commands only in the authoring profile, while
  CI remains verify-only.
- Invoke the existing `cli_reference_autogen_sync` and
  `schema_reference_autogen_sync` checks for source-surface detection and final
  byte-parity verification instead of duplicating their match logic.
- Reuse `carrier_gen` for changelog and path-manifest generation.
- Reuse `verify-path-manifest` for the final fidelity decision.
- Reuse existing work-class parsing and vocabulary normalization.
- Reuse the public-docs confidentiality scanner.
- Keep profile evidence printable in a form suitable for PR body evidence.

The implementation must not broaden worker authority. It writes only inside the
allocated worktree, does not approve or merge, and does not turn validation
evidence into a gate decision.
