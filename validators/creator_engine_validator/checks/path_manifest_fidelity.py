"""Path manifest fidelity check.

Verifies that any handoff, recommended-prompt, or assignment-envelope
document under a path the consumer scans declares a fenced path
manifest whose normalized count and SHA256 match the document's own
``*_PATHS_COUNT=`` and ``*_PATHS_SHA256=`` declarations.

Emits explicit error classes used by both the validator and human
operators to disambiguate failures:

- ``path_manifest_count_mismatch``
- ``path_manifest_hash_mismatch``
- ``path_manifest_missing_declaration``
- ``path_manifest_missing_block``
- ``path_manifest_init_py_corruption``

The ``path_manifest_init_py_corruption`` class is the verifier-side
backstop for the paste-pipeline regression in which
``<package>/checks/__init__.py`` arrives as
``<package>/checks/init.py``. It is emitted at error level whenever a
fenced manifest line or a free-text path reference in the document
body is the literal corrupted form, regardless of whether the
declared count/hash also fail.

Pedagogical prose (regression docs, risk-register narrative) needs to
quote the corrupted form verbatim without tripping the verifier. The
opt-out is the same-line HTML sentinel
``<!-- path_manifest_fidelity: pedagogical -->``. The sentinel
suppresses an emitted error only when the corrupted token appears in
free-text prose, outside any triple-backtick ``text`` fenced block. A
corrupted token inside a triple-backtick ``text`` fenced block — a
path-manifest surface — still errors regardless of nearby sentinel
text. The sentinel is narrow by design: it does not suppress any
other error class.

See:
  - ``docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`` for the
    operating protocol.
  - ``docs/operations/NO_COPY_PASTE_PATTERN.md`` §i for the
    ``__init__.py`` regression class.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "path_manifest_fidelity"
CONTRACT = "docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md"

# Documents we scan: handoffs, recommended prompts, envelopes, and any
# file that declares the manifest-fidelity contract by including a
# `*_PATHS_COUNT=` line.
DOCUMENT_SUFFIXES: frozenset[str] = frozenset({".md"})

SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        "__pycache__",
        "wheelhouse",
        "wheelhouse-dev",
        ".egg-info",
        ".mypy_cache",
        ".pytest_cache",
        ".git",
        "node_modules",
    }
)

COUNT_PATTERN = re.compile(r"^(?P<name>[A-Z][A-Z0-9_]*)_PATHS_COUNT=(?P<value>\d+)\s*$", re.MULTILINE)
HASH_PATTERN = re.compile(r"^(?P<name>[A-Z][A-Z0-9_]*)_PATHS_SHA256=(?P<value>[0-9a-f]{64})\s*$", re.MULTILINE)
FENCE_OPEN = "```text\n"
FENCE_CLOSE = "```"

# Matches the corrupted-paste regression: any path segment ending in
# `/checks/init.py` (preceded by a non-underscore character so we do
# not match the well-formed `__init__.py`).
INIT_PY_CORRUPTION_PATTERN = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z0-9_./-]+/checks/init\.py)(?![A-Za-z0-9_])")

# Same-line HTML sentinel that opts a corrupted token out of the
# init-py-corruption check when (and only when) the token appears in
# free-text prose outside any ```text``` fenced block.
PEDAGOGICAL_SENTINEL = "<!-- path_manifest_fidelity: pedagogical -->"


@dataclass(frozen=True)
class Declaration:
    name: str
    count: int
    sha256: str
    count_line: int
    hash_line: int


def _normalize_manifest(lines: list[str]) -> tuple[int, str, str]:
    """Normalize a manifest. Returns (count, sha256, normalized_text)."""
    unique_sorted = sorted({line for line in lines if line})
    normalized = "\n".join(unique_sorted) + "\n"
    return len(unique_sorted), hashlib.sha256(normalized.encode("utf-8")).hexdigest(), normalized


def _line_of_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _fenced_text_ranges(text: str) -> list[tuple[int, int]]:
    """Return inclusive-exclusive byte ranges for every triple-backtick ``text`` fenced block.

    Each range covers the bytes between the opening fence line and the next
    closing fence marker.
    """
    ranges: list[tuple[int, int]] = []
    idx = 0
    while True:
        open_idx = text.find(FENCE_OPEN, idx)
        if open_idx == -1:
            break
        start = open_idx + len(FENCE_OPEN)
        close_idx = text.find(FENCE_CLOSE, start)
        if close_idx == -1:
            break
        ranges.append((start, close_idx))
        idx = close_idx + len(FENCE_CLOSE)
    return ranges


def _offset_is_in_fenced_text(offset: int, ranges: list[tuple[int, int]]) -> bool:
    for start, end in ranges:
        if start <= offset < end:
            return True
    return False


def _line_containing_offset(text: str, offset: int) -> str:
    line_start = text.rfind("\n", 0, offset) + 1
    line_end = text.find("\n", offset)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end]


def _find_first_fence_after(text: str, offset: int) -> tuple[int, int] | None:
    """Return (start, end) byte offsets of the first ```text fenced block after `offset`.

    `start` is the offset of the first character INSIDE the fence; `end`
    is the offset of the closing fence marker.
    """
    fence_idx = text.find(FENCE_OPEN, offset)
    if fence_idx == -1:
        return None
    start = fence_idx + len(FENCE_OPEN)
    close_idx = text.find(FENCE_CLOSE, start)
    if close_idx == -1:
        return None
    return start, close_idx


def _iter_documents(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for root in paths:
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
        else:
            candidates = []
            for candidate in sorted(root.rglob("*")):
                if any(part in SKIP_DIR_NAMES for part in candidate.parts):
                    continue
                if candidate.is_file():
                    candidates.append(candidate)
        for candidate in candidates:
            if candidate.suffix.lower() not in DOCUMENT_SUFFIXES:
                continue
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def _document_declares_manifest(text: str) -> bool:
    return COUNT_PATTERN.search(text) is not None or HASH_PATTERN.search(text) is not None


def scan_document(text: str, path: str | Path) -> list[ValidationError]:
    """Scan a single document. Returns a list of ValidationError, empty on success."""
    errors: list[ValidationError] = []
    path_str = str(path)

    # Scan for `<package>/checks/init.py` corruption anywhere in the document.
    # Free-text matches may be suppressed by the same-line pedagogical
    # sentinel; matches inside a ```text fenced block — a path-manifest
    # surface — are never suppressed.
    fenced_ranges = _fenced_text_ranges(text)
    for match in INIT_PY_CORRUPTION_PATTERN.finditer(text):
        in_fence = _offset_is_in_fenced_text(match.start(), fenced_ranges)
        if not in_fence and PEDAGOGICAL_SENTINEL in _line_containing_offset(text, match.start()):
            continue
        line = _line_of_offset(text, match.start())
        errors.append(
            make_error(
                "path_manifest_init_py_corruption",
                path_str,
                f"L{line}",
                (
                    f"corrupted path '{match.group(1)}' appears in document — "
                    "expected '__init__.py' (R-012 paste-pipeline regression)"
                ),
                CONTRACT,
            )
        )

    declarations = list(COUNT_PATTERN.finditer(text))
    hashes = {h.group("name"): h for h in HASH_PATTERN.finditer(text)}

    if not declarations and not hashes:
        return errors

    # For each COUNT declaration, require a matching SHA256 and a fenced block.
    for count_match in declarations:
        name = count_match.group("name")
        try:
            declared_count = int(count_match.group("value"))
        except ValueError:
            declared_count = -1
        count_line = _line_of_offset(text, count_match.start())
        hash_match = hashes.get(name)
        if hash_match is None:
            errors.append(
                make_error(
                    "path_manifest_missing_declaration",
                    path_str,
                    f"L{count_line}",
                    f"{name}_PATHS_COUNT declared but no matching {name}_PATHS_SHA256 line found",
                    CONTRACT,
                )
            )
            continue
        declared_hash = hash_match.group("value")
        hash_line = _line_of_offset(text, hash_match.start())

        # Find the first fenced ```text block following the LATER of the two declarations.
        search_from = max(count_match.end(), hash_match.end())
        fence = _find_first_fence_after(text, search_from)
        if fence is None:
            errors.append(
                make_error(
                    "path_manifest_missing_block",
                    path_str,
                    f"L{hash_line}",
                    f"{name}_PATHS_SHA256 declared but no fenced ```text manifest block follows",
                    CONTRACT,
                )
            )
            continue

        body = text[fence[0] : fence[1]]
        # Remove a trailing newline produced by the closing fence indentation.
        if body.endswith("\n"):
            body = body[:-1]
        raw_lines = body.split("\n")
        normalized_lines = [line for line in raw_lines if line]
        actual_count, actual_hash, _ = _normalize_manifest(normalized_lines)
        block_line = _line_of_offset(text, fence[0])

        if actual_count != declared_count:
            errors.append(
                make_error(
                    "path_manifest_count_mismatch",
                    path_str,
                    f"L{count_line}",
                    (
                        f"{name}_PATHS_COUNT declared {declared_count} but fenced manifest "
                        f"at L{block_line} normalizes to {actual_count} unique path lines"
                    ),
                    CONTRACT,
                )
            )
        if actual_hash != declared_hash:
            errors.append(
                make_error(
                    "path_manifest_hash_mismatch",
                    path_str,
                    f"L{hash_line}",
                    (
                        f"{name}_PATHS_SHA256 declared {declared_hash} but recomputed SHA256 "
                        f"of normalized manifest at L{block_line} is {actual_hash}"
                    ),
                    CONTRACT,
                )
            )

    # Any HASH without a matching COUNT is also a missing-declaration error.
    declared_count_names = {m.group("name") for m in declarations}
    for name, hash_match in hashes.items():
        if name in declared_count_names:
            continue
        hash_line = _line_of_offset(text, hash_match.start())
        errors.append(
            make_error(
                "path_manifest_missing_declaration",
                path_str,
                f"L{hash_line}",
                f"{name}_PATHS_SHA256 declared but no matching {name}_PATHS_COUNT line found",
                CONTRACT,
            )
        )

    return errors


