# Contract: Peer authority — per-area ownership × risk-tiered quorum (v3.5-C A-C3)

**Status:** Canonical. Enforced by the `peer_authority` check against
`schemas/coordination-policy.schema.yaml` (the repo policy file is
`.ce/coordination.yml`); the live forge-side enforcement is the generalized
`forge.plan_approval.plan_approved`.

## Purpose

Constrained-BDFL ("the maintainer ratifies") fits maintainer-plus-contributors;
it does not fit **two solo-dev peers with no BDFL**. The resolution
(design §A.5) is **not a new authority engine** — it re-parameterizes the
existing CODEOWNERS + `mutation_class` + independent-review machinery:

| Decision blast-radius | Quorum | Mechanism |
| --- | --- | --- |
| low/medium `mutation_class` within your area | **1** ratifier (the area owner — constrained-BDFL *of that area*) | `area_owners` / CODEOWNERS |
| cross-area (touches the other peer's area) | the **owning area's peer** | federation |
| privileged `mutation_class` (`PRIVILEGED_NAMES`: deploy, governance, identity, security, attestation, redaction) | **both peers** (≥ 2 distinct humans) | `human_ratification_required` re-read as "the other peer, or both" |

**Constrained-BDFL is the N=1 special case:** a solo dev is one area-BDFL of
everything; two peers are two area-BDFLs + consensus-on-privileged; a small
team is N area-BDFLs + per-tier thresholds. Same dial (`mutation_class`),
now symmetric.

## Where it lives

`.ce/coordination.yml` carries the `ratification_authority` block
(`area_owners` and/or `defer_to_codeowners`; `quorum_by_tier`
{`non_privileged: 1`, `privileged: 2`}; `no_self_approval: true`) plus the
`identity_map` resolver data. **The file is self-classified `governance`**
(a schema const): changing the authority map is privileged → both peers —
the authority model cannot be unilaterally rewritten. That is the closing
brick.

The optional `ratifications` list is the offline/auditable attestation form
this check grades; the live path is `plan_approved(..., authority=policy,
changed_paths=..., mutation_class=...)`, which keeps the existing
`approver ≠ author ≠ seat` rule and adds quorum-of-distinct-humans + area
coverage.

## Relationship to the authority-matrix baseline

`docs/contracts/authority-matrix.{md,yml}` is keyed by **role_category**
(which *role* may ratify a privileged class). Peer authority is a
**different axis** — per-**area** × per-**tier** for symmetric peers. This
check references the privileged-class rule (`PRIVILEGED_NAMES`, reused
verbatim) and does not duplicate or replace the matrix.

## Enforced invariants (the `peer_authority` check)

| Code | Invariant |
| --- | --- |
| `VAL-PA-SCHEMA` | the policy validates (quorum floors `privileged ≥ 2` / `non_privileged ≥ 1`; `no_self_approval` const true; `mutation_class` const `governance`). |
| `VAL-PA-INVALID` | the policy file parses as YAML. |
| `VAL-PA-AREA-CONFIG` | an area configuration exists (`defer_to_codeowners: true` and/or non-empty `area_owners`). |
| `VAL-PA-QUORUM` | a ratification carries ≥ the tier's quorum of **distinct, independent, resolved humans** (privileged → both peers). |
| `VAL-PA-SELF-APPROVAL` | the author's (or running seat's) human never counts as a ratifier. |
| `VAL-PA-AREA-OWNER-MISSING` | every declared area a change touches has one of its owners among the ratifiers — except an area the author's human owns, which authorship itself covers (you are the constrained-BDFL of your own area; independence comes from the quorum rule). |
| `VAL-PA-IDENTITY-UNRESOLVED` | an actor that does not resolve through `identity_map` **fails closed** — surfaced, never silently counted. |
| `VAL-PA-N1-SOLO-EXPIRED` | a record marked `quorum: n1_solo` is rejected once the `identity_map` resolves **≥ 2 distinct humans** — automatic expiry at the second human, not a manual migration. |
| `VAL-PA-N1-SOLO-REQUIRED` | a privileged ratification leaning on the **sole resolved human** (a one-human map) must record the honest `quorum: n1_solo`; omitting it is laundered quorum (two accounts of one human are ONE human and never satisfy `privileged: 2`). |

## N=1 native mode — the honest `quorum: n1_solo` carve-out (N1-CARVEOUT)

**N=1 solo-dev is CE's native out-of-the-box mode.** CE's own development is an
N=1 case, not an edge case: a single human owns every area and ratifies their
own privileged decisions. The privileged tier still pins `privileged: 2`
(`quorum_by_tier` is unchanged), so an honest record cannot *claim* a two-human
quorum that does not exist. Instead the cardinality is recorded truthfully on
the ratification record:

- In a **one-human map**, a privileged ratification by the sole human is lawful
  **only** when the record explicitly carries `quorum: n1_solo` (on a
  `.ce/coordination.yml` `ratifications[]` entry, or a Decision Record's
  `ratification.quorum`). Omitting it on a privileged record that leans on the
  sole human fails `VAL-PA-N1-SOLO-REQUIRED`.
- **The instant the map resolves two or more humans, every `n1_solo` record
  fails** (`VAL-PA-N1-SOLO-EXPIRED`). This is automatic expiry — the carve-out
  cannot outlive the condition that justified it. From that point privileged
  decisions need the real two-human quorum.
- **`n1_solo` is not quorum 2, not two-account laundering, and not a no-self
  bypass.** Fail-closed identity resolution and `no_self_approval` are applied
  *before* the solo mode can pass: an unresolved or missing ratifier never
  counts as solo authority, and a ratifier resolving to the author's/seat's (or
  a Decision Record `decision_makers`') human is still self-approval.

The map-sensitive grading (auto-expiry, laundered-quorum) lives here in
`peer_authority`, which holds the current `identity_map`; it also cross-checks
governed Decision Records' `ratification.quorum` against that same map. The
`decision_record` check owns only the local shape rule (`VAL-DR-N1-SOLO-MISUSED`:
the marker is meaningful only on an accepted privileged record). A Decision
Record is graded against a policy only when its path falls inside that policy's
declared `area_owners` decision surface — so unrelated example records with no
governing policy are never graded against this repo's one-human map.

## Identity resolution — declared limits (the §11.5 gap, shipped honestly)

The `identity_map` resolves {git author, PR approver, running seat, App
installation} → `human_id`; quorums count **humans, not accounts** (two
logins of one human are ONE ratifier). The resolver is honest about what it
cannot guarantee:

1. **It is declarative, not cryptographic.** The map asserts which labels
   belong to which human; it cannot *prove* two GitHub accounts are distinct
   people. Token/account separation alone is not sufficient (CE's own rule).
   With two real humans the assertion is genuine; with synthetic second
   accounts it is not — which is why this repo's map currently declares ONE
   human holding both of its accounts (the N=1 special case) rather than
   pretending at two.
2. **Unresolved edges fail closed.** Where a seat→human or App→human edge is
   not in the map, the check surfaces `VAL-PA-IDENTITY-UNRESOLVED` and the
   actor never counts toward quorum. No completeness of identity is claimed.
3. **The map is itself inside the governance loop.** It lives in the
   `governance`-classified policy file — editing who-resolves-to-whom takes
   the full privileged bar, so one peer cannot mint themselves a second
   "human".
