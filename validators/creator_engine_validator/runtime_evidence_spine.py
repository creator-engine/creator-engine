"""Hash-chained runtime-evidence spine (v3 G-1.3a, plane C) — PURE substrate.

The tamper-evident, append-only, content-addressed record chain that the
(deferred, G-1.3b) classifier/audit overlay will write runtime-lifecycle
attestations into. Each record is content-addressed and chain-linked, and is
anchored to the exact runtime-policy it attests via ``policy_sha``.

This REUSES the proven in-repo hash-chain discipline rather than inventing a new
one — it mirrors ``ce_event_runtime`` (content-addressed signed blocks) and
``side_effect_ledger_runtime`` (append-only per-lane hash chain + head manifest):

* **content addressing** — ``content_hash`` is the SHA256 of the canonical JSON
  of the record material *excluding* ``content_hash`` itself (the exact
  ``ce_event_block._canonical_hash`` rule: ``sort_keys=True``, tight separators,
  ``ensure_ascii=False``);
* **chain linkage** — every record carries ``prev_hash``; the genesis record's
  ``prev_hash`` is the all-zero SHA256 sentinel (mirror
  ``side_effect_ledger_runtime.GENESIS_SHA``), and a non-genesis ``prev_hash``
  MUST equal the prior record's ``content_hash``;
* **monotonic sequence** — contiguous from ``0`` at genesis.

**PURE.** ``append`` and ``verify_chain`` operate on in-memory records only — no
disk write, no subprocess, no network, and no wall-clock read (timestamps are
inputs, never read here). Importing this module performs zero I/O. The live event
tap that *produces* these records is the G-1.3b audit overlay, which sits behind
the G-1.2 injectable-runner seam; this substrate never touches a live runtime.

Defensive only — it makes the Creator Engine's own runtime audit trail
tamper-evident; it is never an offensive capability.

See:
  - ``docs/contracts/runtime-evidence.md``
  - ``schemas/runtime-evidence.schema.yaml``
  - ``checks/ce_event_block.py`` / ``ce_event_runtime.py`` (hash-chain provenance)
  - ``side_effect_ledger_runtime.py`` (genesis-sentinel provenance)
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

#: The genesis record has no predecessor: its ``prev_hash`` is the all-zero
#: SHA256 sentinel (mirror ``side_effect_ledger_runtime.GENESIS_SHA``).
GENESIS_PREV_HASH = "0" * 64

#: Discriminators — the ``ce_runtime_evidence`` check self-selects files by
#: ``CHAIN_KIND`` and the schema pins each element to ``RECORD_KIND``.
CHAIN_KIND = "runtime-evidence-chain"
RECORD_KIND = "runtime-evidence-record"

#: The single field excluded from the content-address material.
CONTENT_HASH_FIELD = "content_hash"

#: The RunnerBackend lifecycle phases an evidence record may attest.
LIFECYCLE_PHASES = ("provision", "run", "collect", "teardown")
#: The classifier verdict categories (assigned by the deferred G-1.3b overlay).
CLASSIFICATIONS = ("allowed", "denied", "escalate")

#: v3 G-3.6a run-OUTCOME / terminal-disposition vocabulary. A typed terminal
#: record (``RUN_OUTCOME_RECORD_KIND`` / ``RUN_OUTCOME_RECORD_TYPE``) the
#: orchestrator appends to the chain after ``collect`` to attest WHERE a run
#: ended. This is ORTHOGONAL to the container ``LIFECYCLE_PHASES`` axis —
#: outcomes are plural + work-type-dependent — and is NEVER a ``lifecycle_phase``
#: value. The v3 MVP produces ``pr_opened`` (G-3.7) and ``pr_merged`` (G-3.7b —
#: the gated-merge disposition; its producer is the G-3.7b.1 merge-driving seam,
#: the live merge is G-3.8). The remaining members are reserved vocabulary for
#: later slices (review / research / no-change runs).
RUN_OUTCOME_RECORD_KIND = "runtime-run-outcome"
RUN_OUTCOME_RECORD_TYPE = "runtime_run_outcome"
RUN_OUTCOMES = ("pr_opened", "pr_merged", "review_submitted", "research_delivered", "no_change")

#: v3 G-3.7.2a ratification record. A typed record (``RATIFICATION_RECORD_KIND`` /
#: ``RATIFICATION_RECORD_TYPE``) the orchestrator appends to attest that a run was
#: RATIFIED — the CE-owned SHA-pinned single-use ratification. Value-free: it carries
#: only opaque digests (``approver_ref`` / ``ratified_prompt_sha`` / ``binding_ref``)
#: + the pinned ``ratified_head_sha`` (a git content-address) + the policy/run ids;
#: NEVER a raw account / host / credential / installation identifier, and NEVER a
#: ``lifecycle_phase`` value. The runtime head-SHA assertion (3.7.2b) consumes the
#: ``ratified_head_sha`` / ``binding_ref`` to refuse drift before any ``apply=True``.
RATIFICATION_RECORD_KIND = "runtime-ratification"
RATIFICATION_RECORD_TYPE = "runtime_ratification"

#: v3 G-4 agent-action record. A typed record (``RUNTIME_AGENT_ACTION_RECORD_KIND`` /
#: ``RUNTIME_AGENT_ACTION_RECORD_TYPE``) the (v3) audit overlay appends per observed
#: agent action — the per-run substrate the tokenomics (G-5) and coordination (G-6)
#: gates plug into. It records WHAT an agent did, at WHAT observation fidelity, gated
#: HOW HARD, on a dimension ORTHOGONAL to the container ``lifecycle_phase``, the run
#: ``outcome``, and the ``ratification`` — and is NEVER a ``lifecycle_phase`` value.
#: It is appended to the SAME hash chain (content-addressed + chain-linked +
#: policy-bound) so each action is itself tamper-evident grader input.
#:
#: The vocabulary below is the DURABLE pure-constant taxonomy these records draw on;
#: the classifier + control-point that PRODUCE the records live in the v3
#: ``runner.audit_overlay`` (this shared substrate carries only the value-free
#: constants — no runner/forge import, exactly like the outcome/ratification axes):
#:   * ``AGENT_ACTION_OPS`` — the capability axis ("do we gate?"): reads observe-only,
#:     the rest are gateable;
#:   * ``AGENT_ACTION_FIDELITIES`` — the provenance marker (Fork 1), stamped by the
#:     adapter (never the agent) and itself a policy input (stricter at lower fidelity);
#:   * ``AGENT_ACTION_TIMINGS`` — ``pre`` (gateable before execution, preventive) or
#:     ``post`` (observed after, detective);
#:   * ``DECISION_MODES`` — the gate-mode ladder a decision was produced under
#:     (provenance); ``REMEMBER_VALUES`` — the "always" persistence lever.
#: (The ``mutation_class`` axis reuses the existing planning-layer taxonomy in the
#: shared ``checks.mutation_class`` module — not re-declared here.)
RUNTIME_AGENT_ACTION_RECORD_KIND = "runtime-agent-action"
RUNTIME_AGENT_ACTION_RECORD_TYPE = "runtime_agent_action"
AGENT_ACTION_OPS = ("read", "write", "exec", "egress", "secret", "vcs")
AGENT_ACTION_FIDELITIES = ("faithful", "best_effort", "inferred")
AGENT_ACTION_TIMINGS = ("pre", "post")
DECISION_MODES = ("deny", "allowlist", "ask", "auto", "full")
REMEMBER_VALUES = ("none", "allow_always", "reject_always")

#: v3 G-5 tokenomics spend records. Two typed records on a NEW axis ORTHOGONAL to
#: the container ``lifecycle_phase``, the run ``outcome``, the ``ratification``, and
#: the agent ``action`` — and NEVER a ``lifecycle_phase`` value. Both are appended
#: to the SAME hash chain (content-addressed + chain-linked + policy-bound) so the
#: spend ledger and its breaches are themselves tamper-evident grader input. The
#: spend signal is FAITHFUL-BY-CONSTRUCTION (transport / API-reported, never
#: agent-asserted) — it inherits the Fork-1 fidelity (an agent cannot spoof its own
#: spend). This shared substrate carries only the value-free constants; the PURE
#: decision functions that PRODUCE the records live in the v3 ``runner.spend_gate``
#: (no runner / forge import here, exactly like the outcome / ratification / action
#: axes). The two record types are:
#:   * a METER / ledger record (``RUNTIME_SPEND_LEDGER_*``) — one metered cost leaf
#:     (``$`` for a fleet seat, ``%`` for the single subscription seat) that the
#:     pure ``project_spend`` folds (per scope + window) into the cumulative tally
#:     (state-as-projection — there is no separate mutable ledger file);
#:   * a BREACH record (``RUNTIME_SPEND_BREACH_*``) — a ``soft`` (~80% alert,
#:     continue) or ``hard`` (100% pause + escalate) circuit-breaker trip, carrying
#:     the two-signal refusal (``budget_exhausted`` = do-NOT-retry vs ``throttle``
#:     = retry-with-backoff) — never conflated (the retry-storm hazard).
RUNTIME_SPEND_LEDGER_RECORD_KIND = "runtime-spend-ledger"
RUNTIME_SPEND_LEDGER_RECORD_TYPE = "runtime_spend_ledger"
RUNTIME_SPEND_BREACH_RECORD_KIND = "runtime-spend-breach"
RUNTIME_SPEND_BREACH_RECORD_TYPE = "runtime_spend_breach"
#: The two disjoint billing-tier metric units (Fork C): ``$`` = API-USD (the fleet
#: regime); ``%`` = single-seat utilization meter (the subscription regime).
SPEND_UNITS = ("$", "%")
#: The nested deny-by-default envelope scopes (Fork B), most-restrictive-wins.
SPEND_SCOPES = ("global", "fleet", "run")
#: The accounting windows a cap may apply over.
SPEND_WINDOWS = ("per_run", "rolling_5h", "rolling_weekly", "total")
#: Circuit-breaker tiers (the two-tier breach model).
SPEND_BREACH_TIERS = ("soft", "hard")
#: The two-signal refusal protocol — distinct codes (cf. Portkey 412-vs-429).
SPEND_SIGNALS = ("budget_exhausted", "throttle")

#: Semantic finding kinds returned by :func:`verify_chain`. The check maps these
#: to its own stable error codes — the spine owns the *semantics*, not the codes.
FINDING_KINDS = ("content_address", "chain_link", "sequence", "policy_unbound")

_POLICY_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ChainFinding:
    """One tamper / integrity finding for the record at ``index`` in a chain."""

    kind: str
    index: int
    message: str


def canonical_content_hash(record: dict[str, Any]) -> str:
    """Return the SHA256 of the canonical record material (excludes ``content_hash``).

    Canonicalization is byte-for-byte the ``ce_event_block._canonical_hash`` rule:
    ``json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)``.
    Deterministic and stdlib-only; performs no I/O.
    """
    material = {k: v for k, v in record.items() if k != CONTENT_HASH_FIELD}
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compute_binding_ref(
    repo: str, installation_id: int, permissions: Any, ratified_head_sha: str
) -> str:
    """Return the opaque 64-hex digest binding a ratification to its normative tuple (v3 G-3.7.2b).

    A value-free digest over the ``{repo, installation_id, permissions, ratified_head_sha}`` the
    ratification is pinned to — so the runtime head-SHA assertion can recompute + compare WITHOUT
    any account / installation identifier appearing in the evidence record (only this digest does).
    ``permissions`` is normalized to a sorted ``[scope, level]`` list so the digest is
    order-independent. Reuses the :func:`canonical_content_hash` canonicalization rule
    (``sort_keys=True``, tight separators); deterministic and stdlib-only; performs no I/O.
    """
    perms = sorted([str(k), str(v)] for k, v in dict(permissions).items())
    material = {
        "repo": str(repo),
        "installation_id": int(installation_id),
        "permissions": perms,
        "ratified_head_sha": str(ratified_head_sha),
    }
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def append(chain: Sequence[dict[str, Any]], record_body: dict[str, Any]) -> dict[str, Any]:
    """Return a new chain-linked, content-addressed record to follow ``chain``.

    PURE: does not mutate ``chain`` or ``record_body``. Stamps the computed
    ``sequence`` (``len(chain)``; ``0`` at genesis), ``prev_hash`` (the genesis
    sentinel for an empty chain, else the last record's ``content_hash``), and
    ``content_hash`` (the canonical content address). ``record_body`` supplies
    every semantic field (kind, record_type, schema_version, policy_sha, run_id,
    lifecycle_phase, classification, recorded_at, …).
    """
    record = dict(record_body)
    record.pop(CONTENT_HASH_FIELD, None)
    record["sequence"] = len(chain)
    if chain:
        last = chain[-1]
        record["prev_hash"] = str(last.get(CONTENT_HASH_FIELD) or "") if isinstance(last, dict) else ""
    else:
        record["prev_hash"] = GENESIS_PREV_HASH
    record[CONTENT_HASH_FIELD] = canonical_content_hash(record)
    return record


def verify_chain(records: Sequence[Any]) -> list[ChainFinding]:
    """Return tamper / integrity findings for an in-memory evidence chain.

    Detects, per record: **mutation** (``content_hash`` != recomputed), **reorder
    / truncation** (``sequence`` not contiguous from ``0``), **broken linkage**
    (genesis ``prev_hash`` != sentinel; non-genesis ``prev_hash`` != prior
    ``content_hash``), and **missing policy binding** (``policy_sha`` absent or
    not a 64-hex digest). PURE and deterministic; NEVER raises for a tampered
    chain — it returns findings. An empty list means the chain verifies clean.
    """
    findings: list[ChainFinding] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            findings.append(ChainFinding("content_address", index, f"record[{index}] is not a mapping"))
            continue
        # Mutation: the content address must match the recomputed canonical hash.
        expected_hash = canonical_content_hash(record)
        actual_hash = record.get(CONTENT_HASH_FIELD)
        if actual_hash != expected_hash:
            findings.append(ChainFinding(
                "content_address", index,
                f"content_hash {actual_hash!r} != recomputed {expected_hash} (record mutated after hashing)",
            ))
        # Reorder / truncation: the sequence must be contiguous from 0.
        sequence = record.get("sequence")
        if sequence != index:
            findings.append(ChainFinding(
                "sequence", index,
                f"sequence {sequence!r} != expected {index} (chain reordered or a record was truncated)",
            ))
        # Broken linkage: genesis sentinel, then previous-content-hash binding.
        prev_hash = record.get("prev_hash")
        if index == 0:
            if prev_hash != GENESIS_PREV_HASH:
                findings.append(ChainFinding(
                    "chain_link", index,
                    f"genesis prev_hash {prev_hash!r} != all-zero sentinel {GENESIS_PREV_HASH}",
                ))
        else:
            prior = records[index - 1]
            expected_prev = prior.get(CONTENT_HASH_FIELD) if isinstance(prior, dict) else None
            if prev_hash != expected_prev:
                findings.append(ChainFinding(
                    "chain_link", index,
                    f"prev_hash {prev_hash!r} != prior record content_hash {expected_prev!r} (broken hash chain)",
                ))
        # Policy binding: every record anchors to its runtime-policy via policy_sha.
        policy_sha = record.get("policy_sha")
        if not is_policy_sha(policy_sha):
            findings.append(ChainFinding(
                "policy_unbound", index,
                f"policy_sha {policy_sha!r} is absent or not a 64-hex digest "
                "(record is unbound from the runtime-policy it attests)",
            ))
    return findings


def is_policy_sha(value: Any) -> bool:
    """True when ``value`` is a 64-character lowercase-hex SHA256 digest."""
    return isinstance(value, str) and bool(_POLICY_SHA_RE.match(value))