def extract_manifest_paths(text: str) -> list[str]:
    """Return the normalized path lines from the first fenced ``text`` manifest
    block following a ``*_PATHS_COUNT=`` / ``*_PATHS_SHA256=`` declaration.

    This reuses the exact fence-location logic ``scan_document`` uses for
    fidelity verification, so the in-band hook bridge (CC-G-B) and the
    post-hoc fidelity check never disagree about which path lines the
    ratified manifest contains. Returns ``[]`` when the document declares no
    manifest or the fenced block is absent.
    """
    declarations = list(COUNT_PATTERN.finditer(text))
    hashes = {h.group("name"): h for h in HASH_PATTERN.finditer(text)}
    for count_match in declarations:
        name = count_match.group("name")
        hash_match = hashes.get(name)
        search_from = (
            count_match.end() if hash_match is None else max(count_match.end(), hash_match.end())
        )
        fence = _find_first_fence_after(text, search_from)
        if fence is None:
            continue
        body = text[fence[0] : fence[1]]
        if body.endswith("\n"):
            body = body[:-1]
        return [line.strip() for line in body.split("\n") if line.strip()]
    return []


def extract_manifest_paths_from_file(path: Path) -> list[str]:
    """Read ``path`` and return its declared manifest path lines (or [])."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return extract_manifest_paths(text)


# --------------------------------------------------------------------------
# Structured carrier identity (F6 Phase-0) — reuse, never loose string-match
# --------------------------------------------------------------------------
#
# The F6 base-only re-stamp must prove the carrier's PATH-SET + content pins
# are unchanged across base motion while ALLOWING mechanical base/head/restamp
# prose to differ (`ce-base-only-refresh-microauth`). Raw carrier byte equality
# is therefore too strict. This exposes the SAME fenced-manifest parsing
# `scan_document`/`extract_manifest_paths` already use as a structured identity
# so the re-stamp proof and the post-hoc fidelity check never disagree about
# which path lines (and which normalized hash) the carrier authorizes.


@dataclass(frozen=True)
class CarrierIdentity:
    """The structured, value-free identity of a per-PR carrier's path-set.

    ``declared_count`` / ``declared_sha256`` are the carrier's own
    ``*_PATHS_COUNT`` / ``*_PATHS_SHA256`` declarations; ``paths`` is the
    normalized (stripped, unique, sorted) fenced path-set; ``normalized_sha256``
    is recomputed over that set by the canonical rule
    (``sha256("\\n".join(sorted(unique)) + "\\n")``); ``consistent`` is True iff
    the declared count/hash match the recomputed normalization (a self-honest
    carrier). Carries only paths + hashes — never a secret.
    """

    name: str
    declared_count: int
    declared_sha256: str
    paths: tuple[str, ...]
    normalized_sha256: str
    consistent: bool


def parse_carrier(text: str) -> CarrierIdentity | None:
    """Return the structured :class:`CarrierIdentity` for a carrier document, or None.

    Reuses ``COUNT_PATTERN`` / ``HASH_PATTERN`` and the fenced-block locator the
    fidelity check uses, then recomputes the normalized path-set hash with
    ``_normalize_manifest`` — so a base-only re-stamp can compare carrier
    path-set identity (count + normalized hash) WITHOUT depending on byte
    equality of the mechanical base/head prose. Returns None when the document
    declares no ``*_PATHS_COUNT`` block.
    """
    declarations = list(COUNT_PATTERN.finditer(text))
    hashes = {h.group("name"): h for h in HASH_PATTERN.finditer(text)}
    for count_match in declarations:
        name = count_match.group("name")
        hash_match = hashes.get(name)
        if hash_match is None:
            continue
        try:
            declared_count = int(count_match.group("value"))
        except ValueError:
            continue
        declared_hash = hash_match.group("value")
        search_from = max(count_match.end(), hash_match.end())
        fence = _find_first_fence_after(text, search_from)
        if fence is None:
            continue
        body = text[fence[0] : fence[1]]
        if body.endswith("\n"):
            body = body[:-1]
        path_lines = [line.strip() for line in body.split("\n") if line.strip()]
        actual_count, actual_hash, _ = _normalize_manifest(path_lines)
        unique_sorted = tuple(sorted(set(path_lines)))
        return CarrierIdentity(
            name=name,
            declared_count=declared_count,
            declared_sha256=declared_hash,
            paths=unique_sorted,
            normalized_sha256=actual_hash,
            consistent=(actual_count == declared_count and actual_hash == declared_hash),
        )
    return None


def parse_carrier_file(path: str | Path) -> CarrierIdentity | None:
    """Read ``path`` and return its structured :class:`CarrierIdentity` (or None)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return parse_carrier(text)


