"""CE-native project initialization scaffolder.

The public ``ce init`` command uses this module to bootstrap a new or existing
project into CE's governed, spec-driven workflow. Templates are embedded in the
package, deterministic, and offline-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

Status = Literal["created", "skipped", "overwritten"]


class ProjectInitError(Exception):
    code = "CE-INIT-ERROR"


class ProjectInitRefused(ProjectInitError):
    code = "CE-INIT-REFUSED"


@dataclass(frozen=True)
class TemplateFile:
    path: str
    content: str


@dataclass(frozen=True)
class FileAction:
    path: str
    status: Status
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "status": self.status, "reason": self.reason}


@dataclass(frozen=True)
class ProjectInitResult:
    target: Path
    actions: tuple[FileAction, ...]

    @property
    def created(self) -> tuple[str, ...]:
        return tuple(a.path for a in self.actions if a.status == "created")

    @property
    def skipped(self) -> tuple[str, ...]:
        return tuple(a.path for a in self.actions if a.status == "skipped")

    @property
    def overwritten(self) -> tuple[str, ...]:
        return tuple(a.path for a in self.actions if a.status == "overwritten")

    def to_dict(self) -> dict:
        return {
            "target": str(self.target),
            "created": list(self.created),
            "skipped": list(self.skipped),
            "overwritten": list(self.overwritten),
            "actions": [a.to_dict() for a in self.actions],
        }


README = """# CE-Governed Project

This project is prepared for Creator Engine governed development.

## CE Workflow

CE uses the stage vocabulary `Frame -> Shape -> Build -> Review -> Ship`:

- Frame: understand the request, bounds, and done condition.
- Shape: declare the Scope, acceptance criteria, appetite, mutation class, and plan.
- Build: make the ratified change in a governed run.
- Review: grade the result against evidence and acceptance criteria.
- Ship: deliver the governed terminal outcome.

## Work Sizing

Choose the smallest CE work class that honestly fits the diff:

- `XS`: `scope_card` only.
- `S`: `intent` + `scope` + `tasks`.
- `M`: full `spec.md` + `plan.md` + `tasks.md`.
- `L`: PRD, per-feature plan, and thin slices.

Do not write a full spec for every unit. The tier selects the minimum ceremony.

## PR Wiring

Every governed PR should include:

- `.ce/changelog/<branch>.md`, based on `.ce/changelog/_template.md`.
- `.ce/pr-manifests/<branch>.md`, based on `.ce/pr-manifests/_template.md`.
- A manifest line declaring `Declared work class: XS|S|M|L`.
- A closed path list matching the PR diff.

Run `ce validate-pr` before review. The validator checks changelog fragments,
path-manifest fidelity, work-sizing declarations, and the local test gate.
"""


CE_README = """# CE Project Files

This directory carries project-local Creator Engine governance artifacts.

- `scopes/templates/` contains right-sized planning templates for XS, S, and M work.
- `changelog/_template.md` is the per-PR changelog fragment template.
- `pr-manifests/_template.md` is the path-manifest carrier template.
- `skills/` contains CE-native local skill prompts for governed shaping and review.

The CE stages are `Frame -> Shape -> Build -> Review -> Ship`.
"""


SCOPES_README = """# CE Scope Templates

Use the smallest work class that satisfies the change:

- XS: scope card only.
- S: intent, scope, and tasks.
- M: full spec, plan, and tasks.

These templates intentionally do not force full-spec ceremony onto XS or S work.
"""


XS_SCOPE_CARD = """# XS Scope Card: <short-name>

Declared work class: XS

## Frame

Goal:

Done when:

Change type:

## Shape

Scope:

Out of scope:

Verification:
"""


S_INTENT_SCOPE_TASKS = """# S Work Packet: <short-name>

Declared work class: S

## Intent Line

Goal:

Done when:

Change type:

## Scope Record

In scope:

Out of scope:

Appetite:

## Tasks

- [ ] Shape the acceptance criteria.
- [ ] Build the scoped change.
- [ ] Review evidence and run `ce validate-pr`.
"""


M_SPEC = """# Spec: <short-name>

Declared work class: M

## Frame

Problem:

Users / operators affected:

Done when:

## Shape

Acceptance criteria:

Mutation class:

Appetite:

Risks:

Out of scope:
"""


M_PLAN = """# Plan: <short-name>

## Stage Plan

- Frame:
- Shape:
- Build:
- Review:
- Ship:

## Design

Approach:

Alternatives considered:

Validation:
"""


M_TASKS = """# Tasks: <short-name>

## Build

- [ ] Implement the scoped change.
- [ ] Add or update focused tests.
- [ ] Update coupled docs or generated references.

## Review

- [ ] Run targeted tests.
- [ ] Run `ce validate-pr`.
- [ ] Confirm changelog and path manifest are complete.
"""


CHANGELOG_TEMPLATE = """---
slug: <branch-slug>
date: YYYY-MM-DD
kind: feature
scope: project
issue: <tracker-ref>
---

