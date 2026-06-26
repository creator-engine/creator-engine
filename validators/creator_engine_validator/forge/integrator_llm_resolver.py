"""Read-only LLM conflict resolver for Integrator Phase 2.

The resolver owns no apply path. It converts conflict-marker text into a
structured prompt payload, calls an injected client in read-only mode, and
returns a structured repair artifact. The executor remains the only component
that can write resolved content.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, Literal, Protocol

ResolutionType = Literal["mechanical_assist", "llm_resolved", "escalate"]
_MIN_CONFIDENCE = 0.5


@dataclass(frozen=True)
class LLMConflictInput:
    """Structured, read-only conflict input for an LLM resolver client."""

    path: str
    base_content: str
    ours_content: str
    theirs_content: str
    conflict_markers: tuple[str, ...]
    conflicted_content: str
    context_files: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "base_content": self.base_content,
            "ours_content": self.ours_content,
            "theirs_content": self.theirs_content,
            "conflict_markers": list(self.conflict_markers),
            "conflicted_content": self.conflicted_content,
            "context_files": dict(self.context_files),
        }


@dataclass(frozen=True)
class LLMRepairArtifact:
    """Structured repair artifact emitted by the read-only LLM resolver."""

    resolved_content: str
    confidence: float
    rationale: str
    resolution_type: ResolutionType

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolved_content": self.resolved_content,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "resolution_type": self.resolution_type,
        }


class LLMClient(Protocol):
    """Configurable LLM client seam.

    Implementations may call a real model elsewhere, but tests and offline
    callers can provide a stub. The resolver always passes ``read_only=True``.
    """

    def resolve_conflict(self, conflict: LLMConflictInput, *, read_only: bool) -> LLMRepairArtifact:
        """Return a structured repair artifact for ``conflict``."""


class OfflineEscalatingLLMClient:
    """Default offline client: no API call, no content proposal."""

    def resolve_conflict(self, conflict: LLMConflictInput, *, read_only: bool) -> LLMRepairArtifact:
        assert read_only is True
        return LLMRepairArtifact(
            resolved_content="",
            confidence=0.0,
            rationale="llm resolver unavailable/offline",
            resolution_type="escalate",
        )


def resolve_with_llm(
    conflict: LLMConflictInput,
    *,
    client: LLMClient,
) -> LLMRepairArtifact:
    """Call the client in enforced read-only mode and normalize fail-closed."""

    read_only = True
    assert read_only is True
    raw = client.resolve_conflict(conflict, read_only=read_only)
    return _normalize_artifact(raw)


def resolve_conflict_text_with_llm(
    *,
    path: str,
    conflicted_text: str,
    client: LLMClient,
    context_files: Mapping[str, str] | None = None,
) -> LLMRepairArtifact:
    """Parse conflict-marker text and return a read-only LLM repair artifact."""

    conflict = conflict_input_from_text(
        path=path,
        conflicted_text=conflicted_text,
        context_files=context_files or {},
    )
    return resolve_with_llm(conflict, client=client)


def conflict_input_from_text(
    *,
    path: str,
    conflicted_text: str,
    context_files: Mapping[str, str] | None = None,
) -> LLMConflictInput:
    """Build structured conflict input from one file's conflict-marker text."""

    ours: list[str] = []
    theirs: list[str] = []
    base: list[str] = []
    markers: list[str] = []
    state = "normal"
    saw_hunk = False
    hunk_has_base = False

    for line in conflicted_text.splitlines(keepends=True):
        marker = _marker_kind(line)
        if marker is not None:
            markers.append(line.rstrip("\n"))
            saw_hunk = True
            if marker == "ours":
                if state != "normal":
                    return _malformed_input(path, conflicted_text, context_files, markers)
                state = "ours"
                continue
            if marker == "base":
                if state != "ours":
                    return _malformed_input(path, conflicted_text, context_files, markers)
                state = "base"
                hunk_has_base = True
                continue
            if marker == "separator":
                if state not in {"ours", "base"}:
                    return _malformed_input(path, conflicted_text, context_files, markers)
                state = "theirs"
                continue
            if marker == "end":
                if state != "theirs":
                    return _malformed_input(path, conflicted_text, context_files, markers)
                state = "normal"
                hunk_has_base = False
                continue

        if state == "normal":
            ours.append(line)
            theirs.append(line)
            base.append(line)
        elif state == "ours":
            ours.append(line)
            if not hunk_has_base:
                base.append(line)
        elif state == "base":
            base.append(line)
        elif state == "theirs":
            theirs.append(line)

    if state != "normal" or not saw_hunk:
        return _malformed_input(path, conflicted_text, context_files, markers)
    return LLMConflictInput(
        path=path,
        base_content="".join(base),
        ours_content="".join(ours),
        theirs_content="".join(theirs),
        conflict_markers=tuple(markers),
        conflicted_content=conflicted_text,
        context_files=dict(context_files or {}),
    )


def _normalize_artifact(artifact: LLMRepairArtifact) -> LLMRepairArtifact:
    resolution_type = artifact.resolution_type
    if resolution_type not in {"mechanical_assist", "llm_resolved", "escalate"}:
        return _escalate("invalid llm resolution_type", 0.0)
    try:
        confidence = float(artifact.confidence)
    except (TypeError, ValueError):
        return _escalate("invalid llm confidence", 0.0)
    if not 0.0 <= confidence <= 1.0:
        return _escalate("llm confidence outside 0..1", 0.0)
    rationale = str(artifact.rationale or "").strip() or "llm resolver provided no rationale"
    if resolution_type == "escalate":
        return LLMRepairArtifact("", confidence, rationale, "escalate")
    if confidence < _MIN_CONFIDENCE:
        return _escalate(f"llm confidence below {_MIN_CONFIDENCE}: {rationale}", confidence)
    content = str(artifact.resolved_content)
    if not content:
        return _escalate("llm resolver returned empty resolved content", confidence)
    if _contains_conflict_markers(content):
        return _escalate("llm resolver returned conflict markers", confidence)
    return replace(artifact, resolved_content=content, confidence=confidence, rationale=rationale)


def _marker_kind(line: str) -> str | None:
    if line.startswith("<<<<<<<"):
        return "ours"
    if line.startswith("|||||||"):
        return "base"
    if line.startswith("======="):
        return "separator"
    if line.startswith(">>>>>>>"):
        return "end"
    return None


def _malformed_input(
    path: str,
    conflicted_text: str,
    context_files: Mapping[str, str] | None,
    markers: list[str],
) -> LLMConflictInput:
    return LLMConflictInput(
        path=path,
        base_content="",
        ours_content="",
        theirs_content="",
        conflict_markers=tuple(markers),
        conflicted_content=conflicted_text,
        context_files=dict(context_files or {}),
    )


def _contains_conflict_markers(content: str) -> bool:
    return any(marker in content for marker in ("<<<<<<<", "|||||||", "=======", ">>>>>>>"))


def _escalate(rationale: str, confidence: float) -> LLMRepairArtifact:
    bounded = min(1.0, max(0.0, float(confidence)))
    return LLMRepairArtifact(
        resolved_content="",
        confidence=bounded,
        rationale=rationale,
        resolution_type="escalate",
    )