# --------------------------------------------------------------------------
# PR-diff gate (verify-path-manifest --base) — G-ii
# --------------------------------------------------------------------------
#
# The author-time PreToolUse manifest enforcement is advisory post-G-i; the
# real scope-containment mechanism is this PR-diff gate. It compares the set of
# paths changed between ``<base>..HEAD`` to the ratified manifest path-set
# carried in a PR-committed manifest document, flagging any path in the diff
# but not the manifest (diff∖manifest) and any manifest path not in the diff
# (manifest∖diff). When no manifest is supplied the gate is NEUTRAL (a pass with
# a note) — this is transition-safe and NOT yet a hard-required check.
#
# The git helper mirrors ``role_boundary_attribution`` so the two diff gates
# share one shape and never disagree about how ``<base>..HEAD`` is computed.

DIFF_GATE_CONTRACT = CONTRACT

# Per-PR carrier migration (ce-ops#21). Every gate PR carries its ratified closed
# manifest as its OWN file ``<MANIFEST_DIR>/<branch_slug(branch)>.md`` (self-inclusive),
# replacing the single shared ``LEGACY_CARRIER_PATH`` that every PR used to rewrite. The
# directory admits ONLY carriers — no README/index — so discovery needs no exclusion list.
MANIFEST_DIR = ".ce/pr-manifests"
LEGACY_CARRIER_PATH = ".ce/pr-path-manifest.md"