**Short user-facing summary.**

- Describe the governed change and evidence in one or two bullets.
"""


MANIFEST_TEMPLATE = """# PR path manifest - <branch-slug>

This carrier lists the closed authorized path set for one governed PR.

Declared work class: XS|S|M|L

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

AUTHORIZED_PATHS_COUNT=<count>

AUTHORIZED_PATHS_SHA256=<sha256>

```text
.ce/changelog/<branch-slug>.md
.ce/pr-manifests/<branch-slug>.md
```
"""


SKILLS_README = """# CE-Native Local Skills

These local skill prompts are authored for CE-governed work. They are project
starting points, not mandatory global policy.
"""


SHAPE_SCOPE_SKILL = """# CE Shape Scope

Use this skill when turning a framed request into a CE Scope.

1. Confirm the work class: XS, S, M, or L.
2. Keep the artifact bundle right-sized to that class.
3. State the stage handoff in CE terms: Frame -> Shape -> Build -> Review -> Ship.
4. Record acceptance criteria, mutation class, appetite, and out-of-scope items.
5. Produce the changelog and path-manifest requirements before Build starts.
"""


REVIEW_EVIDENCE_SKILL = """# CE Review Evidence

Use this skill when checking a governed change before review.

1. Compare the diff to the path-manifest carrier.
2. Confirm the declared work class line is present and not below the diff floor.
3. Check the per-PR changelog fragment.
4. Run or cite `ce validate-pr`.
5. Report findings as evidence against the Scope's done criteria.
"""


GITIGNORE = """.hermes/
.ce/state/
"""


def embedded_templates() -> tuple[TemplateFile, ...]:
    """Return deterministic, package-embedded CE project templates."""

    return (
        TemplateFile("README.md", README),
        TemplateFile(".gitignore", GITIGNORE),
        TemplateFile(".ce/README.md", CE_README),
        TemplateFile(".ce/scopes/README.md", SCOPES_README),
        TemplateFile(".ce/scopes/templates/XS-scope-card.md", XS_SCOPE_CARD),
        TemplateFile(".ce/scopes/templates/S-intent-scope-tasks.md", S_INTENT_SCOPE_TASKS),
        TemplateFile(".ce/scopes/templates/M-spec.md", M_SPEC),
        TemplateFile(".ce/scopes/templates/M-plan.md", M_PLAN),
        TemplateFile(".ce/scopes/templates/M-tasks.md", M_TASKS),
        TemplateFile(".ce/changelog/_template.md", CHANGELOG_TEMPLATE),
        TemplateFile(".ce/pr-manifests/_template.md", MANIFEST_TEMPLATE),
        TemplateFile(".ce/skills/README.md", SKILLS_README),
        TemplateFile(".ce/skills/ce-shape-scope/SKILL.md", SHAPE_SCOPE_SKILL),
        TemplateFile(".ce/skills/ce-review-evidence/SKILL.md", REVIEW_EVIDENCE_SKILL),
    )


def plan_actions(
    target: Path | str,
    templates: Iterable[TemplateFile] | None = None,
    *,
    force: bool = False,
) -> tuple[FileAction, ...]:
    """Purely classify the create/skip/overwrite action for each template."""

    root = Path(target)
    actions: list[FileAction] = []
    for template in templates or embedded_templates():
        path = root / template.path
        if path.exists() and not path.is_file():
            actions.append(FileAction(template.path, "skipped", "path exists and is not a file"))
            continue
        if not path.exists():
            actions.append(FileAction(template.path, "created", "missing"))
            continue
        existing = path.read_text(encoding="utf-8")
        if existing == template.content:
            actions.append(FileAction(template.path, "skipped", "already current"))
        elif force:
            actions.append(FileAction(template.path, "overwritten", "force"))
        else:
            actions.append(FileAction(template.path, "skipped", "would overwrite user edits"))
    return tuple(actions)


def init_project(target: Path | str, *, force: bool = False) -> ProjectInitResult:
    """Create a CE project scaffold without clobbering user edits."""

    root = Path(target).resolve()
    if root.exists() and not root.is_dir():
        raise ProjectInitRefused(f"target exists and is not a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)

    templates = {template.path: template for template in embedded_templates()}
    actions = plan_actions(root, templates.values(), force=force)
    for action in actions:
        if action.status == "skipped":
            continue
        template = templates[action.path]
        path = root / template.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template.content, encoding="utf-8")

    return ProjectInitResult(target=root, actions=actions)


__all__ = [
    "FileAction",
    "ProjectInitError",
    "ProjectInitRefused",
    "ProjectInitResult",
    "TemplateFile",
    "embedded_templates",
    "init_project",
    "plan_actions",
]
