"""`ce ask` / `ce support` runtime — honest scaffold (P0.4).

THIS SLICE ships the SUBSTRATE only (corpus allowlist + confidentiality
intersection, read-only profile, system-prompt contract). The model wiring that
turns a question into a cited answer is a SEPARATE, later ticket
(CE_SUPPORT_AGENT_PLAN_20260627.md §3, Phase 1+).

So `ce ask` is deliberately an **honest scaffold**: it prints that the support
agent is not yet wired and does NOT fabricate an answer or claim functionality it
lacks (no-MVP / no-false-success doctrine). It can, on request, print the
read-only foundations it *has* built so the substrate is inspectable.

The command is dev-gated (hidden from `ce --help`, off the public product
surface) per the internal-then-public doctrine, graduating to a public command
only after the eval clears.
"""
from __future__ import annotations

import json
import sys

from . import support_corpus

SCAFFOLD_NOTICE = "support agent not yet available (scaffold)"


def _build_status() -> dict:
    """Inspectable substrate status — what the P0 slice has actually built."""
    result = support_corpus.evaluate()
    return {
        "status": "scaffold",
        "wired": False,
        "notice": SCAFFOLD_NOTICE,
        "foundations": {
            "corpus_allowlist": support_corpus.CONTRACT,
            "system_prompt_contract": (
                "validators/creator_engine_validator/support_system_prompt.md"
            ),
            "readonly_profile": (
                "validators/creator_engine_validator/support_profile.py"
            ),
            "eligible_corpus_files": list(result.eligible),
            "corpus_roots": list(support_corpus.corpus_roots()),
            "rejected_not_clean": [
                {"path": rel, "reason": reason} for rel, reason in result.rejected
            ],
            "missing_not_yet_present": list(result.missing),
        },
        "not_yet_wired": [
            "model integration (answering path)",
            "docs->skill bundle projection",
            "eval harness (accuracy / zero-leak / refusal)",
        ],
    }


def run_cli(args) -> int:
    """Honest scaffold entrypoint. Never fabricates an answer."""
    json_output = bool(getattr(args, "json_output", False))
    show_foundations = bool(getattr(args, "foundations", False))
    question = " ".join(getattr(args, "question", []) or []).strip()

    if json_output:
        payload = _build_status()
        if question:
            payload["question"] = question
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    # Plain terminal output — clearly scaffold, no faked answer.
    print(f"ce ask: {SCAFFOLD_NOTICE}")
    print(
        "The Creator Engine support agent is not yet wired to a model. "
        "No answer can be given yet."
    )
    if question:
        print(f'(received question: "{question}" — not answered; scaffold only)')
    print(
        "The read-only substrate is in place "
        "(product-lens corpus allowlist + confidentiality intersection, "
        "read-only hook profile, system-prompt contract). "
        "Run `ce ask --foundations` to inspect it."
    )

    if show_foundations:
        status = _build_status()
        f = status["foundations"]
        print("", file=sys.stdout)
        print("foundations (P0 substrate):")
        print(f"  corpus allowlist:        {f['corpus_allowlist']}")
        print(f"  system-prompt contract:  {f['system_prompt_contract']}")
        print(f"  read-only profile:       {f['readonly_profile']}")
        print(f"  eligible corpus files:   {len(f['eligible_corpus_files'])}")
        for rel in f["eligible_corpus_files"]:
            print(f"    - {rel}")
        if f["rejected_not_clean"]:
            print("  rejected (not confidentiality-clean, excluded):")
            for item in f["rejected_not_clean"]:
                print(f"    - {item['path']}: {item['reason']}")
        print("  not yet wired:")
        for item in status["not_yet_wired"]:
            print(f"    - {item}")

    return 0