# The repo's canonical id shape — the literal pattern at ``schemas/scope.schema.yaml:58``
# (and ``schemas/completion-report.schema.yaml``, ``schemas/dispatch-record.schema.yaml``):
# a lowercase slug, leading ``[a-z]``, total length 3..64. ``branch_slug`` outputs into
# this exact shape so a carrier stem can later be embedded in a schema-constrained id
# without a shape defect.
SLUG_PATTERN = re.compile(r"[a-z][a-z0-9-]{2,63}")


def branch_slug(branch: str) -> str:
    """Map a git branch name to its per-PR carrier filename stem.

    The output is constrained to the canonical id shape ``^[a-z][a-z0-9-]{2,63}$``
    (``schemas/scope.schema.yaml:58``). Steps, in order:

    1. lowercase-normalize FIRST (esc-14-L7: an uppercase UTC stamp violated the pattern);
    2. collapse every run of non-``[a-z0-9]`` (``/``, ``_``, ``.``, unicode, …) to one ``-``
       and strip leading/trailing ``-``;
    3. guarantee a leading ``[a-z]`` (prefix ``br-`` when the head is a digit or empty);
    4. derive an 8-hex disambiguator from the ORIGINAL branch bytes;
    5. fit the 64-char ceiling (esc-14-L7: a derived id overflowed 64) by truncating to
       55 chars + ``-`` + the hash;
    6. fit the 3-char floor by appending the hash;
    7. fail-closed if any case escapes the canonical shape.
    """
    s = branch.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if not s or not ("a" <= s[0] <= "z"):
        s = ("br-" + s).rstrip("-")
    h = hashlib.sha256(branch.encode("utf-8")).hexdigest()[:8]
    if len(s) > 64:
        s = s[:55].rstrip("-") + "-" + h
    if len(s) < 3:
        s = (s + "-" if s else "br-") + h
    assert SLUG_PATTERN.fullmatch(s), f"branch_slug produced non-canonical id {s!r}"
    return s


