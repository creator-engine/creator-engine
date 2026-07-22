"""Source-checkout compatibility shim for the canonical issue-ref parser.

The live autoclose driver dynamically loads this file from a bare checkout.
Installed consumers import :mod:`creator_engine_validator.issue_refs` directly.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _canonical_module():
    try:
        from creator_engine_validator import issue_refs
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parents[2]
        module_path = repo_root / "validators" / "creator_engine_validator" / "issue_refs.py"
        spec = importlib.util.spec_from_file_location("ce_issue_refs_canonical", module_path)
        if spec is None or spec.loader is None:
            raise ImportError("canonical issue-reference parser is unavailable")
        issue_refs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(issue_refs)
    return issue_refs


_CANONICAL = _canonical_module()
parse_title_refs = _CANONICAL.parse_title_refs
parse_body_closing_refs = _CANONICAL.parse_body_closing_refs
parse_acceptance_evidence = _CANONICAL.parse_acceptance_evidence
parse_all_refs = _CANONICAL.parse_all_refs
