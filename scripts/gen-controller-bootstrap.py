#!/usr/bin/env python3
"""Preview-only controller bootstrap generator for ce-ops#244.

This scaffold intentionally does not mutate live harness files. It renders
bootstrap previews from a tracked JSON SSOT so reviewers can inspect the
cross-harness content before any separately ratified injection step exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from textwrap import dedent
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SSOT = REPO_ROOT / "docs/design/controller-bootstrap-ssot.json"
LIVE_ROOT_FILES = {
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "CLAUDE.md",
}
LIVE_AGENT_ROOT = REPO_ROOT / ".claude/agents"
CANONICAL_ROLES = ("architect_research", "implementer", "verification")
REQUIRED_SECTIONS = (
    "metadata",
    "canonical_roles",
    "schema_roles",
    "foreman_directive",
    "safety_floor",
    "vocabulary_mapping",
    "worker_selection_policy",
    "controller_knowledge_overlay",
    "acceptance_safety_notes",
    "harness_outputs",
)


def require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"invalid SSOT: {path} must be an object")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise SystemExit(f"invalid SSOT: {path} must be a non-empty array")
    return value


def require_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"invalid SSOT: {path} must be a non-empty string")
    return value


def load_ssot(path: Path) -> tuple[dict[str, Any], str, str]:
    resolved = path.expanduser().resolve()
    try:
        raw = resolved.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"SSOT not found: {resolved}") from exc
    try:
        ssot = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid SSOT JSON {resolved}: {exc}") from exc

    validate_ssot(ssot)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return ssot, str(resolved.relative_to(REPO_ROOT)), digest


def validate_ssot(ssot: Any) -> None:
    root = require_mapping(ssot, "$")
    for section in REQUIRED_SECTIONS:
        if section not in root:
            raise SystemExit(f"invalid SSOT: missing required section {section!r}")

    metadata = require_mapping(root["metadata"], "$.metadata")
    for key in (
        "schema_version",
        "source",
        "status",
        "preview_warning",
        "ratification_status",
    ):
        require_text(metadata.get(key), f"$.metadata.{key}")

    roles = require_mapping(root["canonical_roles"], "$.canonical_roles")
    missing_roles = [role for role in CANONICAL_ROLES if role not in roles]
    if missing_roles:
        raise SystemExit(
            "invalid SSOT: missing canonical role(s) "
            + ", ".join(sorted(missing_roles))
        )
    unknown_roles = [role for role in roles if role not in CANONICAL_ROLES]
    if unknown_roles:
        raise SystemExit(
            "invalid SSOT: unknown canonical role(s) "
            + ", ".join(sorted(unknown_roles))
        )
    for role_name, role in roles.items():
        role_path = f"$.canonical_roles.{role_name}"
        role_obj = require_mapping(role, role_path)
        for key in (
            "purpose",
            "allowed_work",
            "disallowed_work",
            "claude_tools",
            "mount_default",
            "egress_default",
            "credential_default",
            "boundaries",
            "evidence",
        ):
            require_list(role_obj.get(key), f"{role_path}.{key}")
        require_list(role_obj.get("aliases"), f"{role_path}.aliases")
        require_text(role_obj.get("spec005_grounding"), f"{role_path}.spec005_grounding")

    schema_roles = require_mapping(root["schema_roles"], "$.schema_roles")
    reviewer = require_mapping(schema_roles.get("reviewer"), "$.schema_roles.reviewer")
    if reviewer.get("maps_to") != "verification":
        raise SystemExit(
            "invalid SSOT: $.schema_roles.reviewer.maps_to must be verification"
        )
    for key in ("description", "canonical_role_statement", "frontmatter_name"):
        require_text(reviewer.get(key), f"$.schema_roles.reviewer.{key}")
    require_list(reviewer.get("aliases"), "$.schema_roles.reviewer.aliases")

    require_list(root["foreman_directive"], "$.foreman_directive")
    require_list(root["safety_floor"], "$.safety_floor")
    require_mapping(root["vocabulary_mapping"], "$.vocabulary_mapping")
    require_list(root["worker_selection_policy"], "$.worker_selection_policy")
    overlay = require_mapping(
        root["controller_knowledge_overlay"], "$.controller_knowledge_overlay"
    )
    for key in (
        "startup_sequence",
        "pre_dispatch_checklist",
        "harvest_sequence",
        "preflight_discipline",
        "g5_body_line_rule",
        "new_ce_group_coupling",
        "merge_gate_checklist",
    ):
        require_list(overlay.get(key), f"$.controller_knowledge_overlay.{key}")
    require_mapping(
        overlay.get("subagent_model_routing"),
        "$.controller_knowledge_overlay.subagent_model_routing",
    )

    outputs = require_mapping(root["harness_outputs"], "$.harness_outputs")
    for harness in ("codex", "claude"):
        harness_obj = require_mapping(outputs.get(harness), f"$.harness_outputs.{harness}")
        require_list(harness_obj.get("files"), f"$.harness_outputs.{harness}.files")


def bullet_lines(values: list[Any], indent: str = "- ") -> str:
    return "\n".join(f"{indent}{require_text(value, 'list item')}" for value in values)


def render_metadata(ssot: dict[str, Any], ssot_path: str, ssot_hash: str) -> str:
    metadata = ssot["metadata"]
    return "\n".join(
        (
            f"Preview source: {metadata['source']}",
            f"SSOT path: `{ssot_path}`",
            f"SSOT schema version: `{metadata['schema_version']}`",
            f"SSOT sha256: `{ssot_hash}`",
            "",
            metadata["preview_warning"],
        )
    )


def render_vocabulary(ssot: dict[str, Any]) -> str:
    rows = "\n".join(
        f"- {source}: {target}"
        for source, target in ssot["vocabulary_mapping"].items()
    )
    reviewer = ssot["schema_roles"]["reviewer"]
    return "\n".join(
        (
            "## Vocabulary Reconciliation",
            "",
            "Canonical worker vocabulary is grounded in Spec 005 section d.2:",
            "`architect_research`, `implementer`, and `verification`.",
            "",
            reviewer["canonical_role_statement"],
            "",
            rows,
        )
    )


def render_role_reference(ssot: dict[str, Any]) -> str:
    blocks = []
    for role_name in CANONICAL_ROLES:
        role = ssot["canonical_roles"][role_name]
        blocks.append(
            "\n".join(
                (
                    f"### {role_name}",
                    f"Aliases: {', '.join(role['aliases'])}",
                    "",
                    f"Purpose: {role['purpose'][0]}",
                    "",
                    f"Spec 005 grounding: {role['spec005_grounding']}",
                    "",
                    f"Mount default: {role['mount_default'][0]}",
                    "",
                    f"Egress default: {role['egress_default'][0]}",
                    "",
                    f"Credential default: {role['credential_default'][0]}",
                    "",
                    "Allowed work:",
                    bullet_lines(role["allowed_work"]),
                    "",
                    "Disallowed work:",
                    bullet_lines(role["disallowed_work"]),
                    "",
                    "Boundaries:",
                    bullet_lines(role["boundaries"]),
                    "",
                    "Expected evidence:",
                    bullet_lines(role["evidence"]),
                )
            )
        )

    reviewer = ssot["schema_roles"]["reviewer"]
    blocks.append(
        "\n".join(
            (
                "### reviewer (schema/harness review role)",
                f"Aliases: {', '.join(reviewer['aliases'])}",
                "",
                f"Maps to canonical role: `{reviewer['maps_to']}`",
                "",
                reviewer["description"],
                "",
                reviewer["canonical_role_statement"],
            )
        )
    )
    return "\n\n".join(blocks)


def render_worker_selection(ssot: dict[str, Any]) -> str:
    return "\n".join(
        (
            "## Worker Selection Policy",
            "",
            bullet_lines(ssot["worker_selection_policy"]),
        )
    )


def render_mapping_lines(values: dict[str, Any]) -> str:
    lines = []
    for key, value in values.items():
        if isinstance(value, list):
            require_list(value, f"mapping item {key}")
            rendered_value = "; ".join(
                require_text(item, f"mapping item {key}") for item in value
            )
        else:
            rendered_value = require_text(value, f"mapping item {key}")
        lines.append(f"- {key}: {rendered_value}")
    return "\n".join(lines)


def render_knowledge_overlay(ssot: dict[str, Any]) -> str:
    overlay = ssot["controller_knowledge_overlay"]
    sections = (
        ("Startup Sequence", bullet_lines(overlay["startup_sequence"])),
        ("Pre-Dispatch Checklist", bullet_lines(overlay["pre_dispatch_checklist"])),
        ("Harvest Sequence", bullet_lines(overlay["harvest_sequence"])),
        (
            "Subagent Model Routing",
            render_mapping_lines(overlay["subagent_model_routing"]),
        ),
        ("Preflight Discipline", bullet_lines(overlay["preflight_discipline"])),
        ("G5 Body-Line Rule", bullet_lines(overlay["g5_body_line_rule"])),
        ("New ce Group Coupling", bullet_lines(overlay["new_ce_group_coupling"])),
        ("Merge-Gate Checklist", bullet_lines(overlay["merge_gate_checklist"])),
    )
    rendered_sections: list[str] = []
    for title, body in sections:
        rendered_sections.extend((f"### {title}", "", body, ""))
    return "\n".join(
        (
            "## Controller Knowledge Overlay",
            "",
            ssot["metadata"]["preview_warning"],
            "",
            *rendered_sections,
        )
    ).rstrip()


def render_foreman_core(
    ssot: dict[str, Any], harness: str, ssot_path: str, ssot_hash: str
) -> str:
    return "\n".join(
        (
            f"# CE Controller Bootstrap Preview - {harness}",
            "",
            render_metadata(ssot, ssot_path, ssot_hash),
            "",
            "## Foreman Directive",
            "",
            bullet_lines(ssot["foreman_directive"]),
            "",
            "Inline controller work is limited to planning, dispatching, monitoring,",
            "triage, local status inspection, and trivial coordination edits.",
            "Code-producing work, feature construction, full review, and binding",
            "source-host actions are worker work.",
            "",
            "## Spec 005 Safety Floor",
            "",
            bullet_lines(ssot["safety_floor"]),
            "",
            "Workers must never receive the Slice 2.5 controller-key private key.",
            "",
            render_vocabulary(ssot),
            "",
            render_worker_selection(ssot),
            "",
            render_knowledge_overlay(ssot),
            "",
            "## Canonical Roles",
            "",
            render_role_reference(ssot),
            "",
        )
    )


def render_codex_agents(ssot: dict[str, Any], ssot_path: str, ssot_hash: str) -> str:
    reviewer = ssot["schema_roles"]["reviewer"]
    return render_foreman_core(ssot, "codex/AGENTS.md", ssot_path, ssot_hash) + dedent(
        f"""

        ## Codex Harness Policy

        A Codex controller may use harness-friendly terms when delegating:
        explorer maps to `architect_research`, implementer maps to
        `implementer`, and reviewer maps to canonical `verification` as a
        non-author review specialization.

        {reviewer["canonical_role_statement"]}

        Test reproduction, CI log replay, and build evidence remain
        `verification` work unless a separately ratified policy grants a
        different role-shaped envelope.

        Do not overwrite live AGENTS.md from this preview. The preview path is
        `codex/AGENTS.md` under the selected output directory.
        """
    )


def render_claude_md(ssot: dict[str, Any], ssot_path: str, ssot_hash: str) -> str:
    return render_foreman_core(ssot, "claude/CLAUDE.md", ssot_path, ssot_hash) + dedent(
        """

        ## Claude Harness Policy

        The Claude controller bootstraps from this foreman directive plus the
        role files under `.claude/agents/`. The launcher charter is previewed as
        `LAUNCHER_CHARTER.md` and records the handoff boundary between the
        visible controller pane and governed worker roles.

        Do not overwrite live CLAUDE.md from this preview. The preview path is
        `claude/CLAUDE.md` under the selected output directory.
        """
    )


def render_launcher_charter(
    ssot: dict[str, Any], ssot_path: str, ssot_hash: str
) -> str:
    return dedent(
        f"""
        # Launcher Charter Preview

        {render_metadata(ssot, ssot_path, ssot_hash)}

        The launcher starts the visible controller harness and binds it to the
        foreman operating mode. It does not grant worker credentials directly.
        Worker allocation, path capability grants, secret injection, and network
        policy are controller-mediated and role-shaped.

        Launcher invariants:
        - Preserve the visible pane substrate for operator inspection.
        - Keep controller identity outside worker containers.
        - Refuse launcher paths that would mount host home, long-lived source
          host credentials, model-provider secrets beyond the named policy, or
          Docker/Podman sockets into workers.
        - Treat generated files from `scripts/gen-controller-bootstrap.py` as
          previews until a separate ratified step installs them.
        """
    ).strip() + "\n"


def role_for_claude_file(ssot: dict[str, Any], role_name: str) -> dict[str, Any]:
    if role_name == "reviewer":
        reviewer = ssot["schema_roles"]["reviewer"]
        canonical = ssot["canonical_roles"][reviewer["maps_to"]]
        role = dict(canonical)
        role["frontmatter_name"] = reviewer["frontmatter_name"]
        role["canonical_name"] = reviewer["maps_to"]
        role["display_name"] = "reviewer"
        role["aliases"] = reviewer["aliases"]
        role["purpose"] = [reviewer["description"]]
        role["canonical_role_statement"] = reviewer["canonical_role_statement"]
        return role

    canonical = ssot["canonical_roles"][role_name]
    role = dict(canonical)
    role["frontmatter_name"] = role_name
    role["canonical_name"] = role_name
    role["display_name"] = role_name
    role["canonical_role_statement"] = f"Canonical role: `{role_name}`."
    return role


def render_claude_role(
    ssot: dict[str, Any], role_name: str, ssot_path: str, ssot_hash: str
) -> str:
    role = role_for_claude_file(ssot, role_name)
    canonical_name = role["canonical_name"]
    display_name = role["display_name"]
    description = (
        f"Preview-only CE governed worker for canonical `{canonical_name}` role"
    )
    if display_name == "reviewer":
        description += "; schema role reviewer is a review specialization mapped to canonical verification"
    description += "; preserves Spec 005 section d.2/f boundaries."

    return "\n".join(
        (
            "---",
            f"name: {role['frontmatter_name']}",
            f"description: {description}",
            f"tools: {', '.join(role['claude_tools'])}",
            "---",
            "",
            f"# Claude Agent Role Preview: {display_name}",
            "",
            f"Canonical role: `{canonical_name}`",
            f"Schema/harness role: `{display_name}`" if display_name != canonical_name else "Schema/harness role: same as canonical role.",
            role["canonical_role_statement"],
            f"Aliases: {', '.join(role['aliases'])}",
            f"SSOT path: `{ssot_path}`",
            f"SSOT sha256: `{ssot_hash}`",
            "Boundary source: Spec 005 section d.2 role-shaped defaults and section f safety floor.",
            "",
            "## Mission",
            "",
            role["purpose"][0],
            "",
            "## Isolation Defaults",
            "",
            f"Mount default: {role['mount_default'][0]}",
            "",
            f"Egress default: {role['egress_default'][0]}",
            "",
            f"Credential default: {role['credential_default'][0]}",
            "",
            "## Allowed Work",
            "",
            bullet_lines(role["allowed_work"]),
            "",
            "## Prohibited Work",
            "",
            bullet_lines(role["disallowed_work"]),
            "",
            "## Boundaries",
            "",
            bullet_lines(role["boundaries"]),
            "",
            "## Expected Evidence",
            "",
            bullet_lines(role["evidence"]),
            "",
            "## Non-Negotiable Safety Floor",
            "",
            "- No host home mount.",
            "- No SSH key, GPG key, GitHub CLI config, Claude config, Codex config, or browser cookie access.",
            "- No Docker or Podman socket mount.",
            "- No controller-key private key injection.",
            "- Secret values must not appear in tracked records or generated evidence.",
            "",
        )
    )


def build_files(
    ssot: dict[str, Any], harness: str, ssot_path: str, ssot_hash: str
) -> dict[Path, str]:
    files: dict[Path, str] = {}
    outputs = ssot["harness_outputs"]
    if harness in {"codex", "all"}:
        codex_files = outputs["codex"]["files"]
        if "codex/AGENTS.md" not in codex_files:
            raise SystemExit("invalid SSOT: codex harness must include codex/AGENTS.md")
        files[Path("codex/AGENTS.md")] = render_codex_agents(ssot, ssot_path, ssot_hash)
    if harness in {"claude", "all"}:
        claude_files = outputs["claude"]["files"]
        expected = {
            "claude/CLAUDE.md",
            "claude/LAUNCHER_CHARTER.md",
            "claude/.claude/agents/architect_research.md",
            "claude/.claude/agents/implementer.md",
            "claude/.claude/agents/verification.md",
            "claude/.claude/agents/reviewer.md",
        }
        missing = sorted(expected.difference(claude_files))
        if missing:
            raise SystemExit(
                "invalid SSOT: claude harness missing expected file(s) "
                + ", ".join(missing)
            )
        files[Path("claude/CLAUDE.md")] = render_claude_md(ssot, ssot_path, ssot_hash)
        files[Path("claude/LAUNCHER_CHARTER.md")] = render_launcher_charter(
            ssot, ssot_path, ssot_hash
        )
        for role_name in (
            "architect_research",
            "implementer",
            "verification",
            "reviewer",
        ):
            files[Path(f"claude/.claude/agents/{role_name}.md")] = render_claude_role(
                ssot, role_name, ssot_path, ssot_hash
            )
    return files


def is_live_agent_path(path: Path) -> bool:
    try:
        path.relative_to(LIVE_AGENT_ROOT)
    except ValueError:
        return False
    return True


def ensure_safe_out_dir(out_dir: Path) -> Path:
    resolved = out_dir.expanduser().resolve()
    if resolved == REPO_ROOT:
        raise SystemExit(f"refusing --out-dir that resolves to repo root: {resolved}")
    if resolved in LIVE_ROOT_FILES:
        raise SystemExit(f"refusing --out-dir that is a live root file: {resolved}")
    if resolved == LIVE_AGENT_ROOT or is_live_agent_path(resolved):
        raise SystemExit(f"refusing --out-dir under live Claude agent root: {resolved}")
    if resolved.exists() and not resolved.is_dir():
        raise SystemExit(f"refusing --out-dir that is not a directory: {resolved}")
    return resolved


def write_preview_files(out_dir: Path, files: dict[Path, str]) -> None:
    resolved_out_dir = ensure_safe_out_dir(out_dir)
    resolved_out_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, content in files.items():
        target = (resolved_out_dir / rel_path).resolve()
        if not target.is_relative_to(resolved_out_dir):
            raise SystemExit(f"refusing path escape for generated file: {rel_path}")
        if target in LIVE_ROOT_FILES or is_live_agent_path(target):
            raise SystemExit(f"refusing to overwrite live bootstrap path: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"wrote {target}")


def print_preview_files(files: dict[Path, str]) -> None:
    for rel_path, content in files.items():
        print(f"===== BEGIN {rel_path} =====")
        print(content, end="" if content.endswith("\n") else "\n")
        print(f"===== END {rel_path} =====")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate preview-only controller bootstrap files."
    )
    parser.add_argument(
        "--ssot",
        type=Path,
        default=DEFAULT_SSOT,
        help=f"Path to controller bootstrap JSON SSOT. Default: {DEFAULT_SSOT}",
    )
    parser.add_argument(
        "--harness",
        choices=("codex", "claude", "all"),
        default="all",
        help="Harness preview to generate. Default: all.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help=(
            "Preview directory. Generated files are written below this directory "
            "only. When omitted, previews are printed to stdout."
        ),
    )
    parser.add_argument(
        "--list-files",
        action="store_true",
        help="List preview-relative files that would be generated and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ssot, ssot_path, ssot_hash = load_ssot(args.ssot)
    files = build_files(ssot, args.harness, ssot_path, ssot_hash)

    if args.list_files:
        for rel_path in files:
            print(rel_path)
        return 0

    if args.out_dir is None:
        print_preview_files(files)
        return 0

    write_preview_files(args.out_dir, files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
