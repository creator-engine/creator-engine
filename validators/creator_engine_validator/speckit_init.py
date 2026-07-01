"""Spec-kit scaffold runtime for ``ce speckit init``.

The scaffold is intentionally path-only and offline: it writes a fixed set of
reusable templates, command notes, and skill artifacts into an existing target
project without reading credentials, invoking git, or reaching the network.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

FileWriter = Callable[[Path, str], None]


@dataclass(frozen=True)
class ScaffoldArtifact:
    """One relative path and UTF-8 payload to scaffold."""

    path: str
    content: str


@dataclass(frozen=True)
class ScaffoldResult:
    """Summary of a scaffold run."""

    target: Path
    created: tuple[str, ...]
    skipped: tuple[str, ...]
    overwritten: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "target": str(self.target),
            "created": list(self.created),
            "skipped": list(self.skipped),
            "overwritten": list(self.overwritten),
        }


class SpeckitInitError(Exception):
    """Base exception with a stable CLI-facing error code."""

    code = "speckit_init_error"


class MissingTargetError(SpeckitInitError):
    code = "missing_target"


class UnsafeArtifactPathError(SpeckitInitError):
    code = "unsafe_artifact_path"


class ScaffoldWriteError(SpeckitInitError):
    code = "write_failed"


def _artifact(path: str, content: str) -> ScaffoldArtifact:
    return ScaffoldArtifact(path=path, content=content if content.endswith("\n") else f"{content}\n")


_SPEC_TEMPLATE = """# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`
**Created**: [DATE]
**Status**: Draft
**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

### Edge Cases

- What happens when [boundary condition]?
- How does the system handle [error scenario]?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST [specific capability]

### Key Entities *(include if feature involves data)*

- **[Entity]**: [What it represents and key attributes]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: [Measurable, technology-agnostic outcome]

## Assumptions

- [Assumption based on reasonable defaults]
"""


_PLAN_TEMPLATE = """# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

## Summary

[Extract from feature spec: primary requirement and technical approach]

## Technical Context

**Language/Version**: [e.g., Python 3.14, TypeScript 5.x, or NEEDS CLARIFICATION]
**Primary Dependencies**: [e.g., FastAPI, React, PostgreSQL or NEEDS CLARIFICATION]
**Storage**: [if applicable, e.g., PostgreSQL, files, N/A]
**Testing**: [e.g., pytest, vitest, or NEEDS CLARIFICATION]
**Target Platform**: [e.g., Linux server, browser, mobile or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Constitution gates determined by the project]

## Project Structure

### Documentation

