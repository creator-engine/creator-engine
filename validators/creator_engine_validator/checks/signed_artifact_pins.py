"""PR-diff guard for files hash-pinned by signed artifacts."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import yaml

from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .git_helpers import repo_root_for, run_git

CHECK_NAME = "signed_artifact_pins"
CONTRACT = "docs/llms-install.md signed artifact hash-pin policy"
SIGNED_ARTIFACT = Path("docs/llms-install.md")

CODE_MISSING_PIN_UPDATE = "VAL-SIGNED-ARTIFACT-PIN-MISSING"
CODE_INVALID = "VAL-SIGNED-ARTIFACT-PINS-INVALID"
CODE_NOTICE = "VAL-SIGNED-ARTIFACT-RESIGN-REQUIRED"

PIN_LINE_RE = re.compile(r"^\s*(?P<key>[A-Za-z0-9_]+_sha256)\s*:\s*(?P<value>[0-9a-fA-F]{64})\s*$")
DIFF_PIN_LINE_RE = re.compile(r"^[+-]\s*(?P<key>[A-Za-z0-9_]+_sha256)\s*:")

PIN_KEY_SOURCE_ALIASES: dict[str, tuple[str, ...]] = {
    "answers_schema_sha256": (
        "validators/creator_engine_validator/schemas/install-answers.schema.yaml",
    ),
    # sha256s_sha256 pins the whole SHA256SUMS file, which is itself the
    # release-op hash manifest for install.sh (both the repo-root script and
    # its published docs/ mirror). A diff touching either byte-for-byte copy
    # without a matching SHA256SUMS/pin-line change must be caught by the
    # same guard that protects the wheelhouse copy.
    "sha256s_sha256": (
        "validators/wheelhouse/SHA256SUMS",
        "install.sh",
        "docs/install.sh",
    ),
}


class SignedArtifactCorruption(ValueError):
    """Raised when the signed artifact's frontmatter cannot be trusted.

    The guard must fail CLOSED on this condition: a signed doc that exists
    but whose protection cannot be established (corrupt YAML, missing
    artifact manifest, or zero discoverable pins) must never be silently
    treated as "nothing to protect".
    """


@dataclass(frozen=True)
class ArtifactPin:
    key: str
    artifact_path: str
    line: int
    protected_paths: tuple[str, ...]


def _normalize_repo_path(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/").strip("/")).as_posix()


def _extract_signed_yaml(text: str) -> dict[str, object]:
    start = text.find("<!--")
    end = text.find("-->", start + 4)
    if start == -1 or end == -1:
        raise SignedArtifactCorruption(
            f"{SIGNED_ARTIFACT.as_posix()} has no HTML-comment frontmatter block "
            "(no '<!--' ... '-->' found); the signed-artifact hash-pin guard "
            "cannot establish protection and is failing closed"
        )
    try:
        parsed = yaml.safe_load(text[start + 4:end])
    except yaml.YAMLError as exc:
        raise SignedArtifactCorruption(
            f"{SIGNED_ARTIFACT.as_posix()} frontmatter is not valid YAML ({exc}); "
            "the signed-artifact hash-pin guard cannot establish protection and "
            "is failing closed"
        ) from exc
    if not isinstance(parsed, dict):
        raise SignedArtifactCorruption(
            f"{SIGNED_ARTIFACT.as_posix()} frontmatter did not parse to a mapping; "
            "the signed-artifact hash-pin guard cannot establish protection and "
            "is failing closed"
        )
    return parsed


def _repo_paths_for_url(url: object) -> tuple[str, ...]:
    if not isinstance(url, str) or not url.strip():
        return ()
    parsed = urlparse(url)
    url_path = parsed.path.lstrip("/")
    if not url_path:
        return ()
    return (_normalize_repo_path(f"docs/{url_path}"),)


def _artifact_manifest(data: dict[str, object]) -> dict[str, object]:
    if "artifact_manifest" not in data:
        raise SignedArtifactCorruption(
            f"{SIGNED_ARTIFACT.as_posix()} frontmatter has no 'artifact_manifest' "
            "section; the signed-artifact hash-pin guard cannot establish "
            "protection and is failing closed"
        )
    manifest = data["artifact_manifest"]
    if not isinstance(manifest, dict):
        raise SignedArtifactCorruption(
            f"{SIGNED_ARTIFACT.as_posix()} frontmatter 'artifact_manifest' section "
            "is not a mapping; the signed-artifact hash-pin guard cannot establish "
            "protection and is failing closed"
        )
    return manifest


def _protected_paths_for_key(key: str, manifest: dict[str, object]) -> tuple[str, ...]:
    paths: list[str] = []
    url_key = f"{key[:-len('_sha256')]}_url"
    paths.extend(_repo_paths_for_url(manifest.get(url_key)))
    paths.extend(PIN_KEY_SOURCE_ALIASES.get(key, ()))
    return tuple(sorted(set(paths)))


def discover_pins(text: str, *, artifact_path: str = SIGNED_ARTIFACT.as_posix()) -> tuple[ArtifactPin, ...]:
    """Return signed-artifact ``*_sha256`` pins with best-effort repo path mappings.

    Raises ``SignedArtifactCorruption`` (fail-closed) if the frontmatter
    cannot be parsed, the artifact manifest section is missing/malformed, or
    zero pins are discoverable in the document — any of these means the
    guard's protection has silently degraded to zero and must be reported
    loudly rather than treated as "nothing to check".
    """
    data = _extract_signed_yaml(text)
    manifest = _artifact_manifest(data)
    pins: list[ArtifactPin] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = PIN_LINE_RE.match(line)
        if not match:
            continue
        key = match.group("key")
        pins.append(
            ArtifactPin(
                key=key,
                artifact_path=artifact_path,
                line=line_number,
                protected_paths=_protected_paths_for_key(key, manifest),
            )
        )
    if not pins:
        raise SignedArtifactCorruption(
            f"{artifact_path} yielded zero *_sha256 pins; the signed-artifact "
            "hash-pin guard cannot establish protection and is failing closed"
        )
    return tuple(pins)


def changed_pin_keys_from_diff(diff_text: str) -> frozenset[str]:
    keys: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith(("+++", "---")):
            continue
        match = DIFF_PIN_LINE_RE.match(line)
        if match:
            keys.add(match.group("key"))
    return frozenset(keys)


def parse_name_status_paths(name_status: str) -> frozenset[str]:
    paths: set[str] = set()
    for line in name_status.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if status.startswith(("R", "C")) and len(parts) >= 3:
            paths.add(_normalize_repo_path(parts[1]))
            paths.add(_normalize_repo_path(parts[2]))
        elif len(parts) >= 2:
            paths.add(_normalize_repo_path(parts[1]))
    return frozenset(paths)


def evaluate_pins(
    pins: Sequence[ArtifactPin],
    *,
    changed_paths: Iterable[str],
    changed_pin_keys: Iterable[str],
) -> CheckResult:
    changed = frozenset(_normalize_repo_path(path) for path in changed_paths)
    changed_keys = frozenset(changed_pin_keys)
    errors: list[ValidationError] = []
    notices: list[ValidationError] = []
    noticed_keys: set[str] = set()

    for pin in pins:
        touched = sorted(path for path in pin.protected_paths if path in changed)
        pin_changed = pin.key in changed_keys
        if touched and not pin_changed:
            for path in touched:
                errors.append(
                    make_error(
                        CODE_MISSING_PIN_UPDATE,
                        path,
                        "",
                        f"{path} is hash-pinned by {pin.artifact_path}:{pin.line} "
                        f"({pin.key}); touching it without updating that pin is "
                        "release-class work requiring the release-op/spec-signing procedure",
                        CONTRACT,
                    )
                )
        elif touched and pin_changed:
            notices.append(
                make_error(
                    CODE_NOTICE,
                    pin.artifact_path,
                    pin.key,
                    "NOTICE: signed artifact pin and pinned file changed together; "
                    "a signed-artifact re-sign is required before release",
                    CONTRACT,
                )
            )
            noticed_keys.add(pin.key)

    if SIGNED_ARTIFACT.as_posix() in changed:
        pins_by_key = {pin.key: pin for pin in pins}
        known_keys = set(pins_by_key)
        for key in sorted(changed_keys & known_keys - noticed_keys):
            # A pin with no protected paths doesn't map to any specific
            # pinned file — it self-references the whole signed document
            # (e.g. content_sha256). The generic "missing pinned-file
            # change" wording is misleading there: any doc edit trips it,
            # even though there is no separate file to have changed.
            if not pins_by_key[key].protected_paths:
                notices.append(
                    make_error(
                        CODE_NOTICE,
                        SIGNED_ARTIFACT,
                        key,
                        "NOTICE: whole-document content pin changed; a full "
                        "signed-artifact re-sign is required before release "
                        "(this is a whole-document re-sign, not a missing "
                        "pinned-file update)",
                        CONTRACT,
                    )
                )
                continue
            notices.append(
                make_error(
                    CODE_NOTICE,
                    SIGNED_ARTIFACT,
                    key,
                    "NOTICE: signed artifact hash pin changed without a matching pinned-file "
                    "change in this diff; a signed-artifact re-sign is required before release",
                    CONTRACT,
                )
            )

    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(notices))


@register(CHECK_NAME, [CODE_MISSING_PIN_UPDATE, CODE_INVALID, CODE_NOTICE])
def run(paths: Iterable[Path]) -> CheckResult:
    return CheckResult(name=CHECK_NAME)


def run_with_base(paths: Iterable[Path], base: str) -> CheckResult:
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    repo_root = repo_root_for(raw_paths[0])
    artifact = repo_root / SIGNED_ARTIFACT
    try:
        text = artifact.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return CheckResult(
            name=CHECK_NAME,
            errors=(
                make_error(
                    CODE_INVALID,
                    SIGNED_ARTIFACT,
                    "",
                    f"could not read signed artifact: {exc}",
                    CONTRACT,
                ),
            ),
        )

    diff_range = f"{base}..HEAD"
    returncode, stdout, _stderr = run_git(["diff", "--name-status", "--find-renames", diff_range], repo_root)
    if returncode != 0:
        return CheckResult(
            name=CHECK_NAME,
            errors=(make_error(CODE_INVALID, "PR_DIFF", "", "git diff name-status failed", CONTRACT),),
        )
    changed_paths = parse_name_status_paths(stdout)

    returncode, doc_diff, _stderr = run_git(
        ["diff", "--unified=0", diff_range, "--", SIGNED_ARTIFACT.as_posix()],
        repo_root,
    )
    if returncode != 0:
        return CheckResult(
            name=CHECK_NAME,
            errors=(make_error(CODE_INVALID, "PR_DIFF", "", "git diff signed artifact failed", CONTRACT),),
        )

    try:
        pins = discover_pins(text)
    except SignedArtifactCorruption as exc:
        return CheckResult(
            name=CHECK_NAME,
            errors=(make_error(CODE_INVALID, SIGNED_ARTIFACT, "", str(exc), CONTRACT),),
        )

    return evaluate_pins(
        pins,
        changed_paths=changed_paths,
        changed_pin_keys=changed_pin_keys_from_diff(doc_diff),
    )
