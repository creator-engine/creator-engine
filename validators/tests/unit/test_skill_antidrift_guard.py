"""Tests for the CE action-skill anti-drift guard (ce-ops#314, NEW-B).

The guard asserts every CE action-skill (a) references an in-tree SSOT and
(b) embeds no mutating forge command. These tests prove the guard has teeth:
it fails when a skill embeds a mutating command or lacks an SSOT pointer, and
passes for a well-formed thin-pointer skill. They also pin that the two pilot
skills shipped in this repo are clean.
"""

from __future__ import annotations

from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.skill_antidrift_guard import (
    CHECK_NAME,
    CODE_MUTATING,
    CODE_NO_SSOT,
    is_ce_action_skill,
    run,
)

GOOD_BODY = """\
> INTERNAL controller ergonomics. Thin pointer.

## SSOT
- Procedure SSOT: `playbooks/controller/briefs/dispatch.md`

## What to do
1. Read `playbooks/controller/briefs/dispatch.md` and follow it verbatim.
2. Record the work claim.
"""

CE_FRONTMATTER = (
    "---\n"
    'name: "ce-example"\n'
    'description: "An internal CE action-skill."\n'
    "ce-internal: true\n"
    "ce-skill-class: \"action\"\n"
    "ce-mutating: false\n"
    "---\n"
)


def _write_skill(root: Path, name: str, frontmatter: str, body: str) -> Path:
    skill_dir = root / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(frontmatter + "\n" + body, encoding="utf-8")
    # Ensure the repo-root detector locks onto tmp_path, not a real ancestor.
    (root / ".git").mkdir(exist_ok=True)
    return skill_file


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_guard_is_registered():
    assert CHECK_NAME in registered_checks()


def test_well_formed_thin_pointer_skill_passes(tmp_path: Path):
    _write_skill(tmp_path, "ce-example", CE_FRONTMATTER, GOOD_BODY)

    result = run([tmp_path])

    assert result.ok, [e.format() for e in result.errors]


def test_embedded_gh_pr_merge_is_rejected(tmp_path: Path):
    body = GOOD_BODY + "\nThen run `gh pr merge 123 --auto`.\n"
    _write_skill(tmp_path, "ce-example", CE_FRONTMATTER, body)

    result = run([tmp_path])

    assert not result.ok
    assert CODE_MUTATING in _codes(result)
    assert "gh pr merge" in result.errors[0].message


def test_embedded_approve_review_is_rejected(tmp_path: Path):
    body = GOOD_BODY + "\nApprove via `gh pr review 123 --approve`.\n"
    _write_skill(tmp_path, "ce-example", CE_FRONTMATTER, body)

    result = run([tmp_path])

    assert CODE_MUTATING in _codes(result)


def test_embedded_git_push_is_rejected(tmp_path: Path):
    body = GOOD_BODY + "\nFinally `git push origin HEAD`.\n"
    _write_skill(tmp_path, "ce-example", CE_FRONTMATTER, body)

    result = run([tmp_path])

    assert CODE_MUTATING in _codes(result)


def test_missing_ssot_pointer_is_rejected(tmp_path: Path):
    body = "## Steps\n1. Compose the brief.\n2. Record the claim.\n"
    _write_skill(tmp_path, "ce-example", CE_FRONTMATTER, body)

    result = run([tmp_path])

    assert not result.ok
    assert CODE_NO_SSOT in _codes(result)


def test_ce_command_counts_as_ssot_pointer(tmp_path: Path):
    body = "## Steps\nRun `ce playbook run dispatch` and surface PASS/FAIL.\n"
    _write_skill(tmp_path, "ce-example", CE_FRONTMATTER, body)

    result = run([tmp_path])

    assert result.ok, [e.format() for e in result.errors]


def test_non_ce_skill_is_not_scanned(tmp_path: Path):
    # A vendored / third-party skill with no CE markers and a non-ce name is
    # not a CE action-skill: it may embed anything without tripping the guard.
    fm = '---\nname: "speckit-thing"\ndescription: "vendor"\n---\n'
    body = "Run `gh pr merge 1` and `git push`.\n"
    _write_skill(tmp_path, "speckit-thing", fm, body)

    result = run([tmp_path])

    assert result.ok


def test_ce_name_prefix_opts_in_without_marker(tmp_path: Path):
    fm = '---\nname: "ce-thing"\ndescription: "no explicit marker"\n---\n'
    body = "Run `gh pr merge 1`.\n"
    _write_skill(tmp_path, "ce-thing", fm, body)

    result = run([tmp_path])

    assert CODE_MUTATING in _codes(result)


def test_is_ce_action_skill_classifier():
    assert is_ce_action_skill("ce-dispatch", "")
    assert is_ce_action_skill("anything", "ce-internal: true")
    assert is_ce_action_skill("anything", 'ce-skill-class: "action"')
    assert not is_ce_action_skill("speckit-plan", "user-invocable: true")


def test_shipped_pilot_skills_pass_the_guard():
    # The two pilot skills shipped in THIS repo must satisfy the guard.
    repo_root = Path(__file__).resolve().parents[3]
    skills_root = repo_root / ".claude" / "skills"
    assert (skills_root / "ce-dispatch" / "SKILL.md").is_file()
    assert (skills_root / "ce-merge-gate" / "SKILL.md").is_file()

    result = run([repo_root])

    assert result.ok, [e.format() for e in result.errors]