```text
specs/[###-feature]/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Tree

```text
[project-specific layout]
```

## Complexity Tracking

[Fill only if a constitution check needs justification]
"""


_TASKS_TEMPLATE = """# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel
- **[Story]**: User story identifier, for example US1

## Phase 1: Setup

- [ ] T001 Create project structure for the feature

## Phase 2: Tests First

- [ ] T002 [P] Add failing test for the primary user story

## Phase 3: Implementation

- [ ] T003 Implement the primary user story

## Phase 4: Polish

- [ ] T004 Run validation and update documentation
"""


_CHECKLIST_TEMPLATE = """# [CHECKLIST TYPE] Checklist: [FEATURE]

**Purpose**: [Brief description of what this checklist validates]
**Created**: [DATE]
**Feature**: [Link to spec.md]

## [Category]

- [ ] First validation item
- [ ] Second validation item
"""


_CONSTITUTION_TEMPLATE = """# [PROJECT] Constitution

## Core Principles

### I. [Principle Name]

[Principle statement]

## Governance

[Governance rules and amendment process]
"""


_COMMON_SH = """#!/usr/bin/env bash
set -euo pipefail

get_repo_root() {
  local current
  current="$(pwd)"
  while [ "$current" != "/" ]; do
    if [ -d "$current/.specify" ] || [ -d "$current/.git" ]; then
      printf '%s\n' "$current"
      return 0
    fi
    current="$(dirname "$current")"
  done
  pwd
}

has_git() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1
}
"""


_CREATE_FEATURE_SH = """#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <feature description>" >&2
  exit 1
fi

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
REPO_ROOT="$(get_repo_root)"
mkdir -p "$REPO_ROOT/specs"
printf '{"feature_directory":"specs"}\n' > "$REPO_ROOT/.specify/feature.json"
echo "specs"
"""


_SETUP_PLAN_SH = """#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
REPO_ROOT="$(get_repo_root)"
FEATURE_DIR="${SPECIFY_FEATURE_DIRECTORY:-$REPO_ROOT/specs/current}"
mkdir -p "$FEATURE_DIR"
cp "$REPO_ROOT/.specify/templates/plan-template.md" "$FEATURE_DIR/plan.md"
echo "$FEATURE_DIR/plan.md"
"""


_SETUP_TASKS_SH = """#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
REPO_ROOT="$(get_repo_root)"
FEATURE_DIR="${SPECIFY_FEATURE_DIRECTORY:-$REPO_ROOT/specs/current}"
mkdir -p "$FEATURE_DIR"
cp "$REPO_ROOT/.specify/templates/tasks-template.md" "$FEATURE_DIR/tasks.md"
echo "$FEATURE_DIR/tasks.md"
"""


_CHECK_PREREQUISITES_SH = """#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
REPO_ROOT="$(get_repo_root)"
test -d "$REPO_ROOT/.specify"
test -d "$REPO_ROOT/.specify/templates"
echo "$REPO_ROOT"
"""


def _skill(name: str, summary: str, body: str) -> ScaffoldArtifact:
    return _artifact(
        f".ce/skills/{name}.md",
        f"""# {name}

{summary}

## Inputs

- User request text, if supplied.
- Project files under the current working tree.
- Speckit scaffold files under `.specify/`.

## Procedure

{body}

## Outputs

- Path-only updates in `specs/` or `.specify/` as required by the command.
- No secrets, credentials, network access, or hidden environment reads.
""",
    )


DEFAULT_ARTIFACTS: tuple[ScaffoldArtifact, ...] = (
    _artifact(".specify/templates/spec-template.md", _SPEC_TEMPLATE),
    _artifact(".specify/templates/plan-template.md", _PLAN_TEMPLATE),
    _artifact(".specify/templates/tasks-template.md", _TASKS_TEMPLATE),
    _artifact(".specify/templates/checklist-template.md", _CHECKLIST_TEMPLATE),
    _artifact(".specify/templates/constitution-template.md", _CONSTITUTION_TEMPLATE),
    _artifact(".specify/scripts/bash/common.sh", _COMMON_SH),
    _artifact(".specify/scripts/bash/create-new-feature.sh", _CREATE_FEATURE_SH),
    _artifact(".specify/scripts/bash/setup-plan.sh", _SETUP_PLAN_SH),
    _artifact(".specify/scripts/bash/setup-tasks.sh", _SETUP_TASKS_SH),
    _artifact(".specify/scripts/bash/check-prerequisites.sh", _CHECK_PREREQUISITES_SH),
    _artifact(".specify/integrations/speckit.manifest.json", '{"name":"speckit","commands":["speckit-specify","speckit-plan","speckit-tasks","speckit-implement"]}'),
    _artifact(".specify/integrations/claude.manifest.json", '{"name":"claude","skill_dir":".ce/skills"}'),
    _artifact(".specify/integrations/codex.manifest.json", '{"name":"codex","skill_dir":".ce/skills"}'),
    _artifact(".specify/workflows/workflow-registry.json", '{"workflows":[{"name":"speckit","path":".specify/workflows/speckit/workflow.yml"}]}'),
    _artifact(".specify/workflows/speckit/workflow.yml", "name: speckit\nsteps:\n  - speckit-specify\n  - speckit-plan\n  - speckit-tasks\n  - speckit-implement\n"),
    _artifact(".specify/extensions.yml", "hooks:\n  before_specify: []\n  after_specify: []\n"),
    _artifact(".specify/extensions/git/README.md", "# Speckit Git Extension\n\nOptional git helper command notes for speckit workflows.\n"),
    _artifact(".specify/extensions/git/extension.yml", "name: speckit.git\ncommands:\n  - speckit.git.feature\n  - speckit.git.initialize\n  - speckit.git.commit\n  - speckit.git.remote\n  - speckit.git.validate\n"),
    _artifact(".specify/extensions/git/config-template.yml", "branch_prefix: ''\n"),
    _artifact(".specify/extensions/git/git-config.yml", "branch_prefix: ''\n"),
    _artifact(".specify/extensions/git/commands/speckit.git.feature.md", "# speckit.git.feature\n\nCreate or select a feature branch for the active speckit feature.\n"),
    _artifact(".specify/extensions/git/commands/speckit.git.initialize.md", "# speckit.git.initialize\n\nInitialize git repository support when a project chooses to use git.\n"),
    _artifact(".specify/extensions/git/commands/speckit.git.commit.md", "# speckit.git.commit\n\nPrepare a commit for completed speckit work.\n"),
    _artifact(".specify/extensions/git/commands/speckit.git.remote.md", "# speckit.git.remote\n\nConfigure or inspect remote repository metadata.\n"),
    _artifact(".specify/extensions/git/commands/speckit.git.validate.md", "# speckit.git.validate\n\nRun project validation before git publication.\n"),
    _artifact(".specify/extensions/git/scripts/bash/create-new-feature.sh", _CREATE_FEATURE_SH),
    _artifact(".specify/extensions/git/scripts/bash/initialize-repo.sh", "#!/usr/bin/env bash\nset -euo pipefail\ngit init\n"),
    _artifact(".specify/extensions/git/scripts/bash/auto-commit.sh", "#!/usr/bin/env bash\nset -euo pipefail\ngit status --short\n"),
    _artifact(".specify/extensions/git/scripts/bash/git-common.sh", "#!/usr/bin/env bash\nset -euo pipefail\n"),
    _skill("speckit-specify", "Create or update a feature specification.", "1. Read `.specify/templates/spec-template.md`.\n2. Create `specs/<feature>/spec.md`.\n3. Keep requirements user-facing and implementation-free."),
    _skill("speckit-plan", "Create an implementation plan from an existing speckit spec.", "1. Read the active `spec.md`.\n2. Copy `.specify/templates/plan-template.md` to `plan.md`.\n3. Fill technical context and constitution checks."),
    _skill("speckit-tasks", "Create an ordered task list from the speckit plan.", "1. Read `plan.md` and related design docs.\n2. Copy `.specify/templates/tasks-template.md` to `tasks.md`.\n3. Keep tasks independently verifiable."),
    _skill("speckit-implement", "Implement a task slice from speckit task files.", "1. Read `tasks.md`.\n2. Execute the requested task scope.\n3. Run the validation named by the project."),
    _skill("speckit-checklist", "Create or update a speckit checklist.", "1. Read `.specify/templates/checklist-template.md`.\n2. Write checklist files under the active spec directory.\n3. Keep checklist items objective."),
    _skill("speckit-analyze", "Analyze speckit documents for consistency.", "1. Read spec, plan, and tasks.\n2. Report contradictions, ambiguities, and missing validation."),
    _skill("speckit-clarify", "Clarify unresolved requirements in a speckit spec.", "1. Identify unresolved choices.\n2. Ask only scope-changing questions.\n3. Update the spec with resolved answers."),
    _skill("speckit-constitution", "Initialize or update project constitution text.", "1. Read `.specify/templates/constitution-template.md`.\n2. Write constitution changes only when explicitly requested."),
    _skill("speckit-taskstoissues", "Translate speckit tasks into issue-ready units.", "1. Read `tasks.md`.\n2. Group related tasks into independently reviewable issue bodies."),
    _skill("speckit-git-feature", "Use the speckit git feature helper.", "1. Read `.specify/extensions/git/commands/speckit.git.feature.md`.\n2. Keep branch operations explicit and user-approved."),
    _skill("speckit-git-initialize", "Use the speckit git initialization helper.", "1. Read `.specify/extensions/git/commands/speckit.git.initialize.md`.\n2. Initialize only the current target project."),
    _skill("speckit-git-commit", "Use the speckit git commit helper.", "1. Read `.specify/extensions/git/commands/speckit.git.commit.md`.\n2. Commit only requested path changes."),
    _skill("speckit-git-remote", "Use the speckit git remote helper.", "1. Read `.specify/extensions/git/commands/speckit.git.remote.md`.\n2. Never transmit secrets."),
    _skill("speckit-git-validate", "Use the speckit git validation helper.", "1. Read `.specify/extensions/git/commands/speckit.git.validate.md`.\n2. Run project validation commands."),
)


def _default_writer(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _resolve_artifact_path(target: Path, relpath: str) -> Path:
    relative = Path(relpath)
    if relative.is_absolute() or ".." in relative.parts:
        raise UnsafeArtifactPathError(f"artifact path must be target-relative: {relpath}")
    return target / relative


def scaffold_speckit(
    target: str | Path,
    *,
    force: bool = False,
    artifacts: Iterable[ScaffoldArtifact] = DEFAULT_ARTIFACTS,
    writer: FileWriter | None = None,
) -> ScaffoldResult:
    """Scaffold speckit files into an existing target directory.

    Existing files are skipped unless ``force`` is true. The target directory is
    never created implicitly, so a misspelled ``--target`` fails closed.
    """

    root = Path(target).expanduser().resolve()
    if not root.is_dir():
        raise MissingTargetError(f"target does not exist or is not a directory: {root}")

    write = writer or _default_writer
    created: list[str] = []
    skipped: list[str] = []
    overwritten: list[str] = []

    for artifact in artifacts:
        destination = _resolve_artifact_path(root, artifact.path)
        if destination.exists() and not force:
            skipped.append(artifact.path)
            continue
        existed = destination.exists()
        try:
            write(destination, artifact.content)
        except OSError as exc:
            raise ScaffoldWriteError(f"could not write {artifact.path}: {exc}") from exc
        if existed:
            overwritten.append(artifact.path)
        else:
            created.append(artifact.path)

    return ScaffoldResult(
        target=root,
        created=tuple(created),
        skipped=tuple(skipped),
        overwritten=tuple(overwritten),
    )


__all__ = [
    "DEFAULT_ARTIFACTS",
    "FileWriter",
    "MissingTargetError",
    "ScaffoldArtifact",
    "ScaffoldResult",
    "ScaffoldWriteError",
    "SpeckitInitError",
    "UnsafeArtifactPathError",
    "scaffold_speckit",
]
