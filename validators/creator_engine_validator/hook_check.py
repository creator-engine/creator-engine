"""Validator-backed hook bridge for Claude Code hooks (CC-G-B).

This module is the Ring 2 (VALIDATOR) substrate that a future Ring 1
Claude ``command``-type hook-pack (CC-G-C) calls in-band so that real-time
scope / mechanics / secret / completion gates and post-hoc verification
never diverge. It evaluates a single Claude hook event deterministically
and returns a machine-readable allow/deny/block decision.

Design contract: ``docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md``
(governed-posture predicate §7; prohibited mechanics §5; the three-ring
model §8). The posture predicate, manifest parsing, mutation-class
vocabulary, and completion-report checks are **reused** from the existing
validator surfaces rather than reimplemented:

* posture       → ``checks.pane_registry.evaluate_posture``
* path manifest → ``checks.path_manifest_fidelity.extract_manifest_paths*``
* mechanics     → ``checks.mutation_class.RESERVED_RESTRICTED``
* completion    → ``checks.completion_report_schema`` /
                  ``checks.completion_report_required_for_envelope`` /
                  ``checks.completion_report_terminal_sections``

Scope discipline: this module never launches Claude, never spawns a pane,
never authors ``.claude/**``, never runs live Integration Queue commands,
and never reads or echoes credential/secret bytes. It only classifies the
event it is handed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .checks import completion_report_required_for_envelope, completion_report_schema
from .checks import mutation_class
from .checks.completion_report_terminal_sections import CANONICAL_HEADERS, _header_positions
from .checks.path_manifest_fidelity import extract_manifest_paths_from_file

CONTRACT = "docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md"

# Tools whose target file_path is subject to the scope gate.
SCOPE_TOOLS = frozenset({"Edit", "Write", "MultiEdit"})

OUT_OF_MANIFEST_REASON = "tracked path is outside the ratified path manifest"


# --------------------------------------------------------------------------
# Decision / context value objects
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class HookContext:
    """Resolved evaluation context for one hook event.

    ``posture`` is ``"governed"`` or ``"ungoverned"``. ``manifest_paths`` are
    repo-relative tracked paths the active ratified manifest authorizes.
    ``evidence_root`` is the ignored evidence-root prefix the gate may write
    under. ``closeout_text`` / ``completion_report_path`` feed the Stop gate.
    ``side_effect_authority`` is the validated, bounded reviewer-venue authority
    envelope (a ``reviewer_authority_envelope`` mapping) that opens exactly one
    restricted mechanic (``pr_review``) on exactly one PR — G2.007.2. ``None`` means
    no authority (restricted mechanics stay denied under governed posture). A raw
    string/loose token is NOT honored; only a schema-valid envelope is.
    """

    posture: str
    manifest_paths: tuple[str, ...] = ()
    evidence_root: str | None = None
    closeout_text: str | None = None
    completion_report_path: str | None = None
    side_effect_authority: dict | None = None
    repo_root: str | None = None


@dataclass(frozen=True)
class HookDecision:
    """A deterministic hook decision, serializable to Claude-hook JSON."""

    ok: bool
    hook_event_name: str
    posture: str
    decision: str  # "allow" | "deny" | "block"
    reason: str
    advisory: bool = False
    would_have_denied: bool = False
    hook_specific_output: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "hookEventName": self.hook_event_name,
            "posture": self.posture,
            "decision": self.decision,
            "reason": self.reason,
            "advisory": self.advisory,
            "wouldHaveDenied": self.would_have_denied,
            "hookSpecificOutput": dict(self.hook_specific_output),
        }

    def to_claude_hook_dict(self) -> dict[str, Any]:
        """Render the minimal Claude Code hook output for this decision.

        This is an *additive* CC-G-C presentation seam; it changes no CC-G-B
        decision semantics. The mapping is:

        * ``PreToolUse`` → ``{"hookSpecificOutput": {"hookEventName":
          "PreToolUse", "permissionDecision": "deny"|"allow",
          "permissionDecisionReason": ...}}``. An ungoverned *advisory* deny
          already carries ``decision == "allow"`` here, so it maps to
          ``permissionDecision: "allow"`` — an ungoverned lane is never
          hard-denied — with the advisory context preserved in the reason.
        * ``Stop`` block → ``{"decision": "block", "reason": ...}``. A Stop
          allow/advisory emits no ``decision`` key (no-decision == allow).
        * any other event → ``{}`` (no Claude-actionable output).
        """
        if self.hook_event_name == "Stop":
            if self.decision == "block":
                return {"decision": "block", "reason": self.reason}
            return {}
        if self.hook_event_name == "PreToolUse":
            permission = "deny" if self.decision == "deny" else "allow"
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": permission,
                    "permissionDecisionReason": self.reason,
                }
            }
        return {}


# --------------------------------------------------------------------------
# Secret classification (PreToolUse Read)
# --------------------------------------------------------------------------

_SECRET_EXACT_NAMES = frozenset(
    {"credentials", "credentials.json", ".netrc", ".npmrc", ".pypirc", ".pgpass", ".htpasswd"}
)
_SECRET_KEY_NAMES = frozenset({"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"})
_SECRET_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx", ".keystore", ".jks"})
_SECRET_DIR_PARTS = frozenset({"secrets", ".ssh", ".gnupg", ".aws"})


def is_secret_path(file_path: Any) -> str | None:
    """Return a non-secret *category label* when ``file_path`` looks like a
    credential / token store, else ``None``.

    The returned label names the matched rule class (e.g. ``".env"`` or
    ``"private-key/cert"``); it is never the file's contents — this module
    never reads the file.
    """
    if not isinstance(file_path, str) or not file_path.strip():
        return None
    p = PurePosixPath(file_path.strip())
    name = p.name
    lowered = name.lower()
    if name == ".env" or name.startswith(".env."):
        return ".env"
    if name in _SECRET_EXACT_NAMES or name in _SECRET_KEY_NAMES:
        return name
    if p.suffix in _SECRET_SUFFIXES:
        return "private-key/cert"
    if set(p.parts) & _SECRET_DIR_PARTS:
        return "credential-store-directory"
    if "credential" in lowered or "secret" in lowered:
        return "credential-like-name"
    return None


# --------------------------------------------------------------------------
# Mechanics classification (PreToolUse Bash)
# --------------------------------------------------------------------------

# Commands that map cleanly onto the shared mutation-class reserved-restricted
# vocabulary. Reusing ``mutation_class.RESERVED_RESTRICTED`` keeps the bridge
# anchored to the canonical taxonomy rather than a bespoke parallel list.
_MECHANIC_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bgh\s+pr\s+merge\b"), "merge"),
    (re.compile(r"\bgit\s+push\b"), "deploy"),
    (re.compile(r"\b(npm|pnpm|yarn)\s+publish\b"), "publish"),
    (re.compile(r"\btwine\s+upload\b"), "publish"),
    (re.compile(r"\bcargo\s+publish\b"), "publish"),
    (re.compile(r"\bgit\s+branch\s+-[dD]\b"), "alter_repo_settings"),
)

# Mechanics the seat contract prohibits that do not map onto a mutation-class
# action verb. Classified with explicit non-vocabulary labels; still denied.
_MECHANIC_RULES_NONVOCAB: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bgh\s+pr\s+review\b"), "pr_review"),
    (re.compile(r"\bgh\s+pr\s+comment\b"), "pr_comment"),
    (re.compile(r"\bgh\s+pr\s+(close|reopen)\b"), "pr_lifecycle"),
    (re.compile(r"\bce\s+(launch|lane\s+launch)\b"), "live_lane_launch"),
    (re.compile(r"\bce\s+(integration-queue|iq)\b"), "live_integration_queue"),
)


def classify_mechanics(command: Any) -> str | None:
    """Return the restricted classification for ``command``, or ``None``.

    Mappable destructive git/release commands return a
    ``mutation_class.RESERVED_RESTRICTED`` action verb; other prohibited
    mechanics return a dedicated non-vocabulary label.
    """
    if not isinstance(command, str):
        return None
    for pattern, action in _MECHANIC_RULES + _MECHANIC_RULES_NONVOCAB:
        if pattern.search(command):
            return action
    return None


# --------------------------------------------------------------------------
# Scope (PreToolUse Edit / Write / MultiEdit)
# --------------------------------------------------------------------------


def _normalize_path(file_path: Any, repo_root: str | None) -> str | None:
    if not isinstance(file_path, str) or not file_path.strip():
        return None
    raw = file_path.strip()
    if raw.startswith("./"):
        raw = raw[2:]
    if repo_root and raw.startswith("/"):
        try:
            return PurePosixPath(raw).relative_to(PurePosixPath(repo_root)).as_posix()
        except ValueError:
            return raw
    return raw


def _path_under(path: str, prefix: str) -> bool:
    prefix = prefix.rstrip("/")
    return path == prefix or path.startswith(prefix + "/")


def is_in_manifest(path: str, manifest_paths: Iterable[str]) -> bool:
    for entry in manifest_paths:
        entry = entry.strip()
        if not entry:
            continue
        if path == entry:
            return True
        if entry.endswith("/") and _path_under(path, entry):
            return True
        if entry.endswith("/**") and _path_under(path, entry[:-3]):
            return True
        if ("*" in entry or "?" in entry) and PurePosixPath(path).match(entry):
            return True
    return False


def _scope_would_deny(file_path: Any, context: HookContext) -> str | None:
    path = _normalize_path(file_path, context.repo_root)
    if path is None:
        return None
    if context.evidence_root and _path_under(path, context.evidence_root.rstrip("/")):
        return None
    if is_in_manifest(path, context.manifest_paths):
        return None
    return OUT_OF_MANIFEST_REASON


# A reviewer-venue authority envelope authorizes exactly one mechanic + one PR. The
# hook can verify the mechanic and the target PR number from the command; head/actor/
# ratified_prompt_sha are auditable bindings the venue honors (the hook cannot re-derive
# head/actor from the command alone).
_PR_REVIEW_NUMBER_RE = re.compile(r"\bgh\s+pr\s+review\b[^|;&]*?\b([0-9]+)\b")


def _extract_pr_number(command: Any) -> int | None:
    if not isinstance(command, str):
        return None
    match = _PR_REVIEW_NUMBER_RE.search(command)
    return int(match.group(1)) if match else None


def _authority_covers(envelope: Any, action: str, command: Any) -> bool:
    """True only when a validated reviewer-authority envelope authorizes this exact
    mechanic AND (for pr_review) the command's target PR number. Any other mechanic,
    a wrong PR, or no/invalid envelope ⇒ not covered (deny)."""
    if not isinstance(envelope, dict):
        return False
    rec = envelope.get("reviewer_authority_envelope", envelope)
    if not isinstance(rec, dict):
        return False
    if str(rec.get("mechanic", "")).strip().lower() != action:
        return False
    if action == "pr_review":
        pr = _extract_pr_number(command)
        return pr is not None and pr == rec.get("pr_number")
    return False


def _mechanics_would_deny(command: Any, context: HookContext) -> str | None:
    action = classify_mechanics(command)
    if action is None:
        return None
    if _authority_covers(context.side_effect_authority, action, command):
        return None
    return (
        f"restricted mechanic ({action}) is denied without a matching ratified "
        "reviewer-venue side-effect-authority envelope (G2.007.2)"
    )


def _secret_would_deny(file_path: Any, context: HookContext) -> str | None:
    category = is_secret_path(file_path)
    if category is None:
        return None
    return f"read of credential-like path denied (matched rule: {category})"


# --------------------------------------------------------------------------
# Stop / completion-report closeout
# --------------------------------------------------------------------------

_NO_NEXT_GATE_MARKERS = (
    "no next gate",
    "no-next-gate",
    "no further gate",
    "no next source",
    "no_next_gate",
)


def _closeout_violation(text: str) -> str | None:
    """Return a violation message when ``text`` lacks the canonical terminal
    closeout sections, or ``None`` when satisfied.

    Reuses ``completion_report_terminal_sections`` header detection. The third
    canonical section may be satisfied either by its header or by an explicit
    no-next-gate statement in the body.
    """
    positions = _header_positions(text)
    present = {header for header, _ in positions}
    missing = [header for header in CANONICAL_HEADERS if header not in present]
    third = CANONICAL_HEADERS[2]
    if third in missing and any(marker in text.lower() for marker in _NO_NEXT_GATE_MARKERS):
        missing = [header for header in missing if header != third]
    if missing:
        return f"closeout missing canonical terminal section(s): {missing!r}"
    return None


def _completion_report_block(report_path: str) -> str | None:
    results = [
        completion_report_schema.run([Path(report_path)]),
        completion_report_required_for_envelope.run([Path(report_path)]),
    ]
    errors = [error for result in results for error in result.errors]
    if not errors:
        return None
    codes = sorted({error.code for error in errors})
    detail = "; ".join(error.format() for error in errors[:3])
    return f"referenced completion report failed checks {codes}: {detail}"


# --------------------------------------------------------------------------
# Event evaluation
# --------------------------------------------------------------------------


def _pre_tool_use_decision(would_deny_reason: str | None, context: HookContext) -> HookDecision:
    if would_deny_reason is None:
        reason = "permitted under active manifest / mechanics / secret policy"
        return HookDecision(
            ok=True,
            hook_event_name="PreToolUse",
            posture=context.posture,
            decision="allow",
            reason=reason,
            hook_specific_output={
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": reason,
            },
        )
    # G-i (v3 kickoff): under governed posture a *path-manifest mismatch* is now
    # ADVISORY (allow-with-warning), not a hard deny — author-time scope
    # containment moves to the PR-diff gate (path_manifest_fidelity --base). The
    # secret-path and restricted-mechanic denies are UNCHANGED: they remain hard
    # denies under governed posture. Branch on the reason so only the manifest
    # outcome is relaxed.
    manifest_mismatch = would_deny_reason == OUT_OF_MANIFEST_REASON
    if context.posture == "governed" and not manifest_mismatch:
        return HookDecision(
            ok=True,
            hook_event_name="PreToolUse",
            posture=context.posture,
            decision="deny",
            reason=would_deny_reason,
            would_have_denied=True,
            hook_specific_output={
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": would_deny_reason,
            },
        )
    # Advisory-allow: an ungoverned would-deny of any class, OR a governed
    # path-manifest mismatch (G-i). Still report what would have been denied.
    if manifest_mismatch and context.posture == "governed":
        reason = f"advisory (governed; manifest enforcement is advisory): would deny — {would_deny_reason}"
    else:
        reason = f"advisory (ungoverned): would deny — {would_deny_reason}"
    return HookDecision(
        ok=True,
        hook_event_name="PreToolUse",
        posture=context.posture,
        decision="allow",
        reason=reason,
        advisory=True,
        would_have_denied=True,
        hook_specific_output={
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        },
    )


def _evaluate_pre_tool_use(event: dict, context: HookContext) -> HookDecision:
    tool = event.get("tool_name") or event.get("toolName") or ""
    tool_input = event.get("tool_input") or event.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    would_deny_reason: str | None = None
    if tool in SCOPE_TOOLS:
        would_deny_reason = _scope_would_deny(tool_input.get("file_path"), context)
    elif tool == "Read":
        would_deny_reason = _secret_would_deny(tool_input.get("file_path"), context)
    elif tool == "Bash":
        would_deny_reason = _mechanics_would_deny(tool_input.get("command"), context)
    # Other tools have no governed scope/mechanics/secret rule here → allow.
    return _pre_tool_use_decision(would_deny_reason, context)


def _evaluate_stop(event: dict, context: HookContext) -> HookDecision:
    reasons: list[str] = []
    if context.closeout_text is None:
        reasons.append("no closeout text available to verify required terminal sections")
    else:
        violation = _closeout_violation(context.closeout_text)
        if violation:
            reasons.append(violation)
    if context.completion_report_path:
        cr_violation = _completion_report_block(context.completion_report_path)
        if cr_violation:
            reasons.append(cr_violation)
    hso = {"hookEventName": "Stop"}
    if not reasons:
        return HookDecision(
            ok=True,
            hook_event_name="Stop",
            posture=context.posture,
            decision="allow",
            reason="closeout satisfies the terminal-section contract",
            hook_specific_output=hso,
        )
    reason = "; ".join(reasons)
    if context.posture == "governed":
        return HookDecision(
            ok=True,
            hook_event_name="Stop",
            posture=context.posture,
            decision="block",
            reason=reason,
            would_have_denied=True,
            hook_specific_output=hso,
        )
    return HookDecision(
        ok=True,
        hook_event_name="Stop",
        posture=context.posture,
        decision="allow",
        reason=f"advisory (ungoverned): would block — {reason}",
        advisory=True,
        would_have_denied=True,
        hook_specific_output=hso,
    )


def evaluate(event: dict, context: HookContext) -> HookDecision:
    """Evaluate one Claude hook event against the resolved context."""
    name = event.get("hook_event_name") or event.get("hookEventName") or ""
    if name == "PreToolUse":
        return _evaluate_pre_tool_use(event, context)
    if name == "Stop":
        return _evaluate_stop(event, context)
    return HookDecision(
        ok=True,
        hook_event_name=name,
        posture=context.posture,
        decision="allow",
        reason=f"no governed rule for hook event {name!r}",
        hook_specific_output={"hookEventName": name},
    )


# --------------------------------------------------------------------------
# Context resolution (CLI / canonical hook path)
# --------------------------------------------------------------------------


def _posture_discovery_root(
    ledger_root: str | None, posture_root: str | None
) -> Path | None:
    """Resolve the directory under which the §7 posture claims+panes are discovered.

    Gate B (posture-claim reachability): a governed seat's REAL Active-Work Ledger is
    launch-pinned via ``--ledger-root`` (exported by ``ce lane launch`` as
    ``CE_LEDGER_ROOT`` — the analog of the proven ``reviewer-authority-ref`` seam).
    When pinned we discover under it, so a worktree seat — whose own tree carries no
    real ledger — resolves ``governed`` from its real claim, not a fixture.

    Otherwise we discover under ``<posture_root>/.hermes/active-work-ledger`` — **never
    the whole posture-root tree** — so tracked ``examples/**`` claim/pane fixtures (and
    snapshot copies) can never be matched as governing claims. ``None`` when neither a
    ledger nor a posture root is resolvable (caller falls to ``ungoverned``).
    """
    if ledger_root:
        return Path(ledger_root)
    if posture_root:
        return Path(posture_root) / ".hermes" / "active-work-ledger"
    return None


def _resolve_posture(
    ce: dict,
    posture_mode: str,
    posture_root: str | None,
    ledger_root: str | None = None,
):
    if posture_mode in {"governed", "ungoverned"}:
        return posture_mode, None
    explicit = ce.get("posture")
    if explicit in {"governed", "ungoverned"}:
        return explicit, None
    discovery_root = _posture_discovery_root(ledger_root, posture_root)
    if discovery_root is None or not discovery_root.is_dir():
        # No pinned ledger and no live ledger under the posture root → an
        # unallocated / unpinned seat. Fail to ungoverned (advisory floor); a
        # tracked examples/** fixture can no longer flip it to governed.
        return "ungoverned", None
    from .checks.pane_registry import evaluate_posture

    result = evaluate_posture([discovery_root])
    return result.posture, result.claim


def _resolve_manifest(manifest_doc, ce, posture_root, bound_claim) -> list[str]:
    if manifest_doc:
        paths = extract_manifest_paths_from_file(Path(manifest_doc))
        if paths:
            return paths
    ce_paths = ce.get("manifest_paths")
    if isinstance(ce_paths, list):
        return [str(p) for p in ce_paths]
    if bound_claim is not None and posture_root:
        envelope_ref = bound_claim.record.get("envelope_ref")
        if isinstance(envelope_ref, str) and envelope_ref:
            for candidate in (Path(posture_root) / envelope_ref, Path(envelope_ref)):
                if candidate.is_file():
                    paths = extract_manifest_paths_from_file(candidate)
                    if paths:
                        return paths
    return []


def _resolve_side_effect_authority(ce: dict, posture_root: str | None) -> dict | None:
    """Resolve a validated, bounded reviewer-venue authority envelope record, or None.

    Accepts an inline ``ce.reviewer_authority`` mapping or a ``ce.reviewer_authority_ref``
    path (resolved under ``posture_root``). A raw loose token is NOT honored — only a
    schema-valid ``reviewer_authority_envelope`` is. Fail-closed: any load/validation
    problem yields ``None`` (no authority).
    """
    from .checks.reviewer_authority_envelope import (
        KEY as _RVA_KEY,
        validate_reviewer_authority_envelope_record,
    )
    from .loader import LoaderError, load_yaml

    candidate: Any = None
    inline = ce.get("reviewer_authority")
    if isinstance(inline, dict):
        candidate = inline if _RVA_KEY in inline else {_RVA_KEY: inline}
    else:
        ref = ce.get("reviewer_authority_ref")
        if isinstance(ref, str) and ref:
            search = [Path(posture_root) / ref, Path(ref)] if posture_root else [Path(ref)]
            for path in search:
                if path.is_file():
                    try:
                        candidate = load_yaml(path)
                    except LoaderError:
                        candidate = None
                    break
    if not isinstance(candidate, dict):
        return None
    if validate_reviewer_authority_envelope_record(candidate, Path(posture_root or ".")):
        return None
    rec = candidate.get(_RVA_KEY)
    return rec if isinstance(rec, dict) else None


def build_context(
    event: dict,
    *,
    posture: str = "auto",
    posture_root: str | None = None,
    ledger_root: str | None = None,
    manifest_doc: str | None = None,
    evidence_root: str | None = None,
    closeout_file: str | None = None,
    completion_report: str | None = None,
) -> HookContext:
    """Build a :class:`HookContext` from a hook event plus optional overrides.

    Resolution precedence: explicit override flags > the event's ``ce``
    extension block > auto-resolution from ``.hermes`` posture inputs.

    ``ledger_root`` is the launch-pinned absolute Active-Work Ledger root (Gate B).
    When present it scopes the §7 posture claim/pane discovery to the seat's real
    ledger; otherwise discovery is scoped to ``<posture_root>/.hermes/active-work-ledger``.
    """
    ce = event.get("ce") if isinstance(event.get("ce"), dict) else {}
    posture_root = posture_root or ce.get("posture_root") or event.get("cwd")
    ledger_root = ledger_root or ce.get("ledger_root")
    posture_value, bound_claim = _resolve_posture(ce, posture, posture_root, ledger_root)
    manifest_paths = _resolve_manifest(manifest_doc, ce, posture_root, bound_claim)
    evidence_root = evidence_root or ce.get("evidence_root")
    completion_report = completion_report or ce.get("completion_report")
    side_effect_authority = _resolve_side_effect_authority(ce, posture_root)

    closeout_text = ce.get("closeout_text")
    if closeout_file:
        try:
            closeout_text = Path(closeout_file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            closeout_text = None

    return HookContext(
        posture=posture_value,
        manifest_paths=tuple(manifest_paths),
        evidence_root=evidence_root,
        closeout_text=closeout_text,
        completion_report_path=completion_report,
        side_effect_authority=side_effect_authority,
        repo_root=posture_root,
    )