def _carrier_stem(carrier_path: str) -> str:
    """Filename stem of a carrier path (the trailing ``.md`` removed, if present)."""
    name = Path(carrier_path).name
    return name[:-3] if name.endswith(".md") else name


def _run_git(args: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command, returning (returncode, stdout, stderr). Never raises."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30, check=False
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout, result.stderr


def _repo_root_for(path: Path) -> Path:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() or (candidate / "validators").is_dir():
            return candidate
    return Path.cwd()


def run_with_base(
    paths: Iterable[Path],
    base: str,
    manifest: str | Path | None = None,
    *,
    manifest_dir: str | None = None,
    head_ref: str | None = None,
    require_carrier: bool = False,
) -> CheckResult:
    """``verify-path-manifest --base <commit>`` PR-diff gate — two modes.

    **Per-PR carrier mode** (``manifest_dir`` supplied, ce-ops#21): discover the
    PR's own carrier ``<manifest_dir>/<branch_slug(head_ref)>.md`` from the diff
    and enforce diff == that carrier's path-set. See :func:`_run_with_base_per_pr`.

    **Single-manifest mode** (``manifest`` supplied) / **neutral** (neither
    supplied): compute ``git diff --name-only --find-renames <base>..HEAD`` and compare it to the
    ratified manifest path-set loaded from ``manifest`` (a PR-committed doc carrying
    a fenced ``*_PATHS`` manifest, parsed by ``extract_manifest_paths_from_file``):

    * ``diff∖manifest`` → ``path_manifest_diff_outside_manifest`` (a changed
      path the ratified manifest does not authorize) — the scope-containment
      failure G-ii exists to catch.
    * ``manifest∖diff`` → ``path_manifest_unfulfilled_manifest_path`` (a
      manifest path the diff never touched) — flagged so an under-delivered
      closed manifest is visible.

    NEUTRAL (a passing ``CheckResult`` with no errors) when neither ``manifest``
    nor ``manifest_dir`` is supplied — the transition-safe default.
    """
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    repo_root = _repo_root_for(raw_paths[0])
    errors: list[ValidationError] = []

    if manifest_dir is not None:
        return _run_with_base_per_pr(
            repo_root, base, manifest_dir, head_ref, require_carrier=require_carrier
        )

    if manifest is None:
        # Transition-safe neutral: no PR-carried manifest → nothing to enforce.
        return CheckResult(name=CHECK_NAME, warnings=())

    manifest_paths = set(extract_manifest_paths_from_file(Path(manifest)))
    if not manifest_paths:
        errors.append(
            make_error(
                "path_manifest_diff_no_manifest_paths",
                str(manifest),
                "",
                (
                    "verify-path-manifest --manifest was supplied but the document declares "
                    "no fenced path manifest (no *_PATHS_COUNT/*_PATHS_SHA256 + ```text block)"
                ),
                DIFF_GATE_CONTRACT,
            )
        )
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    returncode, stdout, stderr = _run_git(
        ["diff", "--name-only", "--find-renames", f"{base}..HEAD"], repo_root
    )
    if returncode != 0:
        errors.append(
            make_error(
                "path_manifest_diff_git_failed",
                str(repo_root),
                "",
                f"git diff --name-only --find-renames {base}..HEAD failed: {stderr.strip() or 'unknown error'}",
                DIFF_GATE_CONTRACT,
            )
        )
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    changed = {line.strip() for line in stdout.splitlines() if line.strip()}

    for path in sorted(changed - manifest_paths):
        errors.append(
            make_error(
                "path_manifest_diff_outside_manifest",
                path,
                "",
                (
                    f"changed file '{path}' is not present in the ratified PR path manifest "
                    f"'{manifest}'; the PR diff exceeds its closed manifest"
                ),
                DIFF_GATE_CONTRACT,
            )
        )
    for path in sorted(manifest_paths - changed):
        errors.append(
            make_error(
                "path_manifest_unfulfilled_manifest_path",
                path,
                "",
                (
                    f"manifest path '{path}' in '{manifest}' was not changed in {base}..HEAD; "
                    "the PR under-delivers its closed manifest"
                ),
                DIFF_GATE_CONTRACT,
            )
        )

    return CheckResult(name=CHECK_NAME, errors=tuple(errors))


def _run_with_base_per_pr(
    repo_root: Path,
    base: str,
    manifest_dir: str,
    head_ref: str | None,
    *,
    require_carrier: bool = False,
) -> CheckResult:
    """Per-PR carrier mode (ce-ops#21): exactly one ADDED carrier per PR.

    Classify the non-deleted ``git diff --name-status <base>..HEAD`` paths under
    ``manifest_dir``; D-status carrier paths are housekeeping deletions and are
    not counted as new carrier claims.

    * **zero** carriers → NEUTRAL pass unless ``require_carrier`` is enabled;
    * **zero** carriers with ``require_carrier`` → ``path_manifest_carrier_required``;
    * **two or more** → ``path_manifest_multiple_carriers`` (each carrier reported);
    * **one**, stem ≠ ``branch_slug(head_ref)`` → ``path_manifest_carrier_slug_mismatch``;
    * **one**, status M/D on the matching slug → ``path_manifest_carrier_not_added``
      (a merged carrier is an immutable ledger entry; in-flight re-pins keep status A
      because the file does not exist on base until merge);
    * **one**, status A, slug matches → ACTIVE: enforce diff == the carrier's declared
      path-set (the existing ``diff∖manifest`` / ``manifest∖diff`` error classes).

    Independently, the retired shared carrier ``LEGACY_CARRIER_PATH`` may only be
    DELETED (status D — this is what lets the #21 migration PR pass); status A or M →
    ``path_manifest_legacy_carrier_path`` (resurrection denied forever).
    """
    errors: list[ValidationError] = []

    if not (head_ref or "").strip():
        errors.append(
            make_error(
                "path_manifest_carrier_head_ref_required",
                manifest_dir,
                "",
                "per-PR carrier mode requires --head-ref to resolve the expected carrier slug",
                DIFF_GATE_CONTRACT,
            )
        )
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    returncode, stdout, stderr = _run_git(
        ["diff", "--name-status", "--find-renames", f"{base}..HEAD"], repo_root
    )
    if returncode != 0:
        errors.append(
            make_error(
                "path_manifest_diff_git_failed",
                str(repo_root),
                "",
                f"git diff --name-status {base}..HEAD failed: {stderr.strip() or 'unknown error'}",
                DIFF_GATE_CONTRACT,
            )
        )
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    status_by_path: dict[str, str] = {}
    changed: set[str] = set()
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0].strip()[:1].upper()
        path = parts[-1].strip()
        status_by_path[path] = status
        changed.add(path)

    # Legacy shared carrier: deletion is the migration; re-add/modify is denied forever.
    legacy_status = status_by_path.get(LEGACY_CARRIER_PATH)
    if legacy_status is not None and legacy_status != "D":
        errors.append(
            make_error(
                "path_manifest_legacy_carrier_path",
                LEGACY_CARRIER_PATH,
                "",
                (
                    f"the retired shared carrier '{LEGACY_CARRIER_PATH}' may only be DELETED "
                    f"(status D), never added or modified (status {legacy_status}); per-PR "
                    f"carriers live under '{manifest_dir}/'"
                ),
                DIFF_GATE_CONTRACT,
            )
        )

    expected_stem = branch_slug(head_ref)
    changelog_path = f".ce/changelog/{expected_stem}.md"
    if require_carrier and status_by_path.get(changelog_path) != "A":
        status = status_by_path.get(changelog_path)
        errors.append(
            make_error(
                "path_manifest_changelog_required",
                changelog_path,
                "",
                (
                    f"CI required-mode expects an ADDED changelog fragment at "
                    f"'{changelog_path}' (status A); got status {status or 'missing'}"
                ),
                DIFF_GATE_CONTRACT,
            )
        )

    prefix = manifest_dir.rstrip("/") + "/"
    carrier_paths = sorted(
        p for p in changed if p.startswith(prefix) and status_by_path.get(p, "") != "D"
    )

    if not carrier_paths:
        if require_carrier:
            expected_carrier = f"{prefix}{expected_stem}.md"
            errors.append(
                make_error(
                    # Contained-seat preflight matches this exact code as a singleton bypass;
                    # change both ends together, and format drift fails closed.
                    "path_manifest_carrier_required",
                    expected_carrier,
                    "",
                    (
                        f"CI required-mode expects an ADDED per-PR carrier at "
                        f"'{expected_carrier}' for head ref {head_ref!r}; none was present "
                        f"under '{manifest_dir}/' in {base}..HEAD"
                    ),
                    DIFF_GATE_CONTRACT,
                )
            )
        if errors:
            return CheckResult(name=CHECK_NAME, errors=tuple(errors))
        return CheckResult(name=CHECK_NAME, warnings=())

    if len(carrier_paths) > 1:
        joined = ", ".join(carrier_paths)
        for cp in carrier_paths:
            errors.append(
                make_error(
                    "path_manifest_multiple_carriers",
                    cp,
                    "",
                    (
                        f"more than one per-PR carrier in the diff under '{manifest_dir}/' "
                        f"({joined}); exactly one carrier per PR"
                    ),
                    DIFF_GATE_CONTRACT,
                )
            )
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    carrier = carrier_paths[0]
    actual_stem = _carrier_stem(carrier)
    if actual_stem != expected_stem:
        errors.append(
            make_error(
                "path_manifest_carrier_slug_mismatch",
                carrier,
                "",
                (
                    f"carrier filename stem '{actual_stem}' does not match the head ref's "
                    f"slug '{expected_stem}' (branch_slug({head_ref!r}))"
                ),
                DIFF_GATE_CONTRACT,
            )
        )
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    carrier_status = status_by_path.get(carrier, "")
    if carrier_status != "A":
        errors.append(
            make_error(
                "path_manifest_carrier_not_added",
                carrier,
                "",
                (
                    f"per-PR carrier '{carrier}' must be ADDED by this PR (status A); got "
                    f"status {carrier_status or '?'} — merged carriers are immutable ledger entries"
                ),
                DIFF_GATE_CONTRACT,
            )
        )
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    # ACTIVE: enforce diff == the carrier's own declared path-set (it self-lists).
    manifest_paths = set(extract_manifest_paths_from_file(repo_root / carrier))
    if not manifest_paths:
        errors.append(
            make_error(
                "path_manifest_diff_no_manifest_paths",
                carrier,
                "",
                (
                    "the per-PR carrier declares no fenced path manifest "
                    "(no *_PATHS_COUNT/*_PATHS_SHA256 + ```text block)"
                ),
                DIFF_GATE_CONTRACT,
            )
        )
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    for path in sorted(changed - manifest_paths):
        errors.append(
            make_error(
                "path_manifest_diff_outside_manifest",
                path,
                "",
                (
                    f"changed file '{path}' is not present in the per-PR carrier '{carrier}'; "
                    "the PR diff exceeds its closed manifest"
                ),
                DIFF_GATE_CONTRACT,
            )
        )
    for path in sorted(manifest_paths - changed):
        errors.append(
            make_error(
                "path_manifest_unfulfilled_manifest_path",
                path,
                "",
                (
                    f"manifest path '{path}' in '{carrier}' was not changed in {base}..HEAD; "
                    "the PR under-delivers its closed manifest"
                ),
                DIFF_GATE_CONTRACT,
            )
        )
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))


@register(CHECK_NAME, ["R-012", "WH-001"])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for doc in _iter_documents([Path(p) for p in paths] or [Path(".")]):
        try:
            text = doc.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not _document_declares_manifest(text):
            # Still scan for init.py corruption in free text, because the
            # regression can appear in any document that names paths.
            corruption_errors = [
                err for err in scan_document(text, doc) if err.code == "path_manifest_init_py_corruption"
            ]
            errors.extend(corruption_errors)
            continue
        errors.extend(scan_document(text, doc))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
