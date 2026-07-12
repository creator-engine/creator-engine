"""Default-OFF, claim-safe provider primitives for governed reviewer spawns.

This module owns no forge, queue, or attestation authority.  Callers provide
all roots and execute the returned argv under their own role-shaped runtime.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


RESPONSE_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_RETENTION_SECONDS = 86_400
DEFAULT_CAPACITY = 0  # Default OFF until an Operator supplies explicit capacity.
MAX_RESPONSE_BYTES = 64 * 1024
_SHA = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_VERDICTS = frozenset({"COMMENT", "REQUEST_CHANGES"})


class ProviderRefused(RuntimeError):
    """A request, response, or durable claim failed closed."""


@dataclass(frozen=True)
class ProviderPolicy:
    """Controller-supplied limits; defaults deliberately leave the provider OFF."""

    capacity: int = DEFAULT_CAPACITY
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    retention_seconds: int = DEFAULT_RETENTION_SECONDS
    sandbox_attestation_required: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ProviderPolicy":
        values = os.environ if env is None else env
        try:
            capacity = int(values.get("CE_REVIEW_SPAWN_CAPACITY", str(DEFAULT_CAPACITY)))
            timeout = int(values.get("CE_REVIEW_SPAWN_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
            retention = int(values.get("CE_REVIEW_SPAWN_RETENTION_SECONDS", str(DEFAULT_RETENTION_SECONDS)))
        except ValueError as exc:
            raise ProviderRefused("review spawn policy values must be integers") from exc
        if capacity < 0 or timeout <= 0 or retention < 0:
            raise ProviderRefused("review spawn policy values are out of range")
        return cls(capacity, timeout, retention, values.get("CE_REVIEW_SPAWN_SANDBOX_ATTESTATION") == "1")


@dataclass(frozen=True)
class SpawnRequest:
    repo: str
    pr_number: int
    head_sha: str
    base_sha: str
    carrier_path_count: int
    carrier_sha256: str
    author: str
    reviewer: str
    request_id: str

    @property
    def claim_key(self) -> str:
        return f"{self.repo}:{self.pr_number}:{self.head_sha}"

    def as_json(self, worktree: str) -> dict[str, Any]:
        return {"version": RESPONSE_VERSION, "request_id": self.request_id, "repo": self.repo,
                "pr_number": self.pr_number, "head_sha": self.head_sha, "base_sha": self.base_sha,
                "carrier": {"path_count": self.carrier_path_count, "sha256": self.carrier_sha256},
                "author": self.author, "reviewer": self.reviewer, "worktree": worktree}


@dataclass(frozen=True)
class ReviewerFinding:
    path: str
    line: int
    detail: str


@dataclass(frozen=True)
class ReviewerResponse:
    verdict: str
    summary: str
    findings: tuple[ReviewerFinding, ...]


def parse_request(payload: Mapping[str, Any]) -> SpawnRequest:
    """Validate the versioned provider request before any claim or process work."""
    carrier = payload.get("carrier")
    if not isinstance(carrier, Mapping):
        raise ProviderRefused("request carrier is required")
    request = SpawnRequest(
        repo=str(payload.get("repo") or ""), pr_number=payload.get("pr_number"),
        head_sha=str(payload.get("head_sha") or "").lower(), base_sha=str(payload.get("base_sha") or "").lower(),
        carrier_path_count=carrier.get("path_count"), carrier_sha256=str(carrier.get("sha256") or "").lower(),
        author=str(payload.get("author") or ""), reviewer=str(payload.get("reviewer") or ""),
        request_id=str(payload.get("request_id") or ""),
    )
    if payload.get("version") != RESPONSE_VERSION or not request.repo or not request.request_id:
        raise ProviderRefused("request version, repo, and request_id are required")
    if (isinstance(request.pr_number, bool) or not isinstance(request.pr_number, int) or request.pr_number <= 0
            or not _SHA.fullmatch(request.head_sha) or not _SHA.fullmatch(request.base_sha)
            or not _DIGEST.fullmatch(request.carrier_sha256) or request.carrier_path_count < 0
            or not request.author or not request.reviewer or request.author == request.reviewer):
        raise ProviderRefused("request bindings are invalid")
    return request


def parse_response(raw: bytes, request: SpawnRequest) -> ReviewerResponse:
    """Accept exactly one bounded JSON response bound to the immutable request."""
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ProviderRefused("reviewer response exceeds cap")
    try:
        text = raw.decode("utf-8")
        if not text.endswith("\n") or text.count("\n") != 1:
            raise ValueError("response must be one JSON object")
        payload = json.loads(text)
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise ProviderRefused("reviewer response is malformed") from exc
    if not isinstance(payload, Mapping):
        raise ProviderRefused("reviewer response is not an object")
    bindings = ("request_id", "repo", "pr_number", "head_sha", "author", "reviewer")
    expected = (request.request_id, request.repo, request.pr_number, request.head_sha, request.author, request.reviewer)
    if payload.get("version") != RESPONSE_VERSION or tuple(payload.get(key) for key in bindings) != expected:
        raise ProviderRefused("reviewer response bindings mismatch")
    verdict, summary, findings = payload.get("verdict"), payload.get("summary"), payload.get("findings")
    if verdict not in _VERDICTS or not isinstance(summary, str) or len(summary.encode()) > 4096 or not isinstance(findings, list):
        raise ProviderRefused("reviewer response fields are invalid")
    parsed: list[ReviewerFinding] = []
    for finding in findings:
        if not isinstance(finding, Mapping):
            raise ProviderRefused("reviewer finding is invalid")
        path, line, detail = finding.get("path"), finding.get("line"), finding.get("detail")
        if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts or isinstance(line, bool) or not isinstance(line, int) or line < 1 or not isinstance(detail, str) or len(detail.encode()) > 32768:
            raise ProviderRefused("reviewer finding is invalid")
        parsed.append(ReviewerFinding(path, line, detail))
    return ReviewerResponse(verdict, summary, tuple(parsed))


def _claim_file(state_root: Path, request: SpawnRequest) -> Path:
    digest = hashlib.sha256(request.claim_key.encode()).hexdigest()
    return state_root / "claims" / f"{digest}.json"


def acquire_dispatch_claim(state_root: Path | str, request: SpawnRequest, *, owner: str, nonce: str) -> bool:
    """Atomically test-and-set a claim using a sibling ``flock`` lock.

    The lock protects the complete read/fold/write sequence, so competing
    providers cannot both observe an absent tuple and launch duplicate work.
    """
    root = Path(state_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    claim = _claim_file(root, request)
    claim.parent.mkdir(parents=True, exist_ok=True)
    lock = claim.with_suffix(".lock")
    with lock.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            if claim.exists():
                try:
                    prior = json.loads(claim.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise ProviderRefused("dispatch claim is unreadable") from exc
                if prior.get("claim_key") == request.claim_key:
                    return False
                raise ProviderRefused("dispatch claim collision")
            claim.write_text(json.dumps({"claim_key": request.claim_key, "owner": owner,
                                         "reviewer": request.reviewer, "nonce": nonce}, sort_keys=True) + "\n", encoding="utf-8")
            return True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def reviewer_argv(executable: str, request_path: Path, response_path: Path) -> tuple[str, ...]:
    """Fixed argv construction: caller supplies only a fixed executable path."""
    if not executable or any(char.isspace() for char in executable):
        raise ProviderRefused("reviewer executable must be a single argv value")
    return (executable, "--request", str(request_path), "--response", str(response_path))
