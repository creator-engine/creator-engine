"""Anti-drift guard for CE action-skills (Playbooks -> Skills pilot).

A CE action-skill is a Claude-Code ``SKILL.md`` under ``.claude/skills/`` that
the controller uses as an ergonomic, *resident-by-name* veneer over an in-tree
procedure SSOT (a ``playbooks/**`` brief or a ``ce`` command). The
Playbooks->Skills design (HYBRID verdict) places two hard invariants on such a
skill so it stays a thin pointer and never becomes a third drift source or a
gate-bypass smuggler:

(a) **SSOT pointer.** The body MUST reference an in-tree SSOT — a
    ``playbooks/`` brief path or a ``ce <command>`` invocation — so the action
    stays singular and is not re-authored inside the skill.

(b) **No mutating forge command.** The body MUST NOT contain a mutating forge
    command (e.g. ``gh pr merge``, ``gh pr review --approve``, ``git push``).
    Governance rides on CE's ``PreToolUse`` hook-check seam, never on a skill;
    a skill that embeds a mutating command could quietly smuggle a
    gate-bypass / self-approval, which this guard structurally forbids.

Only skills that opt in as CE action-skills are scanned. A skill opts in via a
frontmatter marker (``ce-skill-class: action`` or ``ce-internal: true``) or by
using the ``ce-`` name prefix. Third-party / vendored skills (e.g. the bundled
speckit skills) are not CE action-skills and are skipped.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "skill_antidrift_guard"
CODE_NO_SSOT = "skill_antidrift_no_ssot_pointer"
CODE_MUTATING = "skill_antidrift_mutating_forge_command"
CONTRACT = ".ce/state/research/PLAYBOOKS_TO_SKILLS_PLAN_20260627.md"

SKILLS_DIR = (".claude", "skills")

# Mutating forge / VCS commands a CE action-skill must never embed. Matched
# case-insensitively against the skill body. Patterns are deliberately tight so
# that *naming* a command in prose ("never run gh pr merge") in a clearly
# negated sentence is still flagged — the safe move is to not write the literal
# command at all in an action-skill body.
MUTATING_FORGE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bgh\s+pr\s+merge\b", "gh pr merge"),
    (r"\bgh\s+pr\s+review\b[^\n]*--approve\b", "gh pr review --approve"),
    (r"\bgh\s+pr\s+review\s+--approve\b", "gh pr review --approve"),
    (r"\bgh\s+pr\s+close\b", "gh pr close"),
    (r"\bgh\s+pr\s+create\b", "gh pr create"),
    (r"\bgh\s+pr\s+ready\b", "gh pr ready"),
    (r"\bgh\s+issue\s+close\b", "gh issue close"),
    (r"\bgit\s+push\b", "git push"),
    (r"\bgit\s+commit\b", "git commit"),
    (r"\bgh\s+release\s+create\b", "gh release create"),
    (r"\bgh\s+api\b[^\n]*-X\s*(?:POST|PUT|PATCH|DELETE)\b", "gh api -X (mutating)"),
)

# A body satisfies the SSOT-pointer invariant if it references an in-tree
# playbook path or invokes a ``ce`` command.
SSOT_PATTERNS: tuple[str, ...] = (
    r"playbooks/[A-Za-z0-9_./-]+",
    r"\bce\s+[a-z][a-z0-9-]+",
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _repo_root_for(path: Path) -> Path:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() or (candidate / "validators").is_dir():
            return candidate
    return Path.cwd()


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except (ValueError, OSError):
        return str(path).replace("\\", "/")


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body). Frontmatter may be empty."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return "", text
    return match.group(1), text[match.end():]


def is_ce_action_skill(skill_dir_name: str, frontmatter: str) -> bool:
    """A skill opts in as a CE action-skill via marker or ``ce-`` name prefix."""
    fm = frontmatter.lower()
    if re.search(r"^\s*ce-skill-class\s*:\s*[\"']?action[\"']?\s*$", fm, re.MULTILINE):
        return True
    if re.search(r"^\s*ce-internal\s*:\s*[\"']?true[\"']?\s*$", fm, re.MULTILINE):
        return True
    if skill_dir_name.startswith("ce-"):
        return True
    return False


def _find_mutating(body: str) -> list[str]:
    lower = body.lower()
    found: list[str] = []
    for pattern, label in MUTATING_FORGE_PATTERNS:
        if re.search(pattern, lower):
            found.append(label)
    # De-duplicate while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for label in found:
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


def _has_ssot_pointer(body: str) -> bool:
    return any(re.search(pattern, body) for pattern in SSOT_PATTERNS)


def _iter_skill_files(repo_root: Path) -> list[Path]:
    skills_root = repo_root.joinpath(*SKILLS_DIR)
    if not skills_root.is_dir():
        return []
    return sorted(skills_root.glob("*/SKILL.md"))


@register(CHECK_NAME, ["ce-ops#314"])
def run(paths: Iterable[Path]) -> CheckResult:
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    repo_root = _repo_root_for(raw_paths[0])
    errors: list[ValidationError] = []

    for skill_file in _iter_skill_files(repo_root):
        try:
            text = skill_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        frontmatter, body = _split_frontmatter(text)
        skill_dir_name = skill_file.parent.name
        if not is_ce_action_skill(skill_dir_name, frontmatter):
            continue

        rel = _relative(skill_file, repo_root)

        for label in _find_mutating(body):
            errors.append(
                make_error(
                    CODE_MUTATING,
                    rel,
                    "body",
                    (
                        f"CE action-skill embeds mutating forge command '{label}'; "
                        "action-skills must contain no mutating forge command "
                        "(governance rides on the PreToolUse hook, not the skill)"
                    ),
                    CONTRACT,
                )
            )

        if not _has_ssot_pointer(body):
            errors.append(
                make_error(
                    CODE_NO_SSOT,
                    rel,
                    "body",
                    (
                        "CE action-skill references no in-tree SSOT (a 'playbooks/' "
                        "brief path or a 'ce <command>' invocation); a skill must "
                        "point at the SSOT, not re-author the procedure"
                    ),
                    CONTRACT,
                )
            )

    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
