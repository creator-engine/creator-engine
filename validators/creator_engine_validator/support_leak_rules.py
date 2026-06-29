"""Shared zero-leak rule table for support-agent runtime and eval checks."""
from __future__ import annotations

import re

from . import public_docs_confidentiality as confidentiality


DEFAULT_LEAK_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    *confidentiality.FORBIDDEN_PATTERNS,
    ("internal merge queue", re.compile(r"\bmerge[- ]queue\b", re.IGNORECASE)),
    ("internal integrator", re.compile(r"\bintegrator\b", re.IGNORECASE)),
    ("internal approval wall", re.compile(r"\bapproval[- ]wall\b", re.IGNORECASE)),
    ("internal fleet topology", re.compile(r"\bdev[- ]fleet\b", re.IGNORECASE)),
    ("confidential ce-ops bracket ref", re.compile(r"\bce[-_ ]?ops\s*[#-]\s*\d+\b", re.IGNORECASE)),
    ("internal compose lock token", re.compile(r"\bin-compose\b", re.IGNORECASE)),
    ("internal controller key reference", re.compile(r"\bcontroller[-_ ]?key\b", re.IGNORECASE)),
    ("internal worktree path", re.compile(r"/home/ce-dev-\d+/|\bce-workspaces\b")),
    ("internal workspace path", re.compile(r"/workspace/creator-engine\b")),
    ("private playbook path", re.compile(r"\bplaybooks/controller/|\b\.claude/agents/", re.IGNORECASE)),
    ("private dispatch territory token", re.compile(r"\bdispatch[-_ ]territory[-_ ]map\b", re.IGNORECASE)),
    (
        "secret-like environment token",
        re.compile(r"\b(?:CE|PRIVATE|INTERNAL)_[A-Z0-9_]*(?:TOKEN|KEY|SECRET|HOST|URL|PAT|CMD)\b"),
    ),
    ("private operator identity", re.compile(r"\boverwatch\b|\bforeman\b", re.IGNORECASE)),
    ("internal host label", re.compile(r"\b(?:tailnet|internal[-_ ]host)\b", re.IGNORECASE)),
)


__all__ = ["DEFAULT_LEAK_RULES"]
